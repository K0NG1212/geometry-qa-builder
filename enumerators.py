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
import json
import math
from pathlib import Path

from task_families import kit
from task_families.local_geometry import read_pdb_residues
from task_families.protein_design import CA_WINDOW, CB_WINDOW, MARGIN, efficiency

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
    'crystal': '常规晶胞按 CIF 全部对称操作展开（task_families/cell.py）；周期晶体；衍射题为运动学模型与原子序数权重。',
}
# Atomic numbers (angle-independent scattering weights stated in the question) and the X-ray lines already used by
# diffraction_design in templates/family-manifest.json.
Z = {'H': 1, 'C': 6, 'N': 7, 'O': 8, 'F': 9, 'Na': 11, 'Mg': 12, 'Al': 13, 'Si': 14, 'P': 15, 'S': 16, 'Cl': 17, 'K': 19, 'Ca': 20,
     'Ti': 22, 'Fe': 26, 'Co': 27, 'Ni': 28, 'Cu': 29, 'Zn': 30, 'Ga': 31, 'Ge': 32, 'Se': 34, 'Br': 35, 'Sr': 38, 'Zr': 40,
     'Mo': 42, 'Cd': 48, 'Sn': 50, 'I': 53, 'Cs': 55, 'Ba': 56, 'W': 74, 'Au': 79, 'Pb': 82}
LINES = (('Cu', 1.54056), ('Mo', 0.7093), ('Co', 1.78897), ('Cr', 2.2897))


def load_structures(root):
    return json.loads((root / STRUCTURES).read_text(encoding='utf-8'))['structures']


def load_crystals(root):
    return json.loads((root / STRUCTURES).read_text(encoding='utf-8')).get('crystals', [])


def structure_of(spec):
    """Grouping key for sampling and capacity rows: PDB id or COD id."""
    return spec.get('pdb') or spec.get('cod')


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
    from task_families.cell import read_cif
    elements = sorted({e for e, _ in read_cif(ROOT / 'docs' / c['asset'])[1]})
    return elements, dict(id='EN-COD%s-%s' % (c['cod'], key), family=family, source_kind='cif_general', asset=c['asset'],
                          cod=c['cod'], name=c['name'], source='https://www.crystallography.net/cod/%s.html' % c['cod'],
                          license='COD（公共领域 / CC0）', scope=SCOPE['crystal'])


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


CRYSTAL_ENUMERATORS = dict(coordination_shell=coordination_shell, first_diffraction_peak=first_diffraction_peak,
                           kinematic_extinction=kinematic_extinction)


ENUMERATORS = dict(backbone_torsion=backbone_torsion, secondary_structure=secondary_structure, fret_efficiency=fret_efficiency,
                   disulfide_design=disulfide_design, fret_design=fret_design, **CRYSTAL_ENUMERATORS)


def propose(root, families=None):
    """{family: [spec, ...]} over every structure; ids are unique and deterministic."""
    out = {}
    for family, fn in ENUMERATORS.items():
        if families and family not in families:
            continue
        items = load_crystals(root) if family in CRYSTAL_ENUMERATORS else load_structures(root)
        out[family] = [spec for s in items for spec in fn(root, s)]
    return out


def signature(spec):
    """What makes two instances the same question, independent of id and wording."""
    keys = ('family', 'asset', 'chain', 'residue', 'torsion', 'donor', 'acceptor', 'target', 'r0_nm', 'atom', 'wavelength_A')
    sig = {k: spec.get(k) for k in keys}
    for k in ('centre', 'partner'):
        if spec.get(k):
            sig[k] = spec[k].get('element')
    if spec.get('pairs'):
        sig['pairs'] = sorted(sorted(p) for p in spec['pairs'])
    return json.dumps(sig, sort_keys=True)
