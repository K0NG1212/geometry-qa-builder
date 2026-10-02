"""DNA-linked gold-nanoparticle superlattices (materials, 10-100 nm): paper-parameter models.

Inputs are the crystallites built by tools/build_superlattice_assets.py from the SAXS unit-cell
edges in Table 1 of Hill et al., Nano Lett. 2008, 8, 2341 (see sources.json). Every question is
about the lattice period (nearest-neighbour spacing, cell edge, plane spacing, Bragg peaks, filling),
all between about 20 and 80 nm, so the reasoning scale sits in the 10-100 nm cell even though each
crystallite is about 200 nm across.
Answers are computed from the coordinates as written and cross-checked against the Table 1 edge.
"""
import math
from . import kit

VERSION = '0.1.0'
SHELL_TOL = 1e-4          # nm; coordinates carry 6 decimals
PAPER = 'https://doi.org/10.1021/nl8011787'


def load(root, asset):
    raw = (root / 'docs' / asset).read_bytes()
    text = raw.decode('utf-8')
    return text, kit.parse_xyz(text, max_atoms=2000)[1], kit.sha256(raw)


def centre_index(points):
    c = [math.fsum(p[k] for p in points) / len(points) for k in range(3)]
    return min(range(len(points)), key=lambda i: math.dist(points[i], c))


def shells(points, index):
    ds = sorted((math.dist(points[index], p), j) for j, p in enumerate(points) if j != index)
    groups = []
    for d, j in ds:
        if groups and d - groups[-1][0] <= SHELL_TOL:
            groups[-1][1].append(j)
        else:
            groups.append((d, [j]))
    return [(math.fsum(math.dist(points[index], points[j]) for j in g) / len(g), g) for _, g in groups]


def lattice(points, spec):
    """Nearest-neighbour spacing and FCC cell edge from the coordinates, checked against Table 1."""
    groups = shells(points, centre_index(points))
    (d1, g1), (d2, g2) = groups[0], groups[1]
    if len(g1) != 12 or len(g2) != 6 or abs(d2 / d1 - math.sqrt(2)) > 1e-5:
        raise ValueError('Not an FCC environment around the central particle')
    a = d2
    if abs(a - spec['a_nm']) > 1e-4:
        raise ValueError('Crystallite edge does not match the Table 1 value')
    return dict(nn=d1, a=a, groups=groups)


def gold_percent(a, core):
    return 4 * (4 / 3) * math.pi * (core / 2) ** 3 / a ** 3 * 100


def q_star(a):
    return 2 * math.pi * math.sqrt(3) / a


def q_200(a):
    return 4 * math.pi / a


CONDITIONS = ('Model conditions: the only measured input is the unit-cell size that Hill et al. (Nano Lett. 2008, Table 1) obtained '
              'from SAXS; the particle centres sit on an ideal, perfectly ordered lattice with no vacancies, stacking faults, positional '
              '(thermal) disorder or particle-size dispersion, which is the idealization the paper uses to index its SAXS peaks. Each '
              'crystallite is a finite cut of about 177 particles in an arbitrary orientation.')
SUBJECT = ('The XYZ file lists the centres of the gold nanoparticles in a model crystallite of a DNA-linked gold-nanoparticle '
           'superlattice (coordinates in nm; built from a published SAXS unit-cell size). ' + CONDITIONS)


def packet(spec, inputs, question, options, key, audit, rejected, rank, numeric, checks, input_nm, reasoning_nm, definition, hashes):
    return dict(question=question, scope=spec['scope'], inputs=inputs, numeric=numeric, options=options, correct_label=key,
                option_audit=audit, excluded_candidates=rejected, rank=rank, checks=checks,
                scales=dict(input_nm=input_nm, reasoning_nm=reasoning_nm, reasoning_definition=definition), input_hashes=hashes)


def build_shell(spec, root, seed):
    text, pts, digest = load(root, spec['asset'])
    lat = lattice(pts, spec)
    groups = lat['groups']
    far = max(range(len(pts)), key=lambda i: math.dist(pts[i], pts[centre_index(pts)]))
    surface = shells(pts, far)[0]
    fmt = lambda n, d: '%d at %s nm' % (n, kit.display(d, 2))
    right = fmt(12, lat['nn'])
    candidates = [('second_shell', fmt(len(groups[1][1]), groups[1][0]), 3, '报告了第二壳层（常规晶胞边长处的 6 个）。'),
                  ('surface_particle', fmt(len(surface[1]), surface[0]), 3, '数的是晶粒表面粒子的最近邻（表面缺配位）。'),
                  ('third_shell', fmt(len(groups[2][1]), groups[2][0]), 2, '报告了第三壳层。'),
                  ('bcc_assumption', fmt(8, lat['nn']), 2, '误认作体心立方，按 8 个最近邻计。'),
                  ('mixed_shells', fmt(len(groups[1][1]), lat['nn']), 1, '距离取最近壳层，个数取第二壳层。')]
    pool, rejected = [], []
    for rule, value, plaus, reason in candidates:
        if value == right or value in [p[1] for p in pool]:
            rejected.append(dict(rule=rule, value=value, reason='与其他选项重复'))
        else:
            pool.append((rule, value, reason, plaus))
    pool.sort(key=lambda p: (-p[3], kit.digest(seed, spec['id'], p[0])))
    chosen = pool[:3]
    rejected += [dict(rule=p[0], value=p[1], reason='有效但未选（可信度排序）') for p in pool[3:]]
    order = kit.place(('correct', right, '中心粒子的最近壳层：12 个，%.6f nm（= a/√2）。' % lat['nn'], 3), chosen,
                      spec.get('target_position'), seed, spec['id'], key=lambda p: p[0])
    options = [dict(label=l, value=p[1]) for l, p in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [p[0] == 'correct' for p in order])
    audit = [dict(label=l, value=p[1], rule=p[0], reason=p[2], is_correct=p[0] == 'correct') for l, p in zip(kit.LABELS, order)]
    question = ('%s For the particle nearest the centroid of all particles, how many particles form its nearest-neighbour shell, '
                'and at what centre-to-centre distance? Distances are rounded to 0.01 nm.' % SUBJECT)
    shell_pts = [pts[centre_index(pts)]] + [pts[j] for j in groups[0][1]]
    return packet(spec, [dict(name=spec['asset'].rsplit('/', 1)[1], format='xyz', unit='nm', text=text)], question, options, key,
                  audit, rejected, None, None,
                  dict(particles=len(pts), shells=[dict(distance_nm=round(d, 6), count=len(g)) for d, g in groups[:3]],
                       a_nm=lat['a'], table1=spec['table1'], limits='按论文 SAXS 晶胞参数构建的理想 FCC 模型，不是实测粒子坐标。'),
                  kit.dmax(pts), kit.dmax(shell_pts), '中心粒子与最近壳层的最大间距', {spec['asset']: digest})


NUMERIC = {
    'cell_edge': dict(decimals=2, tol='0.005', sep='1.00', unit='nm', ability='perception',
                      ask='What is the edge length of the conventional cubic unit cell of this particle lattice, in nm?'),
    'd111': dict(decimals=2, tol='0.005', sep='1.00', unit='nm', ability='perception',
                 ask='What is the spacing between adjacent close-packed (most densely populated) lattice planes of the particles, in nm?'),
    'q_star': dict(decimals=4, tol='0.00005', sep='0.0050', unit='nm^-1', ability='inference',
                   ask='Treat the particles as identical point scatterers on a perfect, infinite lattice with this geometry. At what '
                       'q (in nm⁻¹, q = 4π sinθ/λ) does the first (lowest-q) Bragg reflection with nonzero intensity appear?'),
    'q_200': dict(decimals=4, tol='0.00005', sep='0.0050', unit='nm^-1', ability='inference',
                  ask='Treat the particles as identical point scatterers on a perfect, infinite lattice with this geometry. At what '
                      'q (in nm⁻¹, q = 4π sinθ/λ) does the second distinct Bragg reflection with nonzero intensity appear?'),
    'gold_fraction': dict(decimals=3, tol='0.0005', sep='0.050', unit='%', ability='inference',
                          ask='Each particle is a solid gold sphere with a core diameter of %s nm and the DNA shell contains no gold. '
                              'Treating the lattice as perfect and infinite, what percentage of the total volume is gold?'),
}


def numeric_candidates(ask, a, nn, core):
    s2, s3 = math.sqrt(2), math.sqrt(3)
    if ask == 'cell_edge':
        return a, [dict(rule='nearest_neighbour', value=nn, plausibility=3, reason='把最近邻间距当作晶胞边长。'),
                   dict(rule='face_diagonal', value=a * s2, plausibility=2, reason='报告了面对角线（2 倍最近邻）。'),
                   dict(rule='body_diagonal', value=a * s3, plausibility=1, reason='报告了体对角线。'),
                   dict(rule='third_shell_distance', value=a * math.sqrt(1.5), plausibility=2, reason='把第三近邻距离当作晶胞边长。'),
                   dict(rule='d111', value=a / s3, plausibility=2, reason='报告了密排面间距。'),
                   dict(rule='d200', value=a / 2, plausibility=2, reason='报告了 (200) 面间距 a/2。'),
                   dict(rule='primitive_cell_root', value=a / 4 ** (1 / 3), plausibility=2,
                        reason='取初基胞体积（a³/4）的立方根，而问的是常规立方晶胞。')]
    if ask == 'd111':
        return a / s3, [dict(rule='d200', value=a / 2, plausibility=3, reason='报告了 (200) 面间距 a/2，不是最密排面。'),
                        dict(rule='nearest_neighbour', value=nn, plausibility=2, reason='把最近邻间距当作面间距。'),
                        dict(rule='in_layer_row_spacing', value=nn * s3 / 2, plausibility=2, reason='算成密排层内相邻原子行的间距。'),
                        dict(rule='d220', value=a / (2 * s2), plausibility=2, reason='报告了 (220) 面间距。'),
                        dict(rule='cell_edge', value=a, plausibility=2, reason='报告了晶胞边长而非面间距。'),
                        dict(rule='half_nearest_neighbour', value=nn / 2, plausibility=1, reason='取最近邻间距的一半。')]
    if ask == 'q_star':
        return q_star(a), [dict(rule='q_100_forbidden', value=2 * math.pi / a, plausibility=3, reason='用 (100)，而 FCC 中 (100) 消光。'),
                           dict(rule='q_from_nearest_neighbour', value=2 * math.pi / nn, plausibility=2, reason='把最近邻间距当作面间距。'),
                           dict(rule='q_200', value=q_200(a), plausibility=3, reason='报告了第二个反射 (200)。'),
                           dict(rule='missing_two_pi', value=s3 / a, plausibility=2, reason='漏掉 2π（把 1/d 当作 q）。'),
                           dict(rule='per_angstrom', value=q_star(a) / 10, plausibility=1, reason='以 Å⁻¹ 数值报告。'),
                           dict(rule='body_diagonal_spacing', value=2 * math.pi / (a * s3), plausibility=1, reason='把体对角线当作面间距。')]
    if ask == 'q_200':
        return q_200(a), [dict(rule='q_111_first_peak', value=q_star(a), plausibility=3, reason='报告了第一个反射 (111)。'),
                          dict(rule='q_100_forbidden', value=2 * math.pi / a, plausibility=2, reason='把消光的 (100) 当作反射。'),
                          dict(rule='q_220', value=2 * math.pi * 2 * s2 / a, plausibility=2, reason='报告了 (220)，跳过了 (200)。'),
                          dict(rule='missing_two_pi', value=2 / a, plausibility=2, reason='漏掉 2π。'),
                          dict(rule='q_from_nearest_neighbour', value=2 * math.pi / nn, plausibility=1, reason='把最近邻间距当作面间距。'),
                          dict(rule='per_angstrom', value=q_200(a) / 10, plausibility=1, reason='以 Å⁻¹ 数值报告。')]
    f = gold_percent(a, core)
    return f, [dict(rule='one_particle_per_cell', value=f / 4, plausibility=3, reason='每个常规晶胞只算 1 个粒子（FCC 为 4 个）。'),
               dict(rule='two_particles_per_cell', value=f / 2, plausibility=2, reason='按体心立方每胞 2 个粒子计。'),
               dict(rule='diameter_as_radius', value=f * 8, plausibility=2, reason='把直径当半径代入球体积。'),
               dict(rule='nearest_neighbour_cube', value=f * 2 * math.sqrt(2) / 4, plausibility=2,
                    reason='用最近邻间距的立方作为每个粒子的体积。'),
               dict(rule='fraction_not_percent', value=f / 100, plausibility=1, reason='给出了体积分数而非百分数。'),
               dict(rule='nearest_neighbour_as_cell_edge', value=f * 2 * math.sqrt(2), plausibility=2,
                    reason='用最近邻间距当作常规晶胞边长（仍按每胞 4 个粒子）。'),
               dict(rule='four_per_primitive_cell', value=f * 4, plausibility=2, reason='用初基胞体积 a³/4，却仍按 4 个粒子计。')]


def build_numeric(spec, root, seed):
    text, pts, digest = load(root, spec['asset'])
    lat = lattice(pts, spec)
    ask, cfg = spec['ask'], NUMERIC[spec['ask']]
    value, cands = numeric_candidates(ask, lat['a'], lat['nn'], spec.get('core_nm'))
    picked, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=cfg['decimals'], tolerance=cfg['tol'],
                                                      min_separation=cfg['sep'], seed=seed, context=spec['id'], lower=0,
                                                      target=spec.get('target_position'),
                                                      distractor_separation=str(float(cfg['sep']) / 2))
    options, audit = kit.label_numeric(value, picked, decimals=cfg['decimals'], unit=cfg['unit'], seed=seed, context=spec['id'],
                                       correct_reason='由坐标得 FCC：最近邻 12 个 %.4f nm，第二壳层 6 个 a = %.4f nm；按定义计算。'
                                       % (lat['nn'], lat['a']))
    key = kit.validate_numeric(options, value, decimals=cfg['decimals'], tolerance=cfg['tol'], min_separation=cfg['sep'],
                               unit=cfg['unit'], distractor_separation=str(float(cfg['sep']) / 2))
    ask_text = cfg['ask'] % spec['core_nm'] if ask == 'gold_fraction' else cfg['ask']
    question = '%s %s' % (SUBJECT, ask_text)
    return packet(spec, [dict(name=spec['asset'].rsplit('/', 1)[1], format='xyz', unit='nm', text=text)], question, options, key,
                  audit, rejected, dict(target=goal, achieved=rank),
                  dict(value=kit.display(value, cfg['decimals']), unit=cfg['unit'], decimals=cfg['decimals'], tolerance=cfg['tol']),
                  dict(particles=len(pts), nn_nm=lat['nn'], a_nm=lat['a'], table1=spec['table1'], core_nm=spec.get('core_nm'),
                       limits='按论文 SAXS 晶胞参数构建的理想 FCC 模型；Bragg 位置对应无限完美晶格，不含形状因子与峰宽。'),
                  kit.dmax(pts), lat['a'], '晶格周期：常规晶胞边长 a', {spec['asset']: digest})


def build_perception(spec, root, seed):
    if NUMERIC[spec['ask']]['ability'] != 'perception':
        raise ValueError('Not a perception quantity: ' + spec['ask'])
    return build_numeric(spec, root, seed)


def build_inference(spec, root, seed):
    if NUMERIC[spec['ask']]['ability'] != 'inference':
        raise ValueError('Not an inference quantity: ' + spec['ask'])
    return build_numeric(spec, root, seed)


GOALS = {
    'q_star': 'its first Bragg reflection (lowest q with nonzero intensity, identical point scatterers, q = 4π sinθ/λ) is closest to '
              'q = %s nm⁻¹',
    'nn': 'the centre-to-centre nearest-neighbour spacing of the particles is closest to %s nm',
    'fraction': 'the nearest-neighbour spacing is as large as possible while at least %s %% of the volume is gold '
                '(solid gold cores of diameter %s nm; perfect infinite lattice)',
}


def build_design(spec, root, seed):
    """Design selection among four real linker choices (Table 1), each with a model crystallite."""
    rows, inputs, hashes = [], [], {}
    for asset in spec['candidates']:
        text, pts, digest = load(root, asset)
        sub = dict(spec, a_nm=spec['edges'][asset])
        lat = lattice(pts, sub)
        name = asset.rsplit('/', 1)[1]
        linker = name[len('Au-FCC-'):-len('.xyz')]
        rows.append(dict(asset=asset, name=name, linker=linker, nn=lat['nn'], a=lat['a'], q=q_star(lat['a']),
                         gold=gold_percent(lat['a'], spec['core_nm']), extent=kit.dmax(pts)))
        inputs.append(dict(name=name, format='xyz', unit='nm', text=text))
        hashes[asset] = digest
    goal, t = spec['goal'], spec['target']
    if goal in ('q_star', 'nn'):
        prop = 'q' if goal == 'q_star' else 'nn'
        ranked = sorted(rows, key=lambda r: abs(r[prop] - t))
        best, runner = ranked[0], ranked[1]
        if abs(runner[prop] - t) < 1.5 * abs(best[prop] - t) or abs(runner[prop] - t) - abs(best[prop] - t) < 0.02 * t:
            raise ValueError('Winning margin too small')
        wrong = {'q_star': [('q_from_nearest_neighbour', lambda r: 2 * math.pi / r['nn'], '把最近邻间距当作面间距（q = 2π/D）时它最接近目标。'),
                            ('q_200_as_first', lambda r: q_200(r['a']), '把 (200) 当作首峰（q = 4π/a）时它最接近目标。'),
                            ('q_100_forbidden', lambda r: 2 * math.pi / r['a'], '用消光的 (100)（q = 2π/a）时它最接近目标。')],
                 'nn': [('cell_edge_as_spacing', lambda r: r['a'], '把常规晶胞边长当作最近邻间距时它最接近目标。'),
                        ('plane_spacing_as_spacing', lambda r: r['a'] / math.sqrt(3), '把密排面间距当作粒子间距时它最接近目标。'),
                        ('face_diagonal', lambda r: r['a'] * math.sqrt(2), '把面对角线当作间距时它最接近目标。')]}[goal]
        why = {}
        for rule, f, reason in wrong:
            pick = min(rows, key=lambda r: abs(f(r) - t))
            if pick is not best and pick['linker'] not in why:
                why[pick['linker']] = (rule, reason, 3)
        verdict = lambda r: r is best
        evidence = lambda r: '%s = %.4f' % ('q*' if prop == 'q' else 'D', r[prop])
        for r in rows:
            if r is not best and r['linker'] not in why:
                why[r['linker']] = ('farther_from_target', '按正确定义离目标更远（%s）。' % evidence(r), 2)
        target_text = GOALS[goal] % t
    else:
        ok = [r for r in rows if r['gold'] >= t]
        if not ok:
            raise ValueError('No candidate meets the constraint')
        best = max(ok, key=lambda r: r['nn'])
        if min(abs(r['gold'] - t) for r in rows) < 0.05 * t:
            raise ValueError('A candidate sits too close to the constraint')
        why = {}
        for r in rows:
            if r is best:
                continue
            if r['gold'] < t:
                wrong_pass = r['gold'] * 8 >= t
                why[r['linker']] = ('violates_gold_constraint' if not wrong_pass else 'diameter_as_radius_passes',
                                    ('金含量 %.3f%% 低于要求；若把直径当半径（×8）会误判为满足。' % r['gold']) if wrong_pass
                                    else '金含量 %.3f%% 低于要求。' % r['gold'], 3 if wrong_pass else 2)
            elif r['gold'] == max(x['gold'] for x in rows):
                why[r['linker']] = ('highest_gold_not_largest_spacing', '金含量最高（%.3f%%），但间距不是满足条件中最大的。' % r['gold'], 2)
            else:
                why[r['linker']] = ('satisfies_but_smaller_spacing', '满足金含量（%.3f%%），但间距 %.2f nm 不是最大。' % (r['gold'], r['nn']), 2)
        target_text = GOALS['fraction'] % (t, spec['core_nm'])
    right = '%s (%s)' % (best['linker'], best['name'])
    others = [(why[r['linker']][0], '%s (%s)' % (r['linker'], r['name']), why[r['linker']][1], why[r['linker']][2])
              for r in rows if r is not best]
    reason_ok = {'q_star': 'q* = 2π√3/a = %.4f nm⁻¹，最接近目标。' % best['q'], 'nn': '最近邻 %.4f nm，最接近目标。' % best['nn'],
                 'fraction': '满足金含量（%.3f%%）的候选中最近邻最大（%.2f nm）。' % (best['gold'], best['nn'])}[goal]
    order = kit.place(('correct', right, reason_ok, 3), others, spec.get('target_position'), seed, spec['id'], key=lambda p: p[0])
    options = [dict(label=l, value=p[1]) for l, p in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [p[0] == 'correct' for p in order])
    audit = [dict(label=l, value=p[1], rule=p[0], reason=p[2], is_correct=p[0] == 'correct') for l, p in zip(kit.LABELS, order)]
    question = ('The four XYZ files list the gold-nanoparticle centres (nm) of model crystallites of DNA-linked gold-nanoparticle '
                'superlattices assembled with four different duplex DNA linkers; each file is named after its linker and was built '
                'from that linker\'s published SAXS unit-cell size. %s You must choose one linker for a new superlattice such that %s. '
                'Which linker should you choose?' % (CONDITIONS, target_text))
    return packet(spec, inputs, question, options, key, audit, [], None, None,
                  dict(candidates=[{k: r[k] for k in ('linker', 'nn', 'a', 'q', 'gold')} for r in rows], goal=goal, target=t,
                       design_note='设计选择：四个候选均为论文中实际做出的连接子，性质由模型坐标计算。',
                       limits='按论文 SAXS 晶胞参数构建的理想 FCC 模型。'),
                  max(r['extent'] for r in rows),
                  max(r['a'] for r in rows), '晶格周期：候选中最大的常规晶胞边长 a', hashes)
