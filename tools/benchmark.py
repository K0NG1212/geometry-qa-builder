"""Run several answerers over the bank and print the model x discipline table.

    python tools/benchmark.py --estimate                        # what a pass would cost, no calls
    python tools/benchmark.py seeded always-a                   # the baselines, free
    python tools/benchmark.py deepseek-chat --sample 30         # ~US$0.10: check the wiring first
    python tools/benchmark.py deepseek-chat gemini-2.5-flash seeded --workers 8

Nothing is asked twice: every answer is cached under runs/eval/cache/ by answerer and exam fingerprint, so
an interrupted run resumes and a repeated command calls nothing. API keys come from the environment
(see evaluation/models.json for which variable each model reads); this repository ships none.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation import benchmark, budget, exam, providers  # noqa: E402


def show_estimate(args):
    questions = exam.load(form=args.form, ids=set(args.ids) if args.ids else None)
    table = providers.catalogue()
    names = [n for n in (args.answerers or sorted(table)) if n in table]
    if not names:
        print('models.json 里没有可估价的模型。基线不花钱，不用估。')
        return 0
    report = budget.report(questions, [table[n] for n in names], setting=args.setting)
    print('%d 道 · %s · 提示词合计 %.2f M token（%s）'
          % (report['questions'], report['setting'], report['total_input_tokens'] / 1e6,
             'tiktoken 精确计数' if report['token_counts_are_exact'] else report['tokenizer'] + '，粗估'))
    print('中位 %d token；≥8k 的 %d 道占掉 %.0f%% 的 token'
          % (report['median_tokens'], report['heavy_questions']['over_8k'],
             100 * (report['heavy_questions']['share_of_tokens'] or 0)))
    print('按学科：' + '，'.join('%s %.2fM' % (k, v['tokens'] / 1e6)
                              for k, v in report['by_domain'].items()))
    print()
    for row in report['models']:
        cost = '未标价' if row['usd_upper_bound'] is None else '≤ US$%.2f' % row['usd_upper_bound']
        print('%s（%s）' % (row['label'], row['model']))
        print('  窗口 %s token，留给提示词 %s → 问得了 %d 道，问不了 %d 道'
              % (row['context_tokens'], row['room_for_prompt'], row['shown'], row['oversize']))
        print('  输入 %.2f M token + 假设每题回 %d token  →  %s  （价格记于 %s，%s）'
              % (row['input_tokens'] / 1e6, row['assumed_output_tokens'] // max(1, row['shown']),
                 cost, row['priced_on'], row['price_source']))
        if row['oversize']:
            print('  问不了的集中在：' + '，'.join('%s %d 道' % (k, v['n'])
                                            for k, v in row['oversize_by_domain'].items()))
    print('\n价格与窗口都来自 evaluation/models.json，本仓库不联网核对；花钱之前请对着厂商当前页面核一遍。')
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
        print('明细：%s' % args.out)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('answerers', nargs='*',
                        help='基线：' + '、'.join(sorted(providers.BASELINES)) + '；模型见 evaluation/models.json')
    parser.add_argument('--form', default='choice', choices=('choice', 'numeric'))
    parser.add_argument('--setting', default='coords', choices=sorted(exam.SETTINGS))
    parser.add_argument('--ids', nargs='*', help='只跑这几道（目录题号，如 BND016）')
    parser.add_argument('--sample', type=int, help='只跑这么多道：四个学科均摊、按题号等距取，每次结果相同；'
                                                  '第一次花钱先用 --sample 30 验接线（约 35 万 token）')
    parser.add_argument('--workers', type=int, default=1, help='并发问几道；真模型建议 4–8')
    parser.add_argument('--group', default='domain', choices=('domain', 'ability', 'family', 'cell'),
                        help='表格按什么分列，默认按学科')
    parser.add_argument('--estimate', action='store_true', help='只估算 token 与花费，一个请求都不发')
    parser.add_argument('--out', help='记录写到哪；默认 runs/eval/<日期>-benchmark-<form>-<setting>.json')
    args = parser.parse_args(argv)

    if args.estimate:
        return show_estimate(args)
    if not args.answerers:
        parser.error('至少给一个作答者，或者加 --estimate 只看估价')

    try:
        record = benchmark.run(args.answerers, form=args.form, setting=args.setting,
                               ids=set(args.ids) if args.ids else None, workers=args.workers,
                               size=args.sample)
    except ValueError as problem:
        print(problem)
        return 2

    tag = '-sample%d' % record['questions'] if record['is_a_sample'] else ''
    out = args.out or 'runs/eval/%s-benchmark-%s-%s%s.json' % (record['date'], args.form, args.setting, tag)
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding='utf-8')

    print(benchmark.markdown(record, group=args.group))
    if record['is_a_sample']:
        print()
        print('注意：这是 %d / %d 道的样本，不是全库成绩。' % (record['questions'], record['whole_exam']))
    print()
    for row in record['runs']:
        money = '' if not row['usd_from_reported_usage'] else '，按回包用量 US$%.4f' % row['usd_from_reported_usage']
        named = '' if not row['answerer_is_a_model'] else (
            '，回包自报 %s' % row['answerer'] if row['named_itself'] else '，回包没报模型名（只能按请求的 %s 记）'
            % row['requested'])
        print('%-26s 调用 %-5d 缓存命中 %-4d 未问 %d+%d%s%s'
              % (row['asked_for'], row['model_calls'], row['answers_from_cache'],
                 row['summary']['oversize'], row['summary']['error'], named, money))
    print('记录：%s' % path)
    md = path.with_suffix('.md')
    md.write_text(benchmark.markdown(record, group=args.group) + '\n', encoding='utf-8')
    print('表格：%s' % md)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
