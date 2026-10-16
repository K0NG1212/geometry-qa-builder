"""Evidence-to-conclusion questions from papers (meeting 6: give the evidence, ask for the key conclusion).

Each question reads one hand-transcribed evidence card, docs/assets/families/evidence/<id>.json, checked against the
full text kept locally (inputs/papers/, not in the repository). The card lists the facts (numbers and observations,
paraphrased, each with its place in the paper), the paper's conclusion and the alternatives the paper rules out. The
student receives the facts as an attachment (evidence.txt), plus any structure files; never the conclusions' sources.

evidence_quantity (inference): compute one quantity from the facts (a spacing, an area, a field, a twist angle, a
    count, a band width, a ratio, a distance difference), then judge. The four options cross two values (correct, or
    the value of a registered mistake) with two conclusions (the paper's, or one the paper rules out), so neither half
    alone gives the answer and no option is a majority cue. The value is computed here and recomputed by the checker.
evidence_elimination (inference): four explanations; each states what it predicts for the observed facts. The code
    keeps the explanations whose predictions all match the observations: exactly one may survive, and it must be the
    paper's conclusion; every other one must contradict at least one fact shown to the student.

What code guarantees: the numbers, the 2x2 structure, and the logical elimination over the card. What it cannot: that
the card renders the paper faithfully. That is the L1 check (each fact and conclusion has a locator for side-by-side
comparison with the original).
"""
import json
import math
import re
from . import kit

VERSION = '0.1.0'
H = 6.62607015e-34          # J s, exact (SI 2019)
E = 1.602176634e-19         # C, exact (SI 2019)
FLUX = {'h/2e': H / (2 * E), 'h/e': H / E}
UNITS = {'nm': ' nm', 'um^2': ' µm²', 'T': ' T', 'degree': '°', 'angstrom': ' Å', '': ''}
NUMBER = re.compile(r'^(-?\d+(?:\.\d+)?)(?: × 10\^(-?\d+))?')


def shown_value(display):
    """Number at the start of a display string such as '1.5 × 10^11 cm^-2' or '4 µm × 4 µm'."""
    m = NUMBER.match(display)
    if not m:
        raise ValueError('Display string does not start with a number: ' + display)
    return float(m.group(1)) * (10 ** int(m.group(2)) if m.group(2) else 1)


def load(root, rel):
    raw = (root / 'docs' / rel).read_bytes()
    card = json.loads(raw.decode('utf-8'))
    if card.get('kind') != 'evidence_card':
        raise ValueError('Not an evidence card: ' + rel)
    return card, raw


def facts_text(card):
    return ''.join('%s. %s\n' % (f['id'], f['text']) for f in card['facts'])


def values(card):
    """Named numbers of the card; each must be displayed verbatim in its fact and parse back to the stored value."""
    out = {}
    for f in card['facts']:
        for name, (value, display) in f.get('values', {}).items():
            if display not in f['text'] or not math.isclose(shown_value(display), value, rel_tol=1e-12):
                raise ValueError('Value %s is not shown as stored in %s' % (name, f['id']))
            if name in out:
                raise ValueError('Duplicate value name ' + name)
            out[name] = float(value)
    return out


def arg(v, x):
    return v[x] if isinstance(x, str) else float(x)


def structures(root, card):
    files, inputs, hashes = {}, [], {}
    for f in card.get('files', []):
        raw = (root / 'docs' / f['asset']).read_bytes()
        text = raw.decode('utf-8')
        files[f['key']] = kit.parse_xyz(text)
        inputs.append(dict(name=f['name'], format='xyz', unit='angstrom', text=text))
        hashes[f['asset']] = kit.sha256(raw)
    return files, inputs, hashes


def compute(kind, a, v, files):
    """Quantity in the card's unit. Distances in the cards are in nm unless the unit says otherwise."""
    if kind == 'inverse_sqrt_density':                           # cm^-2 -> nm
        return 1e7 / math.sqrt(arg(v, a['n_cm2']))
    if kind == 'flux_loop_area':                                 # S = Phi / dB, in um^2
        return FLUX[a['flux']] / (arg(v, a['period_mT']) * 1e-3) * 1e12
    if kind == 'thin_film_parallel_field':                       # Bc|| = sqrt(3) Phi0 / (pi d xi), in T
        return math.sqrt(3) * FLUX['h/2e'] / (math.pi * arg(v, a['d_nm']) * 1e-9 * arg(v, a['xi_nm']) * 1e-9)
    if kind == 'perpendicular_gl_field':                         # Bc2 = Phi0 / (2 pi xi^2), in T
        return FLUX['h/2e'] / (2 * math.pi * (arg(v, a['xi_nm']) * 1e-9) ** 2)
    if kind == 'equal_area_twist':                               # Heron area -> equilateral side -> twist (degrees)
        x, y, z = (arg(v, a[k]) for k in ('l1', 'l2', 'l3'))
        s = (x + y + z) / 2
        area = math.sqrt(s * (s - x) * (s - y) * (s - z))
        side = math.sqrt(4 * area / math.sqrt(3))
        return math.degrees(2 * math.asin(arg(v, a['a_nm']) / (2 * side)))
    if kind == 'single_wavelength_twist':
        return math.degrees(2 * math.asin(arg(v, a['a_nm']) / (2 * arg(v, a['l']))))
    if kind == 'flux_quanta_count':                              # N = B A / Phi
        side = arg(v, a['side_um']) * 1e-6
        return arg(v, a['B_mT']) * 1e-3 * side * side / FLUX[a['flux']]
    if kind in ('cholesteric_bandwidth', 'cholesteric_centre'):  # p = 1/(HTP c); width p*dn, centre p*<n>, in nm
        pitch_nm = 1e3 / (arg(v, a['htp_um']) * arg(v, a['c_wt']) / 100)
        ne, no = arg(v, a['ne']), arg(v, a['no'])
        return pitch_nm * ((ne - no) if kind == 'cholesteric_bandwidth' else (ne + no) / 2)
    if kind == 'htp_ratio':                                      # HTP = n / (lambda c): ratio = lam_R c_R / (lam_L c_L)
        return arg(v, a['lam_R']) * arg(v, a['c_R']) / (arg(v, a['lam_L']) * arg(v, a['c_L']))
    if kind == 'wavelength_ratio':
        return arg(v, a['lam_R']) / arg(v, a['lam_L'])
    if kind == 'xyz_distance_difference':                        # rows counted from 1, in angstrom
        def d(key, rows):
            elements, points = files[key]
            i, j = (r - 1 for r in rows)
            return math.dist(points[i], points[j])
        return d(a['a_file'], a['a_rows']) - d(a['b_file'], a['b_rows'])
    raise ValueError('Unknown quantity kind ' + kind)


def question(card, extra_files):
    files = ' and '.join(['evidence.txt'] + [f['name'] for f in card.get('files', [])]) if extra_files else 'evidence.txt'
    return ('%s The attached %s give%s the evidence (facts E1–E%d from %s; numbers as reported in the paper). %s'
            % (card['topic'], files, '' if extra_files else 's', len(card['facts']), card['short_citation'], card['ask']))


def evidence_input(card):
    return dict(name='evidence.txt', format='text', unit='单位见各条', text=facts_text(card))


def build_quantity(spec, root, seed):
    card, raw = load(root, spec['asset'])
    if card['family'] != 'evidence_quantity':
        raise ValueError('Card is not a quantity card')
    v = values(card)
    files, xyz_inputs, hashes = structures(root, card)
    hashes[spec['asset']] = kit.sha256(raw)
    q, err, concl = card['quantity'], card['error'], card['conclusions']
    right, wrong = compute(q['kind'], q['args'], v, files), compute(err['kind'], err['args'], v, files)
    dec = q['decimals']
    shown_right, shown_wrong = kit.display(right, dec), kit.display(wrong, dec)
    if abs(right - wrong) < float(q['min_separation']) or shown_right == shown_wrong:
        raise ValueError('Mistake value too close to the correct value')
    unit = UNITS[q['unit']]
    text = lambda shown, c: '%s %s%s. %s' % (q['label'], shown, unit, c['text'])
    paper, rejected = concl['paper'], concl['rejected']
    correct = ('correct', text(shown_right, paper), '数值按原文数据计算正确，结论即原文结论（%s）。' % paper['locator'], 3)
    others = [
        (rejected['rule'], text(shown_right, rejected), '数值正确，但结论是原文排除的解释：%s（%s）' % (rejected['reason'], rejected['locator']), 3),
        (err['rule'], text(shown_wrong, paper), '结论措辞取自原文，但数值来自错误做法：%s' % err['reason'], err.get('plausibility', 2)),
        (err['rule'] + '+' + rejected['rule'], text(shown_wrong, rejected), '数值来自错误做法（%s），结论也是原文排除的解释。' % err['reason'], 2)]
    order = kit.place(correct, others, spec.get('target_position'), seed, spec['id'], key=lambda x: x[1])
    options = [dict(label=l, value=x[1]) for l, x in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [x[0] == 'correct' for x in order])
    audit = [dict(label=l, value=x[1], rule=x[0], reason=x[2], is_correct=x[0] == 'correct', plausibility=x[3])
             for l, x in zip(kit.LABELS, order)]
    s = card['scale']
    return dict(
        question=question(card, bool(xyz_inputs)), scope=spec['scope'], inputs=[evidence_input(card)] + xyz_inputs, numeric=None,
        options=options, correct_label=key, option_audit=audit, excluded_candidates=[], rank=None,
        option_order='2×2: value (correct / registered mistake) × conclusion (paper / ruled out); correct at batch target',
        checks=dict(card=card['id'], value=right, shown=shown_right, mistake_value=wrong, mistake_rule=err['rule'],
                    decimals=dec, unit=q['unit'], facts={f['id']: f['locator'] for f in card['facts']},
                    paper_conclusion_locator=paper['locator'], notes=card.get('notes', []),
                    limits='数值由代码计算并经独立检查器复算；结论措辞与证据转录须对照原文位置人工核对（L1）。四个选项是“数值 × 结论”两个二元判断的组合。'),
        scales=dict(input_nm=s['input_nm'], reasoning_nm=s['reasoning_nm'], reasoning_definition=s['definition']),
        input_hashes=hashes)


def eliminate(card):
    """Explanations whose predictions all agree with the observations; with the contradicting facts of the others."""
    observed, where = {}, {}
    for f in card['facts']:
        for k, val in f.get('observed', {}).items():
            if k in observed:
                raise ValueError('Observation stated twice: ' + k)
            observed[k], where[k] = val, f['id']
    survivors, conflicts = [], {}
    for h in card['hypotheses']:
        unknown = set(h['predicts']) - set(observed)
        if unknown:
            raise ValueError('Prediction not covered by any fact: ' + ', '.join(sorted(unknown)))
        bad = sorted({where[k] for k, val in h['predicts'].items() if observed[k] != val})
        conflicts[h['rule']] = bad
        if not bad:
            survivors.append(h)
    return survivors, conflicts


def build_elimination(spec, root, seed):
    card, raw = load(root, spec['asset'])
    if card['family'] != 'evidence_elimination' or len(card['hypotheses']) != 4:
        raise ValueError('Elimination cards need exactly four explanations')
    survivors, conflicts = eliminate(card)
    if len(survivors) != 1 or not survivors[0].get('paper_conclusion'):
        raise ValueError('Exactly one explanation, the paper conclusion, must survive the evidence')
    paper = survivors[0]
    correct = ('correct', paper['text'], '与全部事实一致，即原文结论（%s）。' % paper['locator'], 3)
    others = [(h['rule'], h['text'], '与 %s 矛盾：%s（%s）' % ('、'.join(conflicts[h['rule']]), h['reason'], h['locator']), 3)
              for h in card['hypotheses'] if h is not paper]
    order = kit.place(correct, others, spec.get('target_position'), seed, spec['id'], key=lambda x: x[1])
    options = [dict(label=l, value=x[1]) for l, x in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [x[0] == 'correct' for x in order])
    audit = [dict(label=l, value=x[1], rule=x[0], reason=x[2], is_correct=x[0] == 'correct') for l, x in zip(kit.LABELS, order)]
    s = card['scale']
    return dict(
        question=question(card, False), scope=spec['scope'], inputs=[evidence_input(card)], numeric=None,
        options=options, correct_label=key, option_audit=audit, excluded_candidates=[], rank=None,
        checks=dict(card=card['id'], contradicted_by=conflicts, facts={f['id']: f['locator'] for f in card['facts']},
                    paper_conclusion_locator=paper['locator'], unique_survivor=True,
                    limits='排除逻辑由代码执行；各解释的“预期”与事实转录须对照原文位置人工核对（L1），程序不能保证其科学正确。'),
        scales=dict(input_nm=s['input_nm'], reasoning_nm=s['reasoning_nm'], reasoning_definition=s['definition']),
        input_hashes={spec['asset']: kit.sha256(raw)})
