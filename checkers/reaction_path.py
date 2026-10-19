"""Independent checkers for the reaction-path families. No generation code is imported.

Both checkers read the card named in the answer key (hash-verified), then re-derive everything else from what
the student was given: the attached XYZ files and the numbers printed in the question. Angles are recomputed
from interatomic distances by the law of cosines and dihedrals from an orthonormal frame on the central bond,
in Decimal arithmetic; the generator uses vector dot products and plane normals in floating point.

reaction_mechanism_choice: the classification thresholds are parsed back out of the question text, the two
    reference minima must really be one planar syn and one planar anti structure, the four options must be the
    card's four hypotheses, and exactly one must survive the rule and be the one the card concludes.
reaction_geometry_target: each requirement is parsed back out of the question, the four attachments must be the
    card's four candidates (matched by content, not by name), and exactly one must meet every requirement.

What the card says about the dataset is not something code can verify (L1 compares each locator with the
published files).
"""
import json
import re
from decimal import Decimal, localcontext
from .common import need, find, read_xyz, verify_hashes

NAMED = ('c_a', 'n_a', 'n_b', 'c_b')
EXPECTED_ELEMENTS = dict(c_a='C', n_a='N', n_b='N', c_b='C')
DECIDED_BY = ('near_linear_count', 'ring_plane')
OPS = {'>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b}
RADII = {'C': Decimal('0.76'), 'N': Decimal('0.71')}


def ctx():
    return localcontext(prec=50)


def gap(p, q):
    with ctx():
        return (sum((a - b) ** 2 for a, b in zip(p, q))).sqrt()


def angle_cosine_rule(a, v, b):
    """Law of cosines on the three interatomic distances (the generator uses a vector dot product)."""
    with ctx():
        va, vb, ab = gap(v, a), gap(v, b), gap(a, b)
        cos = (va * va + vb * vb - ab * ab) / (2 * va * vb)
        cos = max(Decimal(-1), min(Decimal(1), cos))
        return degrees(acos(cos))


def acos(x):
    """arccos in [0, pi] via atan2, to the working precision."""
    with ctx():
        root = (1 - x * x).sqrt()
        return atan2(root, x)


def atan2(y, x):
    with ctx():
        if x > 0:
            return arctan(y / x)
        if x < 0:
            return (pi() - arctan(y / -x)) if y >= 0 else (arctan(y / -x) - pi())
        return pi() / 2 if y > 0 else (-pi() / 2 if y < 0 else Decimal(0))


def arctan(x):
    """Arctangent by argument halving plus the Taylor series; |x| may be any finite value."""
    with ctx():
        if x < 0:
            return -arctan(-x)
        if x > 1:
            return pi() / 2 - arctan(1 / x)
        halvings = 0
        while x > Decimal('0.05'):
            x = x / (1 + (1 + x * x).sqrt())
            halvings += 1
        total, term, n = x, x, 1
        while True:
            term = -term * x * x
            n += 2
            step = term / n
            if step == 0:
                break
            total += step
        return total * (2 ** halvings)


def pi():
    return Decimal('3.14159265358979323846264338327950288419716939937510582097494')


def degrees(radians):
    with ctx():
        return radians * 180 / pi()


def dihedral_frame(p0, p1, p2, p3):
    """Signed dihedral from an orthonormal frame on the p1-p2 axis (the generator uses plane normals)."""
    with ctx():
        axis = [b - a for a, b in zip(p1, p2)]
        length = (sum(c * c for c in axis)).sqrt()
        axis = [c / length for c in axis]
        back = [a - b for a, b in zip(p0, p1)]
        fore = [b - a for a, b in zip(p2, p3)]
        strip = lambda v: [c - sum(x * y for x, y in zip(v, axis)) * a for c, a in zip(v, axis)]
        u, w = strip(back), strip(fore)
        x = sum(a * b for a, b in zip(u, w))
        cross = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        y = sum(a * b for a, b in zip(cross, axis))
        return degrees(atan2(y, x))


def thresholds_from(question):
    near = find(r'exceed (\d+(?:\.\d+)?) degrees', question, 'The question does not print the near-linear threshold')
    planar = find(r'within (\d+(?:\.\d+)?) degrees of 0', question, 'The question does not print the planar window')
    twisted = find(r'between (\d+(?:\.\d+)?) and (\d+(?:\.\d+)?) degrees', question,
                   'The question does not print the twisted window')
    return dict(near_linear_deg=Decimal(near.group(1)), planar_window_deg=Decimal(planar.group(1)),
                twisted_window_deg=[Decimal(twisted.group(1)), Decimal(twisted.group(2))])


def fragment_rows(question, card):
    """The four named rows, read back from the question text rather than trusted from the card."""
    need(card['fragment'] in question, 'The question does not name the fragment the card describes')
    rows = re.findall(r'([CN])(\d+) \(row (\d+)\)', card['fragment'])
    need(len(rows) == 4, 'The fragment must name exactly four atoms')
    out = {}
    for key, (element, label, row) in zip(NAMED, rows):
        need(element == EXPECTED_ELEMENTS[key], 'Fragment atom %s is not %s' % (key, EXPECTED_ELEMENTS[key]))
        need(int(label) == int(row), 'Fragment atom label and row disagree: %s%s row %s' % (element, label, row))
        need(int(row) == int(card['atoms'][key]), 'Fragment row differs from the card atom map')
        out[key] = int(row)
    return out


def descriptors(atoms, rows, thresholds):
    index = {}
    for key in NAMED:
        row = rows[key]
        need(1 <= row <= len(atoms), 'Named row outside the structure')
        need(atoms[row - 1][0] == EXPECTED_ELEMENTS[key], 'Named atom %s is not %s' % (key, EXPECTED_ELEMENTS[key]))
        index[key] = row - 1
    need(len(set(index.values())) == 4, 'The four named atoms must be distinct')
    p = {k: atoms[i][1] for k, i in index.items()}
    for first, second in (('c_a', 'n_a'), ('n_a', 'n_b'), ('n_b', 'c_b')):
        limit = Decimal('1.25') * (RADII[EXPECTED_ELEMENTS[first]] + RADII[EXPECTED_ELEMENTS[second]])
        need(gap(p[first], p[second]) <= limit, 'The C-N=N-C fragment is not bonded')
    angle_a = angle_cosine_rule(p['c_a'], p['n_a'], p['n_b'])
    angle_b = angle_cosine_rule(p['c_b'], p['n_b'], p['n_a'])
    dihedral = abs(dihedral_frame(p['c_a'], p['n_a'], p['n_b'], p['c_b']))
    count = sum(1 for x in (angle_a, angle_b) if x > thresholds['near_linear_deg'])
    if count:
        plane = 'undefined'
    elif min(dihedral, 180 - dihedral) <= thresholds['planar_window_deg']:
        plane = 'planar'
    elif thresholds['twisted_window_deg'][0] <= dihedral <= thresholds['twisted_window_deg'][1]:
        plane = 'twisted'
    else:
        plane = 'intermediate'
    cn_a, cn_b = gap(p['c_a'], p['n_a']), gap(p['c_b'], p['n_b'])
    return dict(nn_distance=gap(p['n_a'], p['n_b']), cn_a_distance=cn_a, cn_b_distance=cn_b,
                cn_asymmetry=abs(cn_a - cn_b), angle_a=angle_a, angle_b=angle_b,
                angle_max=max(angle_a, angle_b), angle_min=min(angle_a, angle_b),
                dihedral=dihedral, near_linear_count=count, ring_plane=plane)


def card_of(packet, key, family):
    paths = verify_hashes(key)
    cards = [p for rel, p in paths.items() if rel.startswith('assets/families/reaction/') and rel.endswith('.json')]
    need(len(cards) == 1, 'Exactly one reaction card must be recorded in the key')
    card = json.loads(cards[0].read_text(encoding='utf-8'))
    need(card.get('kind') == 'reaction_card' and card.get('family') == family, 'Card belongs to another family')
    need(card['ask'] in packet['question'], 'The question does not ask the card question')
    assets = {rel: p.read_text(encoding='utf-8-sig') for rel, p in paths.items() if rel.endswith('.xyz')}
    return card, assets


def reaction_mechanism_choice(packet, key):
    card, assets = card_of(packet, key, 'reaction_mechanism_choice')
    inputs = {i['name']: i['text'] for i in packet['inputs']}
    need(set(inputs) == {'transition-state.xyz', 'minimum-A.xyz', 'minimum-B.xyz'},
         'A mechanism packet attaches exactly the transition state and the two minima')
    for entry in card['files']:
        need(entry['asset'] in assets, 'Structure asset not recorded in the key: ' + entry['asset'])
    by_key = {f['key']: assets[f['asset']] for f in card['files']}
    need(inputs['transition-state.xyz'] == by_key['ts'], 'The attached transition state differs from its asset')
    need({inputs['minimum-A.xyz'], inputs['minimum-B.xyz']} == {by_key['min_a'], by_key['min_b']},
         'The attached minima differ from their assets')
    t = thresholds_from(packet['question'])
    rows = fragment_rows(packet['question'], card)
    ts = descriptors(read_xyz(inputs['transition-state.xyz']), rows, t)
    minima = [descriptors(read_xyz(inputs[n]), rows, t) for n in ('minimum-A.xyz', 'minimum-B.xyz')]
    need(all(m['ring_plane'] == 'planar' for m in minima), 'Both reference minima must be planar')
    need({('syn' if m['dihedral'] <= 90 else 'anti') for m in minima} == {'syn', 'anti'},
         'The two reference minima must be one syn and one anti structure')
    by_text = {h['text']: h for h in card['hypotheses']}
    need(len(by_text) == 4 and {o['value'] for o in packet['options']} == set(by_text),
         'Options are not the four card hypotheses')
    alive = []
    for o in packet['options']:
        h = by_text[o['value']]
        need(set(h['predicts']) == set(DECIDED_BY), 'Every hypothesis must predict exactly %s' % ', '.join(DECIDED_BY))
        if all(ts[k] == v for k, v in h['predicts'].items()):
            alive.append((o['label'], h))
    need(len(alive) == 1, '%d hypotheses survive the rule (need exactly 1)' % len(alive))
    label, h = alive[0]
    need(h.get('mechanism_conclusion') is True, 'The surviving hypothesis is not the one the card concludes')
    need(key['correct_label'] == label, 'Key label disagrees with the classification')
    return dict(label=label, recomputed=dict(angle_a=str(round(ts['angle_a'], 3)), angle_b=str(round(ts['angle_b'], 3)),
                                             dihedral=str(round(ts['dihedral'], 3)), ring_plane=ts['ring_plane'],
                                             near_linear_count=ts['near_linear_count']),
                parameters=dict(card=card['id'], conclusion=h['rule']),
                method='Decimal recomputation (law of cosines, axis frame) of the thresholds parsed from the question')


def reaction_geometry_target(packet, key):
    card, assets = card_of(packet, key, 'reaction_geometry_target')
    inputs = {i['name']: i['text'] for i in packet['inputs']}
    names = ['candidate-%d.xyz' % (i + 1) for i in range(4)]
    need(set(inputs) == set(names), 'A target packet attaches exactly candidate-1.xyz to candidate-4.xyz')
    wanted = [f for f in card['files'] if f['key'] in {c['key'] for c in card['candidates']}]
    need(len(wanted) == 4, 'The card must name four candidate structures')
    for entry in wanted:
        need(entry['asset'] in assets, 'Candidate asset not recorded in the key: ' + entry['asset'])
    need(sorted(inputs[n] for n in names) == sorted(assets[e['asset']] for e in wanted),
         'The attached candidates are not the four the card names')
    t = thresholds_from(packet['question']) if 'exceed' in packet['question'] else \
        dict(near_linear_deg=Decimal(360), planar_window_deg=Decimal(0), twisted_window_deg=[Decimal(0), Decimal(0)])
    rows = fragment_rows(packet['question'], card)
    requirements = []
    for con in card['constraints']:
        need('(%s) %s' % (con['name'], con['text']) in packet['question'],
             'Requirement %s is not stated in the question' % con['name'])
        need(con['display'] in con['text'], 'Threshold %s is not printed in its own requirement' % con['name'])
        need(con['op'] in OPS, 'Unknown comparison ' + con['op'])
        requirements.append((con['name'], con['key'], con['op'], Decimal(con['display']), Decimal(str(con['margin']))))
    need(len({name for name, _, _, _, _ in requirements}) == len(requirements), 'Requirement names must be distinct')
    alive, seen = [], set()
    for name in names:
        geometry = descriptors(read_xyz(inputs[name]), rows, t)
        fingerprint = tuple(round(geometry[k], 6) for _, k, _, _, _ in requirements)
        need(fingerprint not in seen, 'Two candidates share the constrained quantities')
        seen.add(fingerprint)
        bad = []
        for label, k, op, threshold, margin in requirements:
            need(abs(geometry[k] - threshold) >= margin, 'Candidate %s sits within the margin of %s' % (name, label))
            if not OPS[op](geometry[k], threshold):
                bad.append(label)
        if not bad:
            alive.append((name, geometry))
    need(len(alive) == 1, '%d candidates meet the target (need exactly 1)' % len(alive))
    winner = alive[0][0]
    expected = 'ABCD'[names.index(winner)]
    need([o['value'] for o in packet['options']] == [n.removesuffix('.xyz') for n in names],
         'Options are not candidate-1 to candidate-4 in order')
    need(key['correct_label'] == expected, 'Key label disagrees with the measured geometry')
    return dict(label=expected, parameters=dict(card=card['id'], candidate=winner,
                                                requirements=[name for name, _, _, _, _ in requirements]),
                method='Decimal recomputation of the requirements parsed from the question, candidates matched by content')


CHECKERS = {'reaction_mechanism_choice': reaction_mechanism_choice,
            'reaction_geometry_target': reaction_geometry_target}
