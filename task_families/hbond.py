"""Hydrogen-bond geometry (chemistry C2c, intramolecular interactions; 0.1-1 nm).

hbond_geometry (perception): one named donor-H...acceptor contact in a supplied conformer; ask the donor-acceptor
    distance, the H...acceptor distance, or the D-H...A angle at H. Distractors are the usual mix-ups (H...A for D...A,
    the covalent D-H bond, a straight-line D-H-A path, the angle taken at the donor or at the acceptor).
hbond_criteria (inference): four candidate contacts (each named by its atoms and conformer); stated geometric criteria
    (H...A <= d_max and D-H...A >= angle_min, vertex at H); exactly one contact meets both. Wrong options record why
    each fails, including the classic trap: donor and acceptor close together while the H points away.
Atoms are named chemically (task_families/chem_names.py); the D-H bond and the absence of an H-A bond are checked with
the covalent-radius rule. Coordinates are copied unchanged from the source assets.
"""
import math
from . import kit, chem_names

VERSION = '0.1.0'
QUANTITY = {'da': 'donor–acceptor distance {D}···{A}', 'ha': 'hydrogen–acceptor distance {H}···{A}',
            'angle': '{D}–{H}···{A} angle at the hydrogen {H}'}
MARGIN_A, MARGIN_DEG = 0.10, 5.0      # every candidate must clear or miss each criterion by at least this much


def load(root, asset, charge=0):
    path = root / 'docs' / asset
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    elements, points = kit.parse_xyz(text)
    return path, raw, text, elements, points, kit.bond_graph(elements, points), chem_names.Molecule(elements, points, charge)


def contact(elements, points, edges, d, h, a):
    """Validated geometry of D-H...A (0-based rows)."""
    if elements[h] != 'H' or elements[d] not in ('N', 'O') or elements[a] not in ('N', 'O', 'F') or a == d:
        raise ValueError('Contact must be N/O-H...N/O/F')
    if (min(d, h), max(d, h)) not in edges:
        raise ValueError('Donor and hydrogen are not covalently bonded')
    if (min(a, h), max(a, h)) in edges:
        raise ValueError('Hydrogen is covalently bonded to the acceptor')
    return dict(da=math.dist(points[d], points[a]), ha=math.dist(points[h], points[a]),
                angle=kit.angle_acos(points[d], points[h], points[a]), dh=math.dist(points[d], points[h]))


def label(elements, i):
    return '%s%d' % (elements[i], i + 1)


def build_geometry(spec, root, seed):
    path, raw, text, elements, points, edges, names = load(root, spec['asset'], spec.get('charge', 0))
    d, h, a = (x - 1 for x in spec['contact'])
    g = contact(elements, points, edges, d, h, a)
    q = spec['quantity']
    D, H, A = label(elements, d), label(elements, h), label(elements, a)
    others = [j for j in range(len(elements)) if elements[j] in ('N', 'O') and j not in (d, a)]
    if q == 'da':
        value, decimals, tol, sep, unit = g['da'], 3, '0.0005', '0.030', 'angstrom'
        cands = [dict(rule='h_acceptor_instead', value=g['ha'], plausibility=3, reason='量成 H···A 距离，而不是给体与受体两个重原子之间的距离。'),
                 dict(rule='path_through_h', value=g['dh'] + g['ha'], plausibility=2, reason='沿 D–H 与 H···A 两段折线相加，当成给体–受体距离。'),
                 dict(rule='covalent_d_h', value=g['dh'], plausibility=1, reason='量成给体与氢之间的共价键长。')]
        cands += [dict(rule='other_acceptor:%s' % label(elements, j), value=math.dist(points[d], points[j]), plausibility=2,
                       reason='量到了另一个杂原子 %s（不是题目指定的受体）。' % label(elements, j)) for j in others]
    elif q == 'ha':
        value, decimals, tol, sep, unit = g['ha'], 3, '0.0005', '0.030', 'angstrom'
        cands = [dict(rule='donor_acceptor_instead', value=g['da'], plausibility=3, reason='量成给体与受体重原子之间的距离，而不是 H···A。'),
                 dict(rule='linear_assumption', value=g['da'] - g['dh'], plausibility=2, reason='假设氢键是直线：用 D···A 减去 D–H 键长。'),
                 dict(rule='covalent_d_h', value=g['dh'], plausibility=1, reason='量成给体与氢之间的共价键长。')]
        cands += [dict(rule='other_acceptor:%s' % label(elements, j), value=math.dist(points[h], points[j]), plausibility=2,
                       reason='量到了另一个杂原子 %s（不是题目指定的受体）。' % label(elements, j)) for j in others]
    elif q == 'angle':
        value, decimals, tol, sep, unit = g['angle'], 1, '0.05', '3.0', 'degree'
        cands = [dict(rule='angle_at_donor', value=kit.angle_acos(points[h], points[d], points[a]), plausibility=3,
                      reason='把顶点放在给体 %s 上（H–D···A 角），而不是氢上。' % D),
                 dict(rule='angle_at_acceptor', value=kit.angle_acos(points[d], points[a], points[h]), plausibility=2,
                      reason='把顶点放在受体 %s 上。' % A),
                 dict(rule='supplement', value=180 - g['angle'], plausibility=2, reason='取了补角（180° − θ），把偏离直线的角度当成氢键角。')]
        for x in kit.neighbors(edges, a):
            cands.append(dict(rule='acceptor_side:%s' % label(elements, x), value=kit.angle_acos(points[h], points[a], points[x]),
                              plausibility=2, reason='量成受体一侧的 H···%s–%s 角。' % (A, label(elements, x))))
    else:
        raise ValueError('Unknown quantity')
    lower, upper = (0, 180) if q == 'angle' else (0, None)
    chosen, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=decimals, tolerance=tol, min_separation=sep, seed=seed,
                                                      context=spec['id'], lower=lower, upper=upper, target=spec.get('target_position'))
    kit.require_rank(spec, goal, rank)
    options, audit = kit.label_numeric(value, chosen, decimals=decimals, unit=unit, seed=seed, context=spec['id'],
                                       correct_reason='按指定原子直接计算；成键关系由共价半径规则确认。')
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=sep, unit=unit)
    what = QUANTITY[q].format(D=D, H=H, A=A)
    question = ('%s In this conformer, %s, is covalently bonded to %s, and %s, is the candidate hydrogen-bond acceptor (rows %d, %d and %d, '
                'counted from 1 after the two XYZ header lines). What is the %s?' % (
                    spec['context'], names.atom(d), H, names.atom(a), d + 1, h + 1, a + 1, what))
    return dict(
        question=question, scope=spec['scope'], inputs=[dict(name=path.name, format='xyz', unit='angstrom', text=text)],
        numeric=dict(value=kit.display(value, decimals), unit=unit, decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
        checks=dict(contact='%s–%s···%s' % (D, H, A), d_a=g['da'], h_a=g['ha'], angle_deg=g['angle'], d_h=g['dh'],
                    donor_h_bonded=True, h_acceptor_bonded=False,
                    limits='单一计算构象；只测几何量，不据此单独判定氢键强弱或能量。'),
        scales=dict(input_nm=kit.dmax(points) / 10, reasoning_nm=max(g['da'], g['ha']) / 10, reasoning_definition='给体–受体或氢–受体距离'),
        input_hashes={spec['asset']: kit.sha256(raw)})


def build_criteria(spec, root, seed):
    dmax, amin = float(spec['ha_max']), float(spec['angle_min'])
    conformers, inputs, hashes = {}, [], {}
    for c in spec['conformers']:
        path, raw, text, elements, points, edges, names = load(root, c['asset'], spec.get('charge', 0))
        conformers[c['label']] = (elements, points, edges, names)
        inputs.append(dict(name='conformer_%s.xyz' % c['label'], format='xyz', unit='angstrom', text=text))
        hashes[c['asset']] = kit.sha256(raw)
    rows = []
    for k in spec['candidates']:
        elements, points, edges, names = conformers[k['conformer']]
        d, h, a = (x - 1 for x in k['contact'])
        g = contact(elements, points, edges, d, h, a)
        ok_d, ok_a = g['ha'] <= dmax, g['angle'] >= amin
        if abs(g['ha'] - dmax) < MARGIN_A or abs(g['angle'] - amin) < MARGIN_DEG:
            raise ValueError('A candidate sits too close to a criterion threshold')
        text = '%s–%s···%s in conformer %s' % (label(elements, d), label(elements, h), label(elements, a), k['conformer'])
        rows.append(dict(text=text, ok=ok_d and ok_a, ok_d=ok_d, ok_a=ok_a, **g,
                         roles='%s → %s' % (names.names[d], names.names[a])))
    winners = [r for r in rows if r['ok']]
    if len(winners) != 1:
        raise ValueError('Exactly one candidate must meet both criteria')
    others = []
    for r in rows:
        if r['ok']:
            continue
        if r['ok_d'] and not r['ok_a']:
            others.append(('distance_only', r['text'], 'H···A %.2f Å 满足距离，但角度 %.1f° 小于 %.0f°。' % (r['ha'], r['angle'], amin), 3))
        elif r['ok_a'] and not r['ok_d']:
            others.append(('angle_only', r['text'], '角度 %.1f° 满足，但 H···A %.2f Å 大于 %.1f Å。' % (r['angle'], r['ha'], dmax), 3))
        elif r['da'] <= 3.0:
            others.append(('donor_acceptor_close', r['text'], '给体与受体只相距 %.2f Å，但 H···A %.2f Å、角度 %.1f°：氢没有指向受体（只看重原子距离会误选）。'
                           % (r['da'], r['ha'], r['angle']), 3))
        else:
            others.append(('neither', r['text'], 'H···A %.2f Å、角度 %.1f°，两项都不满足。' % (r['ha'], r['angle']), 1))
    w = winners[0]
    order = kit.place(('correct', w['text'], 'H···A %.2f Å ≤ %.1f Å，角度 %.1f° ≥ %.0f°，两项都满足。' % (w['ha'], dmax, w['angle'], amin), 3),
                      others, spec.get('target_position'), seed, spec['id'], key=lambda x: x[1])
    options = [dict(label=l, value=x[1]) for l, x in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [x[0] == 'correct' for x in order])
    audit = [dict(label=l, value=x[1], rule=x[0], reason=x[2], is_correct=x[0] == 'correct') for l, x in zip(kit.LABELS, order)]
    files = ', '.join('conformer %s = conformer_%s.xyz' % (c['label'], c['label']) for c in spec['conformers'])
    question = ('%s Attached: %s (atoms are numbered by XYZ row, counted from 1 after the two header lines; numbering differs between '
                'conformers). Use these geometric criteria for an intramolecular hydrogen bond D–H···A: H···A distance ≤ %.1f Å and '
                'D–H···A angle ≥ %.0f° (vertex at H). These are task criteria, not a universal definition. Which of the four candidate '
                'contacts meets both criteria?' % (spec['context'], files, dmax, amin))
    span = max(max(r['da'], r['ha']) for r in rows) / 10
    return dict(
        question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key, option_audit=audit,
        excluded_candidates=[], rank=None,
        checks=dict(candidates=[{k: r[k] for k in ('text', 'ha', 'angle', 'da', 'ok', 'roles')} for r in rows], ha_max=dmax, angle_min=amin,
                    margins=dict(distance_A=MARGIN_A, angle_deg=MARGIN_DEG),
                    limits='几何判据是题设的操作定义；不据此判断氢键能量或光谱位移。'),
        scales=dict(input_nm=span, reasoning_nm=span, reasoning_definition='候选接触中最大的给体–受体或氢–受体距离'),
        input_hashes=hashes)
