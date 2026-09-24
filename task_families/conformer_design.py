"""Design-selection family: choose one of four candidate conformers for a stated target.

S0, the allowed modification (single-bond rotation only: same atoms, same bonding,
same configuration at stereocentres) and the target property are given. The four
candidates are real dataset structures; the property evidence is the dataset's
computed value at a stated level of theory. The checker verifies every candidate
against the constraints and requires a unique best candidate by a stated margin.
This is candidate selection, not open structure generation, and the answer holds
only for the stated computational criterion, not for experiment.
"""
import itertools
import json
import math
from . import kit

VERSION = '0.1.0'
CONSTRAINTS = ('same_atoms', 'same_bonding', 'same_configuration', 'distinct_from_S0', 'dipole_consistent')
OBJECTIVES = {
    'min_energy': dict(key='e_pbe0_mbd_eV', sense=-1, margin=0.0434, unit='eV',
                       text='the lowest total PBE0+MBD energy (single-point energies at the supplied geometries)',
                       margin_basis='1 kcal/mol ≈ 0.0434 eV，高于常见构象能相对误差量级'),
    'max_dipole': dict(key='dipole_eA', sense=1, margin=0.10, unit='e·Å',
                       text='the largest total dipole-moment magnitude (PBE0+MBD, at the supplied geometries)',
                       margin_basis='0.10 e·Å，约为该类小分子偶极的 10%'),
}


def distance_rmsd(p, q):
    """Rotation/translation/reflection-invariant comparison via interatomic distances."""
    pairs = list(itertools.combinations(range(len(p)), 2))
    return math.sqrt(math.fsum((math.dist(p[i], p[j]) - math.dist(q[i], q[j])) ** 2 for i, j in pairs) / len(pairs))


def stereocentres(elements, points, edges):
    centres = {}
    for i in range(len(points)):
        nb = kit.neighbors(edges, i)
        if len(nb) != 4:
            continue
        shells = [(elements[j], tuple(sorted(elements[k] for k in kit.neighbors(edges, j) if k != i))) for j in nb]
        if len(set(shells)) != 4:
            continue           # not a stereocentre under this first-shell rule
        v = [kit.sub(points[j], points[i]) for j in nb[:3]]
        centres[i] = 1 if kit.dot(kit.cross(v[0], v[1]), v[2]) > 0 else -1
    return centres


def rg(points):
    c = [math.fsum(p[k] for p in points) / len(points) for k in range(3)]
    return math.sqrt(math.fsum(math.dist(p, c) ** 2 for p in points) / len(points))


def build(spec, root, seed):
    path = root / 'docs' / spec['asset']
    raw = path.read_bytes()
    data = json.loads(raw)
    objective = OBJECTIVES[spec['objective']]
    elements = data['elements']
    confs = {c['id']: c for c in data['conformers']}
    s0 = confs[spec['s0']]
    graph0 = kit.bond_graph(elements, s0['xyz'])
    chiral0 = stereocentres(elements, s0['xyz'], graph0)
    checks, pool = {}, []
    for cid, c in confs.items():
        if cid == spec['s0']:
            continue
        graph = kit.bond_graph(elements, c['xyz'])
        chiral = stereocentres(elements, c['xyz'], graph)
        vdip = math.sqrt(sum(x * x for x in c['vdip_eA']))
        record = dict(same_atoms=len(c['xyz']) == len(elements), same_bonding=graph == graph0,
                      same_configuration=chiral == chiral0,
                      distinct_from_S0=distance_rmsd(s0['xyz'], c['xyz']) > 0.05,
                      dipole_consistent=abs(vdip - c['dipole_eA']) < 1e-4)
        checks[cid] = record
        if all(record[k] for k in CONSTRAINTS):
            pool.append(c)
    unique = []
    for c in sorted(pool, key=lambda c: c['id']):
        if any(distance_rmsd(c['xyz'], u['xyz']) <= 0.05 or
               (abs(c['e_pbe0_mbd_eV'] - u['e_pbe0_mbd_eV']) < 0.002 and abs(c['dipole_eA'] - u['dipole_eA']) < 0.005)
               for u in unique):
            checks[c['id']]['excluded'] = 'equivalent to another candidate (same or mirror conformer)'
            continue
        unique.append(c)
    value = lambda c: objective['sense'] * c[objective['key']]
    combos = []
    for combo in itertools.combinations(unique, 4):
        ranked = sorted(combo, key=value, reverse=True)
        if value(ranked[0]) - value(ranked[1]) < objective['margin']:
            continue
        radii = sorted(combo, key=lambda c: rg(c['xyz']))
        extreme = ranked[0] in (radii[0], radii[-1])
        thin = value(ranked[0]) - value(ranked[1]) < 1.5 * objective['margin']   # prefer a clear margin when available
        combos.append(((extreme, thin, kit.digest(seed, spec['id'], *sorted(c['id'] for c in combo))), combo, ranked))
    if not combos:
        raise ValueError('No four-candidate set with a unique best above the margin')
    _, combo, ranked = min(combos, key=lambda x: x[0])
    best = ranked[0]
    permutation = kit.place(best, [c for c in combo if c is not best], spec.get('target_position'), seed, spec['id'],
                            key=lambda c: c['id'])
    options = [dict(label=l, value='candidate_%s.xyz' % l) for l in kit.LABELS]   # dataset ids stay reviewer-side
    verdicts = [c is best and all(checks[c['id']][k] for k in CONSTRAINTS) for c in permutation]
    key = kit.validate_verdicts([dict(o, source=c['id']) for o, c in zip(options, permutation)], verdicts,
                               key=lambda o: o['source'])
    margin = value(ranked[0]) - value(ranked[1])
    ref = best[objective['key']]
    audit = []
    for l, c in zip(kit.LABELS, permutation):
        diff = c[objective['key']] - ref
        audit.append(dict(label=l, value='candidate_%s.xyz' % l, source_id=c['id'], is_correct=c is best, property=c[objective['key']],
                          difference_from_best=round(diff, 6), unit=objective['unit'],
                          rg_A=round(rg(c['xyz']), 4), change_from_S0_A=round(distance_rmsd(s0['xyz'], c['xyz']), 4),
                          constraints=checks[c['id']],
                          reason='满足约束且目标值唯一最优（领先第二名 %.4f %s）。' % (margin, objective['unit']) if c is best else
                          '满足约束，但目标值比正确项差 %.4f %s（计算证据，非实验）。' % (abs(diff), objective['unit'])))
    radii = sorted(permutation, key=lambda c: rg(c['xyz']))
    change = sorted(permutation, key=lambda c: distance_rmsd(s0['xyz'], c['xyz']))
    shortcuts = dict(most_compact_rg=radii[0] is best, most_extended_rg=radii[-1] is best,
                     closest_to_S0=change[0] is best, farthest_from_S0=change[-1] is best)
    inputs = [dict(name='S0.xyz', format='xyz', unit='angstrom',
                   text=kit.xyz_text(elements, s0['xyz'], 'S0 starting conformer, angstrom'))]
    for l, c in zip(kit.LABELS, permutation):
        inputs.append(dict(name='candidate_%s.xyz' % l, format='xyz', unit='angstrom',
                           text=kit.xyz_text(elements, c['xyz'], 'candidate %s, angstrom' % l)))
    for item in inputs:
        kit.parse_xyz(item['text'])
    formula = ''.join('%s%s' % (e, elements.count(e) if elements.count(e) > 1 else '')
                      for e in sorted(set(elements), key=lambda e: (e != 'C', e != 'H', e)))
    question = ('S0 is a conformer of a neutral %s molecule. You may change it only by rotating about single bonds: '
                'the same atoms in the same order, the same bonds and the same configuration at every stereocentre. '
                'Goal: obtain %s. All four candidates A–D satisfy the allowed modification. Which candidate best meets the goal?') % (
        formula, objective['text'])
    return dict(
        question=question,
        scope=spec['scope'],
        inputs=inputs,
        numeric=None,
        options=options, correct_label=key, option_audit=audit,
        excluded_candidates=[dict(id=k, **v) for k, v in checks.items() if 'excluded' in v or not all(v[x] for x in CONSTRAINTS)],
        rank=None,
        checks=dict(objective=spec['objective'], margin=round(margin, 6), required_margin=objective['margin'],
                    margin_basis=objective['margin_basis'], level=data['level'], s0=spec['s0'],
                    candidate_pool=len(unique), valid_sets=len(combos), stereocentres=len(chiral0),
                    shortcut_diagnostics=shortcuts,
                    selection_rule='在满足约束且唯一最优的四元组中，优先让正确项不是回转半径最小或最大者，其次优先领先幅度 ≥1.5 倍阈值，再按种子选择。',
                    limits='计算证据仅对所述理论水平与给定几何成立；不是实验构象分布、自由能或开放式分子设计。'),
        scales=dict(input_nm=kit.dmax(s0['xyz']) / 10, reasoning_nm=kit.dmax(s0['xyz']) / 10,
                    reasoning_definition='整分子构象比较：S0 最大原子间距'),
        input_hashes={spec['asset']: kit.sha256(raw)})
