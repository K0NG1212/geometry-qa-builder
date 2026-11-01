"""Run one evaluation and write the record.

    python tools/run_eval.py --provider seeded --form choice --setting coords

With no --out the record goes to runs/eval/, which is outside the repository.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation import exam, providers, run  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--provider', default='seeded', help='作答者；内置基线：' + '、'.join(sorted(providers.BASELINES)))
    parser.add_argument('--form', default='choice', choices=('choice', 'numeric'))
    parser.add_argument('--setting', default='coords', choices=sorted(exam.SETTINGS))
    parser.add_argument('--ids', nargs='*', help='只跑这几道（目录题号，如 BND016）')
    parser.add_argument('--out', help='记录写到哪；默认 runs/eval/<日期>-<作答者>-<form>-<setting>.json')
    parser.add_argument('--replies', action='store_true', help='连模型原话一起存')
    args = parser.parse_args(argv)

    try:
        record = run.run(provider=args.provider, form=args.form, setting=args.setting,
                         ids=set(args.ids) if args.ids else None, keep_replies=args.replies)
    except ValueError as problem:
        print(problem)
        return 2
    out = args.out or 'runs/eval/%s-%s-%s-%s.json' % (record['date'], record['answerer'], args.form, args.setting)
    path = run.save(record, out)

    summary = record['summary']
    print('%s · %s · %s' % (record['answerer'], record['form'], record['setting_label']))
    print('%d 道，答对 %d，读不出 %d，得分 %s'
          % (summary['n'], summary['correct'], summary['unparsed'], summary['score']))
    if not record['answerer_is_a_model']:
        print('注意：这是基线，不是模型跑出来的（model_calls=%d）' % record['model_calls'])
    for ability, bucket in sorted(summary['groups']['ability'].items()):
        print('  %-11s %3d 道  %s' % (ability, bucket['n'], bucket['score']))
    print('记录：%s' % path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
