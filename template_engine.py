"""Reusable numeric template pilot: define -> construct -> verify. No model/API calls.

Finite, explicitly selected XYZ point sets only. No periodic wrapping or chemistry
inference. Outputs are development previews, never automatic catalog admissions.
"""
import argparse
import hashlib
import json
import math
from decimal import Decimal, localcontext, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = '0.1.0'


def parse_xyz(text):
    lines = text.splitlines()
    if len(lines) < 3:
        raise ValueError('XYZ requires count, comment and atom rows')
    try:
        n = int(lines[0].strip())
    except ValueError:
        raise ValueError('Invalid XYZ count')
    rows = [line.split() for line in lines[2:] if line.strip()]
    if n < 2 or n > 5000 or len(rows) != n:
        raise ValueError('Expected 2..5000 atoms and exact row count')
    points = []
    for row in rows:
        if len(row) != 4 or not row[0].isalpha():
            raise ValueError('Expected element and three coordinates')
        point = tuple(float(v) for v in row[1:])
        if not all(math.isfinite(v) for v in point):
            raise ValueError('Nonfinite coordinate')
        points.append(point)
    return points


def calculate(points, template):
    if template == 'global_extent':
        return max(math.dist(a, b) for i, a in enumerate(points) for b in points[i+1:])
    if template == 'equal_weight_rg':
        center = [math.fsum(p[k] for p in points)/len(points) for k in range(3)]
        return math.sqrt(math.fsum(math.dist(p, center)**2 for p in points)/len(points))
    raise ValueError('Unsupported template: '+template)


def verify_decimal(text, template):
    """Re-read decimal coordinates; Rg uses pair-distance identity, not centroid.
    Dmax necessarily uses the same definition with separately implemented loops.
    This is numerical cross-checking, not independent scientific certification.
    """
    parse_xyz(text)
    with localcontext() as ctx:
        ctx.prec = 45
        rows = [[Decimal(x) for x in line.split()[1:]] for line in text.splitlines()[2:] if line.strip()]
        maximum = Decimal(0)
        total = Decimal(0)
        for i in range(len(rows)):
            for j in range(i):
                squared = sum((rows[i][k]-rows[j][k])**2 for k in range(3))
                maximum = max(maximum, squared)
                total += squared
        if template == 'global_extent':
            return maximum.sqrt()
        if template == 'equal_weight_rg':
            return (total/Decimal(len(rows)**2)).sqrt()
        raise ValueError('Unsupported template')


def score_numeric(response, expected, tolerance, unit='angstrom'):
    """Structured response: one finite value + exact declared unit; no text judge."""
    if unit != 'angstrom' or not math.isfinite(float(expected)) or not math.isfinite(float(tolerance)) or tolerance <= 0:
        raise ValueError('Invalid scoring contract')
    if not isinstance(response, dict) or set(response) != {'value', 'unit'}:
        return False
    if type(response['value']) not in (int, float) or response['unit'] != unit:
        return False
    value = response['value']
    return math.isfinite(value) and abs(value-float(expected)) <= tolerance


def run(manifest_path, out):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    registry_path = ROOT/'templates/registry.json'
    registry = {t['id']: t for t in json.loads(registry_path.read_text(encoding='utf-8'))['templates']}
    out = Path(out)
    if out.exists():
        raise ValueError('Output exists; use a new directory to preserve history')
    ids = [x['id'] for x in manifest['items']]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Empty batch or duplicate ID')
    results, students, answers = [], [], []
    for item in manifest['items']:
        template = registry[item['template']]
        if template['status'] != 'implemented' or item['unit'] != 'angstrom' or not item['scope'].strip() or not item['source'].strip():
            raise ValueError('Missing scope/source, unsupported unit or template')
        asset = (ROOT/'docs'/item['asset']).resolve()
        if not asset.is_relative_to((ROOT/'docs/assets').resolve()):
            raise ValueError('Asset must stay inside docs/assets')
        raw = asset.read_bytes()
        text = raw.decode('utf-8-sig')
        points = parse_xyz(text)
        computed = calculate(points, item['template'])
        verified = verify_decimal(text, item['template'])
        short_answer = float(verified.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
        agreement = math.isclose(computed, float(verified), abs_tol=1e-9, rel_tol=1e-12)
        legacy_matches = abs(short_answer-item['legacy_numeric_reference']) <= 0.0001
        student = {'id': item['id'], 'derived_from': item['qa_id'],
                   'question': template['question'], 'scope': item['scope'],
                   'input': {'format': 'xyz', 'unit': 'angstrom', 'text': text},
                   'response_format': {'value': 'one number rounded to four decimals', 'unit': 'angstrom'}}
        answer = {'id': item['id'], 'value': short_answer, 'unit': 'angstrom',
                  'absolute_tolerance': 0.00005, 'rounding': 'half_up_four_decimals',
                  'explanation': template['principle'], 'source': item['source']}
        results.append({'id': item['id'], 'qa_id': item['qa_id'], 'template': item['template'],
                        'atom_count': len(points), 'input': item['asset'], 'scope': item['scope'],
                        'source': item['source'], 'input_sha256': hashlib.sha256(raw).hexdigest(),
                        'computed': computed, 'decimal_crosscheck': str(verified),
                        'numeric_agreement': agreement, 'legacy_reference': item['legacy_numeric_reference'],
                        'legacy_numeric_agreement': legacy_matches, 'short_answer': answer,
                        'status': 'numeric_verified' if agreement and legacy_matches else 'needs_revision',
                        'human_review': 'pending', 'catalog_admitted': False})
        students.append(student)
        answers.append(answer)
    report = {'version': VERSION, 'kind': 'existing_material_template_pilot',
              'count': len(results), 'passed': sum(x['status']=='numeric_verified' for x in results),
              'model_calls': 0, 'new_benchmark_questions': 0,
              'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'registry_sha256': hashlib.sha256(registry_path.read_bytes()).hexdigest(),
              'limits': 'Numeric checks only. Templates and source selection remain pending human review. Not a complete M0–M6 rerun or new catalog admission.',
              'items': results}
    out.mkdir(parents=True)
    for name, data in [('manifest.json',manifest),('student-packets.json',students),('private-answers.json',answers),('verification.json',report)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    (out/'template_engine_snapshot.py').write_bytes(Path(__file__).read_bytes())
    (out/'registry_snapshot.json').write_bytes(registry_path.read_bytes())
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=run(args.manifest,args.out)
    print(json.dumps({'count':result['count'],'passed':result['passed'],'model_calls':0}))
