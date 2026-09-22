"""Four-choice adapter for verified numeric development pilots, not catalog admission."""
import argparse
import hashlib
import json
import math
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import template_engine as numeric

VERSION = '0.1.0'
LABELS = 'ABCD'
TOL = Decimal('0.00005')


def display(value):
    return str(Decimal(str(value)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))


def candidates(points, family):
    center = [math.fsum(p[k] for p in points)/len(points) for k in range(3)]
    radii = [math.dist(p, center) for p in points]
    distances = [math.dist(a, b) for i, a in enumerate(points) for b in points[i+1:]]
    rg = math.sqrt(math.fsum(r*r for r in radii)/len(points))
    common = [('mean_pair_distance', math.fsum(distances)/len(distances), '将所有点对距离的算术平均误当目标量。'),
              ('rms_pair_distance', math.sqrt(math.fsum(d*d for d in distances)/len(distances)), '用点对距离的均方根替代题目定义。')]
    if family == 'global_extent':
        return common + [('radius_as_extent', rg, '将等权回转半径误当最大点对间距。'),
                         ('centroid_diameter', 2*max(radii), '用两倍最大中心距代替实际最大点对间距；二者一般不同。'),
                         ('first_last_rows', math.dist(points[0], points[-1]), '仅计算XYZ首末两行，未搜索全部点对；行序不表示链端。')]
    if family == 'equal_weight_rg':
        return common + [('mean_radius', math.fsum(radii)/len(radii), '用中心距算术平均替代中心距均方根。'),
                         ('maximum_radius', max(radii), '用最大中心距替代均方根。'),
                         ('diameter_for_radius', 2*rg, '把回转半径误乘二，输出直径式量。')]
    raise ValueError('Unsupported family')


def ordered(items, seed, context):
    # Version-independent deterministic permutation; seed is reviewer-only.
    return sorted(items, key=lambda x: hashlib.sha256(f'{seed}|{context}|{x[0]}'.encode()).digest())


def validate_options(options, expected):
    if len(options) != 4 or [o['label'] for o in options] != list(LABELS):
        raise ValueError('Exactly A/B/C/D required')
    values = [Decimal(o['value']) for o in options]
    if any(o['unit'] != 'angstrom' or not v.is_finite() or v < 0 or o['value'] != display(v) for o, v in zip(options, values)):
        raise ValueError('Invalid unit, value or precision')
    if any(abs(a-b) <= 2*TOL for i, a in enumerate(values) for b in values[i+1:]):
        raise ValueError('Duplicate or overlapping tolerance intervals')
    correct = [o['label'] for o, v in zip(options, values) if abs(v-Decimal(str(expected))) <= TOL]
    if len(correct) != 1:
        raise ValueError('Not exactly one correct option')
    return correct[0]


def score_choice(response, correct):
    if correct not in LABELS or len(correct) != 1:
        raise ValueError('Invalid answer key')
    return isinstance(response, str) and response.strip().upper() == correct


def construct(text, family, seed, instance):
    points = numeric.parse_xyz(text)
    exact = numeric.verify_decimal(text, family)
    computed = numeric.calculate(points, family)
    if not math.isclose(computed, float(exact), abs_tol=1e-9, rel_tol=1e-12):
        raise ValueError('Numeric crosscheck failed')
    correct = display(exact)
    selected = [('correct', correct, '由题目定义计算，并用十进制实现交叉复核。')]
    rejected = []
    for rule, value, reason in ordered(candidates(points, family), seed, instance+'/select'):
        rounded = display(value)
        if any(abs(Decimal(rounded)-Decimal(x[1])) <= 2*TOL for x in selected):
            rejected.append({'rule': rule, 'value': rounded, 'reason': '重复或容差区间相交'})
        elif len(selected) < 4:
            selected.append((rule, rounded, reason))
    if len(selected) != 4:
        raise ValueError('Fewer than three distinct valid misconception distractors')
    permutation = ordered(selected, seed, instance+'/labels')
    options = [{'label': label, 'value': value, 'unit': 'angstrom'} for label, (_, value, _) in zip(LABELS, permutation)]
    key = validate_options(options, exact)
    audit = {'correct_label': key, 'correct_value': correct, 'decimal_crosscheck': str(exact),
             'absolute_tolerance': str(TOL), 'option_permutation_seed': seed,
             'permutation_algorithm': 'sha256-sort-v1', 'uniqueness_check': True,
             'options': [{'label': label, 'rule': rule, 'value': value, 'reason': reason,
                          'is_correct': rule == 'correct',
                          'absolute_error': str(abs(Decimal(value)-exact))}
                         for label, (rule, value, reason) in zip(LABELS, permutation)],
             'excluded_candidates': rejected, 'human_review': 'pending',
             'limits': '错误机制是模板设计假设，未通过学习者实验验证；正确性检查不代表难度或科学意义通过。'}
    return options, audit


def run(source, out, seed='geobench-choice-v1'):
    source, out = Path(source), Path(out)
    if out.exists():
        raise ValueError('Output exists; preserve history')
    read = lambda name: json.loads((source/name).read_text(encoding='utf-8'))
    report = read('verification.json')
    for filename, key in [('template_engine_snapshot.py', 'code_sha256'), ('registry_snapshot.json', 'registry_sha256')]:
        if hashlib.sha256((source/filename).read_bytes()).hexdigest() != report[key]:
            raise ValueError('Numeric snapshot mismatch')
    students, teachers, failures = [], [], []
    rows = {r['id']: r for r in report['items']}
    for packet in read('student-packets.json'):
        row = rows[packet['id']]
        try:
            if row['status'] != 'numeric_verified' or packet['input']['unit'] != 'angstrom':
                raise ValueError('Unverified numeric input')
            asset = (numeric.ROOT/'docs'/row['input']).resolve()
            if not asset.is_relative_to((numeric.ROOT/'docs/assets').resolve()):
                raise ValueError('Invalid asset path')
            raw = asset.read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['input_sha256'] or raw.decode('utf-8-sig') != packet['input']['text']:
                raise ValueError('Input provenance mismatch')
            options, audit = construct(packet['input']['text'], row['template'], seed, packet['id'])
            if abs(Decimal(audit['correct_value'])-Decimal(str(row['short_answer']['value']))) > TOL:
                raise ValueError('Previous answer mismatch')
            question = packet['question'].replace('Return only one value rounded to four decimal places and unit angstrom.', '').strip()
            question += ' Select the unique correct value in angstrom (four decimal places). Return only A, B, C or D.'
            students.append({'id': 'MC-'+packet['id'], 'derived_from': packet['derived_from'],
                             'question': question, 'scope': packet['scope'], 'input': packet['input'],
                             'options': options, 'response_format': 'one label: A/B/C/D'})
            teachers.append(dict(audit, id='MC-'+packet['id'], numeric_id=packet['id'],
                                 source=row['source'], input_sha256=row['input_sha256'], template=row['template']))
        except ValueError as e:
            failures.append({'id': packet['id'], 'reason': str(e)})
    rank_counts = {}
    for teacher in teachers:
        rank = sorted(Decimal(o['value']) for o in teacher['options']).index(Decimal(teacher['correct_value']))+1
        teacher['correct_numeric_rank'] = rank
        counts = rank_counts.setdefault(teacher['template'], {str(i): 0 for i in range(1, 5)})
        counts[str(rank)] += 1
    result = {'version': VERSION, 'attempted': len(rows), 'passed': len(students), 'failures': failures,
              'model_calls': 0, 'new_benchmark_questions': 0, 'human_review': 'pending',
              'correct_numeric_rank_counts': rank_counts,
              'difficulty_review': 'Inspect rank shortcuts (always largest/smallest), distractor plausibility and option-only baselines before admission. Numerical validity alone is insufficient.',
              'seed': seed, 'correct_position_counts': {l: sum(t['correct_label'] == l for t in teachers) for l in LABELS},
              'source_report_sha256': hashlib.sha256((source/'verification.json').read_bytes()).hexdigest(),
              'source_manifest_sha256': hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),
              'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'numeric_code_sha256': hashlib.sha256(Path(numeric.__file__).read_bytes()).hexdigest()}
    out.mkdir(parents=True)
    for name, data in [('student-packets.json',students), ('private-answers.json',teachers), ('verification.json',result)]:
        (out/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    (out/'choice_engine_snapshot.py').write_bytes(Path(__file__).read_bytes())
    (out/'template_engine.py').write_bytes(Path(numeric.__file__).read_bytes())
    for name in ['manifest.json', 'verification.json', 'student-packets.json']:
        (out/('numeric-'+name)).write_bytes((source/name).read_bytes())
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', default='geobench-choice-v1')
    a = p.parse_args()
    print(json.dumps(run(a.source, a.out, a.seed), ensure_ascii=False))
