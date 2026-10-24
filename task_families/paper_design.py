"""Design questions built from a documented optimization campaign in a paper (design route 1).

The authors changed one structural feature on purpose (longer aromatic walls, bulkier portal substituents, a
narrower pore) and measured the resulting property for every variant. A card transcribes that measured table,
docs/assets/families/design/<id>.json, checked against the full text kept locally (inputs/papers/, not in the
repository).

The student is given the setting, a target stated as thresholds on measured properties, and four candidates
described only by their structure (candidates.txt). The measured values stay on the reviewer side, so the
question is a design choice - pick the structure that reaches the target - and not a table lookup.

What code guarantees: every candidate has a measured value for every constrained property (the registry's
"four measured candidates" rule, so "untested" is never scored as "wrong"); exactly one candidate satisfies
all constraints; that one is the choice the paper reports; every other candidate fails a named constraint by
a stated margin; the threshold printed in the question is the one the code enforces. What it cannot: that the
structural descriptions are enough to reason the answer out rather than recall it. That is the L1/L4
judgement, and the card records which candidate a naive "more is always better" cue would pick.
"""
import json
import math
import operator
import re
from . import kit

VERSION = '0.1.0'
OPS = {'>=': operator.ge, '>': operator.gt, '<=': operator.le, '<': operator.lt}
LOWER_CONSTRAINTS = ('>=', '>')
MANTISSA = re.compile(r'^\(?([<>]?)\s*(-?\d+(?:\.\d+)?)')
EXPONENT = re.compile(r'× 10\^(-?\d+)')
MARKER_BOUND = {'': None, '>': 'lower', '<': 'upper'}


def parse_display(display):
    """(bound implied by the printed inequality, value) of a display string.

    Covers the forms the papers print: '5 × 10^6 M^-1', '(1.07 ± 0.10) × 10^7', '> 16', '2.7 mmol g^-1'.
    The uncertainty inside the parentheses is read as text only; the significand and the power of ten are
    what must agree with the stored value.
    """
    m = MANTISSA.match(display)
    if not m:
        raise ValueError('Display string does not begin with a number: ' + display)
    exponent = EXPONENT.search(display)
    value = float(m.group(2)) * (10 ** int(exponent.group(1)) if exponent else 1)
    return MARKER_BOUND[m.group(1)], value


def shown_value(display):
    bound, value = parse_display(display)
    if bound is not None:
        raise ValueError('A threshold carries its direction in "op", not in the printed number: ' + display)
    return value


def load(root, rel):
    raw = (root / 'docs' / rel).read_bytes()
    card = json.loads(raw.decode('utf-8'))
    if card.get('kind') != 'design_card' or card.get('family') != 'design_choice':
        raise ValueError('Not a design card: ' + rel)
    return card, raw


def decide(op, value, threshold, bound):
    """Compare a measured value with a threshold; a one-sided bound may only settle what it can settle.

    A value recorded as a lower bound ('> 16' in the paper) proves that a lower-bound target is met, and that
    an upper-bound target is missed, but never the opposite: that is refused rather than guessed.
    """
    ok = OPS[op](value, threshold)
    if bound is None:
        return ok
    if bound not in ('lower', 'upper'):
        raise ValueError('Unknown bound ' + bound)
    settles = ok if (bound == 'lower') == (op in LOWER_CONSTRAINTS) else not ok
    if not settles:
        raise ValueError('A %s bound cannot settle the constraint %s %s' % (bound, op, threshold))
    return ok


def measured(candidate, name):
    entry = candidate['measured'].get(name)
    if entry is None:
        raise ValueError('Candidate %s has no measured %s (all four candidates must be measured)'
                         % (candidate['id'], name))
    if not entry.get('locator'):
        raise ValueError('Measured %s of %s has no place in the paper' % (name, candidate['id']))
    bound, value = parse_display(entry['display'])
    if bound != entry.get('bound') or not math.isclose(value, float(entry['value']), rel_tol=1e-12):
        raise ValueError('Measured %s of %s is not stored as the paper prints it' % (name, candidate['id']))
    return value, bound


def value_of(card, candidate, name):
    """A measured property, or one derived from measured ones (a selectivity ratio)."""
    if name in card.get('derived', {}):
        top, bottom = (measured(candidate, k) for k in card['derived'][name]['ratio'])
        if top[1] or bottom[1]:
            raise ValueError('A derived ratio needs exact measured values, not bounds')
        return top[0] / bottom[0], None
    return measured(candidate, name)


def clear_of(con, card, value):
    """Is a measured value far enough from the threshold that the answer does not hang on the last digit?

    Two kinds, because what counts as "far enough" depends on the quantity:
      * ratio (the default): value/threshold outside [1/margin, margin]. For quantities with a true zero and a
        multiplicative scale - binding constants, uptakes, separation factors, fluxes.
      * absolute: |value - threshold| >= margin, in the property's own unit. For quantities where a ratio means
        nothing: a logarithm (log K: a ratio of logarithms is not a ratio of constants) and a temperature on a
        shifted scale (Tm in degrees Celsius: 53 and 46 differ by 1.16-fold only because of where zero sits).
        Energies (kJ/mol) and differences (delta-Tm, which may be negative) belong here too.
    """
    threshold, margin = float(con['value']), float(con.get('margin', card['margin']))
    kind = con.get('margin_kind', 'ratio')
    if kind == 'absolute':
        if margin <= 0:
            raise ValueError('An absolute margin must be positive: %s' % con['key'])
        return abs(value - threshold) >= margin
    if kind != 'ratio':
        raise ValueError('Unknown margin kind %r for %s' % (kind, con['key']))
    if margin <= 1:
        raise ValueError('A ratio margin must exceed 1: %s' % con['key'])
    if threshold == 0:
        raise ValueError('A ratio margin cannot be measured against a threshold of zero: %s' % con['key'])
    return value / threshold >= margin or value / threshold <= 1 / margin


def evaluate(card):
    """For each candidate: the constraints it fails. Also checks the stated margin to every threshold."""
    failures = {}
    for c in card['candidates']:
        bad = []
        for con in card['constraints']:
            value, bound = value_of(card, c, con['property'])
            threshold = float(con['value'])
            if not clear_of(con, card, value):
                raise ValueError('Candidate %s sits within the margin of the %s threshold' % (c['id'], con['key']))
            if not decide(con['op'], value, threshold, bound):
                bad.append(con['key'])
        failures[c['id']] = bad
    return failures


def candidate_lines(card):
    """What the student sees: one line per candidate, ordered by candidate id, never by the answer."""
    return ''.join('%s: %s — %s\n' % (c['id'], c['name'], c['geometry'])
                   for c in sorted(card['candidates'], key=lambda c: c['id']))


def question(card):
    targets = '; '.join('(%s) %s' % (con['key'], con['text']) for con in card['constraints'])
    return ('%s %s The attached candidates.txt describes four candidate structures, all of them prepared and '
            'measured in %s. The candidate must satisfy: %s. Exactly one of the four does so in the measured '
            'data, which is not shown to you. %s'
            % (card['setting'], card['goal'], card['short_citation'], targets, card['ask']))


def build(spec, root, seed):
    card, raw = load(root, spec['asset'])
    if len(card['candidates']) != 4 or len({c['id'] for c in card['candidates']}) != 4:
        raise ValueError('A design card needs exactly four distinct candidates')
    if len({c['geometry'] for c in card['candidates']}) != 4:
        raise ValueError('Candidates must be distinguishable by their structure')
    if len({con['key'] for con in card['constraints']}) != len(card['constraints']):
        raise ValueError('Constraint keys must be distinct')
    for con in card['constraints']:
        if con['op'] not in OPS:
            raise ValueError('Unknown comparison ' + con['op'])
        if con['display'] not in con['text'] or shown_value(con['display']) != float(con['value']):
            raise ValueError('Threshold %s is not printed in the target as stored' % con['key'])
    failures = evaluate(card)
    winners = [c for c in card['candidates'] if not failures[c['id']]]
    if len(winners) != 1:
        raise ValueError('%d candidates meet the target (need exactly 1)' % len(winners))
    best = winners[0]
    if best['id'] != card['paper_choice'] or best['rule'] != 'correct':
        raise ValueError('The candidate that meets the target is not the one the paper chose')
    label = lambda c: '%s: %s' % (c['id'], c['name'])
    correct = ('correct', label(best), '实测值满足全部目标约束，且是原文选定的结构（%s）。' % card['paper_choice_locator'], 3)
    others = []
    for c in card['candidates']:
        if c is best:
            continue
        if c['rule'] == 'correct':
            raise ValueError('Only the paper choice may carry the rule "correct"')
        others.append((c['rule'], label(c), '不满足约束 %s：%s' % ('、'.join(failures[c['id']]), c['reason']),
                       c.get('plausibility', 3)))
    order = kit.place(correct, others, spec.get('target_position'), seed, spec['id'], key=lambda x: x[1])
    options = [dict(label=l, value=x[1]) for l, x in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [x[0] == 'correct' for x in order])
    audit = [dict(label=l, value=x[1], rule=x[0], reason=x[2], is_correct=x[0] == 'correct', plausibility=x[3])
             for l, x in zip(kit.LABELS, order)]
    s = card['scale']
    return dict(
        question=question(card), scope=spec['scope'], numeric=None, options=options, correct_label=key,
        inputs=[dict(name='candidates.txt', format='text', unit='结构描述，无单位', text=candidate_lines(card))],
        option_audit=audit, excluded_candidates=[], rank=None,
        option_order='候选按 id 排序写入附件；正确项按批次目标位置插入选项，附件顺序与答案无关',
        checks=dict(card=card['id'], paper_choice=card['paper_choice'], failures=failures, margin=card['margin'],
                    measured={c['id']: {k: v['display'] for k, v in c['measured'].items()} for c in card['candidates']},
                    locators={c['id']: {k: v['locator'] for k, v in c['measured'].items()} for c in card['candidates']},
                    naive_cue=card.get('naive_cue'), notes=card.get('notes', []),
                    limits='程序保证：四个候选都有实测值、恰好一个满足全部约束、该候选即原文选定者、题干印出的阈值就是代码执行的阈值。'
                           '程序不能保证：所给结构描述足以推出答案而非靠记忆，也不能保证描述忠于原文——须对照原文位置人工核对（L1），难度由 L4 判定。'),
        scales=dict(input_nm=s['input_nm'], reasoning_nm=s['reasoning_nm'], reasoning_definition=s['definition']),
        input_hashes={spec['asset']: kit.sha256(raw)})
