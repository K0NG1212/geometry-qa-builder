"""One independent checker per task family. Each reads the student packet (what the
model sees) and the answer key, re-derives the task parameters from the question text,
recomputes with a different formula than the generator, and verifies all four options.
A parameter that cannot be read from the question text is a failure: the question is
then not answerable from its own text.
"""
import json
import math
import re
from decimal import Decimal, localcontext
from .common import (CheckError, need, find, read_xyz, dist, vec, dot, cross, verify_hashes,
                     judge_numeric, LABELS)

# Covalent radii (Cordero et al. 2008) for the checker's own bonding rule.
RADII = {'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'S': 1.05, 'Cl': 1.02, 'P': 1.07, 'F': 0.57}


def inputs_by_name(packet):
    return {i['name']: i['text'] for i in packet['inputs']}


# ---------------------------------------------------------------- perception
def named_bond_angle(packet, key):
    """Law of cosines on three interatomic distances (generator: vector dot product)."""
    q = packet['question']
    rows = re.findall(r'([\w\-]+) = row (\d+)', q)
    need(len(rows) == 3, 'Question must map exactly three named atoms to XYZ rows')
    vertex = find(r'bond angle at ([\w\-]+)', q, 'Question does not name the angle vertex').group(1)
    names = [n for n, _ in rows]
    need(vertex == names[1], 'Named vertex is not the middle atom of the listed triple')
    [text] = [i['text'] for i in packet['inputs'] if i['format'] == 'xyz']
    atoms = read_xyz(text)
    need(all(1 <= int(r) <= len(atoms) for _, r in rows), 'Row index outside the XYZ')
    a, v, b = [atoms[int(r) - 1] for _, r in rows]
    for end in (a, b):
        limit = 1.25 * (RADII[end[0]] + RADII[v[0]])
        need(float(dist(end[1], v[1])) <= limit, 'Named end atom is not bonded to the vertex')
    va, vb, ab = dist(v[1], a[1]), dist(v[1], b[1]), dist(a[1], b[1])
    with localcontext() as ctx:
        ctx.prec = 40
        cosine = (va * va + vb * vb - ab * ab) / (2 * va * vb)
    angle = math.degrees(math.acos(max(-1.0, min(1.0, float(cosine)))))
    verify_hashes(key)
    return dict(judge_numeric(packet, key, angle), parameters=dict(atoms=rows, vertex=vertex),
                method='law of cosines from three Decimal distances')


def _pdb_atoms(text):
    atoms = {}
    for line in text.splitlines():
        if line.startswith('ATOM'):
            need(line[16] == ' ', 'Alternate location in excerpt')
            atoms[(line[12:16].strip(), int(line[22:26]))] = tuple(Decimal(line[c:c + 8]) for c in (30, 38, 46))
    return atoms


def backbone_torsion(packet, key):
    """Normals' angle via acos, sign from (n1 x n2).b2 (generator: two atan2 forms)."""
    q = packet['question']
    spec = find(r'defined by atoms ((?:[A-Z0-9]+\(\d+\)–){3}[A-Z0-9]+\(\d+\))', q,
                'Question does not define the four torsion atoms').group(1)
    parts = [re.fullmatch(r'([A-Z0-9]+)\((\d+)\)', p).groups() for p in spec.split('–')]
    need('IUPAC' in q, 'Sign convention not stated')
    [text] = [i['text'] for i in packet['inputs'] if i['format'] == 'pdb-excerpt']
    atoms = _pdb_atoms(text)
    pts = []
    for name, residue in parts:
        need((name, int(residue)) in atoms, 'Torsion atom %s(%s) missing from excerpt' % (name, residue))
        pts.append(atoms[(name, int(residue))])
    b1, b2, b3 = vec(pts[0], pts[1]), vec(pts[1], pts[2]), vec(pts[2], pts[3])
    n1, n2 = cross(b1, b2), cross(b2, b3)
    cosine = dot(n1, n2) / math.sqrt(dot(n1, n1) * dot(n2, n2))
    angle = math.degrees(math.acos(max(-1.0, min(1.0, cosine))))
    if dot(cross(n1, n2), b2) < 0:
        angle = -angle
    # Provenance: every excerpt line must occur verbatim in the public PDB file.
    paths = verify_hashes(key)
    if paths:     # check() requires a recorded source for every real instance
        source = set(line.rstrip() for p in paths.values() for line in p.read_text(encoding='utf-8').splitlines())
        need(all(line in source for line in text.splitlines() if line.startswith('ATOM')),
             'Excerpt lines are not copied unchanged from the source PDB')
    return dict(judge_numeric(packet, key, angle, period=Decimal(360)), parameters=dict(atoms=spec),
                method='acos of plane normals with triple-product sign')


def extent(packet, key):
    """Decimal recomputation: Dmax by squared distances, Rg by centroid (explicit sums)."""
    q = packet['question']
    [text] = [i['text'] for i in packet['inputs'] if i['format'] == 'xyz']
    atoms = read_xyz(text)
    pts = [p for _, p in atoms]
    need('mass weights' not in q or 'Do not use mass weights' in q, 'Weighting ambiguous')
    with localcontext() as ctx:
        ctx.prec = 40
        if 'maximum Euclidean distance' in q:
            best = max(sum((a - b) ** 2 for a, b in zip(p, r)) for i, p in enumerate(pts) for r in pts[i + 1:])
            value, kind = best.sqrt(), 'max_pair_distance'
        elif 'radius of gyration' in q:
            n = len(pts)
            c = [sum(p[k] for p in pts) / n for k in range(3)]
            value, kind = (sum(sum((p[k] - c[k]) ** 2 for k in range(3)) for p in pts) / n).sqrt(), 'equal_weight_rg'
        else:
            raise CheckError('Question does not state which size measure is asked')
    verify_hashes(key)
    return dict(judge_numeric(packet, key, value), parameters=dict(measure=kind, atoms=len(pts)),
                method='Decimal (40 digits) explicit sums')


# ---------------------------------------------------------------- inference
def force_path(packet, key):
    """dE/dlambda at B = -(path direction) . F(B), summed atom by atom in Decimal."""
    q = packet['question']
    need('F_i = −∂E/∂r_i' in q, 'Force–gradient relation not stated in the question')
    if 'starts at B and moves toward A' in q and 'r_i(B) + λ[r_i(A) − r_i(B)]' in q:
        sign, direction = -1, 'B_to_A'
    elif 'r_i(A) + λ[r_i(B) − r_i(A)]' in q and 'at λ = 1' in q:
        sign, direction = 1, 'A_to_B'
    else:
        raise CheckError('Path direction not stated unambiguously')
    files = inputs_by_name(packet)
    need({'A.xyz', 'B.xyz', 'forces_B.txt'} <= set(files), 'Missing A, B or force table')
    a, b = read_xyz(files['A.xyz']), read_xyz(files['B.xyz'])
    rows = [line.split() for line in files['forces_B.txt'].splitlines()[1:] if line.strip()]
    need(len(a) == len(b) == len(rows), 'A, B and forces differ in atom count')
    need([e for e, _ in a] == [e for e, _ in b] == [r[1] for r in rows], 'Atom order differs')
    need([int(r[0]) for r in rows] == list(range(1, len(rows) + 1)), 'Force rows not numbered 1..N')
    with localcontext() as ctx:
        ctx.prec = 40
        projection = sum(Decimal(f) * (pb - pa) for (_, ra), (_, rb), r in zip(a, b, rows)
                         for pa, pb, f in zip(ra, rb, r[2:]))
        value = -sign * projection
    # Provenance: coordinates and forces agree with the public asset to printing precision.
    [path] = verify_hashes(key).values()
    data = json.loads(path.read_text())
    for label, atoms, ref in (('A', a, data['reference_xyz']), ('B', b, data['displaced_xyz'])):
        need(max(abs(float(c) - r) for (_, p), rr in zip(atoms, ref) for c, r in zip(p, rr)) < 1e-7,
             label + ' coordinates differ from the source asset')
    need(max(abs(float(f) - r) for row, rr in zip(rows, data['forces_at_displaced']) for f, r in zip(row[2:], rr)) < 1e-6,
         'Forces differ from the source asset')
    return dict(judge_numeric(packet, key, value), parameters=dict(direction=direction, atoms=len(a)),
                method='Decimal atom-by-atom projection')


def extinction(packet, key):
    """Real/imaginary sums with math.fsum; one option must vanish, three clearly not."""
    q = packet['question']
    weights_text = find(r'\(((?:[A-Z][a-z]? = \d+, )*[A-Z][a-z]? = \d+)\)', q,
                        'Scattering weights not stated in the question').group(1)
    weights = {k: int(v) for k, v in re.findall(r'([A-Z][a-z]?) = (\d+)', weights_text)}
    need('Exactly one of the four reflections' in q, 'Uniqueness premise not stated')
    [text] = [i['text'] for i in packet['inputs'] if i['format'] == 'fractional-cell-table']
    lines = text.splitlines()
    a = float(find(r'cubic a = ([\d.]+) angstrom', lines[0], 'Cell parameter missing').group(1))
    atoms = [(r[0], [float(x) for x in r[1:]]) for r in (line.split() for line in lines[1:] if line.strip())]
    need(all(len(p) == 3 and all(0 <= x < 1 for x in p) for _, p in atoms), 'Fractional coordinates outside [0,1)')
    need({e for e, _ in atoms} == set(weights), 'Weights do not cover exactly the elements present')
    total = sum(weights[e] for e, _ in atoms)
    verdicts = []
    for o in packet['options']:
        hkl = [int(x) for x in find(r'^\((-?\d+) (-?\d+) (-?\d+)\)$', o['value'], 'Option is not (h k l)').groups()]
        phase = [2 * math.pi * sum(h * x for h, x in zip(hkl, p)) for _, p in atoms]
        re_part = math.fsum(weights[e] * math.cos(t) for (e, _), t in zip(atoms, phase))
        im_part = math.fsum(weights[e] * math.sin(t) for (e, _), t in zip(atoms, phase))
        verdicts.append((o['label'], o['value'], math.hypot(re_part, im_part) / total))
    zero = [v for v in verdicts if v[2] <= 1e-6]
    need(len(zero) == 1, '%d options have |F| = 0 (need exactly 1)' % len(zero))
    weakest = min(v[2] for v in verdicts if v[2] > 1e-6)
    need(weakest >= 1e-3, 'A distractor is nearly extinct (|F|/F000 = %.2e)' % weakest)
    need(key['correct_label'] == zero[0][0], 'Key label %s != recomputed %s' % (key['correct_label'], zero[0][0]))
    # Provenance: the table must reproduce the public source (cell edge from the CIF,
    # or every Cartesian row of the published XYZ cell).
    [path] = verify_hashes(key).values()
    if path.suffix == '.cif':
        cif_a = find(r'_cell_length_a\s+([\d.]+)', path.read_text(encoding='utf-8'), 'CIF lacks cell edge').group(1)
        need(abs(float(cif_a) - a) < 1e-4, 'Cell edge differs from the CIF')
    else:
        source = read_xyz(path.read_text(encoding='utf-8-sig'))
        need(len(source) == len(atoms) and all(e == s_e and max(abs(x * a - float(c)) for x, c in zip(f, sp)) < 1e-5
                                               for (e, f), (s_e, sp) in zip(atoms, source)),
             'Fractional table does not reproduce the published cell')
    return dict(label=zero[0][0], recomputed=zero[0][1], parameters=dict(weights=weights, a_A=a, atoms=len(atoms)),
                options={l: round(r, 8) for l, _, r in verdicts}, weakest_nonzero=round(weakest, 6),
                method='separate cos/sin sums over the student table')


# ---------------------------------------------------------------- design
def _bonds(atoms):
    pts = [p for _, p in atoms]
    return {(i, j) for i in range(len(pts)) for j in range(i + 1, len(pts))
            if float(dist(pts[i], pts[j])) <= 1.25 * (RADII[atoms[i][0]] + RADII[atoms[j][0]])}


def _handedness(atoms, bonds):
    out = {}
    for i in range(len(atoms)):
        nb = sorted({b if a == i else a for a, b in bonds if i in (a, b)})
        if len(nb) == 4:
            u, v, w = (vec(atoms[i][1], atoms[j][1]) for j in nb[:3])
            out[i] = dot(cross(u, v), w) > 0
    return out


def _shape_gap(p, q):
    pts = range(len(p))
    diffs = [float(dist(p[i][1], p[j][1]) - dist(q[i][1], q[j][1])) for i in pts for j in pts if i < j]
    return math.sqrt(math.fsum(d * d for d in diffs) / len(diffs))


POLICY = {'min_energy': ('e_pbe0_mbd_eV', -1, 0.0434), 'max_dipole': ('dipole_eA', 1, 0.10)}


def conformer_selection(packet, key):
    """Constraints from the candidate files themselves; property looked up by matching
    coordinates in the hash-verified public dataset extract (never by label or id)."""
    q = packet['question']
    if 'lowest total PBE0+MBD energy' in q:
        goal = 'min_energy'
    elif 'largest total dipole-moment magnitude' in q:
        goal = 'max_dipole'
    else:
        raise CheckError('Design goal not stated')
    need('only by rotating about single bonds' in q, 'Allowed modification not stated')
    files = inputs_by_name(packet)
    need(set(files) == {'S0.xyz'} | {'candidate_%s.xyz' % l for l in LABELS}, 'Need S0 and four candidates')
    need(all('Geom-' not in t for t in files.values()), 'Dataset identifiers visible to the model')
    s0 = read_xyz(files['S0.xyz'])
    bonds0, hand0 = _bonds(s0), _handedness(s0, _bonds(s0))
    [path] = verify_hashes(key).values()
    data = json.loads(path.read_text())
    prop, sense, margin = POLICY[goal]
    rows, candidates = [], []
    for label in LABELS:
        atoms = read_xyz(files['candidate_%s.xyz' % label])
        need([e for e, _ in atoms] == [e for e, _ in s0], label + ': atoms or order differ from S0')
        need(_bonds(atoms) == bonds0, label + ': bonding differs from S0')
        need(_handedness(atoms, bonds0) == hand0, label + ': configuration at a 4-coordinate centre differs')
        need(_shape_gap(atoms, s0) > 0.05, label + ': identical to S0 (or its mirror image)')
        match = [c for c in data['conformers']
                 if max(abs(float(x) - y) for (_, p), r in zip(atoms, c['xyz']) for x, y in zip(p, r)) < 1e-6]
        need(len(match) == 1, label + ': no unique dataset structure with these coordinates')
        candidates.append((label, atoms))
        rows.append((label, match[0][prop]))
    for (l1, a1), (l2, a2) in ((x, y) for i, x in enumerate(candidates) for y in candidates[i + 1:]):
        need(_shape_gap(a1, a2) > 0.05, '%s and %s are the same or mirror conformers' % (l1, l2))
    ranked = sorted(rows, key=lambda r: sense * r[1], reverse=True)
    lead = sense * (ranked[0][1] - ranked[1][1])
    need(lead >= margin, 'Best candidate leads by %.4f, below the %.4f policy margin' % (lead, margin))
    need(key['correct_label'] == ranked[0][0], 'Key label %s != recomputed %s' % (key['correct_label'], ranked[0][0]))
    return dict(label=ranked[0][0], recomputed=ranked[0][0], parameters=dict(goal=goal, atoms=len(s0)),
                options={l: v for l, v in rows}, lead=round(lead, 6), policy_margin=margin,
                method='own bond graph, handedness and distance-matrix checks; property matched by coordinates')


CHECKERS = {
    'named_bond_angle': named_bond_angle,
    'backbone_torsion': backbone_torsion,
    'extent_choice_v2': extent,
    'force_path_derivative': force_path,
    'kinematic_extinction': extinction,
    'conformer_target_selection': conformer_selection,
}
