"""Read saved local stage inputs/outputs. Never uploads or certifies data."""
import argparse
import html
import json
from pathlib import Path

FILES = {
    'M0 目标与配置': (['goal.json'], ['config.json', 'protocol.json']),
    'M1 检索与材料整理': (['goal.json', 'sources.json'], ['bundle.json', 'asset-units.json']),
    'M2 科学证据': (['evidence.packet.json'], ['evidence.json']),
    'M3 任务规划': (['tasks.packet.json'], ['tasks.json']),
    'M4 构题与答案': (['construction.packet.json'], ['construction-receipt.json', 'qa.json']),
    'M5 质量检查': (['review.packet.json'], ['review.json', 'report.json']),
    'M6 整理与导出': (['report.json'], ['model-inputs.json', 'private-answers.json', 'quality-report.json'])}


def render(run):
    run = Path(run)
    if not (run/'manifest.json').is_file():
        raise ValueError('Not an initialized run: manifest.json missing')
    sections = []
    for module, sides in FILES.items():
        body = '<h2>'+html.escape(module)+'</h2>'
        for label, names in zip(('输入 / 上游记录', '输出 / 保存记录'), sides):
            body += '<h3>'+label+'</h3>'
            for name in names:
                path = run/name
                if not path.exists():
                    body += '<p>'+html.escape(name)+' — 未生成 / 未保存在此目录</p>'
                    continue
                text = path.read_text(encoding='utf-8-sig')
                try:
                    text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
                except ValueError:
                    pass
                body += '<details><summary>'+html.escape(name)+'</summary><pre>'+html.escape(text)+'</pre></details>'
        sections.append('<section>'+body+'</section>')
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>本批输入输出</title><style>body{max-width:1000px;margin:40px auto;padding:0 20px;font:15px/1.8 system-ui;background:#f7f8f2;color:#243c32}section{background:white;padding:24px;margin:20px 0;border:1px solid #dce3d8}pre{overflow:auto;max-height:480px;background:#edf2e9;padding:16px}summary{cursor:pointer;padding:8px}h2{font-size:22px}</style><h1>本批输入 / 输出记录</h1><p>本地私有查看器 · 文件存在不代表通过审核。包含内部证据和答案，请勿公开上传。</p><p>'+html.escape(str(run.resolve()))+'</p>'+''.join(sections)+'</html>'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--html', action='store_true')
    args = parser.parse_args()
    run = Path(args.run)
    page = render(run)
    if args.html:
        path = run/'run-view.html'
        path.write_text(page, encoding='utf-8')
        print(path.resolve())
    else:
        for module, sides in FILES.items():
            print(module)
            for label, names in zip(('input', 'output'), sides):
                for name in names:
                    print(' ',label,name,'saved' if (run/name).exists() else 'not saved')
