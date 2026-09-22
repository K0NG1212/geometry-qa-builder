"""Publish only the existing public pilot, with hashes and replay checked."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import choice_engine as c


def export(run, public=False):
    if not public:
        raise ValueError('Explicit public development flag required')
    run = Path(run)
    read = lambda n: json.loads((run/n).read_text(encoding='utf-8'))
    report = read('verification.json')
    manifest = read('numeric-manifest.json')
    if manifest != json.loads((ROOT/'templates/pilot-manifest.json').read_text(encoding='utf-8')):
        raise ValueError('Not approved public material')
    for name, key in [('choice_engine_snapshot.py','code_sha256'), ('template_engine.py','numeric_code_sha256'), ('numeric-verification.json','source_report_sha256'), ('numeric-manifest.json','source_manifest_sha256')]:
        if hashlib.sha256((run/name).read_bytes()).hexdigest() != report[key]:
            raise ValueError('Snapshot mismatch')
    if report['code_sha256'] != hashlib.sha256(Path(c.__file__).read_bytes()).hexdigest():
        raise ValueError('Export with the matching engine version')
    students, teachers = read('student-packets.json'), read('private-answers.json')
    originals = {s['id']: s for s in read('numeric-student-packets.json')}
    if len(students) != report['passed'] or len(teachers) != len(students):
        raise ValueError('Count mismatch')
    for s, t in zip(students, teachers):
        if s['id'] != t['id'] or s['input'] != originals[t['numeric_id']]['input']:
            raise ValueError('Packet mismatch')
        options, audit = c.construct(s['input']['text'], t['template'], report['seed'], t['numeric_id'])
        if s['options'] != options or any(t[k] != v for k, v in audit.items()):
            raise ValueError('Choice replay mismatch')
    payload = dict(report=report, student_packets=students, teacher_answers=teachers,
                   code=(run/'choice_engine_snapshot.py').read_text(encoding='utf-8'),
                   note='Public development examples only; all pending human audit, no new catalog entries.')
    (ROOT/'docs/data/choice-workbench.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
    p.add_argument('--public-development-examples',action='store_true')
    a=p.parse_args();export(a.run,a.public_development_examples)
