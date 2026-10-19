"""Live demonstration that the independent checker catches a tampered question.

Takes one admitted family instance, builds it, and then runs the independent checker five times: once on the
question as generated, and four times with one thing changed - the answer key, a threshold printed in the
question, one atom of an attached structure, and the recorded hash of the reviewer-side card. Only the first
should pass. Nothing is written; this only reads the repository.

  python tools/demo_independent_checker.py
  python tools/demo_independent_checker.py --instance FA-DES-CHE-SIEVE
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checkers  # noqa: E402
import task_families  # noqa: E402

# per instance: the threshold to move in the question text, and the replacement
THRESHOLDS = {
    'FA-RXN-MECH-TS01': ('exceed 160 degrees', 'exceed 190 degrees'),
    'FA-RXN-TARGET-ANGLE': ('at most 132 degrees', 'at most 140 degrees'),
    'FA-DES-CHE-SIEVE': ('at least 12', 'at least 4'),
    'FA-DES-VIN-MV': ('at least 5 × 10^4 M^-1', 'at least 5 × 10^3 M^-1'),
}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--instance', default='FA-RXN-MECH-TS01', help='family instance from templates/family-manifest.json')
    p.add_argument('--seed', default='demo')
    a = p.parse_args()
    manifest = {x['id']: x for x in json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))['items']}
    if a.instance not in manifest:
        raise SystemExit('Unknown instance: ' + a.instance)
    spec = dict(manifest[a.instance], target_position=2)
    family = task_families.FAMILIES[spec['family']]
    built = family['build'](spec, ROOT, a.seed)
    print('%s  (%s, %s)\n' % (a.instance, spec['family'], family['ability']))

    def run(label, packet_change=None, key_change=None):
        packet = dict(id=spec['id'], family=spec['family'], question=built['question'],
                      inputs=built['inputs'], options=built['options'])
        key = dict(id=spec['id'], family=spec['family'], correct_label=built['correct_label'],
                   numeric_answer=built.get('numeric'), input_hashes=dict(built['input_hashes']))
        packet.update(packet_change or {})
        key.update(key_change or {})
        report = checkers.check(packet, key)
        detail = report.get('problem') or report.get('recomputed') or report.get('parameters', '')
        print('  %-38s %-5s %s' % (label, report['status'], detail))

    run('1. 原题')
    wrong = 'ABCD'[('ABCD'.index(built['correct_label']) + 1) % 4]
    run('2. 答案键改成 ' + wrong, key_change=dict(correct_label=wrong))
    if a.instance in THRESHOLDS:
        old, new = THRESHOLDS[a.instance]
        run('3. 题干阈值 %r -> %r' % (old, new),
            packet_change=dict(question=built['question'].replace(old, new)))
    inputs = [dict(i) for i in built['inputs']]
    first = inputs[0]['text']
    digit = re.search(r'\d', first)                 # change the first digit of the first attachment
    if not digit:
        raise SystemExit('No digit to change in ' + inputs[0]['name'])
    at = digit.start()
    moved = str((int(first[at]) + 1) % 10)
    inputs[0] = dict(inputs[0], text=first[:at] + moved + first[at + 1:])
    run('4. 动一个附件里的数字 (%s -> %s)' % (first[at], moved), packet_change=dict(inputs=inputs))
    asset = next(rel for rel in built['input_hashes'])
    run('5. 改审核侧资产（哈希不符）',
        key_change=dict(input_hashes=dict(built['input_hashes'], **{asset: '0' * 64})))
    print('\n只有第 1 行应当是 pass。')


if __name__ == '__main__':
    main()
