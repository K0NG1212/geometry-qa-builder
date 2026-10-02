"""Colloidal (opal) photonic crystals (materials, 100-1000 nm): paper-parameter models.

Inputs are the touching-sphere FCC crystallites built by tools/build_opal_assets.py from published sphere
diameters (polystyrene series of Gazmeh et al., Sci. Rep. 2025; silica opal of Fookes et al., Sensors 2023).
Every question concerns the lattice period (sphere diameter, close-packed plane spacing, cell edge) or the
visible/near-infrared Bragg reflection it produces, all between about 170 and 900 nm.
Answers are computed from the coordinates as written and cross-checked against the published diameter.
"""
import math
from . import kit
from .superlattice import shells, centre_index, numeric_candidates

VERSION = '0.1.0'
FILL = math.pi / (3 * math.sqrt(2))     # touching spheres on an FCC lattice


def load(root, asset):
    raw = (root / 'docs' / asset).read_bytes()
    text = raw.decode('utf-8')
    lines = text.splitlines()
    rows = [l.split() for l in lines[2:] if l.strip()]
    if int(lines[0]) != len(rows) or any(len(r) != 4 or r[0] != 'sphere' for r in rows):
        raise ValueError('Expected count, comment and "sphere x y z" rows')
    return text, [tuple(float(v) for v in r[1:]) for r in rows], kit.sha256(raw)


def lattice(points, diameter):
    groups = shells(points, centre_index(points))
    (d1, g1), (d2, g2) = groups[0], groups[1]
    if len(g1) != 12 or len(g2) != 6 or abs(d2 / d1 - math.sqrt(2)) > 1e-5:
        raise ValueError('Not a touching-sphere FCC environment')
    if abs(d1 - diameter) > 1e-4:
        raise ValueError('Sphere spacing does not match the published diameter')
    return dict(nn=d1, a=d2, d111=d2 / math.sqrt(3))


def n_eff(spec):
    if spec.get('n_eff'):
        return spec['n_eff']
    return math.sqrt(FILL * spec['n_sphere'] ** 2 + (1 - FILL) * spec['n_medium'] ** 2)


def peak(d111, n, theta_deg):
    return 2 * d111 * math.sqrt(n * n - math.sin(math.radians(theta_deg)) ** 2)


def optics_text(spec):
    if spec.get('n_eff'):
        return 'Model the film as this lattice with its close-packed planes parallel to the film surface, and use an effective ' \
               'refractive index of %.2f for the film.' % spec['n_eff']
    return ('Model the film as this lattice with its close-packed planes parallel to the film surface. The spheres have refractive '
            'index %.2f and the voids are filled with a medium of refractive index %.2f; take the effective index from the '
            'volume-weighted average of the squared refractive indices (n_eff² = Σ f_i n_i²), using the sphere volume fraction '
            'of this packing.' % (spec['n_sphere'], spec['n_medium']))


PAPERS = {'polystyrene': 'Gazmeh et al. (Sci. Rep. 2025, Table 3; field-emission SEM)', 'silica': 'Fookes et al. (Sensors 2023; SEM)'}


def conditions(material):
    return ('Model conditions: the only measured input is the sphere diameter reported by %s; the spheres are identical (no size '
            'dispersion), touch their neighbours and sit on an ideal close-packed lattice without stacking faults, vacancies or cracks, '
            'which is the idealization behind the paper\'s Bragg-law estimate of the reflection peak. Each crystallite is a finite cut of '
            '177 spheres in an arbitrary orientation.' % PAPERS[material])


def subject(spec):
    return ('The file lists the sphere centres (nm) of a model %s opal crystallite built from a published sphere diameter; '
            'neighbouring spheres touch. %s' % (spec['material'], conditions(spec['material'])))


PERCEPTION = {'diameter': 'What is the sphere diameter, in nm?',
              'd111': 'What is the spacing between adjacent close-packed (most densely populated) planes of sphere centres, in nm?',
              'cell_edge': 'What is the edge length of the conventional cubic unit cell of the sphere lattice, in nm?'}


def result(spec, text, question, value, cands, decimals, tol, sep, unit, seed, reason, checks, input_nm, reasoning_nm, digest):
    picked, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=decimals, tolerance=tol, min_separation=sep, seed=seed,
                                                      context=spec['id'], lower=0, target=spec.get('target_position'),
                                                      distractor_separation=str(float(sep) / 2))
    options, audit = kit.label_numeric(value, picked, decimals=decimals, unit=unit, seed=seed, context=spec['id'], correct_reason=reason)
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=sep, unit=unit,
                               distractor_separation=str(float(sep) / 2))
    return dict(question=question, scope=spec['scope'],
                inputs=[dict(name=spec['asset'].rsplit('/', 1)[1], format='sphere-centres', unit='nm', text=text)],
                numeric=dict(value=kit.display(value, decimals), unit=unit, decimals=decimals, tolerance=tol),
                options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
                checks=checks, scales=dict(input_nm=input_nm, reasoning_nm=reasoning_nm, reasoning_definition='晶格周期：常规晶胞边长 a'),
                input_hashes={spec['asset']: digest})


def build_geometry(spec, root, seed):
    text, pts, digest = load(root, spec['asset'])
    lat = lattice(pts, spec['diameter_nm'])
    a, d = lat['a'], lat['nn']
    if spec['ask'] == 'diameter':
        value, cands = d, [dict(rule='cell_edge', value=a, plausibility=3, reason='报告了常规晶胞边长（次近邻距离）。'),
                           dict(rule='radius', value=d / 2, plausibility=3, reason='报告了半径。'),
                           dict(rule='d111', value=a / math.sqrt(3), plausibility=2, reason='报告了密排面间距。'),
                           dict(rule='half_cell_edge', value=a / 2, plausibility=2, reason='取晶胞边长的一半。'),
                           dict(rule='face_diagonal', value=a * math.sqrt(2), plausibility=1, reason='报告了面对角线（2D）。')]
    else:
        value, cands = numeric_candidates(spec['ask'], a, d, None)
    checks = dict(spheres=len(pts), diameter_nm=d, a_nm=a, published_diameter_nm=spec['diameter_nm'], sample=spec['sample'],
                  limits='按论文球径构建的理想接触球 FCC 模型，不含尺寸分布与堆垛缺陷。')
    return result(spec, text, '%s %s' % (subject(spec), PERCEPTION[spec['ask']]), value, cands, 1, '0.05', '3.0', 'nm', seed,
                  '由坐标：12 个最近邻在 %.4f nm（= 球径），6 个次近邻在 a = %.4f nm。' % (d, a), checks, kit.dmax(pts), a, digest)


def build_bragg(spec, root, seed):
    text, pts, digest = load(root, spec['asset'])
    lat = lattice(pts, spec['diameter_nm'])
    d111, D, n = lat['d111'], lat['nn'], n_eff(spec)
    theta = spec.get('theta_deg', 0)
    s2 = math.sin(math.radians(theta)) ** 2
    if spec['ask'] == 'peak':
        value = peak(d111, n, theta)
        cands = [dict(rule='diameter_as_spacing', value=peak(D, n, theta), plausibility=3, reason='把球径当作密排面间距。'),
                 dict(rule='no_factor_two', value=value / 2, plausibility=2, reason='Bragg 条件漏掉因子 2。'),
                 dict(rule='d200_planes', value=peak(lat['a'] / 2, n, theta), plausibility=2, reason='用 (200) 面间距 a/2。'),
                 dict(rule='cell_edge_as_spacing', value=peak(lat['a'], n, theta), plausibility=2, reason='把常规晶胞边长当作面间距。')]
        if spec.get('n_eff'):
            cands += [dict(rule='no_refraction', value=2 * d111 * n * math.cos(math.radians(theta)), plausibility=3,
                           reason='用 2 d n cosθ，忽略了入射光在薄膜表面的折射（应为 √(n²−sin²θ)）。'),
                      dict(rule='ignore_angle', value=peak(d111, n, 0), plausibility=2, reason='忽略入射角，按正入射计算。'),
                      dict(rule='angle_from_surface', value=2 * d111 * math.sqrt(n * n - math.cos(math.radians(theta)) ** 2),
                           plausibility=2, reason='把入射角当作与表面的夹角。'),
                      dict(rule='sin_not_squared', value=2 * d111 * math.sqrt(n * n - math.sin(math.radians(theta))), plausibility=1,
                           reason='sinθ 未平方。')]
        else:
            ns, nm = spec['n_sphere'], spec['n_medium']
            cands += [dict(rule='linear_index_average', value=peak(d111, FILL * ns + (1 - FILL) * nm, theta), plausibility=3,
                           reason='对折射率本身而非其平方做体积平均。'),
                      dict(rule='no_index', value=peak(d111, 1.0, theta), plausibility=2, reason='忽略折射率（取 n = 1）。'),
                      dict(rule='sphere_index', value=peak(d111, ns, theta), plausibility=2, reason='用球的折射率代替有效折射率。'),
                      dict(rule='voids_as_air', value=peak(d111, math.sqrt(FILL * ns * ns + (1 - FILL)), theta) if nm != 1 else None,
                           plausibility=3, reason='没有把空隙中的介质折射率代入（仍按空气）。'),
                      dict(rule='wrong_fill_fraction', value=peak(d111, math.sqrt(0.5 * ns * ns + 0.5 * nm * nm), theta), plausibility=1,
                           reason='体积分数按 1:1 估计。')]
        question = ('%s %s %s What is the vacuum wavelength, in nm, of the first-order Bragg reflection from the close-packed planes?'
                    % (subject(spec), optics_text(spec),
                       'Light is incident from air at %g° from the film normal.' % theta if theta else 'Light is incident along the film normal.'))
        decimals, tol, sep, unit = 1, '0.05', '5.0', 'nm'
        reason = 'λ = 2 d111 √(n_eff² − sin²θ)，d111 = %.4f nm，n_eff = %.5f。' % (d111, n)
    else:
        lam = spec['target_nm']
        s = n * n - (lam / (2 * d111)) ** 2
        if not 0 < s < 1:
            raise ValueError('Target wavelength not reachable at any angle')
        value = math.degrees(math.asin(math.sqrt(s)))
        c = lam / (2 * d111 * n)
        cands = [dict(rule='no_refraction', value=math.degrees(math.acos(c)) if c <= 1 else None, plausibility=3,
                      reason='用 λ = 2 d n cosθ 反解，忽略折射。'),
                 dict(rule='from_surface', value=90 - value, plausibility=2, reason='报告了与薄膜表面的夹角。'),
                 dict(rule='diameter_as_spacing', value=math.degrees(math.asin(math.sqrt(n * n - (lam / (2 * D)) ** 2)))
                      if 0 < n * n - (lam / (2 * D)) ** 2 < 1 else None, plausibility=3, reason='把球径当作密排面间距。'),
                 dict(rule='sin_not_squared', value=math.degrees(math.asin(s)), plausibility=2, reason='解出 sinθ 时未开方。'),
                 dict(rule='refraction_angle_inside', value=math.degrees(math.asin(math.sqrt(s) / n)), plausibility=2,
                      reason='报告了膜内的折射角而非空气中的入射角。')]
        question = ('%s %s At what angle of incidence from the film normal, in degrees (light incident from air), does the first-order '
                    'Bragg reflection from the close-packed planes occur at a vacuum wavelength of %g nm?' % (subject(spec), optics_text(spec), lam))
        decimals, tol, sep, unit = 1, '0.05', '1.0', 'degree'
        reason = 'sin²θ = n_eff² − (λ/2d111)²，d111 = %.4f nm，n_eff = %.3f。' % (d111, n)
    checks = dict(spheres=len(pts), d111_nm=d111, n_eff=n, theta_deg=theta, fill_fraction=FILL, sample=spec['sample'],
                  measured_peak_nm=spec.get('measured_peak_nm'), paper_expected_nm=spec.get('paper_expected_nm'),
                  limits='理想 FCC 接触球与有效介质近似；实测峰受尺寸分布、缺陷与多面衍射影响，审核侧附实测值供比较。')
    return result(spec, text, question, value, cands, decimals, tol, sep, unit, seed, reason, checks, kit.dmax(pts), lat['a'], digest)


def build_design(spec, root, seed):
    rows, inputs, hashes = [], [], {}
    for asset, (sample, diameter) in zip(spec['candidates'], spec['diameters']):
        text, pts, digest = load(root, asset)
        lat = lattice(pts, diameter)
        name = asset.rsplit('/', 1)[1]
        ns, nm = spec['n_sphere'], spec['n_medium']
        n = math.sqrt(FILL * ns * ns + (1 - FILL) * nm * nm)
        rows.append(dict(sample=sample, name=name, D=lat['nn'], a=lat['a'], lam=peak(lat['d111'], n, 0),
                         wrong=dict(diameter_as_spacing=peak(lat['nn'], n, 0), no_index=peak(lat['d111'], 1.0, 0),
                                    linear_index_average=peak(lat['d111'], FILL * ns + (1 - FILL) * nm, 0),
                                    sphere_index=peak(lat['d111'], ns, 0)), extent=kit.dmax(pts)))
        inputs.append(dict(name=name, format='sphere-centres', unit='nm', text=text))
        hashes[asset] = digest
    t, goal = spec['target_nm'], spec['goal']
    notes = dict(diameter_as_spacing='把球径当作密排面间距', no_index='忽略折射率', linear_index_average='对折射率本身做体积平均',
                 sphere_index='用球的折射率代替有效折射率')
    why = {}
    if goal == 'closest':
        ranked = sorted(rows, key=lambda r: abs(r['lam'] - t))
        best, runner = ranked[0], ranked[1]
        if abs(runner['lam'] - t) < 1.5 * abs(best['lam'] - t) or abs(runner['lam'] - t) - abs(best['lam'] - t) < 10:
            raise ValueError('Winning margin too small')
        for rule in notes:
            pick = min(rows, key=lambda r: abs(r['wrong'][rule] - t))
            if pick is not best and pick['sample'] not in why:
                why[pick['sample']] = (rule, '%s时它的反射（%.1f nm）最接近目标。' % (notes[rule], pick['wrong'][rule]), 3)
        for r in rows:
            if r is not best and r['sample'] not in why:
                why[r['sample']] = ('farther_from_target', '正确模型下反射在 %.1f nm，离目标更远。' % r['lam'], 2)
        goal_text = 'its first-order normal-incidence Bragg reflection from the close-packed planes is closest to %g nm' % t
        reason_ok = '正确模型下反射在 %.1f nm，最接近目标。' % best['lam']
    else:
        ok = [r for r in rows if r['lam'] < t]
        if not ok:
            raise ValueError('No candidate meets the constraint')
        best = max(ok, key=lambda r: r['D'])
        if min(abs(r['lam'] - t) for r in rows) < 10:
            raise ValueError('A candidate sits too close to the constraint')
        for r in rows:
            if r is best:
                continue
            if r['lam'] >= t:
                fooled = [rule for rule in notes if r['wrong'][rule] < t]
                why[r['sample']] = (('passes_if_' + fooled[0]) if fooled else 'violates_limit',
                                    '反射在 %.1f nm，超出上限%s。' % (r['lam'], '；若%s会误判为满足' % notes[fooled[0]] if fooled else ''),
                                    3 if fooled else 2)
            else:
                why[r['sample']] = ('satisfies_but_smaller', '反射在 %.1f nm 满足上限，但球径 %.2f nm 不是最大。' % (r['lam'], r['D']), 2)
        goal_text = 'the spheres are as large as possible while its first-order normal-incidence Bragg reflection from the ' \
                    'close-packed planes stays below %g nm' % t
        reason_ok = '满足上限的样品中球径最大（%.2f nm，反射 %.1f nm）。' % (best['D'], best['lam'])
    right = '%s (%s)' % (best['sample'], best['name'])
    others = [(why[r['sample']][0], '%s (%s)' % (r['sample'], r['name']), why[r['sample']][1], why[r['sample']][2]) for r in rows if r is not best]
    order = kit.place(('correct', right, reason_ok, 3), others, spec.get('target_position'), seed, spec['id'], key=lambda p: p[0])
    options = [dict(label=l, value=p[1]) for l, p in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [p[0] == 'correct' for p in order])
    audit = [dict(label=l, value=p[1], rule=p[0], reason=p[2], is_correct=p[0] == 'correct') for l, p in zip(kit.LABELS, order)]
    question = ('The four files list the sphere centres (nm) of model opal crystallites made from four different polystyrene sphere '
                'batches (files named by sample; each built from that sample\'s published sphere diameter; neighbouring spheres touch). '
                '%s %s You must choose one sample for a new film such that %s. Which sample should you choose?'
                % (conditions('polystyrene'), optics_text(spec), goal_text))
    return dict(question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
                option_audit=audit, excluded_candidates=[], rank=None,
                checks=dict(candidates=[{k: r[k] for k in ('sample', 'D', 'a', 'lam')} for r in rows], goal=goal, target_nm=t,
                            measured_peaks_nm=spec.get('measured_peaks_nm'),
                            design_note='设计选择：四个候选均为论文实际合成的样品，性质由模型坐标计算。',
                            limits='理想 FCC 接触球与有效介质近似。'),
                scales=dict(input_nm=max(r['extent'] for r in rows), reasoning_nm=max(r['a'] for r in rows),
                            reasoning_definition='晶格周期：候选中最大的常规晶胞边长 a'),
                input_hashes=hashes)
