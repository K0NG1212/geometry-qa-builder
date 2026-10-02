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

from task_families import kit
from task_families.local_geometry import read_pdb_residues
from task_families.protein_design import CA_WINDOW, CB_WINDOW, MARGIN, efficiency

STRUCTURES = 'templates/structures.json'
R0_CHOICES = (2.0, 2.5, 3.0, 4.0, 5.0, 6.0)            # nm; stated in the question as a model parameter
TARGETS = (0.25, 0.5, 0.75)                             # FRET design targets
MIN_SPACING = 3                                         # residues apart for any pair
SCOPE = {
    'backbone_torsion': '只含残基 %d–%d 的 ATOM 记录；无替代构象；按 IUPAC 符号约定。',
    'secondary_structure': '只含残基 %d–%d 的 ATOM 记录；参考构象中心为教科书典型值；条目的 HELIX/SHEET 记录作为审核证据，不给考生。',
    'fret_efficiency': '虚拟点探针（R0 为题设值）；不代表真实染料位置、连接臂或取向分布。',
    'disulfide_design': 'ATOM 片段逐行照抄；筛选窗口为题干给出的几何标准；不评估二面角与稳定性。',
    'fret_design': 'ATOM 片段逐行照抄；点偶极、R0 为题设模型参数（取向因子含于 R0）。',
}


def load_structures(root):
    return json.loads((root / STRUCTURES).read_text(encoding='utf-8'))['structures']


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


ENUMERATORS = dict(backbone_torsion=backbone_torsion, secondary_structure=secondary_structure, fret_efficiency=fret_efficiency,
                   disulfide_design=disulfide_design, fret_design=fret_design)


def propose(root, families=None):
    """{family: [spec, ...]} over every structure; ids are unique and deterministic."""
    out = {}
    for family, fn in ENUMERATORS.items():
        if families and family not in families:
            continue
        out[family] = [spec for s in load_structures(root) for spec in fn(root, s)]
    return out


def signature(spec):
    """What makes two instances the same question, independent of id and wording."""
    keys = ('family', 'asset', 'chain', 'residue', 'torsion', 'donor', 'acceptor', 'target', 'r0_nm', 'atom')
    sig = {k: spec.get(k) for k in keys}
    if spec.get('pairs'):
        sig['pairs'] = sorted(sorted(p) for p in spec['pairs'])
    return json.dumps(sig, sort_keys=True)
