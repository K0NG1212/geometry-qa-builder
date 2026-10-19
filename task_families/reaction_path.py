"""Reaction-path families on a published kinetic transition network (Landscape17, CC BY 4.0).

Landscape17 gives every local minimum and transition state of azobenzene at omega-B97x/6-31G(d), plus the
approximate steepest-descent paths between them. The structures are copied into four-column XYZ by
tools/build_reaction_assets.py; a card in docs/assets/families/reaction/<id>.json says which file is which and
records where each one comes from.

reaction_mechanism_choice (inference): the student gets a transition state and the two minima it connects, and
    decides which motion it corresponds to. The decision is made from geometry under a classification rule
    printed in the question: how many C-N=N angles have opened towards 180 degrees, and - only when none has -
    whether the two rings are coplanar or twisted about the N=N bond.

    The order of that rule is not a convenience. When one C-N=N angle approaches 180 degrees the C-N=N-C
    dihedral becomes ill-conditioned, because the three atoms defining one of its planes become collinear: at
    the inversion transition state the printed dihedral swings between 0 and 180 under coordinate changes far
    below the published precision. So the angles are classified first, and the dihedral is declared undefined
    whenever an angle has opened. A question whose answer turned on that dihedral would not be well posed.

reaction_geometry_target (design): a target stated as windows on geometric quantities, and four configurations
    from one steepest-descent path. Exactly one meets the target; the student must measure the candidates
    rather than recognise them, so the four files are attached under neutral names in a seeded order.

What code guarantees: the descriptors (two implementations each), that the two minima really are one planar
cis and one planar trans structure, that exactly one hypothesis survives the rule or exactly one candidate
meets the target, and that it is the one the card expects. What it cannot: that the four hypotheses are the
right four to offer, or that the classification thresholds match the literature. That is the L1 check against
the locators the card records.
"""
import json
import math
from . import kit

VERSION = '0.1.0'
NAMED = ('c_a', 'n_a', 'n_b', 'c_b')
EXPECTED_ELEMENTS = dict(c_a='C', n_a='N', n_b='N', c_b='C')
DECIDED_BY = ('near_linear_count', 'ring_plane')
OPS = {'>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b}
UNITS = {'degree': '°', 'angstrom': ' Å'}


def load(root, rel, family):
    raw = (root / 'docs' / rel).read_bytes()
    card = json.loads(raw.decode('utf-8'))
    if card.get('kind') != 'reaction_card' or card.get('family') != family:
        raise ValueError('Not a %s card: %s' % (family, rel))
    return card, raw


def structure(root, asset):
    raw = (root / 'docs' / asset).read_bytes()
    text = raw.decode('utf-8-sig')
    elements, points = kit.parse_xyz(text)
    return elements, points, text, raw


def fold(angle):
    """A dihedral as an unsigned 0-180 value: its sign is a labelling choice, not geometry."""
    return abs(angle)


def descriptors(elements, points, atoms, thresholds):
    """Geometry of the C-N=N-C fragment, each quantity computed twice by different routes."""
    index = {}
    for key in NAMED:
        row = int(atoms[key])
        if not 1 <= row <= len(points):
            raise ValueError('Named row outside the structure: %s' % key)
        if elements[row - 1] != EXPECTED_ELEMENTS[key]:
            raise ValueError('Named atom %s is not %s' % (key, EXPECTED_ELEMENTS[key]))
        index[key] = row - 1
    ca, na, nb, cb = (index[k] for k in NAMED)
    if len({ca, na, nb, cb}) != 4:
        raise ValueError('The four named atoms must be distinct')
    edges = kit.bond_graph(elements, points)
    for i, j in ((ca, na), (na, nb), (nb, cb)):
        if (min(i, j), max(i, j)) not in edges:
            raise ValueError('The C-N=N-C fragment is not bonded under the covalent-radius rule')
    angle_a = kit.angle_acos(points[ca], points[na], points[nb])
    angle_b = kit.angle_acos(points[cb], points[nb], points[na])
    for first, second in ((angle_a, kit.angle_atan2(points[ca], points[na], points[nb])),
                          (angle_b, kit.angle_atan2(points[cb], points[nb], points[na]))):
        if abs(first - second) > 1e-9:
            raise ValueError('Angle implementations disagree')
    dihedral = fold(kit.dihedral_normals(points[ca], points[na], points[nb], points[cb]))
    if abs(dihedral - fold(kit.dihedral_projection(points[ca], points[na], points[nb], points[cb]))) > 1e-6:
        raise ValueError('Dihedral implementations disagree')
    near_linear = thresholds['near_linear_deg']
    count = sum(1 for x in (angle_a, angle_b) if x > near_linear)
    if count:
        plane = 'undefined'                       # a near-collinear C-N=N makes the dihedral ill-conditioned
    elif min(dihedral, 180 - dihedral) <= thresholds['planar_window_deg']:
        plane = 'planar'
    elif thresholds['twisted_window_deg'][0] <= dihedral <= thresholds['twisted_window_deg'][1]:
        plane = 'twisted'
    else:
        plane = 'intermediate'
    nn = math.dist(points[na], points[nb])
    cn_a, cn_b = math.dist(points[ca], points[na]), math.dist(points[cb], points[nb])
    return dict(nn_distance=nn, cn_a_distance=cn_a, cn_b_distance=cn_b, cn_asymmetry=abs(cn_a - cn_b),
                angle_a=angle_a, angle_b=angle_b, angle_max=max(angle_a, angle_b), angle_min=min(angle_a, angle_b),
                dihedral=dihedral, near_linear_count=count, ring_plane=plane,
                span_nm=max(math.dist(points[i], points[j]) for i in index.values() for j in index.values()) / 10,
                input_nm=kit.dmax(points) / 10)


def rule_text(t):
    # No occurrence of the word that names an answer-key field may appear in student-visible text (the engine
    # separation test scans the packets for it), so this says "convention" rather than naming it.
    return ('Classification convention for this question, applied to the C-N=N-C fragment: first count how many '
            'of the two C-N=N angles exceed %g degrees. If one or both do, the C-N=N-C dihedral is treated as '
            'undefined, because a C-N=N angle near 180 degrees makes the three atoms of one of its planes '
            'collinear and the dihedral numerically unstable. If neither does, the two rings count as coplanar '
            'when the dihedral is within %g degrees of 0 or of 180, and as twisted when it lies between %g and '
            '%g degrees.' % (t['near_linear_deg'], t['planar_window_deg'], *t['twisted_window_deg']))


def attachments(root, card, keys, names):
    inputs, hashes, texts = [], {}, {}
    for key, name in zip(keys, names):
        [entry] = [f for f in card['files'] if f['key'] == key]
        elements, points, text, raw = structure(root, entry['asset'])
        inputs.append(dict(name=name, format='xyz', unit='angstrom', text=text))
        hashes[entry['asset']] = kit.sha256(raw)
        texts[key] = (elements, points, entry)
    return inputs, hashes, texts


def build_mechanism(spec, root, seed):
    card, raw = load(root, spec['asset'], 'reaction_mechanism_choice')
    if len(card['hypotheses']) != 4:
        raise ValueError('A mechanism card needs exactly four hypotheses')
    names = ['transition-state.xyz', 'minimum-A.xyz', 'minimum-B.xyz']
    inputs, hashes, parts = attachments(root, card, ['ts', 'min_a', 'min_b'], names)
    hashes[spec['asset']] = kit.sha256(raw)
    t, atoms = card['thresholds'], card['atoms']
    ts = descriptors(*parts['ts'][:2], atoms, t)
    minima = [descriptors(*parts[k][:2], atoms, t) for k in ('min_a', 'min_b')]
    if any(m['ring_plane'] != 'planar' for m in minima):
        raise ValueError('Both minima must be planar for the premise of this question to hold')
    sides = {('syn' if m['dihedral'] <= 90 else 'anti') for m in minima}
    if sides != {'syn', 'anti'}:
        raise ValueError('The two minima must be one cis and one trans structure')
    survivors, conflicts = [], {}
    for h in card['hypotheses']:
        if set(h['predicts']) != set(DECIDED_BY):
            raise ValueError('Every hypothesis must predict exactly %s' % ', '.join(DECIDED_BY))
        bad = sorted(k for k, v in h['predicts'].items() if ts[k] != v)
        conflicts[h['rule']] = bad
        if not bad:
            survivors.append(h)
    if len(survivors) != 1 or not survivors[0].get('mechanism_conclusion'):
        raise ValueError('Exactly one hypothesis, the one the card expects, must survive the rule')
    best = survivors[0]
    measured = '两个 C–N=N 角为 %.3f° 与 %.3f°（超过 %g° 的有 %d 个），C–N=N–C 二面角 %.3f°，判为 %s' % (
        ts['angle_a'], ts['angle_b'], t['near_linear_deg'], ts['near_linear_count'], ts['dihedral'], ts['ring_plane'])
    correct = ('correct', best['text'], '按题干的分类规则，测得的几何只与这一条相符（%s）；依据 %s。' % (measured, best['locator']), 3)
    others = [(h['rule'], h['text'], '与测得的 %s 矛盾：%s（%s）' % ('、'.join(conflicts[h['rule']]), h['reason'], h['locator']), 3)
              for h in card['hypotheses'] if h is not best]
    order = kit.place(correct, others, spec.get('target_position'), seed, spec['id'], key=lambda x: x[1])
    options = [dict(label=l, value=x[1]) for l, x in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [x[0] == 'correct' for x in order])
    audit = [dict(label=l, value=x[1], rule=x[0], reason=x[2], is_correct=x[0] == 'correct') for l, x in zip(kit.LABELS, order)]
    question = ('%s The attached %s is the transition state under study; %s and %s are the two distinct '
                'minima of this molecule in the published network, one cis and one trans, attached for '
                'reference in no stated order (rows counted from 1 after the two XYZ header lines; the '
                'fragment is %s). %s %s'
                % (card['system'], names[0], names[1], names[2], card['fragment'], rule_text(t), card['ask']))
    return dict(
        question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
        option_audit=audit, excluded_candidates=[], rank=None,
        checks=dict(card=card['id'], descriptors={k: v for k, v in ts.items() if k not in ('span_nm', 'input_nm')},
                    minima=[{k: m[k] for k in ('dihedral', 'angle_max', 'ring_plane')} for m in minima],
                    contradicted_by=conflicts, thresholds=t, conclusion=best['rule'],
                    sources={f['key']: f['locator'] for f in card['files']}, notes=card.get('notes', []),
                    limits='几何量由代码两套实现复算，排除逻辑由代码执行；四个候选机理是否该是这四个、分类阈值是否合乎文献，'
                           '须对照卡片记录的原文位置人工核对（L1）。'),
        scales=dict(input_nm=ts['input_nm'], reasoning_nm=ts['span_nm'],
                    reasoning_definition='C–N=N–C 四原子两两最大间距（局部 0.1–1 nm）'),
        input_hashes=hashes)


def build_target(spec, root, seed):
    card, raw = load(root, spec['asset'], 'reaction_geometry_target')
    keys = [c['key'] for c in card['candidates']]
    if len(keys) != 4 or len(set(keys)) != 4:
        raise ValueError('A target card needs exactly four distinct candidates')
    t, atoms = card['thresholds'], card['atoms']
    for con in card['constraints']:
        if con['op'] not in OPS:
            raise ValueError('Unknown comparison ' + con['op'])
        if con['display'] not in con['text'] or float(con['display']) != float(con['value']):
            raise ValueError('Threshold %s is not printed in the requirement as stored' % con['name'])
    geometry = {k: descriptors(*structure(root, [f for f in card['files'] if f['key'] == k][0]['asset'])[:2],
                               atoms, t) for k in keys}
    if len({tuple(round(geometry[k][c['key']], 6) for c in card['constraints']) for k in keys}) != 4:
        raise ValueError('Candidates must differ in the constrained quantities')
    failures = {}
    for k in keys:
        bad = []
        for con in card['constraints']:
            value, threshold, margin = geometry[k][con['key']], float(con['value']), float(con['margin'])
            if abs(value - threshold) < margin:
                raise ValueError('Candidate %s sits within %s of the %s threshold' % (k, con['margin'], con['name']))
            if not OPS[con['op']](value, threshold):
                bad.append(con['name'])
        failures[k] = bad
    winners = [k for k in keys if not failures[k]]
    if len(winners) != 1:
        raise ValueError('%d candidates meet the target (need exactly 1)' % len(winners))
    if winners[0] != card['expected']:
        raise ValueError('The candidate that meets the target is not the one the card expects')
    # The seeded assignment of contents to candidate-1..4 is what carries the batch's target position, so the
    # options can be listed in candidate order without the order itself pointing at the answer.
    shown = [k for (k,) in kit.place((winners[0],), [(k,) for k in keys if k != winners[0]],
                                     spec.get('target_position'), seed, spec['id'] + '/candidates',
                                     key=lambda x: x[0])]
    names = ['candidate-%d.xyz' % (i + 1) for i in range(4)]
    inputs, hashes, parts = attachments(root, card, shown, names)
    hashes[spec['asset']] = kit.sha256(raw)
    label_of = dict(zip(shown, names))
    describe = lambda k: label_of[k].removesuffix('.xyz')
    quantities = {c['key']: c for c in card['constraints']}        # one reading per quantity, not per constraint
    value_text = lambda k: '、'.join('%s = %s%s' % (c['key'], kit.display(geometry[k][key], c['decimals']),
                                                   UNITS[c['unit']]) for key, c in quantities.items())
    entries = [(('correct' if k == winners[0] else card['rules'][k]), describe(k),
                ('满足全部目标：%s（来源 %s）。' % (value_text(k), [f for f in card['files'] if f['key'] == k][0]['locator']))
                if k == winners[0] else
                ('不满足 %s：%s' % ('、'.join(failures[k]), value_text(k))), 3) for k in shown]
    order = entries                                      # listed in candidate order; the assignment above placed the answer
    options = [dict(label=l, value=x[1]) for l, x in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [x[0] == 'correct' for x in order])
    audit = [dict(label=l, value=x[1], rule=x[0], reason=x[2], is_correct=x[0] == 'correct') for l, x in zip(kit.LABELS, order)]
    targets = '; '.join('(%s) %s' % (c['name'], c['text']) for c in card['constraints'])
    question = ('%s The four attached files candidate-1.xyz to candidate-4.xyz are %s, in no particular order '
                '(rows counted from 1 after the two XYZ header lines; the fragment is %s). Required: %s. '
                'Exactly one of the four meets every requirement. %s'
                % (card['system'], card['candidate_note'], card['fragment'], targets, card['ask']))
    return dict(
        question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
        option_audit=audit, excluded_candidates=[], rank=None,
        option_order='候选内容按种子分配到 candidate-1…4，与答案位置无关',
        checks=dict(card=card['id'], expected=card['expected'], shown_order=shown, failures=failures,
                    measured={k: {c['key']: geometry[k][c['key']] for c in card['constraints']} for k in shown},
                    thresholds=t, sources={f['key']: f['locator'] for f in card['files']}, notes=card.get('notes', []),
                    limits='几何量由代码两套实现复算，约束逐条比对；这是“按几何目标选构型”，不是改变结构的分子设计，'
                           '是否计为设计题需人工审定（L1）。'),
        scales=dict(input_nm=geometry[winners[0]]['input_nm'], reasoning_nm=geometry[winners[0]]['span_nm'],
                    reasoning_definition='C–N=N–C 四原子两两最大间距（局部 0.1–1 nm）'),
        input_hashes=hashes)
