"""Twisted bilayer graphene moire superlattices (quantum, 10-100 nm): paper-parameter models.

Inputs are built by tools/build_moire_assets.py from published twist angles (Cao et al. 2018 devices
M1/M2/D1; Kerelsky et al. 2019 STM regions): AA-site maps (the STM bright-spot lattice) and one atomistic
two-layer patch. Every question concerns the moire lattice (period 12-18 nm), its cell area, or the
electron densities that fill its spin- and valley-degenerate bands (n_s = 4/A, Cao et al.).
Answers are computed from the coordinates and cross-checked against the published twist angle.
"""
import math
from . import kit

VERSION = '0.1.0'
A_NM = 0.246
TOL = 1e-5


def period(theta_deg):
    return A_NM / (2 * math.sin(math.radians(theta_deg) / 2))


def load_map(root, asset):
    raw = (root / 'docs' / asset).read_bytes()
    text = raw.decode('utf-8')
    lines = text.splitlines()
    rows = [l.split() for l in lines[2:] if l.strip()]
    if int(lines[0]) != len(rows) or any(len(r) != 3 or r[0] != 'AA' for r in rows):
        raise ValueError('Expected count, comment and "AA x y" rows')
    return text, [(float(r[1]), float(r[2])) for r in rows], kit.sha256(raw)


def map_lattice(pts, theta):
    c = (math.fsum(p[0] for p in pts) / len(pts), math.fsum(p[1] for p in pts) / len(pts))
    i = min(range(len(pts)), key=lambda k: math.dist(pts[k], c))
    d = sorted(math.dist(pts[i], p) for j, p in enumerate(pts) if j != i)
    first = [x for x in d if x - d[0] <= TOL]
    if len(first) != 6:
        raise ValueError('AA sites do not form a triangular lattice around the centre')
    lam = math.fsum(first) / 6
    if abs(lam - period(theta)) > 1e-4:
        raise ValueError('Moire period does not match the published twist angle')
    return lam


def area(lam):
    return math.sqrt(3) / 2 * lam ** 2


def density(lam, electrons):
    return electrons / area(lam) * 100          # nm^-2 -> 10^12 cm^-2


def layer_orientation(atoms, z):
    """Mean bond direction modulo 60 degrees for the layer at height z (angstrom)."""
    layer = [p for p in atoms if abs(p[2] - z) < 0.01]
    angles = []
    for i, p in enumerate(layer):
        for q in layer[i + 1:]:
            if abs(math.dist(p[:2], q[:2]) - A_NM * 10 / math.sqrt(3)) < 1e-3:
                angles.append(math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 60)
    ref = angles[0]
    return ref + math.fsum(((x - ref + 30) % 60) - 30 for x in angles) / len(angles)


MAP_SUBJECT = ('The file lists the centres of the AA-stacked regions (the bright spots of an STM topograph) of a model twisted '
               'bilayer graphene sample, coordinates in nm (rigid twist without lattice relaxation or strain; built from a published '
               'twist angle).')
ATOM_SUBJECT = ('The XYZ file lists all carbon atoms of both layers of a model twisted bilayer graphene near an AA-stacked site '
                '(angstrom; rigid twist, layer spacing 3.35 Å; built from a published twist angle).')
ASK = {
    'period': ('What is the moiré period (the moiré lattice constant), in nm?', 2, '0.005', '0.30', 'nm', 'perception'),
    'area': ('What is the area of one moiré unit cell, in nm²?', 1, '0.05', '3.0', 'nm^2', 'perception'),
    'n_full': ('What is the superlattice density n_s, the carrier density that completely fills one set of spin- and '
               'valley-degenerate moiré bands, in units of 10¹² cm⁻²?', 3, '0.0005', '0.050', '10^12 cm^-2', 'inference'),
    'n_half': ('What carrier density corresponds to half filling of one set of spin- and valley-degenerate moiré bands (where '
               'correlated insulators appear), in units of 10¹² cm⁻²?', 3, '0.0005', '0.050', '10^12 cm^-2', 'inference'),
    'twist': ('The graphene lattice constant is 0.246 nm. What twist angle between the two layers produces this moiré pattern, '
              'in degrees?', 3, '0.0005', '0.050', 'degree', 'inference'),
    'period_from_atoms': ('Assuming the two layers are unstrained and rigidly twisted, what is the moiré period (the moiré lattice '
                          'constant) of this bilayer, in nm?', 2, '0.005', '0.30', 'nm', 'inference'),
}


def candidates(ask, lam, theta):
    s3 = math.sqrt(3)
    if ask == 'period':
        return lam, [dict(rule='aa_to_ab_distance', value=lam / s3, plausibility=3, reason='报告了 AA 到 AB 区中心的距离 λ/√3。'),
                     dict(rule='row_spacing', value=lam * s3 / 2, plausibility=3, reason='报告了相邻 AA 行的间距 (√3/2)λ。'),
                     dict(rule='second_neighbour', value=lam * s3, plausibility=2, reason='报告了次近邻 AA 距离 √3λ。'),
                     dict(rule='half_period', value=lam / 2, plausibility=2, reason='报告了半个周期。'),
                     dict(rule='double_period', value=2 * lam, plausibility=2, reason='报告了隔一个 AA 位点的两近邻间距 2λ（六边形对角）。')]
    if ask == 'area':
        return area(lam), [dict(rule='square_cell', value=lam ** 2, plausibility=3, reason='按正方形晶胞 λ² 计算。'),
                           dict(rule='triangle_only', value=s3 / 4 * lam ** 2, plausibility=2, reason='只算了一个三角形（半个晶胞）。'),
                           dict(rule='hexagon_twice', value=s3 * lam ** 2, plausibility=2, reason='面积多乘了 2。'),
                           dict(rule='circle_of_half_period', value=math.pi * (lam / 2) ** 2, plausibility=1, reason='用直径为 λ 的圆面积。'),
                           dict(rule='ab_spacing_cell', value=s3 / 2 * (lam / s3) ** 2, plausibility=2, reason='用 AA–AB 距离当作晶格常数。')]
    if ask in ('n_full', 'n_half'):
        e = 4 if ask == 'n_full' else 2
        out = [dict(rule='no_degeneracy', value=density(lam, 1), plausibility=3, reason='每个晶胞只算 1 个电子，漏掉自旋×谷四重简并。'),
               dict(rule='spin_only', value=density(lam, 2 if e == 4 else 1), plausibility=2, reason='只计自旋简并，漏掉谷简并。'),
               dict(rule='square_cell', value=e / lam ** 2 * 100, plausibility=2, reason='晶胞面积按 λ² 计算。'),
               dict(rule='eight_per_cell', value=density(lam, 2 * e), plausibility=2, reason='多计了一倍（把两层各算一次）。'),
               dict(rule='per_cm2_unit_slip', value=density(lam, e) / 10, plausibility=1, reason='nm⁻² 到 cm⁻² 换算差 10 倍。'),
               dict(rule='ab_distance_as_period', value=density(lam / math.sqrt(3), e), plausibility=2,
                    reason='把 AA–AB 距离 λ/√3 当作莫尔周期，晶胞面积小 3 倍。')]
        if e == 2:
            out.append(dict(rule='full_filling', value=density(lam, 4), plausibility=3, reason='报告了完全填满（n_s）而非半满。'))
        return density(lam, e), out
    if ask == 'twist':
        return theta, [dict(rule='bond_length_as_lattice_constant', value=math.degrees(2 * math.asin(A_NM / s3 / (2 * lam))), plausibility=3,
                            reason='把 C–C 键长当作晶格常数。'),
                       dict(rule='half_angle', value=math.degrees(math.asin(A_NM / (2 * lam))), plausibility=2, reason='漏掉 θ = 2 arcsin(…) 的因子 2。'),
                       dict(rule='radians_as_degrees', value=math.radians(theta), plausibility=2, reason='以弧度数值当作度报告。'),
                       dict(rule='ab_distance_as_period', value=math.degrees(2 * math.asin(A_NM * s3 / (2 * lam))), plausibility=2,
                            reason='把 AA–AB 距离当作莫尔周期。'),
                       dict(rule='double_angle', value=2 * theta, plausibility=1, reason='报告了两倍转角。')]
    return lam, [dict(rule='sin_full_angle', value=A_NM / math.sin(math.radians(theta)) / 2, plausibility=3, reason='用 a/(2 sinθ)：转角没有取一半，周期约少一半。'),
                 dict(rule='bond_length_as_lattice_constant', value=lam / s3, plausibility=3, reason='把 C–C 键长当作晶格常数。'),
                 dict(rule='angle_of_one_layer', value=A_NM / (2 * math.sin(math.radians(theta) / 4)), plausibility=2,
                      reason='用单层相对参考方向的转角 θ/2 代替两层之间的转角。'),
                 dict(rule='row_spacing', value=lam * s3 / 2, plausibility=2, reason='报告了 AA 行间距。'),
                 dict(rule='angstrom_as_nm', value=lam * 10, plausibility=1, reason='埃当作纳米。'),
                 dict(rule='second_neighbour', value=lam * s3, plausibility=2, reason='报告了次近邻 AA 距离 √3λ。'),
                 dict(rule='layer_spacing_as_lattice_constant', value=0.335 / (2 * math.sin(math.radians(theta) / 2)), plausibility=2,
                      reason='把层间距 0.335 nm 当作晶格常数。')]


def build(spec, root, seed, ability):
    ask = spec['ask']
    text_q, decimals, tol, sep, unit, want = ASK[ask]
    if want != ability:
        raise ValueError('Quantity %s is not %s' % (ask, ability))
    theta = spec['twist_deg']
    raw = (root / 'docs' / spec['asset']).read_bytes()
    if ask == 'period_from_atoms':
        text = raw.decode('utf-8')
        atoms = kit.parse_xyz(text)[1]
        measured = (layer_orientation(atoms, 3.35) - layer_orientation(atoms, 0.0) + 30) % 60 - 30
        if abs(abs(measured) - theta) > 1e-4:
            raise ValueError('Layer twist does not match the published angle')
        lam = period(theta)
        subject, fmt, input_nm, digest = ATOM_SUBJECT, dict(format='xyz', unit='angstrom'), kit.dmax(atoms) / 10, kit.sha256(raw)
    else:
        text, pts, digest = load_map(root, spec['asset'])
        lam = map_lattice(pts, theta)
        subject, fmt, input_nm = MAP_SUBJECT, dict(format='aa-site-map', unit='nm'), max(math.dist(p, q) for p in pts for q in pts)
    value, cands = candidates(ask, lam, theta)
    picked, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=decimals, tolerance=tol, min_separation=sep, seed=seed,
                                                      context=spec['id'], lower=0, target=spec.get('target_position'),
                                                      distractor_separation=str(float(sep) / 2))
    options, audit = kit.label_numeric(value, picked, decimals=decimals, unit=unit, seed=seed, context=spec['id'],
                                       correct_reason='θ = %.2f°，λ = a/(2 sin(θ/2)) = %.4f nm，A = (√3/2)λ²，n_s = 4/A。' % (theta, lam))
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=sep, unit=unit,
                               distractor_separation=str(float(sep) / 2))
    return dict(question='%s %s' % (subject, text_q), scope=spec['scope'],
                inputs=[dict(name=spec['asset'].rsplit('/', 1)[1], text=text, **fmt)],
                numeric=dict(value=kit.display(value, decimals), unit=unit, decimals=decimals, tolerance=tol),
                options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
                checks=dict(twist_deg=theta, period_nm=lam, cell_area_nm2=area(lam), n_s_1e12=density(lam, 4), sample=spec['sample'],
                            limits='刚性转角模型（无晶格弛豫、无异质应变）；实测样品常有少量应变，使莫尔周期偏离理想值。'),
                scales=dict(input_nm=input_nm, reasoning_nm=lam, reasoning_definition='莫尔周期 λ'),
                input_hashes={spec['asset']: digest})


def build_geometry(spec, root, seed):
    return build(spec, root, seed, 'perception')


def build_inference(spec, root, seed):
    return build(spec, root, seed, 'inference')


GOALS = {'half': ('half filling of one set of spin- and valley-degenerate moiré bands occurs at a carrier density closest to %g × 10¹² cm⁻²',
                  lambda lam: density(lam, 2)),
         'full': ('the superlattice density n_s (complete filling of one set of spin- and valley-degenerate moiré bands) is closest to '
                  '%g × 10¹² cm⁻²', lambda lam: density(lam, 4)),
         'period': ('the moiré period is closest to %g nm', lambda lam: lam)}
WRONG = {'half': [('full_filling', lambda lam: density(lam, 4), '把半满当成完全填满'),
                  ('no_degeneracy', lambda lam: density(lam, 1), '漏掉自旋×谷简并'),
                  ('square_cell', lambda lam: 2 / lam ** 2 * 100, '晶胞面积按 λ² 计算')],
         'full': [('no_degeneracy', lambda lam: density(lam, 1), '漏掉自旋×谷简并'),
                  ('spin_only', lambda lam: density(lam, 2), '只计自旋简并'),
                  ('square_cell', lambda lam: 4 / lam ** 2 * 100, '晶胞面积按 λ² 计算')],
         'period': [('aa_to_ab_distance', lambda lam: lam / math.sqrt(3), '把 AA–AB 距离当作周期'),
                    ('second_neighbour', lambda lam: lam * math.sqrt(3), '把次近邻 AA 距离当作周期'),
                    ('row_spacing', lambda lam: lam * math.sqrt(3) / 2, '把 AA 行间距当作周期')]}


def build_design(spec, root, seed):
    rows, inputs, hashes = [], [], {}
    for asset, (sample, theta) in zip(spec['candidates'], spec['twists']):
        text, pts, digest = load_map(root, asset)
        lam = map_lattice(pts, theta)
        rows.append(dict(sample=sample, name=asset.rsplit('/', 1)[1], lam=lam, theta=theta))
        inputs.append(dict(name=asset.rsplit('/', 1)[1], format='aa-site-map', unit='nm', text=text))
        hashes[asset] = digest
    goal, t = spec['goal'], spec['target']
    text_goal, prop = GOALS[goal]
    ranked = sorted(rows, key=lambda r: abs(prop(r['lam']) - t))
    best, runner = ranked[0], ranked[1]
    if abs(prop(runner['lam']) - t) < 1.5 * abs(prop(best['lam']) - t) or abs(prop(runner['lam']) - t) - abs(prop(best['lam']) - t) < 0.02 * t:
        raise ValueError('Winning margin too small')
    why = {}
    for rule, f, note in WRONG[goal]:
        pick = min(rows, key=lambda r: abs(f(r['lam']) - t))
        if pick is not best and pick['sample'] not in why:
            why[pick['sample']] = (rule, '%s时它最接近目标（%.3f）。' % (note, f(pick['lam'])), 3)
    for r in rows:
        if r is not best and r['sample'] not in why:
            why[r['sample']] = ('farther_from_target', '正确计算为 %.3f，离目标更远。' % prop(r['lam']), 2)
    right = '%s (%s)' % (best['sample'], best['name'])
    others = [(why[r['sample']][0], '%s (%s)' % (r['sample'], r['name']), why[r['sample']][1], why[r['sample']][2]) for r in rows if r is not best]
    order = kit.place(('correct', right, '正确计算为 %.3f，最接近目标。' % prop(best['lam']), 3), others, spec.get('target_position'),
                      seed, spec['id'], key=lambda p: p[0])
    options = [dict(label=l, value=p[1]) for l, p in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [p[0] == 'correct' for p in order])
    audit = [dict(label=l, value=p[1], rule=p[0], reason=p[2], is_correct=p[0] == 'correct') for l, p in zip(kit.LABELS, order)]
    question = ('The four files list the centres of the AA-stacked regions (nm) of model twisted bilayer graphene samples (files named by '
                'sample; each built from that sample\'s published twist angle; rigid twist without relaxation or strain). You must choose '
                'one sample such that %s. Which sample should you choose?' % (text_goal % t))
    return dict(question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
                option_audit=audit, excluded_candidates=[], rank=None,
                checks=dict(candidates=[dict(sample=r['sample'], twist_deg=r['theta'], period_nm=r['lam'], value=prop(r['lam'])) for r in rows],
                            goal=goal, target=t, design_note='设计选择：候选均为论文中的实际样品（转角为报道值），性质由模型坐标计算。',
                            limits='刚性转角模型（无晶格弛豫、无异质应变）。'),
                scales=dict(input_nm=2 * 45.0, reasoning_nm=max(r['lam'] for r in rows), reasoning_definition='候选中最大的莫尔周期 λ'),
                input_hashes=hashes)
