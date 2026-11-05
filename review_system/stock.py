"""The paper itself, in the question's own folder, with the place in it written down.

  python -m review_system.stock            # put the source file and a reading copy in every question folder
  python -m review_system.stock --check    # say what is missing without writing anything

`review_system.sources` fetches each paper into one store (<data>/paper-sources) and writes a plain-text
check sheet per question. The advisor's point (2026-11-05) is that the paper has to be *in the question's
folder*, and the folder has to say where in it to look: opening a question should give you the question,
the evidence, the document the evidence came from, and a page or heading to turn to.

So each question folder gets, under source/:

  <paper file>        the document as downloaded -- the arXiv PDF, or the Europe PMC full-text XML. Hard
                      linked from the store when the data drive allows it, so 27 folders cost one copy.
  论文核对.html        a reading copy: the citation, every fact of the card with the page or heading it was
                      found under, and the paper's own text with those passages highlighted. XML is not
                      readable by a person and a 6 MB PDF is not searchable by eye; this is.
  SOURCE_CHECK.txt    the plain-text sheet sources.py already writes.

Nothing here is committed or published. Four of these papers are PMC author manuscripts and one is
CC BY-NC-ND: free to read at the source, not ours to redistribute. The reading copy carries the paper's
own words, so it stays on the data drive with everything else, and the repository keeps only citations,
links, hashes and verdicts.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from review_system import sources                                            # noqa: E402

READING = '论文核对.html'

PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>%(title)s</title>
<style>
 body{max-width:52rem;margin:0 auto;padding:1.5rem;font:16px/1.65 "Segoe UI",system-ui,sans-serif;color:#1a1a1a}
 h1{font-size:1.4rem;margin:0 0 .3rem} h2{font-size:1rem;margin:2rem 0 .4rem;color:#444}
 .meta{color:#555;font-size:.88rem;border-left:3px solid #ccc;padding:.5rem .8rem;background:#fafafa}
 .meta code{word-break:break-all}
 table{border-collapse:collapse;width:100%%;margin:1rem 0;font-size:.9rem}
 th,td{border:1px solid #ddd;padding:.45rem .6rem;vertical-align:top;text-align:left}
 th{background:#f3f3f3;font-weight:600}
 mark{background:#ffe9a8;padding:.05rem 0}
 .body p{margin:.5rem 0;white-space:pre-wrap}
 .where{white-space:nowrap;color:#005a9e}
 .no{color:#9a3a00}
 footer{margin-top:3rem;border-top:1px solid #ddd;padding-top:.8rem;color:#666;font-size:.85rem}
</style></head><body>
<h1>%(title)s</h1>
<div class="meta">%(meta)s</div>
%(facts)s
<h2>论文原文（本地副本渲染，供查证用）</h2>
<div class="body">%(body)s</div>
<footer>%(footer)s</footer>
</body></html>
"""


def esc(text):
    return html.escape(text, quote=False)


def mark_passages(text, passages):
    """The paper's own text with this card's passages highlighted, escaped once and only once."""
    spans = []
    for passage in passages:
        at = text.find(passage)
        if at >= 0:
            spans.append((at, at + len(passage)))
    spans.sort()
    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    out, at = [], 0
    for start, end in merged:
        out += [esc(text[at:start]), '<mark>', esc(text[start:end]), '</mark>']
        at = end
    out.append(esc(text[at:]))
    return ''.join(out)


def jump(label, local):
    """A link that lands the reader on the place: a PDF page, or the heading in this page's own text.

    Browsers open `file.pdf#page=5` on that page, so the location a fact was found at is one click from
    the fact, not a number to go hunting with."""
    page = re.match(r'PDF 第 (\d+) 页', label)
    if page and local and local.lower().endswith('.pdf'):
        return '%s#page=%s' % (local, page.group(1))
    return '#' + re.sub(r'[^\w]+', '-', label)


def reading_copy(card_name, card, row, segs, report, question):
    """One self-contained page: what the card claims, where each claim is, and the text around it."""
    title = '%s · 证据核对（题 %s）' % (card_name, question)
    local = Path(row['file']).name if row.get('held') else None
    meta = ['<b>论文</b>：%s' % esc(card['citation'] or '（卡片未记引文）'),
            '<b>链接</b>：<a href="%s">%s</a>' % (row.get('link', ''), esc(row.get('link', '')))]
    if row.get('held'):
        meta += ['<b>本文件夹里的原件</b>：<code>%s</code>（就在这个 html 旁边，双击可开）' % esc(local),
                 '<b>校验</b>：sha256 <code>%s</code> · %d 字节 · 取自 <code>%s</code>'
                 % (row['sha256'], row['bytes'], esc(row['url'])),
                 '<b>许可</b>：%s' % esc(card['license'] or '（未标）')]
    else:
        meta.append('<b>原件</b>：<span class="no">未取得 —— %s</span>' % esc(row.get('reason', '')))

    rows = ['<tr><th>事实</th><th>卡片上写的</th><th>在原文的位置</th><th>结论</th></tr>']
    checked = {f['id']: f for f in report.get('facts', [])}
    passages = []
    for fact in card['facts']:
        seen = checked.get(fact.get('id'), {})
        numbers, named = sources.tokens(fact.get('text', ''))
        if row.get('held') and (numbers or named):
            best = sources.best_located(segs, numbers, named)
            passages += [p for _, _, p in best]
            where = '；'.join('<a href="%s">%s</a>（命中 %d/%d）'
                             % (jump(label, local), esc(label), score, len(numbers) + len(named))
                             for score, label, p in best) or '<span class="no">没找到</span>'
            note = seen.get('page_note')
            if note:
                where += '<br><span class="no">注意：%s</span>' % esc(note)
            verdict = {'pass': '✓ 数字与专名都在原文里', 'check': '✗ 有对不上的'}.get(
                seen.get('verdict'), seen.get('verdict', ''))
        elif row.get('held'):
            where = '<span class="no">这条没有数字也没有专名</span>'
            verdict = '程序核不了，请自己读原文判断'
        else:
            where, verdict = '<span class="no">没有原件</span>', '无法核验'
        rows.append('<tr><td>%s</td><td>%s</td><td class="where">%s</td><td>%s</td></tr>'
                    % (esc(fact.get('id') or ''), esc(fact.get('text', '')), where, esc(verdict)))
    facts = ('<h2>这张卡说了什么，分别在原文哪里</h2><table>%s</table>' % ''.join(rows)
             + '<p>下面是论文原文，<mark>黄色</mark>就是上表那几段。'
               'PDF 的小标题是页码，全文 XML 的小标题是小节或表号。</p>')

    body = []
    for label, text in segs:
        here = [p for p in passages if p in text]
        body.append('<h2 id="%s">%s</h2><p>%s</p>'
                    % (re.sub(r'[^\w]+', '-', label), esc(label), mark_passages(text, here)))
    footer = ('本页由 <code>review_system/stock.py</code> 从上面那份本地副本生成，<b>只在本机</b>。'
              '正文版权属原作者，按其许可不得再分发：不要提交进 Git，不要上网站，不要外发。')
    return PAGE % dict(title=esc(title), meta='<br>'.join(meta), facts=facts,
                       body=''.join(body) or '<p>没有原件可渲染。</p>', footer=footer)


def place(src, dest):
    """A hard link where the drive allows one, a copy otherwise. 27 folders then cost one copy."""
    if dest.exists() and dest.stat().st_size == src.stat().st_size:
        return 'already'
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    try:
        os.link(src, dest)
        return 'linked'
    except OSError:                                   # different volume, or a filesystem without links
        shutil.copy2(src, dest)
        return 'copied'


def stock(check=False):
    cards = sources.read_cards()
    held = json.loads(sources.MANIFEST.read_text(encoding='utf-8'))['papers'] \
        if sources.MANIFEST.exists() else {}
    probe_path = sources.MANIFEST.with_name('source-probe.json')
    report = json.loads(probe_path.read_text(encoding='utf-8')) if probe_path.exists() else {}
    if not sources.QA.exists():
        print('找不到题目文件夹 %s' % sources.QA)
        return 1

    segs_by_paper, counts, missing = {}, {'already': 0, 'linked': 0, 'copied': 0}, []
    folders = 0
    for folder in sorted(sources.QA.iterdir()):
        info = folder / 'info.json'
        if not info.exists():
            continue
        meta = json.loads(info.read_text(encoding='utf-8'))
        name = (meta.get('originality') or {}).get('card')
        if not name or name not in cards:
            continue
        card = cards[name]
        row = held.get(card['paper'] or '', {})
        folders += 1
        if not row.get('held'):
            missing.append('%s（%s）：%s' % (folder.name, name, row.get('reason', '源文件未取得')))
            continue
        src = Path(row['file'])
        if not src.exists():
            missing.append('%s（%s）：清单里有，本机没有 %s' % (folder.name, name, src))
            continue
        if card['paper'] not in segs_by_paper:
            segs_by_paper[card['paper']] = sources.segments(src)
        if check:
            continue
        counts[place(src, folder / 'source' / src.name)] += 1
        page = reading_copy(name, card, row, segs_by_paper[card['paper']],
                            report.get(name, {}), folder.name)
        (folder / 'source' / READING).write_text(page, encoding='utf-8', newline='')

    if check:
        print('%d 个题目文件夹用证据卡；其中 %d 个没有可放进去的原件' % (folders, len(missing)))
    else:
        print('%d 个题目文件夹：原件已就位（新建硬链接 %d、复制 %d、本来就有 %d），每个还写了一份 %s'
              % (folders - len(missing), counts['linked'], counts['copied'], counts['already'], READING))
    for line in missing:
        print('  没有原件：%s' % line)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='只报告缺什么，不写文件')
    return stock(check=parser.parse_args(argv).check)


if __name__ == '__main__':
    raise SystemExit(main())
