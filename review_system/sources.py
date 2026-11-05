"""The source document behind every paper-sourced question, fetched and kept where a reviewer can open it.

  python -m review_system.sources --fetch     # download what is missing, record url/date/sha256/licence
  python -m review_system.sources             # report what is held and what each fact can be checked against
  python -m review_system.sources --probe     # for every fact, find the sentences in the source that carry
                                              # its distinctive numbers and terms

An evidence card states facts "from the paper" with a locator like "Main text (translocation channel);
Fig. 3a". A reader cannot act on that: there is no document in the question folder and no sentence to look
for, so the only thing backing the fact is our say-so. The advisor asked for the opposite (2026-10-28):
"把那个所有你抽的题，那些 PDF 什么都保存下来", "你原始文档的那种 link 肯定要给的，然后本地也要都下下来".

So this fetches the source document itself, and then -- the part that matters -- lets a fact be checked
against it mechanically: every number and named term in a fact is looked for in the source's own text, and
a fact whose numbers appear nowhere in the paper it cites is reported. That is a check a reader can trust
without trusting us, which prose locators are not.

Where the files go, and what is never published:

  Documents land in <data>/paper-sources/ -- outside the repository, like runs/ and inputs/. Nothing here
  is committed and nothing reaches the website. Four of these papers are PMC author manuscripts and one is
  CC BY-NC-ND; they are free to read at the source but not ours to redistribute, so the repository keeps
  only the citation, the link and this manifest. Publishing the documents is not a thing this file can do.

  Paywalled sources are not fetched at all. The user's standing permission (2026-11-04) covers RCSB, COD
  and Europe PMC open-access full text; arXiv and the open publisher copies here were authorised
  separately on 2026-11-05, local-only. A paper behind a paywall is recorded as not held, with its link,
  and its facts are reported as unverifiable rather than quietly passed.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / 'docs' / 'assets' / 'families' / 'evidence'
MANIFEST = ROOT / 'reviews' / 'source-manifest.json'
# runs/ is a junction onto the data drive; its parent is where bulk data lives, and none of it is in git
STORE = (ROOT / 'runs').resolve().parent / 'paper-sources'

EPMC = 'https://www.ebi.ac.uk/europepmc/webservices/rest'
AGENT = 'GeoBench-source-fetch/0.1 (academic benchmark construction)'
TIMEOUT = 60

# A paper we may not take a copy of. Its facts stay unverifiable and say so.
PAYWALLED = {'doi:10.1038/ncomms6757': 'Nature Communications 2014, 版权所有，Europe PMC 无开放全文'}


def read_cards():
    """Every evidence card, with the paper it cites resolved to an identifier we can fetch by."""
    out = {}
    for path in sorted(CARDS.glob('*.json')):
        card = json.loads(path.read_text(encoding='utf-8'))
        if card.get('kind') != 'evidence_card' and not card.get('facts'):
            continue                                   # sources.json is a registry, not a card
        cite = card.get('citation') or ''
        arxiv = re.search(r'arXiv[:\s]*(\d{4}\.\d{4,5})', cite)
        pmc = re.search(r'(PMC\d+)', cite)
        doi = re.search(r'doi:\s*([^\s,;)）]+)', cite, re.I)
        if arxiv:
            ident = 'arXiv:' + arxiv.group(1)
        elif pmc:
            ident = pmc.group(1)
        elif doi:
            ident = 'doi:' + doi.group(1).rstrip('.')
        else:
            ident = None
        out[path.stem] = dict(paper=ident, citation=cite, license=card.get('license') or '',
                              facts=card.get('facts') or [])
    return out


def papers(cards):
    """One entry per distinct paper, with the cards that cite it."""
    out = {}
    for name, card in cards.items():
        if not card['paper']:
            continue
        row = out.setdefault(card['paper'], dict(cards=[], license=card['license'], facts=0))
        row['cards'].append(name)
        row['facts'] += len(card['facts'])
    return out


def get(url, accept=None):
    request = urllib.request.Request(url, headers={'User-Agent': AGENT,
                                                   **({'Accept': accept} if accept else {})})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read(), response.headers.get('Content-Type', '')


def pmcid_for_doi(doi):
    url = EPMC + '/search?query=' + urllib.parse.quote('DOI:' + doi) + '&resultType=core&format=json&pageSize=1'
    body, _ = get(url)
    hits = json.loads(body.decode('utf-8')).get('resultList', {}).get('result', [])
    if not hits:
        return None, None
    hit = hits[0]
    return hit.get('pmcid'), (hit.get('license') or '').strip()


def plan(ident):
    """Where this paper can be fetched from, and under what name it is stored."""
    if ident in PAYWALLED:
        return None
    if ident.startswith('arXiv:'):
        number = ident.split(':', 1)[1]
        return dict(url='https://arxiv.org/pdf/%s' % number, name='arxiv-%s.pdf' % number, kind='pdf')
    if ident.startswith('PMC'):
        return dict(url='%s/%s/fullTextXML' % (EPMC, ident), name='%s.xml' % ident, kind='xml')
    if ident.startswith('doi:'):
        pmcid, _ = pmcid_for_doi(ident.split(':', 1)[1])
        if pmcid:
            return dict(url='%s/%s/fullTextXML' % (EPMC, pmcid), name='%s.xml' % pmcid, kind='xml',
                        via='Europe PMC 开放全文（由 DOI 解析）')
    return None


def fetch(ident, force=False):
    """Download one paper. Returns its manifest row, or a row saying why it is not held."""
    where = plan(ident)
    if where is None:
        return dict(held=False, reason=PAYWALLED.get(ident, '没有可用的开放获取副本'),
                    link=link_for(ident))
    folder = STORE / ident.replace(':', '-').replace('/', '_')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / where['name']
    if path.exists() and not force:
        body = path.read_bytes()
    else:
        body, _ = get(where['url'], accept='application/xml' if where['kind'] == 'xml' else None)
        path.write_bytes(body)
    return dict(held=True, file=str(path), url=where['url'], kind=where['kind'],
                bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                link=link_for(ident), **({'via': where['via']} if where.get('via') else {}))


def link_for(ident):
    if ident.startswith('arXiv:'):
        return 'https://arxiv.org/abs/' + ident.split(':', 1)[1]
    if ident.startswith('PMC'):
        return 'https://europepmc.org/article/PMC/' + ident
    if ident.startswith('doi:'):
        return 'https://doi.org/' + ident.split(':', 1)[1]
    return ''


# Markup that sits inside a word. NH<sub>2</sub> is the word NH2, so these close up rather than
# becoming a space -- the first probe reported NH2 missing from a paper that says it on every page.
INLINE = ('sub', 'sup', 'italic', 'bold', 'sc', 'underline', 'overline', 'monospace', 'roman', 'xref')


def text_of(path):
    """The source's own words, as plain text: JATS body for XML, pdftotext for PDF.

    Tables are kept. Locators point at them ("Table 1"), and an extractor that drops them reports the
    numbers in them as absent from the paper, which is the opposite of what this file is for."""
    path = Path(path)
    if path.suffix == '.xml':
        raw = path.read_text(encoding='utf-8', errors='replace')
        raw = re.sub(r'</?(?:%s)(?:\s[^>]*)?>' % '|'.join(INLINE), '', raw)
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', raw))
    out = subprocess.run(['pdftotext', '-q', '-enc', 'UTF-8', str(path), '-'],
                         capture_output=True)
    if out.returncode == 0 and out.stdout.strip():
        return re.sub(r'\s+', ' ', out.stdout.decode('utf-8', 'replace'))
    from pypdf import PdfReader                                    # fallback, slower and rougher
    return re.sub(r'\s+', ' ', ' '.join(p.extract_text() or '' for p in PdfReader(str(path)).pages))


# What in a fact can be looked for in the source: numbers with their units, and named entities such as
# Phe427 or KcsA. Ordinary words are useless here -- every paper contains "the channel".
NUMBER = re.compile(r'\b\d+(?:\.\d+)?\b')
NAMED = re.compile(r'\b(?:[A-Z][a-z]{1,2}\d{1,4}|[A-Z]{2,}[A-Za-z]*\d*)\b')


def tokens(fact_text):
    numbers = {m.group(0) for m in NUMBER.finditer(fact_text)}
    named = {m.group(0) for m in NAMED.finditer(fact_text)} - {'A', 'I'}
    return sorted(numbers), sorted(named)


def found(token, text):
    """Whether the source says this, allowing for how papers write things.

    A number may be written 6 or 6.0. A residue is Thr112 to us and "Thr 112" in the body and
    "Threonine 112" in the caption of the same paper, so the letters and the number are allowed to be
    apart. Nothing looser than that: the point is to catch a fact the paper does not support, and a
    matcher that shrugs at anything catches nothing."""
    if re.fullmatch(r'\d+', token):
        return re.search(r'(?<![\d.])' + token + r'(?:\.0+)?(?![\d])', text) is not None
    split = re.fullmatch(r'([A-Za-z]+)(\d+)', token)
    if split:
        letters, number = split.groups()
        return re.search(r'\b%s[a-z]*[\s -]*%s\b' % (re.escape(letters), number),
                         text, re.I) is not None
    return token.lower() in text.lower()


def sentences(text, token, width=2):
    """The passages of the source that carry this token, so a reviewer can read them in place."""
    hits = []
    for m in re.finditer(r'(?<![\d.])' + re.escape(token) + r'(?![\d])', text, re.I):
        start = max(0, m.start() - 220)
        hits.append(text[start:m.end() + 220].strip())
        if len(hits) >= width:
            break
    return hits


def best_passages(text, numbers, named, keep=2):
    """The passages that carry the most of this fact at once.

    Looking up one token at a time lands on the wrong place: the first "14" in a paper is an affiliation
    or a reference range, not the 14-stranded barrel. A passage that holds several of the fact's numbers
    and terms together is the sentence the fact was written from."""
    wanted = named + numbers
    if not wanted:
        return []
    windows = {}
    for token in wanted:
        for m in re.finditer(r'(?<![\d.])' + re.escape(token) + r'(?![\d])', text, re.I):
            start = max(0, m.start() - 240)
            key = start // 160                                  # fold near-identical windows together
            windows.setdefault(key, text[start:m.start() + 260].strip())
    scored = []
    for passage in dict.fromkeys(windows.values()):
        score = sum(1 for t in wanted if found(t, passage))
        scored.append((score, -len(passage), passage))
    scored.sort(reverse=True)
    out = []
    for score, _, passage in scored:
        if out and score < 2:
            break
        core = passage[len(passage) // 3:len(passage) // 3 + 110]
        # two windows onto the same sentence are one passage, however their edges fall
        if any(core in kept or kept[len(kept) // 3:len(kept) // 3 + 110] in passage
               for _, kept in out):
            continue
        out.append((score, passage))
        if len(out) >= keep or score == len(wanted):
            break
    return out or ([(1, scored[0][2])] if scored else [])


def probe(cards, held):
    """Per fact: which of its numbers and named terms are in the source, and which are not."""
    report = {}
    texts = {}
    for name, card in sorted(cards.items()):
        row = held.get(card['paper'] or '', {})
        entry = report.setdefault(name, dict(paper=card['paper'], facts=[]))
        if not row.get('held'):
            entry['unverifiable'] = row.get('reason', '源文件未取得')
            continue
        if card['paper'] not in texts:
            texts[card['paper']] = text_of(row['file'])
        text = texts[card['paper']]
        for fact in card['facts']:
            numbers, named = tokens(fact.get('text', ''))
            missing_n = [t for t in numbers if not found(t, text)]
            missing_t = [t for t in named if not found(t, text)]
            entry['facts'].append(dict(
                id=fact.get('id'), locator=fact.get('locator'),
                numbers=len(numbers), named=len(named),
                missing_numbers=missing_n, missing_terms=missing_t,
                verdict='pass' if not missing_n and not missing_t else 'check'))
    return report


QA = (ROOT / 'runs').resolve().parent / 'qa'
BAR = '-' * 78


def sheet_for(card_name, card, row, text, report):
    """What a reviewer needs to check one card against the paper, as one readable file."""
    out = ['证据核对 · %s' % card_name, BAR,
           '论文  ：%s' % (card['citation'] or '（卡片未记引文）'),
           '链接  ：%s' % row.get('link', ''),
           '许可  ：%s' % (card['license'] or '（未标）')]
    if row.get('held'):
        out += ['本地副本：%s' % row['file'],
                '        sha256 %s · %d 字节 · 取自 %s' % (row['sha256'][:16], row['bytes'], row['url'])]
    else:
        out += ['本地副本：**未取得** —— %s' % row.get('reason', ''),
                '        这张卡的事实无法机械核验，只能你自己点开链接看。']
    out += ['', '怎么用这份文件：每条事实下面是**原文里带着它的数字与专名的那一段**，照抄未改。',
            '拿它去原文里搜，一下就能定位。对不上就是问题，请记进 REVIEW_ISSUES.md。', '']

    facts = {f['id']: f for f in report.get('facts', [])}
    for fact in card['facts']:
        fid = fact.get('id')
        checked = facts.get(fid, {})
        out += [BAR, '%s  [%s]' % (fid, checked.get('verdict', '未核验')),
                '  卡片上写的：%s' % fact.get('text', ''),
                '  卡片记的位置：%s' % (fact.get('locator') or '（没记）')]
        if not row.get('held'):
            out += ['  原文：未取得副本，无法摘录。', '']
            continue
        numbers, named = tokens(fact.get('text', ''))
        out.append('  要找的：数字 %s；专名 %s' % (numbers or '无', named or '无'))
        passages = best_passages(text, numbers, named)
        for score, passage in passages:
            out.append('  原文（命中 %d/%d 项）：…%s…' % (score, len(numbers) + len(named), passage))
        if not passages:
            out.append('  原文：没找到含这些词的段落——**这条要人看**。')
        out.append('')
    out += [BAR, '本文件由 review_system/sources.py 生成，只在本地。',
            '其中引用的原文段落来自上面那篇论文，按其许可**不得再分发**：不要提交进 Git，不要上网站。']
    return '\n'.join(out) + '\n'


def write_sheets(cards, held, report):
    """One sheet per question folder, for every question built from an evidence card."""
    if not QA.exists():
        print('找不到题目文件夹 %s，跳过' % QA)
        return 0
    texts, written, by_card = {}, 0, {}
    for folder in sorted(QA.iterdir()):
        info = folder / 'info.json'
        if not info.is_dir() and info.exists():
            pass
        if not info.exists():
            continue
        meta = json.loads(info.read_text(encoding='utf-8'))
        name = (meta.get('originality') or {}).get('card')
        if not name or name not in cards:
            continue
        card = cards[name]
        row = held.get(card['paper'] or '', {})
        if row.get('held') and card['paper'] not in texts:
            texts[card['paper']] = text_of(row['file'])
        body = sheet_for(name, card, row, texts.get(card['paper'], ''), report.get(name, {}))
        (folder / 'source' / 'SOURCE_CHECK.txt').write_text(body, encoding='utf-8', newline='')
        written += 1
        by_card[name] = by_card.get(name, 0) + 1
    print('写了 %d 份 source/SOURCE_CHECK.txt，覆盖 %d 张证据卡' % (written, len(by_card)))
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--fetch', action='store_true', help='下载缺的源文件')
    parser.add_argument('--force', action='store_true', help='已经下过的也重下')
    parser.add_argument('--probe', action='store_true', help='逐条事实在原文里找它的数字与专名')
    parser.add_argument('--sheet', action='store_true',
                        help='给每道题的文件夹写一份 source/SOURCE_CHECK.txt（只在本地）')
    args = parser.parse_args(argv)

    cards = read_cards()
    by_paper = papers(cards)
    print('%d 张证据卡，引用 %d 篇论文，共 %d 条事实'
          % (len(cards), len(by_paper), sum(len(c['facts']) for c in cards.values())))

    held = {}
    if MANIFEST.exists():
        held = json.loads(MANIFEST.read_text(encoding='utf-8')).get('papers', {})
    if args.fetch:
        for ident in sorted(by_paper):
            try:
                row = fetch(ident, force=args.force)
            except Exception as exc:                                    # network, 404, rate limit
                row = dict(held=False, reason='%s: %s' % (type(exc).__name__, exc), link=link_for(ident))
            row.update(cards=sorted(by_paper[ident]['cards']), license=by_paper[ident]['license'])
            held[ident] = row
            print('  %-26s %s' % (ident, '%(bytes)d 字节  %(file)s' % row if row['held']
                                  else '未取得：' + row['reason']))
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(dict(kind='geobench_source_manifest', store=str(STORE),
                                            papers=held), ensure_ascii=False, indent=1) + '\n',
                            encoding='utf-8')
        print('清单写到', MANIFEST)

    if args.probe:
        report = probe(cards, held)
        bad = 0
        for name, entry in sorted(report.items()):
            if entry.get('unverifiable'):
                print('  %-26s 无法核验：%s' % (name, entry['unverifiable']))
                continue
            flags = [f for f in entry['facts'] if f['verdict'] != 'pass']
            bad += len(flags)
            print('  %-26s %d 条事实，%d 条对不上' % (name, len(entry['facts']), len(flags)))
            for f in flags:
                print('      %s 缺数字 %s 缺专名 %s' % (f['id'], f['missing_numbers'], f['missing_terms']))
        out = MANIFEST.with_name('source-probe.json')
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print('逐条结果写到', out, '；对不上的共', bad, '条')
        if args.sheet:
            write_sheets(cards, held, report)
        return 0

    if args.sheet:
        path = MANIFEST.with_name('source-probe.json')
        report = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        write_sheets(cards, held, report)
        return 0

    for ident, row in sorted(held.items()):
        print('  %-26s %s' % (ident, '已存' if row.get('held') else '未取得：' + row.get('reason', '')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
