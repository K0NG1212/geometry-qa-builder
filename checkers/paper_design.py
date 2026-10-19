"""Independent checker for design_choice. No generation code is imported.

The checker reads the design card named in the answer key (hash-verified) and re-derives the task from what the
student was given: the four candidate lines in candidates.txt, and the target thresholds printed in the question
text. Every threshold it enforces is parsed back out of the question, so a card whose stored threshold differs
from the one the student was shown fails here. Comparisons are redone in Decimal, the "all four candidates are
measured" rule is enforced again, and exactly one candidate must satisfy every constraint and be the one the
paper chose. Whether the card renders the paper faithfully is not something code can verify (L1 compares each
locator with the original).
"""
import json
import re
from decimal import Decimal, localcontext
from .common import need, verify_hashes

OPS = {'>=': lambda a, b: a >= b, '>': lambda a, b: a > b, '<=': lambda a, b: a <= b, '<': lambda a, b: a < b}
LOWER = ('>=', '>')
MANTISSA = re.compile(r'^\(?([<>]?)\s*(-?\d+(?:\.\d+)?)')
EXPONENT = re.compile(r'× 10\^(-?\d+)')
MARKER_BOUND = {'': None, '>': 'lower', '<': 'upper'}


def parse_display(display):
    """(bound implied by the printed inequality, value): '(1.07 ± 0.10) × 10^7', '> 16', '2.7 mmol g^-1'."""
    m = MANTISSA.match(display)
    need(m is not None, 'Display string does not begin with a number: ' + display)
    exponent = EXPONENT.search(display)
    value = Decimal(m.group(2)) * (Decimal(10) ** int(exponent.group(1)) if exponent else 1)
    return MARKER_BOUND[m.group(1)], value


def number(display):
    bound, value = parse_display(display)
    need(bound is None, 'A threshold carries its direction in the comparison, not in the printed number: ' + display)
    return value


def card_of(packet, key):
    paths = verify_hashes(key)
    cards = [p for rel, p in paths.items() if rel.startswith('assets/families/design/') and rel.endswith('.json')]
    need(len(cards) == 1, 'Exactly one design card must be recorded in the key')
    card = json.loads(cards[0].read_text(encoding='utf-8'))
    need(card.get('kind') == 'design_card' and card.get('family') == packet['family'], 'Card belongs to another family')
    inputs = {i['name']: i['text'] for i in packet['inputs']}
    need(set(inputs) == {'candidates.txt'}, 'A design packet attaches exactly candidates.txt')
    lines = inputs['candidates.txt'].rstrip('\n').split('\n')
    need(len(lines) == 4 and len(card['candidates']) == 4, 'Exactly four candidates required')
    shown = sorted(card['candidates'], key=lambda c: c['id'])
    for line, c in zip(lines, shown):
        need(line == '%s: %s — %s' % (c['id'], c['name'], c['geometry']), 'Candidate %s differs from the card' % c['id'])
    need(card['ask'] in packet['question'] and card['goal'] in packet['question'], 'Question does not state the goal')
    return card, inputs


def targets(card, question):
    """Thresholds re-read from the question text; the card only says which property and direction each one tests."""
    out = []
    for con in card['constraints']:
        stated = '(%s) %s' % (con['key'], con['text'])
        need(stated in question, 'Target %s is not stated in the question' % con['key'])
        need(con['display'] in con['text'], 'Threshold %s is not printed in its own target text' % con['key'])
        need(con['op'] in OPS, 'Unknown comparison ' + con['op'])
        out.append((con['key'], con['property'], con['op'], number(con['display'])))
    need(len({k for k, _, _, _ in out}) == len(out), 'Constraint keys must be distinct')
    return out


def value_of(card, candidate, name):
    if name in card.get('derived', {}):
        parts = []
        for k in card['derived'][name]['ratio']:
            v, bound = value_of(card, candidate, k)
            need(bound is None, 'A derived ratio needs exact measured values, not bounds')
            parts.append(v)
        return parts[0] / parts[1], None
    entry = candidate['measured'].get(name)
    need(entry is not None, 'Candidate %s has no measured %s' % (candidate['id'], name))
    need(entry.get('locator'), 'Measured %s of %s has no place in the paper' % (name, candidate['id']))
    bound, value = parse_display(entry['display'])
    need(bound == entry.get('bound') and value == Decimal(repr(entry['value'])),
         'Measured %s of %s is not stored as the paper prints it' % (name, candidate['id']))
    return value, bound


def satisfied(op, value, threshold, bound):
    ok = OPS[op](value, threshold)
    if bound is None:
        return ok
    need(bound in ('lower', 'upper'), 'Unknown bound ' + str(bound))
    need(ok if (bound == 'lower') == (op in LOWER) else not ok,
         'A %s bound cannot settle the constraint %s %s' % (bound, op, threshold))
    return ok


def design_choice(packet, key):
    card, _ = card_of(packet, key)
    constraints = targets(card, packet['question'])
    by_text = {'%s: %s' % (c['id'], c['name']): c for c in card['candidates']}
    need(len(by_text) == 4 and {o['value'] for o in packet['options']} == set(by_text),
         'Options are not the four card candidates')
    margin = Decimal(repr(card['margin']))
    alive, failures = [], {}
    with localcontext() as ctx:
        ctx.prec = 50
        for o in packet['options']:
            c = by_text[o['value']]
            bad = []
            for name, prop, op, threshold in constraints:
                value, bound = value_of(card, c, prop)
                need(threshold != 0, 'A threshold of zero cannot carry a margin')
                ratio = value / threshold
                need(ratio >= margin or ratio <= 1 / margin, 'Candidate %s sits within the margin of %s' % (c['id'], name))
                if not satisfied(op, value, threshold, bound):
                    bad.append(name)
            failures[c['id']] = bad
            if not bad:
                alive.append((o['label'], c))
    need(len(alive) == 1, '%d candidates meet the target (need exactly 1)' % len(alive))
    label, best = alive[0]
    need(best['id'] == card['paper_choice'], 'The candidate that meets the target is not the one the paper chose')
    need(key['correct_label'] == label, 'Key label disagrees with the measured values')
    return dict(label=label, parameters=dict(card=card['id'], choice=best['id'], failures=failures),
                method='Decimal re-evaluation of the thresholds parsed from the question against the hashed card')


CHECKERS = {'design_choice': design_choice}
