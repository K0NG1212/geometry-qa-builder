"""Diffraction design (materials 0.1-1 and 1-10 nm): the inverse of first_diffraction_peak.

Three modes, all decided by the first reflection with non-zero kinematic intensity computed from the full
cell contents (so extinctions matter):
  crystal     choose one of four crystals whose first reflection (given wavelength) is closest to a target 2θ
  anode       for one crystal, choose one of four stated X-ray lines that puts its first reflection closest to a target 2θ
  wavelength  numeric: the wavelength that puts the first reflection exactly at a target 2θ
Inputs are the same fractional-cell tables as coordination_shell / first_diffraction_peak (COD structures).
"""
import itertools
import math
from . import kit
from .crystal import load_cell
from .extinction import factor, rule_absent

VERSION = '0.1.0'
SHOW = lambda hkl: '(%d %d %d)' % hkl


def reflections(a, rows, weights):
    """All (hkl, d, relative |F|) with h >= k >= l, index <= 4, sorted by decreasing d."""
    f000 = sum(weights[e] for e, _ in rows)
    out = []
    for hkl in itertools.product(range(5), repeat=3):
        if hkl == (0, 0, 0) or not hkl[0] >= hkl[1] >= hkl[2]:
            continue
        out.append(dict(hkl=hkl, d=a / math.sqrt(sum(x * x for x in hkl)), rel=abs(factor(rows, hkl, weights)) / f000))
    out.sort(key=lambda r: (-r['d'], r['hkl']))
    return out


def first_allowed(refl):
    allowed = [r for r in refl if r['rel'] > 1e-6]
    if len(allowed) > 1 and abs(allowed[0]['d'] - allowed[1]['d']) < 1e-9:
        raise ValueError('Two reflections share the first spacing')
    if allowed[0]['rel'] < 1e-3:
        raise ValueError('First reflection too weak to be unambiguous')
    return allowed[0]


def two_theta(d, lam):
    s = lam / (2 * d)
    return math.degrees(2 * math.asin(s)) if s <= 1 else None


def crystal_info(spec, root):
    cell, rows, text, digest = load_cell(spec, root)
    if cell.kind != 'cubic':
        raise ValueError('diffraction_design supports cubic cells only')
    a = cell.a
    refl = reflections(a, rows, spec['weights'])
    first = first_allowed(refl)
    return dict(a=a, rows=rows, text=text, digest=digest, refl=refl, first=first, lowest=refl[0])


def weights_text(w):
    return ', '.join('%s = %s' % kv for kv in sorted(w.items()))


RULE_TEXT = ('Use the kinematic structure factor with atomic numbers as angle-independent weights and first-order Bragg '
             'diffraction; the relevant peak is the lowest-angle reflection with non-zero intensity.')


def choose(spec, seed, rows, prop, target, wrong, label, reason_ok):
    """rows: candidate dicts; prop(row) -> 2θ; wrong: [(rule, f, note)]. Closest-to-target selection with margins."""
    ranked = sorted(rows, key=lambda r: abs(prop(r) - target))
    best, runner = ranked[0], ranked[1]
    d1, d2 = abs(prop(best) - target), abs(prop(runner) - target)
    if d2 < 1.5 * d1 or d2 - d1 < 0.5:
        raise ValueError('Winning margin too small')
    why = {}
    for rule, f, note in wrong:
        vals = [(abs(f(r) - target), r) for r in rows if f(r) is not None]
        if not vals:
            continue
        pick = min(vals, key=lambda v: v[0])[1]
        if pick is not best and label(pick) not in why:
            why[label(pick)] = (rule, '%s时它最接近目标（%.2f°）。' % (note, f(pick)), 3)
    for r in rows:
        if r is not best and label(r) not in why:
            why[label(r)] = ('farther_from_target', '首个非零反射在 2θ = %.2f°，离目标更远。' % prop(r), 2)
    others = [(why[label(r)][0], label(r), why[label(r)][1], why[label(r)][2]) for r in rows if r is not best]
    order = kit.place(('correct', label(best), reason_ok(best), 3), others, spec.get('target_position'), seed, spec['id'], key=lambda p: p[0])
    options = [dict(label=l, value=p[1]) for l, p in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [p[0] == 'correct' for p in order])
    audit = [dict(label=l, value=p[1], rule=p[0], reason=p[2], is_correct=p[0] == 'correct') for l, p in zip(kit.LABELS, order)]
    return options, key, audit, dict(margin_deg=d2 - d1)


def build(spec, root, seed):
    mode = spec['mode']
    if mode == 'crystal':
        lam, target = spec['wavelength_A'], spec['target_2theta']
        rows, inputs, hashes = [], [], {}
        for c in spec['candidates']:
            info = crystal_info(c, root)
            rows.append(dict(c, **info))
            inputs.append(dict(name=c['id'] + '-cell.txt', format='fractional-cell-table', unit='fractional; a in angstrom', text=info['text']))
            hashes[c['asset']] = info['digest']
        prop = lambda r: two_theta(r['first']['d'], lam)
        wrong = [('lowest_index_ignoring_extinction', lambda r: two_theta(r['lowest']['d'], lam), '取最低指数反射、未检查消光'),
                 ('theta_not_two_theta', lambda r: prop(r) / 2, '把 θ 当作 2θ 比较'),
                 ('assumed_simple_cubic', lambda r: two_theta(next(x for x in r['refl'] if not rule_absent('P', x['hkl']))['d'], lam), '一律按简单立方规则')]
        label = lambda r: '%s (%s-cell.txt)' % (r['short'], r['id'])
        options, key, audit, extra = choose(spec, seed, rows, prop, target, wrong, label,
                                            lambda r: '首个非零反射 %s，2θ = %.2f°，最接近目标。' % (SHOW(r['first']['hkl']), prop(r)))
        wl = '; '.join('%s: %s' % (r['short'], weights_text(r['weights'])) for r in rows)
        question = ('The four tables list every atom of one conventional cubic cell of four crystals (files named by crystal). %s '
                    'Weights: %s. For X-rays of wavelength %.5f Å, you must choose the crystal whose lowest-angle reflection with '
                    'non-zero intensity lies closest to 2θ = %.2f° (for example, to calibrate a detector at that angle). Which crystal '
                    'should you choose?' % (RULE_TEXT, wl, lam, target))
        checks = dict(candidates=[dict(crystal=r['short'], first=SHOW(r['first']['hkl']), d_A=r['first']['d'], two_theta=prop(r)) for r in rows],
                      wavelength_A=lam, target_2theta=target, **extra)
        reasoning = max(r['first']['d'] for r in rows) / 10
        input_nm = max(r['a'] for r in rows) / 10
        return dict(question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
                    option_audit=audit, excluded_candidates=[], rank=None, checks=dict(checks, limits=LIMITS),
                    scales=dict(input_nm=input_nm, reasoning_nm=reasoning, reasoning_definition='候选中最大的首个非零反射晶面间距 d'),
                    input_hashes=hashes)
    info = crystal_info(spec, root)
    d, target = info['first']['d'], spec['target_2theta']
    inputs = [dict(name=spec['id'] + '-cell.txt', format='fractional-cell-table', unit='fractional; a in angstrom', text=info['text'])]
    common = ('The table lists every atom of one conventional cubic cell of %s. %s Weights: %s.' % (spec['name'], RULE_TEXT, weights_text(spec['weights'])))
    scales = dict(input_nm=info['a'] / 10, reasoning_nm=d / 10, reasoning_definition='首个非零反射的晶面间距 d')
    base_checks = dict(first=SHOW(info['first']['hkl']), d_A=d, lowest_index=SHOW(info['lowest']['hkl']), a_A=info['a'], target_2theta=target,
                       limits=LIMITS)
    if mode == 'anode':
        lines = [dict(name=n, lam=l) for n, l in spec['lines']]
        prop = lambda r: two_theta(d, r['lam'])
        wrong = [('lowest_index_ignoring_extinction', lambda r: two_theta(info['lowest']['d'], r['lam']), '取最低指数反射、未检查消光'),
                 ('theta_not_two_theta', lambda r: prop(r) / 2 if prop(r) else None, '把 θ 当作 2θ 比较'),
                 ('d_equals_a', lambda r: two_theta(info['a'], r['lam']), '把晶格常数 a 当作晶面间距')]
        label = lambda r: '%s (λ = %.5f Å)' % (r['name'], r['lam'])
        options, key, audit, extra = choose(spec, seed, [r for r in lines if prop(r)], prop, target, wrong, label,
                                            lambda r: '首个非零反射 %s，d = %.4f Å，2θ = %.2f°。' % (SHOW(info['first']['hkl']), d, prop(r)))
        question = ('%s You must choose the X-ray source line that places this lowest-angle reflection with non-zero intensity closest '
                    'to 2θ = %.2f° (for example, to keep it clear of the beam stop while resolving it well). Which line should you '
                    'choose?' % (common, target))
        return dict(question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
                    option_audit=audit, excluded_candidates=[], rank=None,
                    checks=dict(base_checks, lines={r['name']: prop(r) for r in lines}, **extra), scales=scales,
                    input_hashes={spec['asset']: info['digest']})
    # wavelength (numeric)
    value = 2 * d * math.sin(math.radians(target / 2))
    cands = [dict(rule='lowest_index_ignoring_extinction', value=2 * info['lowest']['d'] * math.sin(math.radians(target / 2)), plausibility=3,
                  reason='用最低指数反射 %s 的 d（该反射消光）。' % SHOW(info['lowest']['hkl'])),
             dict(rule='two_theta_as_theta', value=2 * d * math.sin(math.radians(target)), plausibility=3, reason='把 2θ 当作 θ 代入。'),
             dict(rule='d_equals_a', value=2 * info['a'] * math.sin(math.radians(target / 2)), plausibility=2, reason='把晶格常数 a 当作 d。'),
             dict(rule='missing_factor_two', value=d * math.sin(math.radians(target / 2)), plausibility=2, reason='λ = d sinθ，漏掉因子 2。'),
             dict(rule='second_allowed', value=2 * next(r for r in info['refl'] if r['rel'] > 1e-6 and r['d'] < d - 1e-9)['d'] *
                  math.sin(math.radians(target / 2)), plausibility=2, reason='用了第二个非零反射。')]
    picked, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=4, tolerance='0.00005', min_separation='0.0500', seed=seed,
                                                      context=spec['id'], lower=0, target=spec.get('target_position'), distractor_separation='0.0250')
    options, audit = kit.label_numeric(value, picked, decimals=4, unit='angstrom', seed=seed, context=spec['id'],
                                       correct_reason='首个非零反射 %s，d = %.4f Å，λ = 2d sin(θ)。' % (SHOW(info['first']['hkl']), d))
    key = kit.validate_numeric(options, value, decimals=4, tolerance='0.00005', min_separation='0.0500', unit='angstrom', distractor_separation='0.0250')
    question = ('%s You must choose the X-ray wavelength that places this lowest-angle reflection with non-zero intensity exactly at '
                '2θ = %.2f°. What wavelength, in Å, should you use?' % (common, target))
    return dict(question=question, scope=spec['scope'], inputs=inputs,
                numeric=dict(value=kit.display(value, 4), unit='angstrom', decimals=4, tolerance='0.00005'),
                options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
                checks=dict(base_checks, wavelength_A=value), scales=scales, input_hashes={spec['asset']: info['digest']})


LIMITS = '运动学近似、零角度原子序数权重；不含原子散射因子角度依赖、吸收与仪器因素。设计选择基于计算证据。'
