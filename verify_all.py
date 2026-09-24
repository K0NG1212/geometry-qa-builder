"""Run the independent checkers over every instance of a batch. No model calls.

Input: a family run directory (student-packets.json + private-answers.json) or the
published workbench JSON. Exit status 1 if any instance fails, so a batch with a
single disagreement cannot be exported.

python verify_all.py --run runs/family-pilot-v01 --out runs/family-pilot-v01-independent-check.json
python verify_all.py --workbench docs/data/family-workbench.json --out docs/data/independent-check.json
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import checkers

ROOT = Path(__file__).resolve().parent


def load(run=None, workbench=None):
    if run:
        run = Path(run)
        read = lambda n: json.loads((run / n).read_text(encoding='utf-8'))
        return read('student-packets.json'), read('private-answers.json'), dict(source=str(run.name))
    data = json.loads(Path(workbench).read_text(encoding='utf-8'))
    return data['student_packets'], data['teacher_answers'], dict(source=Path(workbench).name, run=data['run'])


def verify(packets, keys, origin):
    keys = {k['id']: k for k in keys}
    missing = sorted(set(keys) ^ {p['id'] for p in packets})
    results = [checkers.check(p, keys[p['id']]) if p['id'] in keys else
               dict(id=p['id'], family=p['family'], status='fail', problem='No answer key') for p in packets]
    results += [dict(id=i, family=keys[i]['family'], status='fail', problem='Answer key without packet')
                for i in missing if i in keys]
    by_family = {}
    for r in results:
        f = by_family.setdefault(r['family'], Counter())
        f[r['status']] += 1
    code = sorted((ROOT / 'checkers').glob('*.py')) + [Path(__file__)]
    return dict(kind='independent_check', checker_version=checkers.VERSION, origin=origin,
                checked=len(results), passed=sum(r['status'] == 'pass' for r in results),
                failed=[dict(id=r['id'], problem=r['problem']) for r in results if r['status'] != 'pass'],
                by_family={k: dict(v) for k, v in by_family.items()},
                checker_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in code},
                model_calls=0,
                scope='Checks input→output, all four options, key agreement, answer-key leakage and source hashes. '
                      'It does not judge scientific meaning or source interpretation; those remain sampled human/model review.',
                results=results)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--run', type=Path)
    group.add_argument('--workbench', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.resolve().is_relative_to((ROOT / 'runs').resolve()) and a.out.exists():
        raise SystemExit('Refusing to overwrite a file under runs/')
    report = verify(*load(a.run, a.workbench))
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(checked=report['checked'], passed=report['passed'], failed=report['failed']), ensure_ascii=False))
    sys.exit(0 if report['passed'] == report['checked'] else 1)
