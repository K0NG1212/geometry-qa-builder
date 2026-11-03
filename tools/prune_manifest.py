"""Drop from the manifest the instances a run could not build, so the manifest says what the bank can produce.

An enumerated proposal is only a guess: the family decides at generation time whether four candidates with one clear
answer exist, and most proposals of the stricter families do not survive. Leaving the failures in
templates/family-manifest.json would make every later run report them again, so this removes them and records what
was dropped and why.

A built instance is dropped too when its measured reasoning scale falls outside the declared window
(builder_modules/m0_scope/prototype-policy.json, 0.1-1000 nm): the 16-cell coverage count only bins questions inside
it, so admitting one outside would make tools/export_admission_audit.py disagree with the coverage table. An X-ray
C-H distance of 0.95 A is a real number, it is just below this project's smallest scale.

  --keep-also lists instances whose failure has already been fixed in this working tree (so the run's report is
  out of date for them) and which must therefore stay in the manifest.

  python tools/prune_manifest.py --run runs/family-pilot-v43 --dry-run
  python tools/prune_manifest.py --run runs/family-pilot-v43 --write

FA-CONF-7063-max_dipole is kept on purpose: tests/test_task_families.py pins it as the one known failure, so that
the failure list cannot grow unnoticed.
"""
import argparse
import json
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'templates/family-manifest.json'
RECORD = ROOT / 'templates/pruned-instances.json'
POLICY = ROOT / 'builder_modules/m0_scope/prototype-policy.json'
KEEP = {'FA-CONF-7063-max_dipole'}
_BINS = json.loads(POLICY.read_text(encoding='utf-8'))['scale_bins_nm']
WINDOW = (_BINS[0][0], _BINS[-1][1])


def out_of_window(run):
    """(instance, reasoning scale) for every built instance whose reasoning scale leaves the declared window."""
    answers = json.loads((run / 'private-answers.json').read_text(encoding='utf-8'))
    return [(a['id'], a['scales']['reasoning_nm']) for a in answers
            if not WINDOW[0] <= a['scales']['reasoning_nm'] <= WINDOW[1]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--keep-also', default='', help='逗号分隔的实例号：这次不要剪掉（失败原因已在工作区修好）')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not args.write and not args.dry_run:
        parser.error('要么 --dry-run，要么 --write')

    keep = KEEP | {x.strip() for x in args.keep_also.split(',') if x.strip()}
    report = json.loads((ROOT / args.run / 'verification.json').read_text(encoding='utf-8'))
    failures = {f['id']: f.get('reason', '') for f in report['failures'] if f['id'] not in keep}
    for instance, scale in out_of_window(ROOT / args.run):
        if instance not in keep:
            failures[instance] = '推理尺度 %.4f nm 落在申报窗口 %s 之外' % (scale, WINDOW)
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'), object_pairs_hook=OrderedDict)
    before = len(manifest['items'])
    reasons = Counter(failures.values())

    print('这次运行 attempted %d / passed %d / failures %d' %
          (report['attempted'], report['passed'], len(report['failures'])))
    print('要从清单里拿掉 %d 条（保留 %s）' % (len(failures), ', '.join(sorted(keep))))
    for reason, count in reasons.most_common(12):
        print('  %-66s %d' % (reason[:66], count))

    if args.write and failures:
        kept = [item for item in manifest['items'] if item['id'] not in failures]
        manifest['items'] = kept
        MANIFEST.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
        existing = json.loads(RECORD.read_text(encoding='utf-8'),
                              object_pairs_hook=OrderedDict) if RECORD.exists() else OrderedDict(
            kind='pruned_instances', note='枚举提案里族自己判定做不成题的那些，连同原因。留着是为了别再提一遍同样的候选。',
            batches=OrderedDict())
        existing['batches'][args.run.replace('\\', '/').split('/')[-1]] = OrderedDict(
            attempted=report['attempted'], passed=report['passed'], pruned=len(failures),
            reasons=OrderedDict(reasons.most_common()), ids=OrderedDict(sorted(failures.items())))
        RECORD.write_bytes((json.dumps(existing, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
        print('清单 %d → %d 条；原因记在 %s' % (before, len(kept), RECORD.relative_to(ROOT).as_posix()))


if __name__ == '__main__':
    main()
