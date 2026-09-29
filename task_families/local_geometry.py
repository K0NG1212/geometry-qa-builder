"""Perception families on named local geometry: bond angle and protein backbone torsion.

Chemical identity (which atoms, which linkage) is part of the template input and
is checked against connectivity; the model never receives arbitrary row pairs.
"""
import math
from pathlib import Path
from . import kit

VERSION = '0.1.0'


def _angle_candidates(elements, points, edges, a, v, b, names, ideal):
    """Error mechanisms for an A-V-B bond angle."""
    theta = kit.angle_acos(points[a], points[v], points[b])
    label = lambda i: '%s(row %d)' % (elements[i], i + 1)
    out = [dict(rule='supplement', value=180 - theta, plausibility=1,
                reason='用 180°−θ：把其中一根键矢量方向取反（从顶点指出的方向写反）。'),
           dict(rule='triangle_angle_at_first_atom', value=kit.angle_acos(points[v], points[a], points[b]), plausibility=1,
                reason='把三角形 %s–%s–%s 的顶点错放在 %s 上。' % (names[0], names[1], names[2], names[0]))]
    if ideal:
        out.append(dict(rule='idealized_value', value=ideal['value'], plausibility=3,
                        reason='直接套用理想杂化角 %s（%s），没有测量这一构象。' % (ideal['value'], ideal['basis'])))
    for x in kit.neighbors(edges, v):
        if x in (a, b):
            continue
        out.append(dict(rule='other_neighbor:%s-%s-%s' % (names[0], names[1], label(x)),
                        value=kit.angle_acos(points[a], points[v], points[x]), plausibility=3,
                        reason='顶点正确，但另一端选成与 %s 相连的 %s。' % (names[1], label(x))))
        out.append(dict(rule='other_neighbor:%s-%s-%s' % (label(x), names[1], names[2]),
                        value=kit.angle_acos(points[x], points[v], points[b]), plausibility=3,
                        reason='顶点正确，但一端选成与 %s 相连的 %s。' % (names[1], label(x))))
    for end, other, name in ((a, b, names[0]), (b, a, names[2])):
        for y in kit.neighbors(edges, end):
            if y == v:
                continue
            out.append(dict(rule='angle_at_adjacent_atom:%s-%s-%s' % (names[1], name, label(y)),
                            value=kit.angle_acos(points[v], points[end], points[y]), plausibility=2,
                            reason='测成相邻原子 %s 处的键角，而非题目指定的顶点 %s。' % (name, names[1])))
    return theta, out


def build_bond_angle(spec, root, seed):
    path = root / 'docs' / spec['asset']
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    elements, points = kit.parse_xyz(text)
    a, v, b = [x['row'] - 1 for x in spec['atoms']]
    names = [x['name'] for x in spec['atoms']]
    for x, idx in zip(spec['atoms'], (a, v, b)):
        if not 0 <= idx < len(points) or elements[idx] != x['element']:
            raise ValueError('Named atom does not match XYZ row element')
    edges = kit.bond_graph(elements, points)
    bonded = [(min(a, v), max(a, v)) in edges, (min(b, v), max(b, v)) in edges]
    if not all(bonded):
        raise ValueError('Named angle atoms are not bonded to the vertex under the covalent-radius rule')
    theta, candidates = _angle_candidates(elements, points, edges, a, v, b, names, spec.get('ideal'))
    second = kit.angle_atan2(points[a], points[v], points[b])
    if abs(theta - second) > 1e-9:
        raise ValueError('Angle implementations disagree')
    decimals, tol, sep = 2, '0.005', '1.50'
    context = spec['id']
    chosen, rejected, goal, rank = kit.choose_numeric(theta, candidates, decimals=decimals, tolerance=tol,
                                                      min_separation=sep, seed=seed, context=context, target=spec.get('target_position'),
                                                      lower=0, upper=180, distractor_separation='0.50')
    options, audit = kit.label_numeric(theta, chosen, decimals=decimals, unit='degree', seed=seed,
                                       context=context, correct_reason='按向量夹角公式在指定顶点计算；另以 atan2 实现复核。')
    key = kit.validate_numeric(options, theta, decimals=decimals, tolerance=tol, min_separation=sep, unit='degree',
                               distractor_separation='0.50')
    rows = ', '.join('%s = row %d' % (x['name'], x['row']) for x in spec['atoms'])
    question = ('%s Atoms %s–%s–%s form %s (%s; rows counted from 1 after the two XYZ header lines). '
                'What is the %s–%s–%s bond angle at %s in this supplied conformer?') % (
        spec['context'], names[0], names[1], names[2], spec['linkage'], rows, names[0], names[1], names[2], names[1])
    span = max(math.dist(points[i], points[j]) for i in (a, v, b) for j in (a, v, b)) / 10
    return dict(
        question=question,
        scope=spec['scope'],
        inputs=[dict(name=path.name, format='xyz', unit='angstrom', text=text)],
        numeric=dict(value=kit.display(theta, decimals), unit='degree', decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected,
        rank=dict(target=goal, achieved=rank),
        checks=dict(bond_rule='covalent radii sum × 1.2', vertex_bonded_to_both=True,
                    acos_deg=theta, atan2_deg=second, implementations_agree=True,
                    vertex_neighbors=[kit.neighbors(edges, v)]),
        scales=dict(input_nm=kit.dmax(points) / 10, reasoning_nm=span,
                    reasoning_definition='指定三原子两两最大间距（局部 0.1–1 nm）'),
        input_hashes={spec['asset']: kit.sha256(raw)})


def read_pdb_residues(text, chain):
    residues, order, altloc = {}, [], set()
    for line in text.splitlines():
        if line.startswith('ENDMDL'):
            break
        if not line.startswith('ATOM') or line[21] != chain:
            continue
        number = int(line[22:26])
        if line[16] != ' ':
            altloc.add(number)
        if number not in residues:
            residues[number] = dict(name=line[17:20], atoms={}, lines=[])
            order.append(number)
        residues[number]['atoms'][line[12:16].strip()] = tuple(float(line[c:c + 8]) for c in (30, 38, 46))
        residues[number]['lines'].append(line.rstrip())
    return residues, order, altloc


TORSIONS = {
    'phi': (('C', -1), ('N', 0), ('CA', 0), ('C', 0)),
    'psi': (('N', 0), ('CA', 0), ('C', 0), ('N', 1)),
    'omega': (('CA', 0), ('C', 0), ('N', 1), ('CA', 1)),
}
SYMBOL = {'phi': 'φ', 'psi': 'ψ', 'omega': 'ω'}


def torsion(residues, number, kind, implementation=kit.dihedral_normals):
    pts = []
    for atom, offset in TORSIONS[kind]:
        res = residues.get(number + offset)
        if not res or atom not in res['atoms']:
            return None
        pts.append(res['atoms'][atom])
    return implementation(*pts)


def build_backbone_torsion(spec, root, seed):
    path = root / 'docs' / spec['asset']
    raw = path.read_bytes()
    residues, order, altloc = read_pdb_residues(raw.decode('utf-8'), spec['chain'])
    n, kind = spec['residue'], spec['torsion']
    window = [n - 1, n, n + 1]
    if kind not in ('phi', 'psi') or any(r not in residues for r in window) or altloc & set(window):
        raise ValueError('Residue window missing, has alternate locations or unsupported torsion')
    for left, right in ((n - 1, n), (n, n + 1)):
        if math.dist(residues[left]['atoms']['C'], residues[right]['atoms']['N']) > 1.5:
            raise ValueError('Chain break between residues %d and %d' % (left, right))
    value = torsion(residues, n, kind)
    second = torsion(residues, n, kind, kit.dihedral_projection)
    if value is None or abs(value - second) > 1e-8:
        raise ValueError('Torsion implementations disagree or atoms missing')
    if abs(abs(value) - 180) < 1.0:
        raise ValueError('Correct value too close to the ±180° boundary for unambiguous rounding')
    other = 'psi' if kind == 'phi' else 'phi'
    res = residues[n]
    name = '%s%d' % (res['name'].title(), n)
    tau = kit.angle_acos(res['atoms']['N'], res['atoms']['CA'], res['atoms']['C'])
    neighbor = n + 1 if kind == 'phi' else n - 1
    omega_residue = n - 1 if kind == 'phi' else n
    candidates = [
        dict(rule='opposite_sign', value=-value, plausibility=3,
             reason='符号约定取反：相当于把镜像手性当成原构象。'),
        dict(rule='other_backbone_torsion', value=torsion(residues, n, other), plausibility=3,
             reason='算成同一残基的 %s 而非 %s。' % (SYMBOL[other], SYMBOL[kind])),
        dict(rule='neighbor_residue_same_torsion', value=torsion(residues, neighbor, kind), plausibility=2,
             reason='算成相邻残基 %d 的 %s。' % (neighbor, SYMBOL[kind])),
        dict(rule='peptide_omega', value=torsion(residues, omega_residue, 'omega'), plausibility=1,
             reason='算成肽键扭转角 ω（残基 %d–%d）。' % (omega_residue, omega_residue + 1)),
        dict(rule='unsigned_plane_angle', value=180 - abs(value), plausibility=1,
             reason='用两平面法向量夹角且方向取反，丢失符号（180°−|θ|）。'),
        dict(rule='backbone_bond_angle', value=tau, plausibility=1,
             reason='算成 N–CA–C 键角 τ，而非二面角。'),
    ]
    decimals, tol, sep = 1, '0.05', '5.0'
    chosen, rejected, goal, rank = kit.choose_numeric(value, candidates, decimals=decimals, tolerance=tol,
                                                      min_separation=sep, seed=seed, context=spec['id'], target=spec.get('target_position'),
                                                      lower=-180, upper=180, period=360)
    options, audit = kit.label_numeric(value, chosen, decimals=decimals, unit='degree', seed=seed,
                                       context=spec['id'], correct_reason='IUPAC 符号约定的二面角；法向量与投影两种实现一致。')
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=sep,
                               unit='degree', period=360)
    atoms = TORSIONS[kind]
    definition = '–'.join('%s(%d)' % (a, n + o) for a, o in atoms)
    excerpt = '\n'.join(line for r in window for line in residues[r]['lines']) + '\nEND\n'
    chain_label = spec['chain'] if spec['chain'].strip() else '(blank)'
    question = ('The excerpt contains residues %d–%d of chain %s from PDB entry %s (%s), ATOM records copied '
                'unchanged (coordinates in angstrom). Compute the backbone torsion %s of %s, defined by atoms %s, '
                'using the IUPAC sign convention (range −180° to +180°).') % (
        n - 1, n + 1, chain_label, spec['pdb'], spec['context'], SYMBOL[kind], name, definition)
    pts = [residues[n + o]['atoms'][a] for a, o in atoms]
    return dict(
        question=question,
        scope=spec['scope'],
        inputs=[dict(name='%s-%s%d-excerpt.pdb' % (spec['pdb'], spec['chain'].strip() or '_', n),
                     format='pdb-excerpt', unit='angstrom', text=excerpt)],
        numeric=dict(value=kit.display(value, decimals), unit='degree', decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected,
        rank=dict(target=goal, achieved=rank),
        checks=dict(normals_deg=value, projection_deg=second, implementations_agree=True,
                    chain_continuity_max_C_N_A=1.5, altloc_in_window=False,
                    periodic_separation=True, residue=name, torsion=kind),
        scales=dict(input_nm=kit.dmax([p for r in window for p in residues[r]['atoms'].values()]) / 10,
                    reasoning_nm=math.dist(pts[0], pts[3]) / 10,
                    reasoning_definition='二面角首末原子间距（局部 0.1–1 nm）'),
        input_hashes={spec['asset']: kit.sha256(raw)})


# ------------------------------------------------------------------ named bond distance
BOHR_PER_ANGSTROM = 1.8897261246


def _distance_candidates(elements, points, edges, a, b, labels, typical):
    d = math.dist(points[a], points[b])
    out = [dict(rule='covalent_radii_sum', value=kit.COVALENT[elements[a]] + kit.COVALENT[elements[b]], plausibility=2,
                reason='用共价半径之和估计，没有测量这一结构。'),
           dict(rule='bohr_units', value=d * BOHR_PER_ANGSTROM, plausibility=1, reason='把埃换算成玻尔半径后报告。')]
    if typical:
        out.append(dict(rule='typical_value', value=typical['value'], plausibility=3,
                        reason='套用教科书典型值 %s Å（%s），没有测量。' % (typical['value'], typical['basis'])))
    for end, other in ((a, b), (b, a)):
        for x in kit.neighbors(edges, end):
            if x == other:
                continue
            out.append(dict(rule='other_bond:%s-%s' % (labels(end), labels(x)), value=math.dist(points[end], points[x]),
                            plausibility=3, reason='量成 %s 的另一根键（到 %s）。' % (labels(end), labels(x))))
    near = sorted((math.dist(points[a], points[j]), j) for j in range(len(points))
                  if j not in (a, b) and elements[j] == elements[b] and (min(a, j), max(a, j)) not in edges)
    if near:
        out.append(dict(rule='nearest_nonbonded_same_element', value=near[0][0], plausibility=2,
                        reason='量到最近的另一个同种元素原子（%s，未成键）。' % labels(near[0][1])))
    return d, out


def build_bond_distance(spec, root, seed):
    path = root / 'docs' / spec['asset']
    raw = path.read_bytes()
    if spec.get('pdb'):
        residues, _, altloc = read_pdb_residues(raw.decode('utf-8'), spec['chain'])
        wanted = [r for r, _ in spec['pdb_atoms']]
        if altloc & set(wanted):
            raise ValueError('Alternate locations in named residues')
        lines = [l for r in sorted(set(wanted)) for l in residues[r]['lines']]
        ssbond = [l.rstrip() for l in raw.decode('utf-8').splitlines() if l.startswith('SSBOND')
                  and {int(l[17:21]), int(l[31:35])} == set(wanted)]
        text = '\n'.join(ssbond + lines) + '\nEND\n'
        names, elements, points = [], [], []
        for r in sorted(set(wanted)):
            for n, xyz in residues[r]['atoms'].items():
                names.append('%s(%s%d)' % (n, residues[r]['name'].title(), r))
                elements.append(n[0] if n[0] in 'CNOS' else 'H')
                points.append(xyz)
        index = {(r, n): i for i, (r, n) in enumerate((r, n) for r in sorted(set(wanted)) for n in residues[r]['atoms'])}
        a, b = [index[tuple(x)] for x in spec['pdb_atoms']]
        inputs = [dict(name='%s-excerpt.pdb' % spec['pdb'], format='pdb-excerpt', unit='angstrom', text=text)]
        label = lambda i: names[i]
        where = 'atoms %s and %s' % (names[a], names[b])
    else:
        text = raw.decode('utf-8-sig')
        elements, points = kit.parse_xyz(text)
        rows = spec['atoms']
        a, b = rows[0]['row'] - 1, rows[1]['row'] - 1
        for x, idx in zip(rows, (a, b)):
            if elements[idx] != x['element']:
                raise ValueError('Named atom does not match XYZ row element')
        inputs = [dict(name=path.name, format='xyz', unit='angstrom', text=text)]
        label = lambda i: '%s%d' % (elements[i], i + 1)
        where = 'atoms %s (row %d) and %s (row %d)' % (rows[0]['name'], a + 1, rows[1]['name'], b + 1)
    edges = kit.bond_graph(elements, points)
    if (min(a, b), max(a, b)) not in edges:
        raise ValueError('Named atoms are not bonded under the covalent-radius rule')
    d, candidates = _distance_candidates(elements, points, edges, a, b, label, spec.get('typical'))
    second = float(sum((kit.Decimal(repr(x)) - kit.Decimal(repr(y))) ** 2 for x, y in zip(points[a], points[b])).sqrt())
    if abs(d - second) > 1e-9:
        raise ValueError('Distance implementations disagree')
    decimals, tol, sep = 3, '0.0005', '0.020'
    chosen, rejected, goal, rank = kit.choose_numeric(d, candidates, decimals=decimals, tolerance=tol, min_separation=sep,
                                                      seed=seed, context=spec['id'], lower=0, target=spec.get('target_position'),
                                                      distractor_separation='0.010')
    options, audit = kit.label_numeric(d, chosen, decimals=decimals, unit='angstrom', seed=seed, context=spec['id'],
                                       correct_reason='两指定原子的欧氏距离；另以 Decimal 实现复核。')
    key = kit.validate_numeric(options, d, decimals=decimals, tolerance=tol, min_separation=sep, unit='angstrom',
                               distractor_separation='0.010')
    question = '%s In this supplied structure, %s form %s. What is this bond length?' % (spec['context'], where, spec['bond'])
    return dict(
        question=question, scope=spec['scope'], inputs=inputs,
        numeric=dict(value=kit.display(d, decimals), unit='angstrom', decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected,
        rank=dict(target=goal, achieved=rank),
        checks=dict(bonded=True, bond_rule='covalent radii sum × 1.2', float_A=d, decimal_A=second,
                    limits='单一结构中的键长；不据此单独判定成键状态或键级。'),
        scales=dict(input_nm=kit.dmax(points) / 10, reasoning_nm=d / 10, reasoning_definition='两成键原子间距'),
        input_hashes={spec['asset']: kit.sha256(raw)})
