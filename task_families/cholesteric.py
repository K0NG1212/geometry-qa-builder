"""Cholesteric (chiral nematic) liquid-crystal films (chemistry, 100-1000 nm): paper-parameter models.

Inputs are the director fields built by tools/build_cholesteric_assets.py from Shaban et al. (Materials 2024; R5011/S5011 in E44,
HTP 107.5 /um, measured reflection 585 / 593 nm and bandwidth 85.6 nm) and Dinc et al. (Org. Chem. Front. 2024; reflection 670 /
603 nm, average index 1.6). Questions concern the helical pitch (274-423 nm) and handedness, the Bragg reflection band, the
helical twisting power, and the choice of dopant concentration or film for a target colour (design).
"""
import math
from . import kit

VERSION = '0.1.0'
HTP = 107.5
NE, NO = 1.7904, 1.5484
HAND_RULE = ('A helix is right-handed if, with the right thumb pointing along the direction of travel along the helix axis, the director '
             'turns in the sense of the curled fingers; otherwise it is left-handed.')


def conditions(paper, film=None):
    if paper == 'shaban':
        return ('Model conditions: the only measured inputs are those reported by Shaban et al. (Materials 2024) for the nematic host E44 '
                'doped with the chiral dopant R5011 or S5011: the helical twisting power (107.5 μm⁻¹), the dopant concentration and the host '
                'refractive indices (ne = 1.7904, no = 1.5484 at 589 nm, 20 °C); the director twists uniformly about a straight helix axis '
                '(ideal planar Grandjean texture) with no defects, surface-anchoring distortion or temperature gradient, which is the '
                'idealization behind the paper\'s relations p = 1/(HTP·c) and λc = p·(ne + no)/2. Each file samples the director every 5 nm '
                'over 1.5 μm along an arbitrarily oriented axis.')
    return ('Model conditions: the only measured input is the reflection wavelength reported by Dinc et al. (Org. Chem. Front. 2024) for '
            'this cholesteric polymer coating, converted to a pitch with the paper\'s average refractive index of 1.6; the director twists '
            'uniformly about a straight helix axis with no defects, which is the idealization behind the paper\'s relation λ = n·p. Each '
            'file samples the director every 5 nm over 1.5 μm along an arbitrarily oriented axis.')


def load(root, asset):
    raw = (root / 'docs' / asset).read_bytes()
    text = raw.decode('utf-8')
    lines = text.splitlines()
    rows = [l.split() for l in lines[2:] if l.strip()]
    if int(lines[0]) != len(rows) or any(len(r) != 7 or r[0] != 'site' for r in rows):
        raise ValueError('Expected count, comment and "site x y z nx ny nz" rows')
    return text, [tuple(float(v) for v in r[1:4]) for r in rows], [tuple(float(v) for v in r[4:]) for r in rows], kit.sha256(raw)


def helix(pos, dirs, pitch_expected, hand_expected):
    """Pitch from the mean twist angle per step; handedness from (n_i x n_i+1) . step."""
    turns, hands = [], set()
    for (p, q), (m, n) in zip(zip(pos, pos[1:]), zip(dirs, dirs[1:])):
        step = [b - a for a, b in zip(p, q)]
        c = [m[1] * n[2] - m[2] * n[1], m[2] * n[0] - m[0] * n[2], m[0] * n[1] - m[1] * n[0]]
        turns.append(math.atan2(math.sqrt(sum(x * x for x in c)), sum(a * b for a, b in zip(m, n))))
        hands.add(1 if sum(a * b for a, b in zip(c, step)) > 0 else -1)
    if len(hands) != 1:
        raise ValueError('Twist sense changes along the axis')
    ds = math.dist(pos[0], pos[1])
    pitch = 2 * math.pi * ds / (math.fsum(turns) / len(turns))
    if abs(pitch - pitch_expected) > 1e-3 or hands.pop() != hand_expected:
        raise ValueError('Helix does not match the published parameters')
    return pitch


SUBJECT = ('The file lists the director (unit vector of average molecular orientation, n equivalent to −n) at sites along the helix axis '
           'of a model cholesteric liquid-crystal film; columns are site x y z (nm) nx ny nz.')
INDEX_TEXT = {'shaban': 'Use the average refractive index (ne + no)/2 of the host and its birefringence ne − no.',
              'dinc': 'Use the average refractive index 1.6.'}


def numeric(spec, root, seed, ability):
    text, pos, dirs, digest = load(root, spec['asset'])
    p = helix(pos, dirs, spec['pitch_nm'], spec['hand'])
    ask = spec['ask']
    n_avg = (NE + NO) / 2 if spec['paper'] == 'shaban' else 1.6
    if ask == 'pitch':
        want, decimals, tol, sep, unit = 'perception', 2, '0.005', '10.00', 'nm'     # 2 decimals: 670/1.6 = 418.75 sits on a 1-decimal rounding boundary
        value = p
        cands = [dict(rule='half_pitch', value=p / 2, plausibility=3, reason='报告了 p/2（n 与 −n 等价时的光学周期），而螺距是指向矢转 360° 的距离。'),
                 dict(rule='double_pitch', value=2 * p, plausibility=2, reason='报告了两个螺距。'),
                 dict(rule='quarter_pitch', value=p / 4, plausibility=1, reason='报告了转 90° 的距离。'),
                 dict(rule='reflection_wavelength', value=p * n_avg, plausibility=2, reason='报告了反射波长 n·p 而非螺距。'),
                 dict(rule='three_quarter_pitch', value=0.75 * p, plausibility=1, reason='报告了转 270° 的距离。')]
        q = 'What is the helical pitch p (the distance along the helix axis over which the director rotates by 360°), in nm?'
    elif ask in ('lambda', 'bandwidth'):
        want, decimals, tol, sep, unit = 'inference', 1, '0.05', '8.0', 'nm'
        if ask == 'lambda':
            value = n_avg * p
            cands = [dict(rule='extraordinary_index', value=NE * p if spec['paper'] == 'shaban' else 1.75 * p, plausibility=3, reason='用 ne 代替平均折射率。'),
                     dict(rule='ordinary_index', value=NO * p if spec['paper'] == 'shaban' else 1.5 * p, plausibility=3, reason='用 no 代替平均折射率。'),
                     dict(rule='half_pitch', value=n_avg * p / 2, plausibility=2, reason='用 p/2 计算（混淆了螺距与光学周期）。'),
                     dict(rule='no_index', value=p, plausibility=2, reason='忽略折射率，直接取螺距。'),
                     dict(rule='double_pitch', value=2 * n_avg * p, plausibility=1, reason='用 2p 计算。')]
            q = 'At normal incidence, what is the central wavelength λc of the selective (Bragg) reflection band, in nm? ' + INDEX_TEXT[spec['paper']]
        else:
            dn = NE - NO
            value = dn * p
            cands = [dict(rule='central_wavelength', value=n_avg * p, plausibility=2, reason='报告了反射中心波长。'),
                     dict(rule='half_pitch', value=dn * p / 2, plausibility=3, reason='用 p/2 计算带宽。'),
                     dict(rule='relative_birefringence', value=dn / n_avg * p, plausibility=2, reason='用 Δn/⟨n⟩ 代替 Δn。'),
                     dict(rule='half_birefringence', value=dn / 2 * p, plausibility=2, reason='用 Δn/2。'),
                     dict(rule='double_pitch', value=2 * dn * p, plausibility=1, reason='用 2p 计算。')]
            q = 'At normal incidence, what is the width Δλ of the selective (Bragg) reflection band, in nm? ' + INDEX_TEXT[spec['paper']]
    else:
        want, decimals, tol, sep, unit = 'inference', 1, '0.05', '5.0', 'um^-1'
        c = spec['concentration_wt']
        value = 1000 / (p * c / 100)
        cands = [dict(rule='percent_not_fraction', value=1000 / (p * c), plausibility=3, reason='浓度直接代入百分数而非质量分数。'),
                 dict(rule='half_pitch', value=1000 / (p / 2 * c / 100), plausibility=3, reason='用 p/2 代替螺距。'),
                 dict(rule='reflection_for_pitch', value=1000 / (p * n_avg * c / 100), plausibility=2, reason='用反射波长代替螺距。'),
                 dict(rule='nm_um_slip', value=1 / (p * c / 100), plausibility=1, reason='螺距单位 nm 与 μm 混用。'),
                 dict(rule='double_pitch', value=1000 / (2 * p * c / 100), plausibility=2, reason='用 2p 代替螺距。')]
        q = ('The film contains %.2f wt%% of the chiral dopant. What is the helical twisting power HTP = 1/(p·c) of the dopant in this host '
             '(c as a weight fraction), in μm⁻¹?' % c)
    if want != ability:
        raise ValueError('Quantity %s is not %s' % (ask, ability))
    picked, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=decimals, tolerance=tol, min_separation=sep, seed=seed,
                                                      context=spec['id'], lower=0, target=spec.get('target_position'),
                                                      distractor_separation=str(float(sep) / 2))
    options, audit = kit.label_numeric(value, picked, decimals=decimals, unit=unit, seed=seed, context=spec['id'],
                                       correct_reason='由指向矢每步转角得螺距 p = %.3f nm；λc = ⟨n⟩p，Δλ = Δn·p，HTP = 1/(p c)。' % p)
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=sep, unit=unit,
                               distractor_separation=str(float(sep) / 2))
    return pack(spec, text, digest, '%s %s %s' % (SUBJECT, conditions(spec['paper']), q), options, key, audit, rejected,
                dict(target=goal, achieved=rank), dict(value=kit.display(value, decimals), unit=unit, decimals=decimals, tolerance=tol), p)


def pack(spec, text, digest, question, options, key, audit, rejected, rank, numeric_, p):
    return dict(question=question, scope=spec['scope'],
                inputs=[dict(name=spec['asset'].rsplit('/', 1)[1], format='director-field', unit='nm', text=text)],
                numeric=numeric_, options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=rank,
                checks=dict(pitch_nm=p, handedness='right' if spec['hand'] > 0 else 'left', measured_reflection_nm=spec.get('measured_nm'),
                            limits='理想均匀扭曲的胆甾螺旋（论文关系式所用的同一理想化）；模型值与实测反射相差约 1–2%。'),
                scales=dict(input_nm=1500.0, reasoning_nm=p, reasoning_definition='螺距 p'), input_hashes={spec['asset']: digest})


def build_geometry(spec, root, seed):
    if spec['ask'] != 'pitch_handedness':
        return numeric(spec, root, seed, 'perception')
    text, pos, dirs, digest = load(root, spec['asset'])
    p = helix(pos, dirs, spec['pitch_nm'], spec['hand'])
    hand = 'right-handed' if spec['hand'] > 0 else 'left-handed'
    other = 'left-handed' if spec['hand'] > 0 else 'right-handed'
    fmt = lambda h, x: '%s, pitch %s nm' % (h, kit.display(x, 1))
    right = fmt(hand, p)
    others = [('opposite_handedness', fmt(other, p), '螺距对，但手性判反（转向与右手定则比较时看错方向）。', 3),
              ('half_pitch', fmt(hand, p / 2), '手性对，但报告了 p/2（指向矢转 180° 的距离）。', 3),
              ('both_wrong', fmt(other, p / 2), '手性判反且报告了 p/2。', 2)]
    order = kit.place(('correct', right, '每步转角给出 p = %.3f nm；(n_i × n_i+1)·前进方向 的符号给出%s。' % (p, '右手' if spec['hand'] > 0 else '左手'), 3),
                      others, spec.get('target_position'), seed, spec['id'], key=lambda q: q[0])
    options = [dict(label=l, value=q[1]) for l, q in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [q[0] == 'correct' for q in order])
    audit = [dict(label=l, value=q[1], rule=q[0], reason=q[2], is_correct=q[0] == 'correct') for l, q in zip(kit.LABELS, order)]
    question = ('%s %s %s What are the handedness and the helical pitch p (the distance over which the director rotates by 360°) of this '
                'helix?' % (SUBJECT, conditions(spec['paper']), HAND_RULE))
    return pack(spec, text, digest, question, options, key, audit, [], None, None, p)


def build_inference(spec, root, seed):
    return numeric(spec, root, seed, 'inference')


def build_design(spec, root, seed):
    rows, inputs, hashes = [], [], {}
    for c in spec['candidates']:
        text, pos, dirs, digest = load(root, c['asset'])
        p = helix(pos, dirs, c['pitch_nm'], c['hand'])
        n_avg = (NE + NO) / 2 if c['paper'] == 'shaban' else 1.6
        n_e = NE if c['paper'] == 'shaban' else None
        rows.append(dict(c, p=p, lam=n_avg * p, lam_ne=(n_e * p if n_e else None), lam_half=n_avg * p / 2))
        inputs.append(dict(name=c['asset'].rsplit('/', 1)[1], format='director-field', unit='nm', text=text))
        hashes[c['asset']] = digest
    goal, t = spec['goal'], spec['target_nm']
    label = lambda r: '%s (%s)' % (r['label'], r['asset'].rsplit('/', 1)[1])
    why = {}
    if goal == 'closest':
        ranked = sorted(rows, key=lambda r: abs(r['lam'] - t))
        best, runner = ranked[0], ranked[1]
        if abs(runner['lam'] - t) < 1.5 * abs(best['lam'] - t) or abs(runner['lam'] - t) - abs(best['lam'] - t) < 10:
            raise ValueError('Winning margin too small')
        for rule, key_, note in (('extraordinary_index', 'lam_ne', '用 ne 代替平均折射率'), ('half_pitch', 'lam_half', '用 p/2 计算')):
            vals = [r for r in rows if r[key_] is not None]
            pick = min(vals, key=lambda r: abs(r[key_] - t))
            if pick is not best and pick['label'] not in why:
                why[pick['label']] = (rule, '%s时它的反射（%.1f nm）最接近目标。' % (note, pick[key_]), 3)
        reason_ok = '反射中心 %.1f nm，最接近目标。' % best['lam']
        goal_text = 'its normal-incidence reflection band is centred as close as possible to %g nm' % t
    elif goal == 'left_closest':
        ok = [r for r in rows if r['hand'] < 0]
        ranked = sorted(ok, key=lambda r: abs(r['lam'] - t))
        best = ranked[0]
        if len(ranked) > 1 and abs(ranked[1]['lam'] - t) - abs(best['lam'] - t) < 10:
            raise ValueError('Winning margin too small among left-handed films')
        right_best = min((r for r in rows if r['hand'] > 0), key=lambda r: abs(r['lam'] - t))
        why[right_best['label']] = ('right_handed_closer', '反射 %.1f nm 也接近目标，但螺旋是右手的。' % right_best['lam'], 3)
        reason_ok = '左手螺旋，反射 %.1f nm，在左手候选中最接近目标。' % best['lam']
        goal_text = ('the helix is left-handed and its normal-incidence reflection band is centred as close as possible to %g nm' % t)
    else:
        ok = [r for r in rows if r['lam'] <= t]
        if not ok or min(abs(r['lam'] - t) for r in rows) < 10:
            raise ValueError('No candidate meets the limit, or one sits too close to it')
        best = min(ok, key=lambda r: r['conc'])
        for r in rows:
            if r is best:
                continue
            if r['lam'] > t:
                why[r['label']] = ('reflects_too_red', '反射 %.1f nm，超过 %g nm；只看螺距 p（%.1f nm）会误判为满足。' % (r['lam'], t, r['p']), 3)
            else:
                why[r['label']] = ('meets_but_more_dopant', '反射 %.1f nm 满足，但掺杂剂更多。' % r['lam'], 2)
        reason_ok = '满足上限的候选中掺杂剂最少（反射 %.1f nm）。' % best['lam']
        goal_text = ('as little dopant as possible is used while the normal-incidence reflection band is centred at or below %g nm' % t)
    for r in rows:
        if r is not best and r['label'] not in why:
            why[r['label']] = ('farther_from_target' if r['hand'] < 0 or goal != 'left_closest' else 'right_handed',
                               '反射 %.1f nm%s。' % (r['lam'], '' if r['hand'] < 0 or goal != 'left_closest' else '，且为右手螺旋'), 2)
    others = [(why[r['label']][0], label(r), why[r['label']][1], why[r['label']][2]) for r in rows if r is not best]
    order = kit.place(('correct', label(best), reason_ok, 3), others, spec.get('target_position'), seed, spec['id'], key=lambda q: q[0])
    options = [dict(label=l, value=q[1]) for l, q in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [q[0] == 'correct' for q in order])
    audit = [dict(label=l, value=q[1], rule=q[0], reason=q[2], is_correct=q[0] == 'correct') for l, q in zip(kit.LABELS, order)]
    papers = sorted({r['paper'] for r in rows})
    index_text = ' '.join(['For the E44 films use the average refractive index (ne + no)/2 of E44.' if 'shaban' in papers else '',
                           'For the polymer coatings use the average refractive index 1.6.' if 'dinc' in papers else '']).strip()
    question = ('The four files list the director fields of four model cholesteric liquid-crystal films (files named by composition; columns '
                'site x y z in nm and the unit director nx ny nz, n equivalent to −n). %s %s %s You must choose one film such that %s. Which '
                'film should you choose?' % (' '.join(conditions(pp) for pp in papers), HAND_RULE if goal == 'left_closest' else '',
                                            index_text, goal_text))
    return dict(question=' '.join(question.split()), scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
                option_audit=audit, excluded_candidates=[], rank=None,
                checks=dict(candidates=[dict(label=r['label'], pitch_nm=r['p'], reflection_nm=r['lam'], hand=r['hand']) for r in rows],
                            goal=goal, target_nm=t, design_note='设计选择：按目标颜色、手性或掺杂量选择膜（推断的逆问题）。',
                            limits='理想均匀扭曲的胆甾螺旋；非实测浓度的候选为按论文 HTP 计算的模型。'),
                scales=dict(input_nm=1500.0, reasoning_nm=max(r['p'] for r in rows), reasoning_definition='候选中最大的螺距'),
                input_hashes=hashes)
