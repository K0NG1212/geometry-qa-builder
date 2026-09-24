"""Inference family: which reflection is extinct for this real cell (kinematic model).

Physical model stated in the question: F(hkl) = sum_j Z_j exp[2 pi i (h x_j + k y_j + l z_j)],
atomic numbers as angle-independent weights. The checker evaluates all four options
from the same coordinate table the student receives; exactly one must vanish and the
other three must be clearly nonzero. Centering rules are necessary conditions only;
the answer comes from the actual coordinates, not from a rule lookup.
"""
import cmath
import itertools
import math
import sys
from fractions import Fraction
from . import kit

VERSION = '0.1.0'
ZERO = 1e-6      # |F| / F(000) at or below: extinct
CLEAR = 0.05     # |F| / F(000) at or above: clearly nonzero; between: ambiguous, never used


def cell_from_cif(root, asset):
    sys.path.insert(0, str(root / 'tools'))
    import recompute_materials_batch as legacy  # limited cubic reader, reused unchanged
    crystal = legacy.read_cubic(root / 'docs' / asset)
    rows = [(r['element'], [Fraction(x) for x in r['fractional_exact']]) for r in crystal['rows']]
    return crystal['a_A'], [(e, [float(x) for x in f]) for e, f in rows]


def cell_from_xyz(root, asset, a):
    elements, points = kit.parse_xyz((root / 'docs' / asset).read_text(encoding='utf-8-sig'))
    frac = [[x / a for x in p] for p in points]
    if any(not -1e-9 <= x < 1 + 1e-9 for p in frac for x in p):
        raise ValueError('Coordinates are not inside one conventional cell')
    return a, list(zip(elements, frac))


def table(a, rows, name):
    lines = ['%s; cubic a = %.5f angstrom; %d atoms; element x y z (fractional)' % (name, a, len(rows))]
    lines += ['%s %.8f %.8f %.8f' % (e, *f) for e, f in rows]
    return '\n'.join(lines) + '\n'


def parse_table(text):
    lines = text.splitlines()
    rows = [line.split() for line in lines[1:] if line.strip()]
    return [(r[0], [float(x) for x in r[1:]]) for r in rows]


def factor(rows, hkl, weights):
    return sum(weights[e] * cmath.exp(2j * math.pi * sum(h * x for h, x in zip(hkl, f))) for e, f in rows)


def rule_absent(rule, hkl):
    h, k, l = hkl
    if rule == 'I':
        return (h + k + l) % 2 == 1
    if rule == 'F':
        return len({h % 2, k % 2, l % 2}) > 1
    if rule == 'F+d':
        return rule_absent('F', hkl) or (h % 2 == k % 2 == l % 2 == 0 and (h + k + l) % 4 == 2)
    return False


RULES = {'P': '简单立方（无中心化消光）', 'I': '体心 I：h+k+l 为奇数消光',
         'F': '面心 F：奇偶混合消光', 'F+d': '面心 F 加金刚石滑移：另有全偶且 h+k+l=4n+2 消光'}


def build(spec, root, seed):
    raw = (root / 'docs' / spec['asset']).read_bytes()
    if spec['source_kind'] == 'cif':
        a, rows = cell_from_cif(root, spec['asset'])
    else:
        a, rows = cell_from_xyz(root, spec['asset'], spec['a'])
    weights = spec['weights']
    if set(e for e, _ in rows) != set(weights):
        raise ValueError('Weights must cover exactly the elements present')
    text = table(a, rows, spec['name'])
    rows = parse_table(text)            # evaluate exactly what the student receives
    f000 = sum(weights[e] for e, _ in rows)
    equal = {e: 1 for e in weights}
    pool = []
    for hkl in itertools.product(range(5), repeat=3):
        if hkl == (0, 0, 0) or not (hkl[0] >= hkl[1] >= hkl[2]) or sum(x * x for x in hkl) > 20:
            continue
        amp = abs(factor(rows, hkl, weights)) / f000
        amp_equal = abs(factor(rows, hkl, equal)) / len(rows)
        pool.append(dict(hkl=hkl, rel=amp, rel_equal=amp_equal))
    zeros = [p for p in pool if p['rel'] <= ZERO]
    clear = [p for p in pool if p['rel'] >= CLEAR]
    if not zeros or len(clear) < 3:
        raise ValueError('Need at least one extinct and three clearly nonzero reflections')
    low = [p for p in zeros if sum(x * x for x in p['hkl']) <= 12] or zeros
    # Prefer extinctions caused by the basis (not predicted by I or F centering alone),
    # so the answer depends on the coordinates rather than on recalling a lattice rule.
    basis = [p for p in low if not rule_absent('I', p['hkl']) and not rule_absent('F', p['hkl'])]
    correct = kit.ordered(basis or low, seed, spec['id'] + '/correct', key=lambda p: p['hkl'])[0]
    correct_origin = 'basis_or_glide' if basis else 'lattice_centering'
    for p in clear:
        mechanisms = []
        for rule in ('I', 'F', 'F+d'):
            if rule_absent(rule, p['hkl']):
                mechanisms.append((3, 'wrong_rule:' + rule, '按“%s”会判为消光，但本结构实际坐标给出非零 |F|。' % RULES[rule]))
        if p['rel_equal'] <= ZERO:
            mechanisms.append((3, 'identical_atom_assumption', '若把所有原子当作同种原子会相消；实际不同原子序数使其不为零。'))
        if p['rel'] < 0.25:
            mechanisms.append((2, 'weak_not_absent', '强度较弱（|F|/F000=%.3f），但不为零，弱不等于消光。' % p['rel']))
        if not mechanisms:
            mechanisms.append((1, 'allowed_generic', '普通允许反射，非零。'))
        p['plausibility'], p['rule'], p['reason'] = max(mechanisms)
        p['all_mechanisms'] = [m[1] for m in mechanisms]
    ranked = sorted(clear, key=lambda p: (-p['plausibility'], sum(x * x for x in p['hkl']),
                                          kit.digest(seed, spec['id'], p['hkl'])))
    chosen, used = [], set()
    for p in ranked:                  # prefer distinct mechanisms, then fill
        if p['rule'] not in used and len(chosen) < 3:
            chosen.append(p)
            used.add(p['rule'])
    for p in ranked:
        if len(chosen) < 3 and p not in chosen:
            chosen.append(p)
    permutation = kit.place(dict(correct, rule='correct', reason='由表中全部原子坐标求和，|F|/F000 ≤ 1e-6。'),
                            chosen, spec.get('target_position'), seed, spec['id'], key=lambda p: p['hkl'])
    show = lambda hkl: '(%d %d %d)' % hkl
    options = [dict(label=l, value=show(p['hkl'])) for l, p in zip(kit.LABELS, permutation)]
    verdicts = [abs(factor(rows, p['hkl'], weights)) / f000 <= ZERO for p in permutation]
    key = kit.validate_verdicts(options, verdicts)
    if any(ZERO < abs(factor(rows, p['hkl'], weights)) / f000 < CLEAR for p in permutation):
        raise ValueError('Ambiguous weak reflection among options')
    audit = [dict(label=l, value=show(p['hkl']), rule=p['rule'], reason=p['reason'], is_correct=v,
                  relative_amplitude=round(p['rel'], 8), mechanisms=p.get('all_mechanisms', []))
             for l, p, v in zip(kit.LABELS, permutation, verdicts)]
    shortcuts = {}
    for rule in RULES:
        predicted = [o['label'] for o, p in zip(options, permutation) if rule_absent(rule, p['hkl'])]
        shortcuts[rule] = dict(predicted_absent=predicted, uniquely_correct=predicted == [key])
    wlist = ', '.join('%s = %s' % kv for kv in sorted(weights.items()))
    question = ('The table lists every atom of one conventional cubic cell of %s as fractional coordinates. '
                'Use the kinematic structure factor F(hkl) = Σ_j Z_j exp[2πi(h x_j + k y_j + l z_j)] with atomic numbers '
                'as angle-independent weights (%s). Exactly one of the four reflections below has |F| = 0. Which one?') % (spec['name'], wlist)
    return dict(
        question=question,
        scope=spec['scope'],
        inputs=[dict(name=spec['id'] + '-cell.txt', format='fractional-cell-table', unit='fractional; a in angstrom', text=text)],
        numeric=None,
        options=options, correct_label=key, option_audit=audit,
        excluded_candidates=[dict(hkl=show(p['hkl']), relative_amplitude=round(p['rel'], 6))
                             for p in pool if ZERO < p['rel'] < CLEAR],
        rank=None,
        checks=dict(f000=f000, extinction_origin=correct_origin, zero_threshold=ZERO, clear_threshold=CLEAR, atoms=len(rows), a_A=a,
                    extinct_pool=[show(p['hkl']) for p in zeros], rule_shortcuts=shortcuts,
                    limits='零角度原子序数权重的运动学模型；不含原子散射因子角度依赖、热振动或多重散射。'),
        scales=dict(input_nm=a / 10, reasoning_nm=a / 10, reasoning_definition='晶胞边长 a：相位求和跨越整个晶胞'),
        input_hashes={spec['asset']: kit.sha256(raw)})
