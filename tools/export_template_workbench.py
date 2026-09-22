"""Publish explicitly public development examples; never auto-export private runs."""
import argparse
import json
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def export(run, public=False):
    if not public:
        raise ValueError('Explicit --public-development-examples required')
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    run=Path(run)
    report=read(run/'verification.json')
    # This publisher is intentionally limited to the reviewed, already public pilot.
    approved=read(ROOT/'templates/pilot-manifest.json')
    if read(run/'manifest.json') != approved:
        raise ValueError('Only the approved public pilot manifest may be published')
    code=(run/'template_engine_snapshot.py').read_bytes()
    registry_bytes=(run/'registry_snapshot.json').read_bytes()
    if hashlib.sha256(code).hexdigest()!=report['code_sha256'] or hashlib.sha256(registry_bytes).hexdigest()!=report['registry_sha256']:
        raise ValueError('Snapshot hash mismatch')
    payload={'registry':json.loads(registry_bytes),'report':report,
             'student_packets':read(run/'student-packets.json'),
             'teacher_answers':read(run/'private-answers.json'),
             'code':code.decode('utf-8'),
             'note':'Explicitly public development examples; student packet and teacher answer are separate. Do not use these as a hidden test set.'}
    path=ROOT/'docs/data/template-workbench.json'
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return path


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--public-development-examples',action='store_true')
    a=p.parse_args();print(export(a.run,a.public_development_examples))
