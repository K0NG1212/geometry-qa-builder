"""Publish a family pilot run as public development examples after a full replay.

Only runs built from templates/family-manifest.json (all inputs already public under
docs/assets) with the current code may be published. Private runs are never exported
automatically.

python tools/export_family_workbench.py --run runs/family-pilot-v01 --public-development-examples
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import family_engine
import verify_all
from task_families import kit


def export(run, public=False):
    if not public:
        raise ValueError('Explicit --public-development-examples required')
    run = Path(run)
    read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
    report = read(run / 'verification.json')
    if read(run / 'snapshot/manifest.json') != read(ROOT / 'templates/family-manifest.json'):
        raise ValueError('Only the approved public family manifest may be published')
    current = {k: kit.sha256(p.read_bytes()) for k, p in family_engine.code_files().items()}
    for rel, digest in report['code_sha256'].items():
        if kit.sha256((run / 'snapshot' / rel).read_bytes()) != digest:
            raise ValueError('Snapshot hash mismatch: ' + rel)
    if current != report['code_sha256']:
        raise ValueError('Export with the matching code version')
    with tempfile.TemporaryDirectory() as tmp:
        replay = Path(tmp) / 'replay'
        family_engine.run(ROOT / 'templates/family-manifest.json', replay, report['seed'])
        for name in ['student-packets.json', 'numeric-student-packets.json', 'private-answers.json', 'stage-records.json']:
            if read(replay / name) != read(run / name):
                raise ValueError('Replay mismatch: ' + name)
    # Independent checkers (no generation code) must agree on every instance before publication.
    independent = verify_all.verify(read(run / 'student-packets.json'), read(run / 'private-answers.json'),
                                    dict(source=run.name))
    if independent['failed']:
        raise ValueError('Independent check failed: %s' % independent['failed'])
    code = {rel: (run / 'snapshot' / rel).read_text(encoding='utf-8') for rel in report['code_sha256']
            if rel.startswith('task_families/') or rel == 'family_engine.py'}
    payload = dict(report=report, registry=read(run / 'snapshot/registry.json'),
                   student_packets=read(run / 'student-packets.json'),
                   # Same inputs as the choice packet; the page re-attaches them for download.
                   numeric_student_packets=[dict({k: v for k, v in n.items() if k != 'inputs'}, inputs_same_as=n['id'][2:])
                                            for n in read(run / 'numeric-student-packets.json')],
                   teacher_answers=read(run / 'private-answers.json'),
                   stage_records=read(run / 'stage-records.json'), code=code,
                   run=run.name,
                   note='Public development examples; student packets and reviewer packets are separate. '
                        'All pending human audit; no catalog admissions; not a hidden test set.')
    path = ROOT / 'docs/data/family-workbench.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    independent['checker_code'] = {rel: (ROOT / rel).read_text(encoding='utf-8') for rel in independent['checker_sha256']}
    (ROOT / 'docs/data/independent-check.json').write_text(json.dumps(independent, ensure_ascii=False, indent=1) + '\n',
                                                            encoding='utf-8', newline='\n')
    return path


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--public-development-examples', action='store_true')
    a = p.parse_args()
    print(export(a.run, a.public_development_examples))
