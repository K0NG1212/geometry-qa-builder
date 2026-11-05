"""Instance enumerators: propose every candidate instance a structure offers.

A family's build function already decides whether one instance is admissible (unique answer,
separated options, chain continuity, windows and margins). An enumerator only proposes specs:
every residue, every residue pair, every candidate set built around an admissible answer.
tools/enumerate_instances.py builds the proposals, keeps the ones the family accepts and runs
the independent checkers on them. Enumerators may compute geometry to pre-select promising
proposals (e.g. a pair inside the disulfide windows), but the answer, the options and every
admissibility check are decided by the family's build function and re-verified by the
independent checker; a proposal the family rejects is simply dropped.

Structures come from templates/structures.json (assets already committed with source and licence).
This module lives outside task_families/ on purpose: it writes manifests (which every run snapshots
and hashes) and does not change how any question is built.
"""
import itertools
import json
import math
from pathlib import Path

from task_families import kit
from task_families.local_geometry import read_pdb_residues
from task_families.protein_design import CA_WINDOW, CB_WINDOW, MARGIN, efficiency
from task_families import rotational, chem_names

STRUCTURES = 'templates/structures.json'
ROOT = Path(__file__).resolve().parent
R0_CHOICES = (2.0, 2.5, 3.0, 4.0, 5.0, 6.0)            # nm; stated in the question as a model parameter
TARGETS = (0.25, 0.5, 0.75)                             # FRET design targets
MIN_SPACING = 3                                         # residues apart for any pair
SCOPE = {
    'backbone_torsion': '只含残基 %d–%d 的 ATOM 记录；无替代构象；按 IUPAC 符号约定。',
    'secondary_structure': '只含残基 %d–%d 的 ATOM 记录；参考构象中心为教科书典型值；条目的 HELIX/SHEET 记录作为审核证据，不给考生。',
    'fret_efficiency': '虚拟点探针（R0 为题设值）；不代表真实染料位置、连接臂或取向分布。',
    'disulfide_design': 'ATOM 片段逐行照抄；筛选窗口为题干给出的几何标准；不评估二面角与稳定性。',
    'fret_design': 'ATOM 片段逐行照抄；点偶极、R0 为题设模型参数（取向因子含于 R0）。',
    'molecule': '单一构象（QM7-X 为 DFTB3+MBD 优化几何，SAMPL9 为挑战赛提供的 3D 结构）；坐标原样；成键按共价半径规则。',
    'rotational': '单一构象的刚性转子（QM7-X 为 DFTB3+MBD 优化几何，SAMPL9 为挑战赛提供的 3D 结构）；坐标原样；同位素质量与常数见题干；不含振动平均与离心畸变。',
    'crystal': '常规晶胞按 CIF 全部对称操作展开（task_families/cell.py）；周期晶体；衍射题为运动学模型与原子序数权重。',
}
# Atomic numbers (angle-independent scattering weights stated in the question). The table covers every element
# task_families/cell.py can read, so a crystal is never skipped merely because its element was missing here.
Z = {'H': 1, 'He': 2, 'Li': 3, 'Be': 4, 'B': 5, 'C': 6, 'N': 7, 'O': 8, 'F': 9, 'Ne': 10, 'Na': 11, 'Mg': 12, 'Al': 13,
     'Si': 14, 'P': 15, 'S': 16, 'Cl': 17, 'Ar': 18, 'K': 19, 'Ca': 20, 'Sc': 21, 'Ti': 22, 'V': 23, 'Cr': 24, 'Mn': 25,
     'Fe': 26, 'Co': 27, 'Ni': 28, 'Cu': 29, 'Zn': 30, 'Ga': 31, 'Ge': 32, 'As': 33, 'Se': 34, 'Br': 35, 'Kr': 36,
     'Rb': 37, 'Sr': 38, 'Y': 39, 'Zr': 40, 'Nb': 41, 'Mo': 42, 'Tc': 43, 'Ru': 44, 'Rh': 45, 'Pd': 46, 'Ag': 47,
     'Cd': 48, 'In': 49, 'Sn': 50, 'Sb': 51, 'Te': 52, 'I': 53, 'Xe': 54, 'Cs': 55, 'Ba': 56, 'La': 57, 'Ce': 58,
     'Pr': 59, 'Nd': 60, 'Pm': 61, 'Sm': 62, 'Eu': 63, 'Gd': 64, 'Tb': 65, 'Dy': 66, 'Ho': 67, 'Er': 68, 'Tm': 69,
     'Yb': 70, 'Lu': 71, 'Hf': 72, 'Ta': 73, 'W': 74, 'Re': 75, 'Os': 76, 'Ir': 77, 'Pt': 78, 'Au': 79, 'Hg': 80,
     'Tl': 81, 'Pb': 82, 'Bi': 83, 'Po': 84, 'At': 85, 'Rn': 86, 'Fr': 87, 'Ra': 88, 'Ac': 89, 'Th': 90, 'Pa': 91,
     'U': 92}
LINES = (('Cu', 1.54056), ('Mo', 0.7093), ('Co', 1.78897), ('Cr', 2.2897))


def load_structures(root):
    return json.loads((root / STRUCTURES).read_text(encoding='utf-8'))['structures']


def load_crystals(root):
    return json.loads((root / STRUCTURES).read_text(encoding='utf-8')).get('crystals', [])


def domain_of(spec):
    """Benchmark domain of an enumerated spec, from the structure registries."""
    if spec.get('domain'):
        return spec['domain']
    if spec.get('molecule'):
        return next(m['domain'] for m in load_molecules(ROOT) if m['molecule'] == spec['molecule'])
    if spec.get('assembly'):
        return next(p['domain'] for p in load_assemblies(ROOT) if p['asset'] == spec['asset'])
    if spec.get('cod'):
        return 'materials'
    return 'biology'


def structure_of(spec):
    """Grouping key for sampling and capacity rows: PDB id or COD id."""
    return spec.get('assembly') or spec.get('pdb') or spec.get('cod') or spec.get('molecule')


def residues_of(root, s):
    text = (root / 'docs' / s['asset']).read_text(encoding='utf-8')
    residues, order, altloc = read_pdb_residues(text, s['chain'])
    return residues, [n for n in order if n not in altloc]


def base(s, family, key, scope):
    return dict(id='EN-%s-%s' % (s['pdb'], key), family=family, asset=s['asset'], pdb=s['pdb'], chain=s['chain'],
                context=s['context'], source=s['source'], license=s['license'], scope=scope)


def pick_r0(r, *context):
    """A stated Förster radius with 0.6 <= r/R0 <= 1.6 (efficiencies away from 0 and 1), chosen by hash so that
    r falls on both sides of R0. Always taking the nearest R0 left r < R0 in most proposals, where nearly every
    misconception gives a smaller efficiency and the correct option became the largest one (found by the
    capacity probe, runs/enum-v01). None if no stated value fits."""
    fits = [x for x in R0_CHOICES if 0.6 <= r / x <= 1.6]
    return min(fits, key=lambda x: kit.digest('r0', *context, str(x))) if fits else None


def pairs_by_atom(residues, numbers, atom):
    pts = [(n, residues[n]['atoms'][atom]) for n in numbers if atom in residues[n]['atoms']]
    for a in range(len(pts)):
        for b in range(a + 1, len(pts)):
            (i, p), (j, q) = pts[a], pts[b]
            if j - i >= MIN_SPACING:
                yield i, j, math.dist(p, q) / 10


# ------------------------------------------------------------------ per-residue families
def backbone_torsion(root, s):
    if s['kind'] != 'protein':
        return
    residues, numbers = residues_of(root, s)
    for n in numbers:
        for kind in ('phi', 'psi'):
            yield dict(base(s, 'backbone_torsion', 'TOR-%d-%s' % (n, kind.upper()), SCOPE['backbone_torsion'] % (n - 1, n + 1)),
                       residue=n, torsion=kind)


def secondary_structure(root, s):
    if s['kind'] != 'protein':
        return
    residues, numbers = residues_of(root, s)
    for n in numbers:
        yield dict(base(s, 'secondary_structure', 'SS-%d' % n, SCOPE['secondary_structure'] % (n - 1, n + 1)), residue=n)


# ------------------------------------------------------------------ pair families
def fret_efficiency(root, s):
    residues, numbers = residues_of(root, s)
    atom = 'CA' if s['kind'] == 'protein' else "C1'"
    for i, j, r in pairs_by_atom(residues, numbers, atom):
        fits = [x for x in R0_CHOICES if 0.6 <= r / x <= 1.6]
        # Stated R0 values on both sides of r, so the family can reach every answer rank (see scattering.build_fret).
        if r >= 1.0 and any(x < r for x in fits) and any(x > r for x in fits):   # reasoning scale = r: 1-10 nm cell
            yield dict(base(s, 'fret_efficiency', 'FRET-%d-%d' % (i, j), SCOPE['fret_efficiency']),
                       donor=[i, atom], acceptor=[j, atom], R0_choices=fits, path_atom=atom)


def disulfide_rows(residues, numbers):
    rows = []
    usable = [n for n in numbers if residues[n]['name'] not in ('CYS', 'GLY') and {'CA', 'CB'} <= set(residues[n]['atoms'])]
    for a in range(len(usable)):
        for b in range(a + 1, len(usable)):
            i, j = usable[a], usable[b]
            if j - i < MIN_SPACING:
                continue
            ra, rb = residues[i]['atoms'], residues[j]['atoms']
            dca, dcb = math.dist(ra['CA'], rb['CA']), math.dist(ra['CB'], rb['CB'])
            miss_ca = max(CA_WINDOW[0] - dca, dca - CA_WINDOW[1], 0)
            miss_cb = max(CB_WINDOW[0] - dcb, dcb - CB_WINDOW[1], 0)
            if miss_ca == 0 and miss_cb == 0:
                kind = 'pass'
            elif 0 < max(miss_ca, miss_cb) < MARGIN:
                continue                                      # too close to a window: the family rejects such sets
            elif miss_ca == 0:
                kind = 'calpha_only'
            elif miss_cb == 0:
                kind = 'cbeta_only'
            elif dca <= 9.0:
                kind = 'both_out'                             # plausible neighbours only
            else:
                continue
            rows.append(dict(pair=[i, j], kind=kind))
    return rows


def disulfide_design(root, s):
    """One proposal per admissible pair: the pair plus one distractor of each failure kind where available."""
    if s['kind'] != 'protein':
        return
    residues, numbers = residues_of(root, s)
    rows = disulfide_rows(residues, numbers)
    failing = {k: [r['pair'] for r in rows if r['kind'] == k] for k in ('calpha_only', 'cbeta_only', 'both_out')}
    for good in (r['pair'] for r in rows if r['kind'] == 'pass'):
        picks = []
        for kind in ('calpha_only', 'cbeta_only', 'both_out'):
            pool = sorted(failing[kind], key=lambda p: kit.digest(s['pdb'], str(good), str(p)))
            picks += pool[:1]
        rest = sorted([p for k in failing for p in failing[k] if p not in picks], key=lambda p: kit.digest(s['pdb'], str(good), 'fill', str(p)))
        picks += rest[:3 - len(picks)]
        if len(picks) == 3:
            yield dict(base(s, 'disulfide_design', 'DS-%d-%d' % tuple(good), SCOPE['disulfide_design']), pairs=[good] + picks)


def fret_design(root, s):
    """For each target, each pair whose efficiency is within 0.03 of the target, plus three pairs clearly farther away."""
    residues, numbers = residues_of(root, s)
    atom = 'CA' if s['kind'] == 'protein' else 'P'
    pairs = [(i, j, r) for i, j, r in pairs_by_atom(residues, numbers, atom) if 1.0 <= r < 10]
    for t in TARGETS:
        for i, j, r in pairs:
            r0 = pick_r0(r, s['pdb'], str(t), str(i), str(j))
            if not r0 or abs(efficiency(r, r0) - t) > 0.03:
                continue
            d = abs(efficiency(r, r0) - t)
            far = [(a, b) for a, b, q in pairs if {a, b}.isdisjoint({i, j}) and abs(efficiency(q, r0) - t) >= max(1.5 * d, d + 0.05) + 0.02]
            far.sort(key=lambda p: kit.digest(s['pdb'], str(t), str((i, j)), str(p)))
            if len(far) >= 3:
                spec = dict(base(s, 'fret_design', 'FD-%02d-%d-%d' % (round(t * 100), i, j), SCOPE['fret_design']),
                            atom=atom, r0_nm=r0, target=t, pairs=[[i, j]] + [list(p) for p in far[:3]])
                if s['kind'] == 'nucleic':
                    spec['nucleic'] = True
                yield spec


# ------------------------------------------------------------------ crystal families (COD CIFs)
def crystal_base(c, family, key):
    """CIF crystals use the general reader; the two MOF cells are committed as whole-cell XYZ files (source_kind xyz_cell)."""
    from task_families.cell import read_cif
    if c.get('source_kind') == 'xyz_cell':
        elements = sorted(set(kit.parse_xyz((ROOT / 'docs' / c['asset']).read_text(encoding='utf-8-sig'))[0]))
        extra = dict(source_kind='xyz_cell', a=c['a'])
    else:
        elements = sorted({e for e, _ in read_cif(ROOT / 'docs' / c['asset'])[1]})
        extra = dict(source_kind='cif_general')
    return elements, dict(id='EN-COD%s-%s' % (c['cod'], key), family=family, asset=c['asset'], cod=c['cod'], name=c['name'],
                          source='https://www.crystallography.net/cod/%s.html' % c['cod'], license='COD（公共领域 / CC0）',
                          scope=SCOPE['crystal'], **extra)


def coordination_shell(root, c):
    elements, _ = crystal_base(c, 'coordination_shell', '')
    for centre in elements:
        for partner in elements:
            _, spec = crystal_base(c, 'coordination_shell', 'COORD-%s-%s' % (centre, partner))
            yield dict(spec, centre={'element': centre}, partner={'element': partner}, centre_text='%s atom' % centre,
                       partner_text='%s atoms' % partner)


def first_diffraction_peak(root, c):
    elements, _ = crystal_base(c, 'first_diffraction_peak', '')
    if any(e not in Z for e in elements):
        return
    for line, lam in LINES:
        _, spec = crystal_base(c, 'first_diffraction_peak', 'PEAK-%s' % line)
        yield dict(spec, weights={e: Z[e] for e in elements}, wavelength_A=lam)


def kinematic_extinction(root, c):
    elements, spec = crystal_base(c, 'kinematic_extinction', 'EXT')
    if all(e in Z for e in elements):
        yield dict(spec, weights={e: Z[e] for e in elements})


def diffraction_design(root, c):
    """Inverse of the first peak, cubic cells only (the family's limit). The target angle sits near the answer for one
    line / one crystal, offset by a seeded amount; the family itself rejects sets whose winning margin is too small."""
    from task_families.diffraction_design import crystal_info, two_theta
    elements, spec = crystal_base(c, 'diffraction_design', '')
    if any(e not in Z for e in elements):
        return
    spec = dict(spec, weights={e: Z[e] for e in elements}, short=c['name'].split(' (')[0])
    try:
        info = crystal_info(spec, ROOT)
    except ValueError:
        return                                     # non-cubic or ambiguous first reflection
    d = info['first']['d']
    lines = [['%s Kα1' % n, lam] for n, lam in LINES]
    for name, lam in lines:
        angle = two_theta(d, lam)
        if angle is None or angle > 150:
            continue
        shift = (int.from_bytes(kit.digest(c['cod'], name)[:2], 'big') % 21 - 10) / 10      # -1.0 .. +1.0 degree
        yield dict(spec, id=spec['id'] + 'XD-ANODE-%s' % name.split()[0], mode='anode', lines=lines,
                   target_2theta=round(angle + shift, 1))
    for target in (20.0, 35.0):
        yield dict(spec, id=spec['id'] + 'XD-WAVE-%d' % target, mode='wavelength', target_2theta=target)
    others = [o for o in load_crystals(ROOT) if o['cod'] != c['cod']]
    for name, lam in lines:
        angle = two_theta(d, lam)
        if angle is None or angle > 150:
            continue
        picks = sorted(others, key=lambda o: kit.digest(c['cod'], name, o['cod']))
        cands = [dict(asset=c['asset'], source_kind=spec['source_kind'], name=c['name'], weights=spec['weights'], id='COD' + c['cod'],
                      short=spec['short'], **({'a': c['a']} if c.get('a') else {}))]
        for o in picks:
            if len(cands) == 4:
                break
            oe, os_ = crystal_base(o, 'diffraction_design', '')
            if any(e not in Z for e in oe):
                continue
            cand = dict(asset=o['asset'], source_kind=os_['source_kind'], name=o['name'], weights={e: Z[e] for e in oe}, id='COD' + o['cod'],
                        short=o['name'].split(' (')[0], **({'a': o['a']} if o.get('a') else {}))
            try:
                crystal_info(cand, ROOT)
            except ValueError:
                continue
            cands.append(cand)
        shift = (int.from_bytes(kit.digest(c['cod'], name, 'crystal')[:2], 'big') % 11 - 5) / 10
        yield dict(spec, id=spec['id'] + 'XD-CRYSTAL-%s' % name.split()[0], mode='crystal', wavelength_A=lam,
                   target_2theta=round(angle + shift, 1), candidates=cands)


CRYSTAL_ENUMERATORS = dict(coordination_shell=coordination_shell, first_diffraction_peak=first_diffraction_peak,
                           kinematic_extinction=kinematic_extinction, diffraction_design=diffraction_design)


# ------------------------------------------------------------------ small molecules (QM7-X, SAMPL9)
def load_molecules(root):
    return json.loads((root / STRUCTURES).read_text(encoding='utf-8')).get('molecules', [])


def molecule_graph(m):
    elements, points = kit.parse_xyz((ROOT / 'docs' / m['asset']).read_text(encoding='utf-8-sig'))
    edges = kit.bond_graph(elements, points)
    degree = lambda i: len(kit.neighbors(edges, i))
    return elements, points, edges, degree


def molecule_base(m, family, key):
    return dict(id='EN-%s-%s' % (m['molecule'], key), family=family, asset=m['asset'], molecule=m['molecule'], context=m['context'],
                source=m['source'], license=m['license'], scope=SCOPE['molecule'], charge=m['charge'])


def molecule_names(m):
    elements, points, edges, degree = molecule_graph(m)
    return chem_names.Molecule(elements, points, m['charge'])


def named_bond_distance(root, m):
    """Every covalent bond between two non-hydrogen atoms, described chemically (bond order and the functional-group role
    of both atoms, task_families/chem_names.py). Bonds with an atom the naming rules do not recognise are skipped: the
    advisor asked for named chemical entities, not row pairs (HANDOFF_2026-10-06 section 0.2)."""
    elements, points, edges, degree = molecule_graph(m)
    names = molecule_names(m)
    for i, j in sorted(edges):
        if 'H' in (elements[i], elements[j]) or names.bond(i, j) is None:
            continue
        a, b = '%s%d' % (elements[i], i + 1), '%s%d' % (elements[j], j + 1)
        yield dict(molecule_base(m, 'named_bond_distance', 'BOND-%d-%d' % (i + 1, j + 1)),
                   atoms=[dict(row=i + 1, name=a, element=elements[i]), dict(row=j + 1, name=b, element=elements[j])],
                   bond=names.bond(i, j), strict_rank=True)


def named_bond_angle(root, m):
    """Every angle A–V–B with all three atoms non-hydrogen and both ends bonded to the vertex, described chemically."""
    elements, points, edges, degree = molecule_graph(m)
    names = molecule_names(m)
    for v in range(len(elements)):
        ends = [x for x in kit.neighbors(edges, v) if elements[x] != 'H']
        if elements[v] == 'H':
            continue
        for p in range(len(ends)):
            for q in range(p + 1, len(ends)):
                a, b = sorted((ends[p], ends[q]))
                if names.angle(a, v, b) is None:
                    continue
                labels = ['%s%d' % (elements[k], k + 1) for k in (a, v, b)]
                yield dict(molecule_base(m, 'named_bond_angle', 'ANG-%d-%d-%d' % (a + 1, v + 1, b + 1)),
                           atoms=[dict(row=k + 1, name=n, element=elements[k]) for k, n in zip((a, v, b), labels)],
                           linkage=names.angle(a, v, b))


def extent_choice_v2(root, m):
    """Whole-molecule size: maximum pairwise distance and equal-weight radius of gyration of all supplied atoms."""
    for template, key in (('global_extent', 'DMAX'), ('equal_weight_rg', 'RG')):
        yield dict(molecule_base(m, 'extent_choice_v2', key), template=template)


def rotational_line(root, m):
    """The three J = 1 <- 0 lines of every molecule small enough for the rotational-spectroscopy scope."""
    elements, points, edges, degree = molecule_graph(m)
    if len(elements) > rotational.MAX_ATOMS:
        return
    for key in rotational.LINES:
        yield dict(molecule_base(m, 'rotational_line', 'ROT-%s' % key), line=key, strict_rank=True,
                   scope=SCOPE['rotational'])


def isotopologue_design(root, m):
    """Candidate sets of four hydrogens around each admissible winner. The farthest-from-centre-of-mass hydrogen usually
    gives the largest shift (it does for nearly every 1_01 set), so sets where a farther hydrogen is a distractor are
    proposed for every winner, plus sets where that shortcut would succeed (several fills of the same winner when
    needed), one for every three of the others: the shortcut then works at about chance level, and "never the
    farthest" is no cue either (one such set per molecule and line gave 52 of 524 in the probe runs/enum-v32). Distractors that a real slip would pick (best for another line or for
    one constant) are preferred; the rest are filled in hash order."""
    elements, points, edges, degree = molecule_graph(m)
    if len(elements) > rotational.MAX_ATOMS:
        return
    hydrogens = [i for i, e in enumerate(elements) if e == 'H']
    com = rotational.centre(rotational.masses_of(elements), points)
    far = lambda i: math.dist(points[i], com)
    shifts = {k: rotational.shifts(elements, points, k, hydrogens)[1] for k in rotational.LINES}
    for key in rotational.LINES:
        d = shifts[key]
        winners = []
        for best in sorted(hydrogens, key=lambda i: -abs(d[i])):
            ok = [i for i in hydrogens if i != best and abs(d[best]) >= rotational.DESIGN_RATIO * abs(d[i])
                  and abs(d[best]) - abs(d[i]) >= rotational.DESIGN_MIN_MHZ]
            if len(ok) >= 3:
                winners.append((best, ok, [i for i in ok if far(i) > far(best)]))
        sets = []
        for best, ok, farther in winners:
            if farther:
                sets.append((best, [max(farther, key=far)], ok))
        quota = max(1, len(sets) // 3)
        lucky = [(best, ok) for best, ok, farther in winners if not farther]
        fills = {best: itertools.combinations(sorted(ok, key=lambda i: kit.digest('iso', m['molecule'], key, best, i)), 3)
                 for best, ok in lucky}
        while quota and fills:
            for best, ok in lucky:
                trio = next(fills.get(best, iter(())), None)
                if trio is None:
                    fills.pop(best, None)
                elif quota:
                    sets.append((best, list(trio), ok))
                    quota -= 1
        for best, pick, ok in sets:
            pick = list(pick)
            for k in rotational.LINES[key]['others']:
                rival = max(ok, key=lambda i: abs(shifts[k][i]))
                if rival not in pick and len(pick) < 3:
                    pick.append(rival)
            for i in sorted(ok, key=lambda i: kit.digest('iso', m['molecule'], key, best, i)):
                if len(pick) == 3:
                    break
                if i not in pick:
                    pick.append(i)
            rows = sorted(r + 1 for r in pick + [best])
            yield dict(molecule_base(m, 'isotopologue_design', 'ISO-%s-%s' % (key, '-'.join(map(str, rows)))), line=key,
                       candidates=rows, scope=SCOPE['rotational'])


MOLECULE_ENUMERATORS = dict(named_bond_distance=named_bond_distance, named_bond_angle=named_bond_angle, extent_choice_v2=extent_choice_v2,
                            rotational_line=rotational_line, isotopologue_design=isotopologue_design)


# ------------------------------------------------------------------ large assemblies and scattering
QRG_DEBYE = (1.6, 2.1, 2.6)       # beyond the Guinier range (the family rejects qRg <= 1.3)
QRG_GUINIER = (0.5, 0.9, 1.2)     # inside it
Q_TARGETS = (0.3, 0.5, 0.7)


def load_assemblies(root):
    return json.loads((root / STRUCTURES).read_text(encoding='utf-8')).get('assemblies', [])


def assembly_points(p, component=None):
    from task_families import assembly
    text, fmt, labels, points, digest = assembly.load(ROOT, dict(asset=p['asset']))
    return labels, assembly.select(labels, points, component)


def assembly_rg_nm(points):
    from task_families import assembly
    return assembly.rg(points) / 10


def components(p):
    if p['kind'] == 'xyz':
        return [None]
    labels, _ = assembly_points(p)
    counts = {l: labels.count(l) for l in set(labels)}
    return sorted(c for c, n in counts.items() if n >= 12)


def assembly_base(p, family, key, component):
    spec = dict(id='EN-%s-%s%s' % (p['pdb'], key, ('-' + component) if component else ''), family=family, asset=p['asset'],
                assembly=p['pdb'] + ('-T' if p['kind'] == 'table' else ''), context=p['context'], scope=p['scope'],
                source=p['source'], license=p['license'])
    if component:
        spec['component'] = component
    return spec


# assembly_extent proposes without strict_rank, unlike its three siblings below, and 2026-11-05 showed why that
# matters at scale: Dmax is a maximum, so 9 of the family's 11 misconception rules necessarily land below the answer
# and only 9 of 60 instances could even assemble three higher candidates. The published positions came out A2 B20
# C23 D15, which tests/test_admission.AnswerPositionTests refuses at n = 60 (it passed at n = 22 only on the
# tolerance's absolute floor). strict_rank does not rescue it either (measured: still A2, 46 instances). So this
# batch's 38 enumerated proposals were held out (templates/pruned-instances.json, hold-2026-11-05-assembly-extent),
# the same answer the comment below gives for debye_intensity: the family waits for an L1 review that can give it a
# plausible OVER-estimate rule. Enumerating it again before that will reproduce the same imbalance.
def assembly_extent(root, p):
    if not p['subunits_only']:
        for c in components(p):
            yield assembly_base(p, 'assembly_extent', 'EXT', c)


def assembly_rg(root, p):
    if not p['subunits_only']:
        for c in components(p):
            yield dict(assembly_base(p, 'assembly_rg', 'RG', c), strict_rank=True)


def debye_intensity(root, p):
    if p['subunits_only']:
        return
    for c in components(p):
        rg = assembly_rg_nm(assembly_points(p, c)[1])
        for x in QRG_DEBYE:
            yield dict(assembly_base(p, 'debye_intensity', 'DEB-%02d' % round(10 * x), c), q_per_nm=round(x / rg, 3), strict_rank=True)


def scattering_q_design(root, p):
    if p['subunits_only']:
        return
    for c in components(p):
        for target in Q_TARGETS:
            yield dict(assembly_base(p, 'scattering_q_design', 'QDES-%02d' % round(100 * target), c), target=target)


def guinier_intensity(root, p):
    """Whole point sets only (the family reads every supplied point), so xyz particles and the 7ARQ nucleotide table."""
    if p['kind'] != 'xyz' and p['pdb'] != '7ARQ' or not p.get('representation'):
        return
    rg = assembly_rg_nm(assembly_points(p)[1])
    for x in QRG_GUINIER:
        yield dict(assembly_base(p, 'guinier_intensity', 'GUIN-%02d' % round(10 * x), None), pdb=p['pdb'], context=p['noun'],
                   representation=p['representation'], q_per_nm=round(x / rg, 2), strict_rank=True)


def capsid_architecture(root, p):
    if not p.get('capsid') or p['pentamer_only']:
        return
    # Caspar-Klug counts apply to the major shell protein only (e.g. HSV-1 VP26 decorates hexons only: 900 copies
    # would give a spurious T = 15 instead of T = 16).
    for c in [p.get('component')]:
        labels, pts = assembly_points(p, c)
        t = len(pts) // 60
        if len(pts) % 60 and p.get('capsomer_form') != 'trimer':
            continue
        if p.get('capsomer_form') == 'trimer':           # PBCV-1: trimeric capsomers, N = 30(T-1); the family asks T only
            yield dict(assembly_base(p, 'capsid_architecture', 'CAPSID-T', c), ask='T', component=c, capsomer_form='trimer')
            continue
        for ask in (('T', 'capsomers') + (('hexons',) if t > 1 else ())):
            yield dict(assembly_base(p, 'capsid_architecture', 'CAPSID-%s' % ask, c), ask=ask, component=c)


# debye_intensity is not enabled for batches yet: on hollow shells three plausible smaller-intensity mistakes rarely
# coexist, so even with strict_rank the accepted answers sat at A/B (runs/enum-v29: A23 B24 C6 D3; v30: A23 B24 C17 D4).
# The family itself was improved (Guinier slips, I squared); the enumerator waits for the L1 review of the family.
ASSEMBLY_ENUMERATORS = dict(assembly_extent=assembly_extent, assembly_rg=assembly_rg,
                            scattering_q_design=scattering_q_design, guinier_intensity=guinier_intensity,
                            capsid_architecture=capsid_architecture)


# ------------------------------------------------------------------ E1: the families that had no enumerator
# These families are driven by committed JSON assets (QM7-X stereoisomers, conformer pools, force paths, the SAMPL9
# binding table) rather than by a structure registry, so they enumerate over the asset files themselves. Each one only
# proposes; whether a proposal becomes a question is still the family's decision at generation time.
QM7X_SOURCE = ('QM7-X, Hoja et al., Sci. Data 8, 43 (2021) https://www.nature.com/articles/s41597-021-00812-2 ; '
               'data https://zenodo.org/records/4288677')
SAMPL9_SOURCE = ('SAMPL9 host-guest challenge (\u4ee3\u7801 MIT\uff1b\u7ed3\u6784\u4e0e\u5b9e\u6d4b\u8868\u7b49'
                 '\u5176\u4f59\u6750\u6599 CC BY 4.0\uff0c\u89c1 docs/data/license-statements.json): '
                 'https://github.com/samplchallenges/SAMPL9 ; experimental_data/experimental_measurements.csv '
                 '(ITC, Isaacs lab); guest structures host_guest/WP6/guest_files')
SAMPL9_SCOPE = ('\u4e3b\u4f53\u4e0e\u5ba2\u4f53\u4e3a SAMPL9 \u63d0\u4f9b\u7684 3D \u7ed3\u6784\uff1b'
                '\u7b54\u6848\u4f9d\u636e\u5b9e\u6d4b ITC \u7ed3\u5408\u81ea\u7531\u80fd\uff081\u00d7 PBS\uff0c'
                'pH 7.40\uff0c298.15 K\uff0c1:1\uff09\uff0c\u8bc1\u636e\u53ea\u5728\u5ba1\u6838\u4fa7\u3002')
SAMPL9_LICENSE = 'SAMPL9 \u975e\u8f6f\u4ef6\u6750\u6599 (CC BY 4.0)'
SAME_ISOMER, OTHER_ISOMER = '\u540c\u4e00', '\u4e24\u4e2a\u4e0d\u540c'
SCOPE_SREL = 'QM7-X \u5206\u5b50 %s %s\u7acb\u4f53\u5f02\u6784\u4f53\u7684\u4e24\u4e2a\u6784\u8c61\u3002'
SCOPE_SPROP = ('QM7-X \u5206\u5b50 %s \u4e24\u4e2a\u975e\u5bf9\u6620\u4f53\u5404\u81ea\u7684\u6570\u636e\u96c6'
               '\u6700\u4f4e\u80fd\u6784\u8c61\uff1b\u6027\u8d28\u4e3a PBE0+MBD \u8ba1\u7b97\u503c\u3002')
SCOPE_SDES = ('QM7-X \u5206\u5b50 %s \u7684\u7acb\u4f53\u5f02\u6784\u4f53\u4e0e\u6784\u8c61\uff1b'
              '\u6784\u9020\u5f02\u6784\u4f53\u53d6\u540c\u5206\u5b50\u5f0f\u7684 %s\uff1b'
              '\u80fd\u91cf\u4e3a PBE0+MBD \u8ba1\u7b97\u503c\u3002')
SCOPE_CONF = ('QM7-X \u5206\u5b50 %s \u540c\u4e00\u7acb\u4f53\u5f02\u6784\u4f53\uff08%s\uff09\u7684 '
              'DFTB3+MBD \u4f18\u5316\u6784\u8c61\uff1b\u53ea\u5141\u8bb8\u5355\u952e\u65cb\u8f6c\uff1b'
              '\u6027\u8d28\u4e3a\u6570\u636e\u96c6 PBE0+MBD \u8ba1\u7b97\u503c\u3002')
SCOPE_FP = ('QM7-X \u5206\u5b50 %s\uff1aA \u4e3a DFTB3+MBD \u4f18\u5316\u7ed3\u6784\uff0cB \u4e3a\u914d\u5bf9'
            '\u4f4d\u79fb\u7ed3\u6784\uff1bB \u5904 PBE0+MBD \u603b\u529b\uff1b\u53ea\u95ee \u03bb=1 '
            '\u5904\u65b9\u5411\u5bfc\u6570\u3002')
MAX_CONFORMER_PAIRS = 12          # per stereo asset, so one molecule cannot flood its family
MAX_GUEST_SETS = 12               # per host table


def load_asset_files(root, folder, pattern='*.json'):
    """Every committed asset of one family folder, in name order, with its parsed contents."""
    out = []
    for path in sorted((root / 'docs/assets/families' / folder).glob(pattern)):
        if path.name.startswith('sources'):
            continue
        try:
            out.append(('assets/families/%s/%s' % (folder, path.name), json.loads(path.read_text(encoding='utf-8'))))
        except (ValueError, OSError):
            continue
    return out


def load_stereo(root):
    return [dict(asset=asset, data=data) for asset, data in load_asset_files(root, 'stereo', 'QM7X-*.json')]


def load_conformer_pools(root):
    return [dict(asset=asset, data=data) for asset, data in load_asset_files(root, 'conformers', 'QM7X-*.json')]


def load_force_paths(root):
    return [dict(asset=asset, data=data) for asset, data in load_asset_files(root, 'force-path', 'QM7X-*.json')]


def load_binding_tables(root):
    return [dict(asset=asset, data=data) for asset, data in load_asset_files(root, 'hostguest', '*-binding.json')]


def qm7x_base(a, family, key):
    molecule = a['data'].get('molecule')
    return dict(id='EN-QM7X%s-%s' % (molecule, key), family=family, asset=a['asset'], molecule='QM7X-%s' % molecule,
                source=QM7X_SOURCE, license='CC BY 4.0', domain='quantum')


def stereo_relationship(root, a):
    """Every pair of conformers of one stereo asset: whether they are the same isomer is what the family asks."""
    conformers = a['data'].get('conformers', [])
    pairs = [(x, y) for i, x in enumerate(conformers) for y in conformers[i + 1:]]
    pairs.sort(key=lambda pair: kit.digest('srel', pair[0]['id'], pair[1]['id']))
    for s0, x in pairs[:MAX_CONFORMER_PAIRS]:
        same = s0.get('isomer') == x.get('isomer')
        yield dict(qm7x_base(a, 'stereo_relationship', 'SREL'),
                   id='EN-QM7X%s-SREL-%s-%s' % (a['data']['molecule'], s0['id'], x['id']),
                   s0=dict(asset=a['asset'], id=s0['id']), x=dict(asset=a['asset'], id=x['id']),
                   scope=SCOPE_SREL % (a['data']['molecule'], SAME_ISOMER if same else OTHER_ISOMER))


def stereo_property_inference(root, a):
    """Each ordered pair of stereoisomers of one molecule; the family compares their lowest-energy conformers."""
    isomers = sorted({c.get('isomer') for c in a['data'].get('conformers', []) if c.get('isomer')})
    for s0 in isomers:
        for x in isomers:
            if s0 != x:
                yield dict(qm7x_base(a, 'stereo_property_inference', 'SPROP-%s-%s' % (s0, x)), s0_isomer=s0,
                           x_isomer=x, scope=SCOPE_SPROP % a['data']['molecule'])


def stereo_design_selection(root, a):
    """A molecule plus a constitutional isomer of it: another stereo asset with the same formula."""
    mates = [b for b in load_stereo(ROOT)
             if b['asset'] != a['asset'] and b['data'].get('formula') == a['data'].get('formula')]
    for mate in sorted(mates, key=lambda b: b['asset'])[:2]:
        yield dict(qm7x_base(a, 'stereo_design_selection', 'SDES-%s' % mate['data']['molecule']),
                   mate_asset=mate['asset'], scope=SCOPE_SDES % (a['data']['molecule'], mate['data']['molecule']))


def conformer_target_selection(root, a):
    """Each conformer of the pool as the starting point, for each stated objective."""
    conformers = a['data'].get('conformers', [])
    for s0 in sorted(conformers, key=lambda c: kit.digest('conf', c['id']))[:4]:
        for objective in ('min_energy', 'max_dipole'):
            yield dict(qm7x_base(a, 'conformer_target_selection', 'CONF-%s-%s' % (s0['id'], objective)),
                       objective=objective, s0=s0['id'],
                       scope=SCOPE_CONF % (a['data']['molecule'], a['data'].get('isomer', 'i1')))


def force_path_derivative(root, a):
    """Both directions of the same displaced pair; the sign of the derivative is the point of the question.

    One molecule can have several displaced pairs (7040 is committed as c1-d1 and c1-d2), so the id names the
    asset's own pair and not just the molecule -- the same thing the hand-written FA-FP-QM7X-7040-D1/-D2 do.
    """
    pair = Path(a['asset']).stem.split('-', 2)[2].upper()                  # QM7X-7040-c1-d2 -> C1-D2
    for direction in ('A_to_B', 'B_to_A'):
        yield dict(qm7x_base(a, 'force_path_derivative', 'FP-%s-%s' % (pair, direction)), direction=direction,
                   scope=SCOPE_FP % a['data']['molecule'])


def binding_sets(a):
    """Four guests of the measured table, in a deterministic order; the family checks that one is the clear best."""
    guests = sorted(a['data'].get('guests', {}))
    quads = [guests[i:i + 4] for i in range(max(len(guests) - 3, 0))]
    quads.sort(key=lambda q: kit.digest('hg', *q))
    return quads[:MAX_GUEST_SETS]


def binding_evidence_choice(root, a):
    host = a['asset'].split('/')[-1].split('-')[0]
    for quad in binding_sets(a):
        yield dict(id='EN-%s-EV-%s' % (host, ''.join(quad)), family='binding_evidence_choice', asset=a['asset'],
                   molecule='SAMPL9-%s' % host, source=SAMPL9_SOURCE, license=SAMPL9_LICENSE, domain='chemistry',
                   scope=SAMPL9_SCOPE, guests=quad)


def binding_design_choice(root, a):
    host = a['asset'].split('/')[-1].split('-')[0]
    for quad in binding_sets(a):
        for reference in quad:
            others = [g for g in quad if g != reference]
            yield dict(id='EN-%s-DES-%s-%s' % (host, reference, ''.join(others)), family='binding_design_choice',
                       asset=a['asset'], molecule='SAMPL9-%s' % host, source=SAMPL9_SOURCE, license=SAMPL9_LICENSE,
                       domain='chemistry', scope=SAMPL9_SCOPE, reference=reference, gain=2.0,
                       guests=others + [reference])


STEREO_ENUMERATORS = dict(stereo_relationship=stereo_relationship, stereo_property_inference=stereo_property_inference,
                          stereo_design_selection=stereo_design_selection)
CONFORMER_ENUMERATORS = dict(conformer_target_selection=conformer_target_selection)
FORCE_PATH_ENUMERATORS = dict(force_path_derivative=force_path_derivative)
BINDING_ENUMERATORS = dict(binding_evidence_choice=binding_evidence_choice,
                           binding_design_choice=binding_design_choice)


ENUMERATORS = dict(backbone_torsion=backbone_torsion, secondary_structure=secondary_structure, fret_efficiency=fret_efficiency,
                   disulfide_design=disulfide_design, fret_design=fret_design, **CRYSTAL_ENUMERATORS, **MOLECULE_ENUMERATORS,
                   **ASSEMBLY_ENUMERATORS, **STEREO_ENUMERATORS, **CONFORMER_ENUMERATORS, **FORCE_PATH_ENUMERATORS,
                   **BINDING_ENUMERATORS)


def propose(root, families=None):
    """{family: [spec, ...]} over every structure; ids are unique and deterministic."""
    out = {}
    for family, fn in ENUMERATORS.items():
        if families and family not in families:
            continue
        items = (load_crystals(root) if family in CRYSTAL_ENUMERATORS else
                 load_molecules(root) if family in MOLECULE_ENUMERATORS else
                 load_assemblies(root) if family in ASSEMBLY_ENUMERATORS else
                 load_stereo(root) if family in STEREO_ENUMERATORS else
                 load_conformer_pools(root) if family in CONFORMER_ENUMERATORS else
                 load_force_paths(root) if family in FORCE_PATH_ENUMERATORS else
                 load_binding_tables(root) if family in BINDING_ENUMERATORS else load_structures(root))
        out[family] = [spec for s in items for spec in fn(root, s)]
    return out


def signature(spec):
    """What makes two instances the same question, independent of id and wording."""
    keys = ('family', 'asset', 'chain', 'residue', 'torsion', 'donor', 'acceptor', 'target', 'r0_nm', 'atom', 'wavelength_A', 'template',
            'mode', 'target_2theta', 'component', 'ask', 'q_per_nm', 'line', 'candidates')
    sig = {k: spec.get(k) for k in keys}
    if spec.get('atoms'):                      # bond / angle: same atoms in either direction are the same question
        rows = [x['row'] for x in spec['atoms']]
        sig['atoms'] = sorted(rows) if len(rows) == 2 else [min(rows[0], rows[2]), rows[1], max(rows[0], rows[2])]
    for k in ('centre', 'partner'):
        if spec.get(k):
            sig[k] = spec[k].get('element')
    if spec.get('pairs'):
        sig['pairs'] = sorted(sorted(p) for p in spec['pairs'])
    return json.dumps(sig, sort_keys=True)
