"""Stereochemistry ladder: perception -> inference -> design (meeting 2 example).

No CIP priorities are needed: every answer is decided from geometry and bonding.
  * constitution: covalent-radius bond graph (plus a graph invariant across molecules);
  * stereocentres: 4-coordinate atoms with four different first-shell neighbour classes,
    pyramidal 3-coordinate S/P, and aziridine-type N (3-ring, slow inversion), each with
    distinct neighbour classes; descriptor = sign of the
    triple product of neighbour vectors (index order) - flips under reflection only;
  * stereo double bonds: bond between trigonal C (3 neighbours) / N (2 neighbours) whose
    ends carry distinguishable substituents; descriptor = same/opposite side.
Every classification is cross-checked against the dataset's own stereoisomer labels, and
instances that disagree are rejected, not relabelled.
"""
import hashlib
import json
import math
from . import kit

VERSION = '0.1.0'
MARGIN_E = 0.0434      # eV, 1 kcal/mol
MARGIN_MU = 0.10       # e*angstrom
RELATIONS = [('same', 'the same compound as S0 (only conformation and/or orientation differ)'),
             ('enantiomer', 'an enantiomer of S0 (its non-superimposable mirror image)'),
             ('diastereomer', 'a diastereomer of S0 (a stereoisomer that is not its mirror image)'),
             ('constitutional', 'a constitutional isomer of S0 (same formula, different bonding)')]


def load(root, asset):
    raw = (root / 'docs' / asset).read_bytes()
    return json.loads(raw), kit.sha256(raw)


def conformer(data, cid):
    matches = [c for c in data['conformers'] if c['id'] == cid]
    if len(matches) != 1:
        raise ValueError('Unknown conformer ' + cid)
    return matches[0]


def shell_classes(elements, edges):
    return [(elements[i], tuple(sorted(elements[j] for j in kit.neighbors(edges, i)))) for i in range(len(elements))]


def descriptors(elements, points, edges):
    cls = shell_classes(elements, edges)
    centres, bonds = {}, {}
    for i in range(len(points)):
        nb = kit.neighbors(edges, i)
        distinct = len({cls[j] for j in nb}) == len(nb)
        # Pyramidal N only inside a three-membered ring (aziridine): inversion is slow there,
        # so the nitrogen configuration is a stable stereo element; ordinary amines invert.
        in_small_ring = any(j in kit.neighbors(edges, k) for j in nb for k in nb if j < k)
        pyramidal = len(nb) == 3 and distinct and (elements[i] in ('S', 'P') or (elements[i] == 'N' and in_small_ring))
        if len(nb) == 4 and distinct or pyramidal:
            v = [kit.sub(points[j], points[i]) for j in nb[:3]]
            volume = kit.dot(kit.cross(v[0], v[1]), v[2])
            if len(nb) == 3 and abs(volume) < 0.1 * kit.norm(v[0]) * kit.norm(v[1]) * kit.norm(v[2]):
                continue                     # planar: not a stereocentre
            centres[i] = 1 if volume > 0 else -1
    trigonal = {i for i in range(len(points)) if (elements[i] == 'C' and len(kit.neighbors(edges, i)) == 3)
                or (elements[i] == 'N' and len(kit.neighbors(edges, i)) == 2)}
    for i, j in sorted(edges):
        if i not in trigonal or j not in trigonal:
            continue
        subs_i = [k for k in kit.neighbors(edges, i) if k != j]
        subs_j = [k for k in kit.neighbors(edges, j) if k != i]
        if any(len(s) == 2 and cls[s[0]] == cls[s[1]] for s in (subs_i, subs_j)):
            continue                         # e.g. =CH2: no cis/trans isomerism
        angle = kit.dihedral_normals(points[min(subs_i)], points[i], points[j], points[min(subs_j)])
        bonds[(i, j)] = 'same' if abs(angle) < 90 else 'opposite'
    return dict(centres=centres, bonds=bonds)


def graph_invariant(elements, edges, rounds=4):
    labels = list(elements)
    for _ in range(rounds):
        labels = [hashlib.sha256((labels[i] + '|' + ','.join(sorted(labels[j] for j in kit.neighbors(edges, i))))
                                 .encode()).hexdigest()[:16] for i in range(len(labels))]
    return hashlib.sha256('|'.join(sorted(labels)).encode()).hexdigest()


def relationship(el_a, pts_a, el_b, pts_b, same_order):
    """Returns (relation, facts). Raises if the rules cannot decide."""
    if sorted(el_a) != sorted(el_b):
        raise ValueError('Different formulas')
    ea, eb = kit.bond_graph(el_a, pts_a), kit.bond_graph(el_b, pts_b)
    if not same_order or el_a != el_b or ea != eb:
        if graph_invariant(el_a, ea) == graph_invariant(el_b, eb):
            raise ValueError('Same graph invariant but no atom correspondence: undecidable')
        return 'constitutional', dict(bond_graphs_equal=False)
    da, db = descriptors(el_a, pts_a, ea), descriptors(el_b, pts_b, eb)
    if set(da['centres']) != set(db['centres']) or set(da['bonds']) != set(db['bonds']):
        raise ValueError('Different stereo elements detected: undecidable')
    flipped = sorted(k for k in da['centres'] if da['centres'][k] != db['centres'][k])
    switched = sorted(k for k in da['bonds'] if da['bonds'][k] != db['bonds'][k])
    facts = dict(bond_graphs_equal=True, stereocentres=sorted(da['centres']), stereo_bonds=sorted(da['bonds']),
                 centres_inverted=flipped, bonds_switched=switched)
    if not flipped and not switched:
        return 'same', facts
    if da['centres'] and len(flipped) == len(da['centres']) and not switched:
        return 'enantiomer', facts
    return 'diastereomer', facts


def placed(points, seed, context):
    """Deterministic proper rotation + translation (internal geometry unchanged)."""
    d = kit.digest(seed, context, 'pose')
    q = [int.from_bytes(d[k:k + 4], 'big') / 2 ** 31 - 1 for k in (0, 4, 8, 12)]
    n = math.sqrt(sum(x * x for x in q))
    w, x, y, z = (c / n for c in q)
    r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    shift = [(d[16 + k] / 255 - 0.5) * 6 for k in range(3)]
    return [tuple(sum(r[i][k] * p[k] for k in range(3)) + shift[i] for i in range(3)) for p in points]


def mirror(points):
    return [(x, y, -z) for x, y, z in points]


def as_xyz(elements, points, comment):
    text = kit.xyz_text(elements, points, comment)
    return text, kit.parse_xyz(text)[1]          # evaluate what the student receives


def best(data, isomer):
    return min((c for c in data['conformers'] if c['isomer'] == isomer), key=lambda c: c['e_pbe0_mbd_eV'])


def check_labels(data, relation, a, b):
    """Dataset labels must agree with the geometric classification."""
    same_isomer = a['isomer'] == b['isomer']
    if relation == 'same' and not same_isomer:
        raise ValueError('Dataset lists different stereoisomers but geometry finds no difference')
    if relation in ('enantiomer', 'diastereomer') and same_isomer:
        raise ValueError('Dataset lists one stereoisomer but geometry finds a configuration change')
    if relation == 'enantiomer':
        gap = abs(best(data, a['isomer'])['e_pbe0_mbd_eV'] - best(data, b['isomer'])['e_pbe0_mbd_eV'])
        if gap > 0.01:
            raise ValueError('Enantiomers must have equal lowest energies; dataset gap %.4f eV' % gap)


# ------------------------------------------------------------------ perception
def build_relationship(spec, root, seed):
    da, ha = load(root, spec['s0']['asset'])
    db, hb = load(root, spec['x']['asset'])
    a, b = conformer(da, spec['s0']['id']), conformer(db, spec['x']['id'])
    same_molecule = da['molecule'] == db['molecule']
    s0_text, s0_pts = as_xyz(da['elements'], a['xyz'], 'S0, angstrom')
    x_text, x_pts = as_xyz(db['elements'], placed(b['xyz'], seed, spec['id']), 'X (rigidly rotated and translated), angstrom')
    relation, facts = relationship(da['elements'], s0_pts, db['elements'], x_pts, same_molecule)
    if same_molecule:
        check_labels(da, relation, a, b)
    elif relation != 'constitutional':
        raise ValueError('Different dataset molecules must be constitutional isomers')
    options = [dict(label=l, value=text) for l, (_, text) in zip(kit.LABELS, RELATIONS)]
    key = kit.validate_verdicts(options, [r == relation for r, _ in RELATIONS])
    why = {
        'same': '键连相同且所有立体描述符一致：仅构象/取向不同。' if relation == 'same' else '存在构型差异或键连不同，不是同一化合物。',
        'enantiomer': '所有立体中心反转且双键构型不变：互为镜像。' if relation == 'enantiomer' else '不满足“全部立体中心反转、双键不变”的镜像关系。',
        'diastereomer': '键连相同，构型部分改变（或双键顺反改变），但不是镜像。' if relation == 'diastereomer' else '不是“键连相同而构型部分不同”的情形。',
        'constitutional': '键连图不同（图不变量不同）。' if relation == 'constitutional' else '键连图相同，不是构造异构体。'}
    audit = [dict(label=l, value=r, is_correct=r == relation, reason=why[r]) for l, (r, _) in zip(kit.LABELS, RELATIONS)]
    question = ('S0.xyz and X.xyz each contain one structure of formula %s (angstrom). X has been rigidly rotated and '
                'translated, and its atom order may differ from S0. Treat structures that interconvert only by rotation '
                'about single bonds as the same compound. Which describes X relative to S0?') % da['formula']
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name='S0.xyz', format='xyz', unit='angstrom', text=s0_text),
                dict(name='X.xyz', format='xyz', unit='angstrom', text=x_text)],
        numeric=None, options=options, correct_label=key, option_audit=audit, excluded_candidates=[], rank=None,
        checks=dict(relation=relation, dataset_ids=[a['id'], b['id']], dataset_isomers=[a['isomer'], b['isomer']],
                    same_dataset_molecule=same_molecule, bond_rule='covalent radii sum × 1.2', **facts,
                    limits='立体中心按第一配位层四（或三）个不同基团判定；与数据集立体异构体标签交叉核对，不一致即拒绝。'),
        scales=dict(input_nm=max(kit.dmax(s0_pts), kit.dmax(x_pts)) / 10, reasoning_nm=kit.dmax(s0_pts) / 10,
                    reasoning_definition='整分子立体构型比较：S0 最大原子间距'),
        input_hashes={spec['s0']['asset']: ha, spec['x']['asset']: hb})


# ------------------------------------------------------------------ inference
STATEMENTS = {(-1, 1): 'X is lower in energy than S0 and has a larger dipole moment',
              (-1, -1): 'X is lower in energy than S0 and has a smaller dipole moment',
              (1, 1): 'X is higher in energy than S0 and has a larger dipole moment',
              (1, -1): 'X is higher in energy than S0 and has a smaller dipole moment'}


def build_property(spec, root, seed):
    data, digest = load(root, spec['asset'])
    a, b = best(data, spec['s0_isomer']), best(data, spec['x_isomer'])
    s0_text, s0_pts = as_xyz(data['elements'], a['xyz'], 'S0, angstrom')
    x_text, x_pts = as_xyz(data['elements'], placed(b['xyz'], seed, spec['id']), 'X (rigidly rotated and translated), angstrom')
    relation, facts = relationship(data['elements'], s0_pts, data['elements'], x_pts, True)
    check_labels(data, relation, a, b)
    if relation != 'diastereomer':
        raise ValueError('Property comparison needs diastereomers (enantiomers have equal scalar properties)')
    de, dmu = b['e_pbe0_mbd_eV'] - a['e_pbe0_mbd_eV'], b['dipole_eA'] - a['dipole_eA']
    if abs(de) < MARGIN_E or abs(dmu) < MARGIN_MU:
        raise ValueError('Differences below the stated margins')
    truth = (1 if de > 0 else -1, 1 if dmu > 0 else -1)
    others = [k for k in STATEMENTS if k != truth]
    order = kit.place(truth, others, spec.get('target_position'), seed, spec['id'], key=lambda k: STATEMENTS[k])
    options = [dict(label=l, value=STATEMENTS[k]) for l, k in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [k == truth for k in order])
    audit = []
    for l, k in zip(kit.LABELS, order):
        wrong = [name for name, s, t in (('能量方向', k[0], truth[0]), ('偶极方向', k[1], truth[1])) if s != t]
        audit.append(dict(label=l, value=STATEMENTS[k], is_correct=k == truth,
                          reason='ΔE = %+.4f eV，Δμ = %+.4f e·Å（X − S0，数据集计算值）。' % (de, dmu) if k == truth else
                          '与数据集计算值不符：' + '、'.join(wrong) + '相反。'))
    question = ('S0 and X are two stereoisomers of the same neutral %s molecule; atom order is shared and X has been rigidly '
                'rotated and translated. Each structure is the lowest-energy QM7-X conformer of its configuration. Compare X '
                'with S0 by PBE0+MBD total energy and dipole-moment magnitude at the supplied geometries; each difference is at '
                'least 0.0434 eV (1 kcal/mol) in energy and 0.10 e·Å in dipole. Which statement is correct?') % data['formula']
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name='S0.xyz', format='xyz', unit='angstrom', text=s0_text),
                dict(name='X.xyz', format='xyz', unit='angstrom', text=x_text)],
        numeric=None, options=options, correct_label=key, option_audit=audit, excluded_candidates=[], rank=None,
        checks=dict(relation=relation, dataset_ids=[a['id'], b['id']], delta_energy_eV=round(de, 6),
                    delta_dipole_eA=round(dmu, 6), margins=dict(energy_eV=MARGIN_E, dipole_eA=MARGIN_MU), level=data['level'],
                    **facts, limits='计算证据只对所述理论水平与给定几何成立；比较的是各构型在数据集中的最低能构象。'),
        scales=dict(input_nm=kit.dmax(s0_pts) / 10, reasoning_nm=kit.dmax(s0_pts) / 10,
                    reasoning_definition='整分子立体构型对性质的影响：S0 最大原子间距'),
        input_hashes={spec['asset']: digest})


# ------------------------------------------------------------------ design
def build_design(spec, root, seed):
    data, digest = load(root, spec['asset'])
    mate, mate_digest = load(root, spec['mate_asset'])
    isomers = sorted({c['isomer'] for c in data['conformers']})
    if len(isomers) != 2:
        raise ValueError('Design template expects exactly two stereoisomers')
    setups = []
    for a_iso in isomers:
        b_best = best(data, [i for i in isomers if i != a_iso][0])
        own = [c for c in data['conformers'] if c['isomer'] == a_iso]
        for s0 in own:
            lower = [c for c in own if c['e_pbe0_mbd_eV'] <= s0['e_pbe0_mbd_eV'] - MARGIN_E]
            if lower and s0['e_pbe0_mbd_eV'] >= b_best['e_pbe0_mbd_eV'] + MARGIN_E:
                setups.append((s0, b_best, min(lower, key=lambda c: c['e_pbe0_mbd_eV'])))
    if not setups:
        raise ValueError('No S0 with both a lower diastereomer and a lower same-configuration conformer')
    s0, target, trap = min(setups, key=lambda s: kit.digest(seed, spec['id'], s[0]['id']))
    const = min(mate['conformers'], key=lambda c: c['e_pbe0_mbd_eV'])
    s0_text, s0_pts = as_xyz(data['elements'], s0['xyz'], 'S0 starting structure, angstrom')
    pool = [('diastereomer_lower', data['elements'], target['xyz'], target['e_pbe0_mbd_eV'], target['id']),
            ('mirror_image', data['elements'], mirror(s0['xyz']), s0['e_pbe0_mbd_eV'], 'mirror of ' + s0['id']),
            ('conformer_only', data['elements'], trap['xyz'], trap['e_pbe0_mbd_eV'], trap['id']),
            ('constitutional_isomer', mate['elements'], const['xyz'], const['e_pbe0_mbd_eV'], const['id'])]
    order = kit.place(pool[0], pool[1:], spec.get('target_position'), seed, spec['id'], key=lambda p: p[0])
    inputs = [dict(name='S0.xyz', format='xyz', unit='angstrom', text=s0_text)]
    options, verdicts, audit = [], [], []
    for label, (kind, elements, xyz, energy, source_id) in zip(kit.LABELS, order):
        text, pts = as_xyz(elements, placed(xyz, seed, spec['id'] + label), 'candidate %s (rigidly rotated), angstrom' % label)
        inputs.append(dict(name='candidate_%s.xyz' % label, format='xyz', unit='angstrom', text=text))
        try:
            relation, facts = relationship(data['elements'], s0_pts, elements, pts, elements == data['elements'] and kind != 'constitutional_isomer')
        except ValueError as error:
            raise ValueError('Candidate %s undecidable: %s' % (label, error))
        expected = {'diastereomer_lower': ('diastereomer',), 'mirror_image': ('enantiomer', 'same'),
                    'conformer_only': ('same',), 'constitutional_isomer': ('constitutional',)}[kind]
        if relation not in expected:
            raise ValueError('Candidate %s (%s) classified as %s' % (label, kind, relation))
        de = energy - s0['e_pbe0_mbd_eV']
        allowed = relation in ('enantiomer', 'diastereomer')
        ok = allowed and de <= -MARGIN_E
        verdicts.append(ok)
        options.append(dict(label=label, value='candidate_%s.xyz' % label))
        reason = {'diastereomer_lower': '只改变构型（非对映体），能量低 %.4f eV，满足目标。' % -de,
                  'mirror_image': ('镜像（对映体）：构型改变但能量按反演对称与 S0 完全相同，未达到降低目标。' if relation == 'enantiomer'
                                   else 'S0 无手性中心，镜像仍是同一化合物（仅构象镜像），未改变构型且能量相同。'),
                  'conformer_only': '能量更低（%.4f eV）但只是同一构型的另一构象，不属于允许的修改。' % de,
                  'constitutional_isomer': '分子式相同但键连不同（构造异构体），违反“键连不变”。'}[kind]
        audit.append(dict(label=label, value='candidate_%s.xyz' % label, source_id=source_id, is_correct=ok, kind=kind,
                          relation=relation, delta_energy_eV=round(de, 6), allowed_modification=allowed, reason=reason))
    options_checked = [dict(o, source=a['source_id']) for o, a in zip(options, audit)]
    key = kit.validate_verdicts(options_checked, verdicts, key=lambda o: o['source'])
    question = ('S0 is one conformer of a %s molecule. You may change it only by changing the configuration of its stereo '
                'elements (the handedness of stereocentres or the cis/trans arrangement at double bonds): same atoms, same '
                'bonds; a change of conformation alone does not count. Goal: a structure whose PBE0+MBD energy (single point at '
                'the supplied geometry) is at least 0.0434 eV (1 kcal/mol) lower than that of S0. Candidates A–D have been '
                'rigidly rotated and their atom order may differ from S0. Which candidate satisfies both the allowed '
                'modification and the goal?') % data['formula']
    return dict(
        question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
        option_audit=audit, excluded_candidates=[], rank=None,
        checks=dict(s0=s0['id'], s0_energy_eV=s0['e_pbe0_mbd_eV'], margin_eV=MARGIN_E, level=data['level'],
                    selection_rule='S0 取有更低能非对映体（≥1 kcal/mol）且有更低能同构型构象的构象，按种子选择；'
                                   '陷阱：镜像（能量不变）、仅构象改变（更低但不允许）、构造异构体（键连不同）。',
                    energy_of_mirror='反演对称：镜像结构能量与 S0 相同（物理定律，非数据集查值）。',
                    limits='计算证据只对所述理论水平与给定几何成立；不是自由能或实验。'),
        scales=dict(input_nm=kit.dmax(s0_pts) / 10, reasoning_nm=kit.dmax(s0_pts) / 10,
                    reasoning_definition='整分子立体构型设计：S0 最大原子间距'),
        input_hashes={spec['asset']: digest, spec['mate_asset']: mate_digest})
