"""Independent checkers for evidence_quantity and evidence_elimination. No generation code is imported.

The checker reads the evidence card named in the answer key (hash-verified), and requires that the student's
evidence.txt lists exactly the card's facts and that every stored number is printed in its fact. Quantities are
recomputed with Decimal arithmetic and different formula routes (generator: floats). For the 2x2 quantity options the
checker parses each option into value and conclusion and requires the four combinations, exactly one of which is the
recomputed value with the paper's conclusion. For elimination it re-runs the comparison of predictions with
observations and requires a single surviving explanation, the paper's. What the card says about the paper is not
something code can verify (L1 compares each locator with the original).
"""
import json
import math
import re
from decimal import Decimal, localcontext, ROUND_HALF_UP
from .common import need, read_xyz, dist, verify_hashes

H = Decimal('6.62607015e-34')
E = Decimal('1.602176634e-19')
UNIT_TEXT = {'nm': ' nm', 'um^2': ' µm²', 'T': ' T', 'degree': '°', 'angstrom': ' Å', '': ''}
NUM = re.compile(r'(-?\d+(?:\.\d+)?)(?: × 10\^(-?\d+))?')


def ctx():
    return localcontext(prec=50)


def number(display):
    m = NUM.match(display)
    need(m is not None, 'Display string does not start with a number: ' + display)
    base = Decimal(m.group(1))
    return base * (Decimal(10) ** int(m.group(2))) if m.group(2) else base


def card_of(packet, key):
    paths = verify_hashes(key)
    cards = [p for rel, p in paths.items() if rel.startswith('assets/families/evidence/') and rel.endswith('.json')]
    need(len(cards) == 1, 'Exactly one evidence card must be recorded in the key')
    card = json.loads(cards[0].read_text(encoding='utf-8'))
    need(card.get('family') == packet['family'], 'Card belongs to another family')
    inputs = {i['name']: i['text'] for i in packet['inputs']}
    need('evidence.txt' in inputs, 'No evidence.txt attached')
    lines = inputs['evidence.txt'].rstrip('\n').split('\n')
    need(len(lines) == len(card['facts']), 'evidence.txt does not list exactly the card facts')
    for line, fact in zip(lines, card['facts']):
        need(line == '%s. %s' % (fact['id'], fact['text']), 'Fact %s differs from the card' % fact['id'])
    need(packet['question'].count('evidence.txt') >= 1 and card['ask'] in packet['question'], 'Question does not point to the evidence or ask the card question')
    for f in card.get('files', []):
        need(f['name'] in inputs, 'Structure file not attached: ' + f['name'])
        source = [p for rel, p in paths.items() if rel == f['asset']]
        need(len(source) == 1 and source[0].read_bytes().decode('utf-8') == inputs[f['name']], 'Attached structure differs from its asset')
    return card, inputs


def fact_numbers(card):
    out = {}
    for f in card['facts']:
        for name, (value, display) in f.get('values', {}).items():
            need(display in f['text'], 'Number %s not printed in %s' % (name, f['id']))
            parsed = number(display)
            need(abs(parsed - Decimal(repr(value))) <= abs(parsed) * Decimal('1e-12'), 'Printed %s differs from the stored value' % name)
            out[name] = parsed
    return out


def flux(kind):
    need(kind in ('h/2e', 'h/e'), 'Unknown flux quantum')
    return H / (2 * E) if kind == 'h/2e' else H / E


def get(v, x):
    return v[x] if isinstance(x, str) else Decimal(repr(x))


def asin_deg(x):
    # asin via atan2 (the generator uses math.asin)
    x = float(x)
    return Decimal(repr(math.degrees(math.atan2(x, math.sqrt(1 - x * x)))))


def quantity(kind, a, v, inputs, card):
    with ctx():
        if kind == 'inverse_sqrt_density':
            return Decimal(10) ** 7 / get(v, a['n_cm2']).sqrt()
        if kind == 'flux_loop_area':
            return flux(a['flux']) * Decimal(10) ** 15 / get(v, a['period_mT'])          # Wb / mT -> µm²
        if kind == 'thin_film_parallel_field':
            d, xi = get(v, a['d_nm']) * Decimal('1e-9'), get(v, a['xi_nm']) * Decimal('1e-9')
            return Decimal(3).sqrt() * flux('h/2e') / (Decimal(repr(math.pi)) * d * xi)
        if kind == 'perpendicular_gl_field':
            xi = get(v, a['xi_nm']) * Decimal('1e-9')
            return flux('h/2e') / (2 * Decimal(repr(math.pi)) * xi * xi)
        if kind == 'equal_area_twist':
            x, y, z = (get(v, a[k]) for k in ('l1', 'l2', 'l3'))
            area = (4 * x * x * y * y - (x * x + y * y - z * z) ** 2).sqrt() / 4          # Heron, product-free form
            side = (4 * area / Decimal(3).sqrt()).sqrt()
            return 2 * asin_deg(get(v, a['a_nm']) / (2 * side))
        if kind == 'single_wavelength_twist':
            return 2 * asin_deg(get(v, a['a_nm']) / (2 * get(v, a['l'])))
        if kind == 'flux_quanta_count':
            side = get(v, a['side_um']) * Decimal('1e-6')
            return get(v, a['B_mT']) * Decimal('1e-3') * side * side / flux(a['flux'])
        if kind in ('cholesteric_bandwidth', 'cholesteric_centre'):
            ne, no = get(v, a['ne']), get(v, a['no'])
            index = ne - no if kind == 'cholesteric_bandwidth' else (ne + no) / 2
            return index * Decimal(100000) / (get(v, a['htp_um']) * get(v, a['c_wt']))    # nm
        if kind == 'htp_ratio':
            return (get(v, a['lam_R']) * get(v, a['c_R'])) / (get(v, a['lam_L']) * get(v, a['c_L']))
        if kind == 'wavelength_ratio':
            return get(v, a['lam_R']) / get(v, a['lam_L'])
        if kind == 'xyz_distance_difference':
            names = {f['key']: f['name'] for f in card['files']}
            facts = ' '.join(f['text'] for f in card['facts'])

            def d(key, rows):
                for r in rows:
                    need('row %d' % r in facts, 'Row %d not named in the evidence' % r)
                atoms = read_xyz(inputs[names[key]])
                i, j = rows
                return dist(atoms[i - 1][1], atoms[j - 1][1])
            return d(a['a_file'], a['a_rows']) - d(a['b_file'], a['b_rows'])
    need(False, 'Unknown quantity kind ' + kind)


def rounded(value, decimals):
    return value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def evidence_quantity(packet, key):
    card, inputs = card_of(packet, key)
    v = fact_numbers(card)
    q, err, concl = card['quantity'], card['error'], card['conclusions']
    right = quantity(q['kind'], q['args'], v, inputs, card)
    wrong = quantity(err['kind'], err['args'], v, inputs, card)
    dec, tol = q['decimals'], Decimal(q['tolerance'])
    need(abs(right - wrong) >= Decimal(q['min_separation']), 'Mistake value within the separation of the correct value')
    unit = UNIT_TEXT[q['unit']]
    pattern = re.compile(r'^%s (-?\d+\.\d{%d})%s\. (.+)$' % (re.escape(q['label']), dec, re.escape(unit)))
    texts = {concl['paper']['text']: 'paper', concl['rejected']['text']: 'rejected'}
    parsed = []
    for o in packet['options']:
        m = pattern.match(o['value'])
        need(m is not None, 'Option %s is not "label value unit. conclusion"' % o['label'])
        need(m.group(2) in texts, 'Option %s conclusion is not on the card' % o['label'])
        parsed.append((o['label'], Decimal(m.group(1)), texts[m.group(2)]))
    shown = sorted({p[1] for p in parsed})
    need(len(shown) == 2 and {(p[1], p[2]) for p in parsed} == {(s, c) for s in shown for c in ('paper', 'rejected')},
         'Options are not the four value × conclusion combinations')
    near = [p for p in parsed if abs(p[1] - right) <= tol]
    need(len({p[1] for p in near}) == 1 and near[0][1] == rounded(right, dec), 'Recomputed value is not shown correctly rounded')
    other = [s for s in shown if s != near[0][1]][0]
    need(abs(other - rounded(wrong, dec)) <= tol, 'Second value is not the registered mistake')
    hits = [p[0] for p in near if p[2] == 'paper']
    need(len(hits) == 1 and key['correct_label'] == hits[0], 'Key label disagrees with value and conclusion')
    return dict(label=hits[0], recomputed=str(rounded(right, dec)), mistake=str(rounded(wrong, dec)),
                parameters=dict(card=card['id'], kind=q['kind']), method='Decimal recomputation from the hashed card; 2×2 option structure')


def evidence_elimination(packet, key):
    card, inputs = card_of(packet, key)
    observed = {}
    for f in card['facts']:
        for k, val in f.get('observed', {}).items():
            need(k not in observed, 'Observation stated twice: ' + k)
            observed[k] = (val, f['id'])
    by_text = {h['text']: h for h in card['hypotheses']}
    need(len(by_text) == 4 and {o['value'] for o in packet['options']} == set(by_text), 'Options are not the four card explanations')
    alive = []
    for o in packet['options']:
        h = by_text[o['value']]
        clash = []
        for k, val in h['predicts'].items():
            need(k in observed, 'Prediction %s is not tested by any fact' % k)
            if observed[k][0] != val:
                clash.append(observed[k][1])
        if not clash:
            alive.append((o['label'], h))
    need(len(alive) == 1, '%d explanations survive the evidence (need exactly 1)' % len(alive))
    label, h = alive[0]
    need(h.get('paper_conclusion') is True, 'The surviving explanation is not the paper conclusion')
    need(key['correct_label'] == label, 'Key label disagrees with the elimination')
    return dict(label=label, parameters=dict(card=card['id'], observations=len(observed)),
                method='predictions compared with observations from the hashed card; single survivor')


CHECKERS = {'evidence_quantity': evidence_quantity, 'evidence_elimination': evidence_elimination}
