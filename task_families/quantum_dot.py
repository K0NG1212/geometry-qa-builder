"""CdSe quantum dots (quantum, 1-10 nm): size-dependent optics from the Yu et al. (2003) empirical curves.

Inputs are model zinc-blende nanocrystals (tools/build_qdot_assets.py). The question states the published
sizing polynomial and extinction law and defines the size as the largest atom-atom distance, so the answer is
fixed by the coordinates: invert D(lambda) for the first excitonic peak, evaluate eps = 5857 D^2.65, derive a
concentration from an absorbance, or choose the particle that meets an optical target (design).
"""
import itertools
import math
import numpy as np
from . import kit

VERSION = '0.1.0'
COEF = (1.6122e-9, -2.6575e-6, 1.6242e-3, -0.4277, 41.57)
LO, HI = 400.0, 700.0
CURVE = ('Use the empirical CdSe sizing curve of Yu et al. (Chem. Mater. 2003): D = 1.6122e-9·λ⁴ − 2.6575e-6·λ³ + 1.6242e-3·λ² − '
         '0.4277·λ + 41.57, with D the particle diameter in nm and λ the wavelength of the first excitonic absorption peak in nm '
         '(valid for 400–700 nm), and its extinction law ε = 5857·D^2.65 M⁻¹ cm⁻¹ at that peak. Take D as the largest distance '
         'between any two atoms of the supplied nanocrystal.')
SUBJECT = 'The XYZ file lists every atom of a model zinc-blende CdSe nanocrystal (no ligands; angstrom).'
CONDITIONS = ('Model conditions: the nanocrystal is an ideal spherical cut from bulk zinc-blende CdSe (assumed lattice constant 6.08 Å) '
              'without ligands, surface relaxation or shape anisotropy; the empirical curves above were calibrated by Yu et al. on real '
              'nanocrystals whose sizes were measured by TEM, and are applied here to this ideal particle.')


def diameter_curve(lam):
    return sum(c * lam ** (4 - i) for i, c in enumerate(COEF))


def peak(d):
    """First excitonic peak for diameter d (nm): bisection on the monotonic 400-700 nm branch."""
    if not diameter_curve(LO) < d < diameter_curve(HI):
        return None
    lo, hi = LO, HI
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if diameter_curve(mid) < d else (lo, mid)
    return (lo + hi) / 2


def eps(d):
    return 5857 * d ** 2.65


def load(root, asset):
    raw = (root / 'docs' / asset).read_bytes()
    text = raw.decode('utf-8')
    pts = kit.parse_xyz(text)[1]
    return text, pts, kit.sha256(raw)


def sizes(pts):
    a = np.asarray(pts)
    dmax = max(float(np.sqrt(((a[i:i + 500, None, :] - a[None, :, :]) ** 2).sum(axis=2)).max()) for i in range(0, len(a), 500)) / 10
    if abs(dmax - kit.dmax(pts) / 10) > 1e-9:
        raise ValueError('Dmax implementations disagree')
    c = a.mean(axis=0)
    r = np.sqrt(((a - c) ** 2).sum(axis=1))
    span = a.max(axis=0) - a.min(axis=0)
    return dict(D=dmax, R=dmax / 2, rg=float(np.sqrt((r ** 2).mean())) / 10, box=float(np.sqrt((span ** 2).sum())) / 10)


def build(spec, root, seed):
    text, pts, digest = load(root, spec['asset'])
    s = sizes(pts)
    ask = spec['ask']
    wrong_sizes = [('bounding_box_diagonal', s['box'], 3, '用包围盒对角线代替最大原子间距。'),
                   ('two_rg', 2 * s['rg'], 2, '用 2 倍回转半径代替直径。'),
                   ('radius_as_diameter', s['R'], 2, '把半径当作直径代入。')]
    if ask == 'peak':
        value = peak(s['D'])
        cands = [dict(rule=r, value=peak(x), plausibility=p, reason=why) for r, x, p, why in wrong_sizes]
        cands.append(dict(rule='diameter_in_angstrom', value=peak(s['D'] * 10), plausibility=1, reason='D 用 Å 代入（超出曲线范围）。'))
        text_q, decimals, tol, sep, unit = 'At what wavelength, in nm, is its first excitonic absorption peak?', 1, '0.05', '3.0', 'nm'
        reason = 'D = %.4f nm，反解 D(λ) 得 λ = %.2f nm。' % (s['D'], value)
    elif ask == 'epsilon':
        value = eps(s['D']) / 1e5
        cands = [dict(rule=r, value=eps(x) / 1e5, plausibility=p, reason=why) for r, x, p, why in wrong_sizes]
        cands += [dict(rule='cubic_exponent', value=5857 * s['D'] ** 3 / 1e5, plausibility=2, reason='指数误用 3（体积标度）。'),
                  dict(rule='exponent_as_factor', value=5857 * 2.65 * s['D'] / 1e5, plausibility=1, reason='把 D^2.65 算成 2.65·D。')]
        text_q, decimals, tol, sep, unit = ('What is its molar extinction coefficient at the first excitonic peak, in units of 10⁵ M⁻¹ cm⁻¹?',
                                            3, '0.0005', '0.100', '1e5 M^-1 cm^-1')
        reason = 'ε = 5857 × %.4f^2.65 = %.0f M⁻¹ cm⁻¹。' % (s['D'], eps(s['D']))
    elif ask == 'concentration':
        absorb, path = spec['absorbance'], spec['path_cm']
        conc = lambda d: absorb / (eps(d) * path) * 1e6
        value = conc(s['D'])
        cands = [dict(rule=r, value=conc(x), plausibility=p, reason=why) for r, x, p, why in wrong_sizes]
        cands += [dict(rule='path_in_mm', value=value / 10, plausibility=2, reason='光程按 10 mm 数值代入（多除以 10）。'),
                  dict(rule='cubic_exponent', value=absorb / (5857 * s['D'] ** 3 * path) * 1e6, plausibility=2, reason='ε 的指数误用 3。')]
        text_q = ('A dilute solution of these nanocrystals has an absorbance of %.2f at the first excitonic peak in a %.1f cm cuvette. '
                  'What is the nanocrystal concentration, in µM (Beer–Lambert law)?' % (absorb, path))
        decimals, tol, sep, unit = 3, '0.0005', '0.050', 'uM'
        reason = 'c = A/(ε l) = %.2f/(%.0f × %.1f) = %.4f µM。' % (absorb, eps(s['D']), path, value)
    else:
        raise ValueError('Unknown ask')
    picked, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=decimals, tolerance=tol, min_separation=sep, seed=seed,
                                                      context=spec['id'], lower=0, target=spec.get('target_position'),
                                                      distractor_separation=str(float(sep) / 2))
    options, audit = kit.label_numeric(value, picked, decimals=decimals, unit=unit, seed=seed, context=spec['id'], correct_reason=reason)
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=sep, unit=unit,
                               distractor_separation=str(float(sep) / 2))
    return dict(question='%s %s %s %s' % (SUBJECT, CURVE, CONDITIONS, text_q), scope=spec['scope'],
                inputs=[dict(name=spec['asset'].rsplit('/', 1)[1], format='xyz', unit='angstrom', text=text)],
                numeric=dict(value=kit.display(value, decimals), unit=unit, decimals=decimals, tolerance=tol),
                options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
                checks=dict(atoms=len(pts), sizes_nm=s, peak_nm=peak(s['D']), epsilon=eps(s['D']),
                            limits='模型粒子（理想闪锌矿球形切割，无配体）；经验曲线只在其拟合尺寸范围内可靠。'),
                scales=dict(input_nm=s['D'], reasoning_nm=s['D'], reasoning_definition='纳米晶最大原子间距（整个粒子）'),
                input_hashes={spec['asset']: digest})


def build_inference(spec, root, seed):
    return build(spec, root, seed)


def build_design(spec, root, seed):
    rows, inputs, hashes = [], [], {}
    for asset in spec['candidates']:
        text, pts, digest = load(root, asset)
        s = sizes(pts)
        name = asset.rsplit('/', 1)[1]
        rows.append(dict(name=name, D=s['D'], lam=peak(s['D']), wrong=dict(radius_as_diameter=peak(s['R']), two_rg=peak(2 * s['rg']),
                                                                           bounding_box_diagonal=peak(s['box']))))
        inputs.append(dict(name=name, format='xyz', unit='angstrom', text=text))
        hashes[asset] = digest
    goal, t = spec['goal'], spec['target_nm']
    notes = dict(radius_as_diameter='把半径当直径', two_rg='用 2 倍回转半径', bounding_box_diagonal='用包围盒对角线')
    why = {}
    if goal == 'closest':
        ranked = sorted(rows, key=lambda r: abs(r['lam'] - t))
        best = ranked[0]
        if abs(ranked[1]['lam'] - t) < 1.5 * abs(best['lam'] - t) or abs(ranked[1]['lam'] - t) - abs(best['lam'] - t) < 5:
            raise ValueError('Winning margin too small')
        for rule in notes:
            pick = min((r for r in rows if r['wrong'][rule] is not None), key=lambda r: abs(r['wrong'][rule] - t), default=None)
            if pick is not None and pick is not best and pick['name'] not in why:
                why[pick['name']] = (rule, '%s时它的吸收峰（%.1f nm）最接近目标。' % (notes[rule], pick['wrong'][rule]), 3)
        goal_text = 'its first excitonic absorption peak is closest to %g nm' % t
        reason_ok = '吸收峰 %.1f nm，最接近目标。' % best['lam']
        for r in rows:
            if r is not best and r['name'] not in why:
                why[r['name']] = ('farther_from_target', '吸收峰 %.1f nm，离目标更远。' % r['lam'], 2)
    else:
        ok = [r for r in rows if r['lam'] >= t]
        if not ok or min(abs(r['lam'] - t) for r in rows) < 3:
            raise ValueError('No candidate meets the target, or one sits too close to it')
        best = min(ok, key=lambda r: r['D'])
        for r in rows:
            if r is best:
                continue
            if r['lam'] < t:
                fooled = [k for k in notes if r['wrong'][k] is not None and r['wrong'][k] >= t]
                why[r['name']] = (('passes_if_' + fooled[0]) if fooled else 'peak_too_blue',
                                  '吸收峰 %.1f nm，未达到 %g nm%s。' % (r['lam'], t, '；若%s会误判为满足' % notes[fooled[0]] if fooled else ''), 3 if fooled else 2)
            else:
                why[r['name']] = ('meets_but_larger', '吸收峰 %.1f nm 满足要求，但粒子更大（D = %.2f nm）。' % (r['lam'], r['D']), 2)
        goal_text = 'it is the smallest particle whose first excitonic absorption peak lies at or beyond %g nm' % t
        reason_ok = '满足要求的粒子中最小（D = %.2f nm，吸收峰 %.1f nm）。' % (best['D'], best['lam'])
    others = [(why[r['name']][0], r['name'], why[r['name']][1], why[r['name']][2]) for r in rows if r is not best]
    order = kit.place(('correct', best['name'], reason_ok, 3), others, spec.get('target_position'), seed, spec['id'], key=lambda p: p[0])
    options = [dict(label=l, value=p[1]) for l, p in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [p[0] == 'correct' for p in order])
    audit = [dict(label=l, value=p[1], rule=p[0], reason=p[2], is_correct=p[0] == 'correct') for l, p in zip(kit.LABELS, order)]
    question = ('The four XYZ files list every atom of four model zinc-blende CdSe nanocrystals (no ligands; angstrom). %s You must choose '
                'one nanocrystal for a device such that %s. Which file should you choose?' % (CURVE + ' ' + CONDITIONS.replace('the nanocrystal is', 'each nanocrystal is', 1).replace('this ideal particle', 'these ideal particles'), goal_text))
    return dict(question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
                option_audit=audit, excluded_candidates=[], rank=None,
                checks=dict(candidates=[dict(name=r['name'], D=r['D'], peak_nm=r['lam']) for r in rows], goal=goal, target_nm=t,
                            design_note='设计选择：按经验曲线选择粒径以达到目标吸收（推断的逆问题）。',
                            limits='模型粒子；经验曲线只在拟合尺寸范围内可靠。'),
                scales=dict(input_nm=max(r['D'] for r in rows), reasoning_nm=max(r['D'] for r in rows),
                            reasoning_definition='候选中最大的纳米晶最大原子间距'),
                input_hashes=hashes)
