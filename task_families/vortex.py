"""Abrikosov vortex lattices (quantum, 100-1000 nm): paper-parameter models.

Inputs are the vortex-centre maps built by tools/build_vortex_assets.py: MgB2 at the four applied fields of Cottet et al.
(arXiv:1401.4062) and BSCCO at the measured lattice constant of Schaefermeier et al. (arXiv:2602.13060). Questions concern the
lattice spacing (356-855 nm), the vortex density, flux quantisation (one h/2e per vortex), the first SANS Bragg peak, and the
choice of field for a target lattice (design).
"""
import math
from . import kit

VERSION = '0.1.0'
PHI0 = 2.067833848e-15
TOL = 1e-5
PAPERS = {'cottet': 'Cottet et al. (arXiv:1401.4062; MgB2, cryo-Lorentz TEM at 5 K)',
          'schaefermeier': 'Schaefermeier et al. (arXiv:2602.13060; BSCCO-2212, scanning NV magnetometry at 71 K)'}


def conditions(paper, field_text):
    return ('Model conditions: the only measured input is %s reported by %s; the vortices form an ideal triangular lattice with '
            'exactly one superconducting flux quantum per vortex, no pinning disorder, lattice defects or thermal motion, and a uniform '
            'field, which is the idealization the paper compares its images with; the map is a finite patch of about 97 vortices in an '
            'arbitrary orientation.' % (field_text, PAPERS[paper]))


def load(root, asset):
    raw = (root / 'docs' / asset).read_bytes()
    text = raw.decode('utf-8')
    lines = text.splitlines()
    rows = [l.split() for l in lines[2:] if l.strip()]
    if int(lines[0]) != len(rows) or any(len(r) != 3 or r[0] != 'V' for r in rows):
        raise ValueError('Expected count, comment and "V x y" rows')
    return text, [(float(r[1]), float(r[2])) for r in rows], kit.sha256(raw)


def lattice_spacing(pts, expected):
    c = (math.fsum(p[0] for p in pts) / len(pts), math.fsum(p[1] for p in pts) / len(pts))
    i = min(range(len(pts)), key=lambda k: math.dist(pts[k], c))
    d = sorted(math.dist(pts[i], p) for j, p in enumerate(pts) if j != i)
    first = [x for x in d if x - d[0] <= TOL]
    if len(first) != 6:
        raise ValueError('Vortices do not form a triangular lattice around the centre')
    a = math.fsum(first) / 6
    if abs(a - expected) > 1e-3:
        raise ValueError('Lattice spacing does not match the published value')
    return a


def field_from(a):                    # tesla, a in nm
    return 2 * PHI0 / (math.sqrt(3) * (a * 1e-9) ** 2)


def spacing_from(b):                  # nm
    return math.sqrt(2 * PHI0 / (math.sqrt(3) * b)) * 1e9


def density(a):                       # vortices per um^2
    return 2 / (math.sqrt(3) * (a / 1000) ** 2)


def q10(a):                           # um^-1, first Bragg peak of the triangular lattice
    return 4 * math.pi / (math.sqrt(3) * a / 1000)


SUBJECT = ('The file lists the vortex centres (nm) seen in a model image of the Abrikosov vortex lattice of a type-II superconductor '
           'in a perpendicular magnetic field.')
ASK = {
    'spacing': ('What is the vortex lattice spacing (centre-to-centre distance between neighbouring vortices), in nm?',
                1, '0.05', '10.0', 'nm', 'perception'),
    'density': ('How many vortices are there per square micrometre (areal vortex density)?', 3, '0.0005', '0.150', 'um^-2', 'perception'),
    'field': ('Each vortex carries one superconducting flux quantum Φ0 = h/(2e) = 2.0678 × 10⁻¹⁵ Wb. What is the magnetic induction B '
              'inside the superconductor that produces this lattice, in mT?', 3, '0.0005', '0.150', 'mT', 'inference'),
    'flux': ('The magnetic induction inside the superconductor is B = %s mT. How much magnetic flux does each vortex carry, in units of '
             '10⁻¹⁵ Wb?', 3, '0.0005', '0.150', '1e-15 Wb', 'inference'),
    'sans_q': ('In a small-angle neutron scattering experiment on this lattice, at what scattering vector q (q = 4π sinθ/λ) does the '
               'first-order Bragg peak of the vortex lattice appear, in μm⁻¹?', 2, '0.005', '0.50', 'um^-1', 'inference'),
}


def candidates(ask, a, b_mT):
    s3 = math.sqrt(3)
    if ask == 'spacing':
        return a, [dict(rule='row_spacing', value=a * s3 / 2, plausibility=3, reason='报告了相邻涡旋行的间距（√3/2）a。'),
                   dict(rule='second_neighbour', value=a * s3, plausibility=2, reason='报告了次近邻距离 √3 a。'),
                   dict(rule='square_lattice_guess', value=a * (s3 / 2) ** 0.5, plausibility=2, reason='按正方格子由密度反推间距。'),
                   dict(rule='half_spacing', value=a / 2, plausibility=1, reason='报告了半个间距。'),
                   dict(rule='double_spacing', value=2 * a, plausibility=2, reason='报告了隔一个涡旋的距离 2a。')]
    if ask == 'density':
        n = density(a)
        return n, [dict(rule='square_cell', value=1 / (a / 1000) ** 2, plausibility=3, reason='每个涡旋按 a² 的正方形面积计。'),
                   dict(rule='triangle_cell', value=2 * n, plausibility=2, reason='用三角形面积（半个晶胞）当作每个涡旋的面积。'),
                   dict(rule='half_density', value=n / 2, plausibility=2, reason='晶胞面积多乘了 2。'),
                   dict(rule='circle_cell', value=1 / (math.pi * (a / 2000) ** 2), plausibility=2, reason='每个涡旋按直径为 a 的圆面积计。')]
    if ask == 'field':
        b = field_from(a) * 1e3
        return b, [dict(rule='square_lattice', value=PHI0 / (a * 1e-9) ** 2 * 1e3, plausibility=3, reason='按正方格子 B = Φ0/a²。'),
                   dict(rule='flux_h_over_e', value=2 * b, plausibility=3, reason='用 h/e（单电子磁通量子）代替 h/2e。'),
                   dict(rule='flux_h_over_4e', value=b / 2, plausibility=2, reason='磁通量子多除了 2。'),
                   dict(rule='gauss_mT_slip', value=b * 10, plausibility=2, reason='高斯与毫特斯拉换算错（1 mT = 10 G）。'),
                   dict(rule='second_neighbour_as_spacing', value=b / 3, plausibility=2, reason='把次近邻距离 √3a 当作晶格间距。')]
    if ask == 'flux':
        cell = math.sqrt(3) / 2 * (a * 1e-9) ** 2
        phi = b_mT * 1e-3 * cell * 1e15
        return phi, [dict(rule='h_over_e', value=phi * 2, plausibility=3, reason='报告了 h/e（把超导电子对的电荷当作 e）。'),
                     dict(rule='square_cell', value=b_mT * 1e-3 * (a * 1e-9) ** 2 * 1e15, plausibility=3, reason='每个涡旋按 a² 面积计。'),
                     dict(rule='triangle_cell', value=phi / 2, plausibility=2, reason='每个涡旋按三角形面积计。'),
                     dict(rule='hbar_over_2e', value=phi / (2 * math.pi), plausibility=1, reason='报告了 ħ/(2e)，即 Φ0/2π。')]
    q = q10(a)
    return q, [dict(rule='two_pi_over_a', value=2 * math.pi / (a / 1000), plausibility=3, reason='用 2π/a，而三角格子首峰为 4π/(√3 a)。'),
               dict(rule='missing_two_pi', value=q / (2 * math.pi), plausibility=2, reason='漏掉 2π。'),
               dict(rule='second_order_peak', value=q * math.sqrt(3), plausibility=2, reason='报告了第二个峰（√3 倍）。'),
               dict(rule='square_lattice_q', value=2 * math.pi / (a * (math.sqrt(3) / 2) ** 0.5 / 1000), plausibility=2,
                    reason='按等密度正方格子计算首峰。')]


def build(spec, root, seed, ability):
    ask = spec['ask']
    text_q, decimals, tol, sep, unit, want = ASK[ask]
    if want != ability:
        raise ValueError('Quantity %s is not %s' % (ask, ability))
    text, pts, digest = load(root, spec['asset'])
    a = lattice_spacing(pts, spec['spacing_nm'])
    b_mT = spec.get('field_mT')
    if ask == 'flux':
        text_q = text_q % kit.display(b_mT, 2)
    value, cands = candidates(ask, a, b_mT)
    picked, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=decimals, tolerance=tol, min_separation=sep, seed=seed,
                                                      context=spec['id'], lower=0, target=spec.get('target_position'),
                                                      distractor_separation=str(float(sep) / 2))
    options, audit = kit.label_numeric(value, picked, decimals=decimals, unit=unit, seed=seed, context=spec['id'],
                                       correct_reason='三角涡旋晶格：a = %.3f nm，B = 2Φ0/(√3 a²) = %.4f mT，n = B/Φ0。' % (a, field_from(a) * 1e3))
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=sep, unit=unit,
                               distractor_separation=str(float(sep) / 2))
    question = '%s %s %s' % (SUBJECT, conditions(spec['paper'], spec['measured_text']), text_q)
    return dict(question=question, scope=spec['scope'],
                inputs=[dict(name=spec['asset'].rsplit('/', 1)[1], format='vortex-map', unit='nm', text=text)],
                numeric=dict(value=kit.display(value, decimals), unit=unit, decimals=decimals, tolerance=tol),
                options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
                checks=dict(vortices=len(pts), spacing_nm=a, field_mT=field_from(a) * 1e3, density_per_um2=density(a), q10_per_um=q10(a),
                            limits='理想三角涡旋晶格（论文用作对比的同一理想化）；不含钉扎无序与热涨落。'),
                scales=dict(input_nm=max(math.dist(p, q) for p in pts for q in pts), reasoning_nm=a, reasoning_definition='涡旋晶格间距 a'),
                input_hashes={spec['asset']: digest})


def build_geometry(spec, root, seed):
    return build(spec, root, seed, 'perception')


def build_inference(spec, root, seed):
    return build(spec, root, seed, 'inference')


GOALS = {'spacing': ('the vortex lattice spacing is closest to %g nm', lambda a: a),
         'sans_q': ('the first-order small-angle-neutron-scattering Bragg peak of the vortex lattice (q = 4π sinθ/λ) is closest to %g μm⁻¹',
                    q10),
         'min_density': ('the field is as low as possible while the areal vortex density is at least %g vortices per square micrometre',
                         density)}
WRONG = {'spacing': [('row_spacing', lambda a: a * math.sqrt(3) / 2, '把行间距当作晶格间距'),
                     ('second_neighbour', lambda a: a * math.sqrt(3), '把次近邻距离当作晶格间距')],
         'sans_q': [('two_pi_over_a', lambda a: 2 * math.pi / (a / 1000), '用 2π/a 计算首峰'),
                    ('second_order_peak', lambda a: q10(a) * math.sqrt(3), '用第二个峰')],
         'min_density': [('square_cell', lambda a: 1 / (a / 1000) ** 2, '每个涡旋按 a² 面积计'),
                         ('half_density', lambda a: density(a) / 2, '晶胞面积多乘 2')]}


def build_design(spec, root, seed):
    rows, inputs, hashes = [], [], {}
    for asset, (label, b_mT, a_exp) in zip(spec['candidates'], spec['fields']):
        text, pts, digest = load(root, asset)
        a = lattice_spacing(pts, a_exp)
        rows.append(dict(label=label, name=asset.rsplit('/', 1)[1], a=a, b=b_mT))
        inputs.append(dict(name=asset.rsplit('/', 1)[1], format='vortex-map', unit='nm', text=text))
        hashes[asset] = digest
    goal, t = spec['goal'], spec['target']
    text_goal, prop = GOALS[goal]
    why = {}
    if goal == 'min_density':
        ok = [r for r in rows if prop(r['a']) >= t]
        if not ok or min(abs(prop(r['a']) - t) for r in rows) < 0.2:
            raise ValueError('No candidate meets the target, or one sits too close to it')
        best = min(ok, key=lambda r: r['b'])
        for r in rows:
            if r is best:
                continue
            fooled = [rule for rule, f, _ in WRONG[goal] if (f(r['a']) >= t) != (prop(r['a']) >= t)]
            if prop(r['a']) < t:
                why[r['label']] = (('passes_if_' + fooled[0]) if fooled else 'too_sparse',
                                   '密度 %.2f /μm²，未达到 %g%s。' % (prop(r['a']), t, '；若%s会误判为满足' % dict((x, z) for x, _, z in WRONG[goal])[fooled[0]] if fooled else ''),
                                   3 if fooled else 2)
            else:
                why[r['label']] = ('meets_but_higher_field', '密度 %.2f /μm² 满足，但磁场更高。' % prop(r['a']), 2)
        reason_ok = '满足密度要求的候选中磁场最低（密度 %.2f /μm²）。' % prop(best['a'])
    else:
        ranked = sorted(rows, key=lambda r: abs(prop(r['a']) - t))
        best, runner = ranked[0], ranked[1]
        if abs(prop(runner['a']) - t) < 1.5 * abs(prop(best['a']) - t) or abs(prop(runner['a']) - t) - abs(prop(best['a']) - t) < 0.03 * t:
            raise ValueError('Winning margin too small')
        for rule, f, note in WRONG[goal]:
            pick = min(rows, key=lambda r: abs(f(r['a']) - t))
            if pick is not best and pick['label'] not in why:
                why[pick['label']] = (rule, '%s时它最接近目标（%.2f）。' % (note, f(pick['a'])), 3)
        for r in rows:
            if r is not best and r['label'] not in why:
                why[r['label']] = ('farther_from_target', '正确计算为 %.2f，离目标更远。' % prop(r['a']), 2)
        reason_ok = '正确计算为 %.2f，最接近目标。' % prop(best['a'])
    label = lambda r: '%s (%s)' % (r['label'], r['name'])
    others = [(why[r['label']][0], label(r), why[r['label']][1], why[r['label']][2]) for r in rows if r is not best]
    order = kit.place(('correct', label(best), reason_ok, 3), others, spec.get('target_position'), seed, spec['id'], key=lambda p: p[0])
    options = [dict(label=l, value=p[1]) for l, p in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [p[0] == 'correct' for p in order])
    audit = [dict(label=l, value=p[1], rule=p[0], reason=p[2], is_correct=p[0] == 'correct') for l, p in zip(kit.LABELS, order)]
    question = ('The four files list the vortex centres (nm) in model images of the Abrikosov vortex lattice of an MgB2 crystal at four '
                'applied fields (files named by field). %s You must choose one applied field such that %s. Which field should you choose?'
                % (conditions('cottet', 'the applied magnetic field of each image'), text_goal % t))
    return dict(question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
                option_audit=audit, excluded_candidates=[], rank=None,
                checks=dict(candidates=[dict(field=r['label'], spacing_nm=r['a'], value=prop(r['a'])) for r in rows], goal=goal, target=t,
                            design_note='设计选择：候选为论文中实际施加的磁场，性质由模型涡旋图计算（推断的逆问题）。',
                            limits='理想三角涡旋晶格；论文指出 188.7 G 时单个涡旋已难以分辨。'),
                scales=dict(input_nm=12 * max(r['a'] for r in rows), reasoning_nm=max(r['a'] for r in rows),
                            reasoning_definition='候选中最大的涡旋晶格间距'),
                input_hashes=hashes)
