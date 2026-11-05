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


def pdf_text(path):
    """A PDF's text with its page breaks intact: pdftotext separates pages with a form feed."""
    out = subprocess.run(['pdftotext', '-q', '-enc', 'UTF-8', str(path), '-'], capture_output=True)
    if out.returncode == 0 and out.stdout.strip():
        return out.stdout.decode('utf-8', 'replace')
    from pypdf import PdfReader                                    # fallback, slower and rougher
    return '\f'.join(p.extract_text() or '' for p in PdfReader(str(path)).pages)


def label_of(markup, width=58):
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', markup)).strip()
    return text[:width] + ('…' if len(text) > width else '')


def segments(path):
    """The source cut into labelled pieces, so a passage can be reported with where in the paper it is.

    A reader needs a place, not only a sentence: "it is in the paper somewhere" is not a locator. A PDF
    has pages and pdftotext marks them with a form feed, so the page a passage sits on is free. JATS XML
    has no pages at all; what a reader can navigate to there is the heading above the passage -- a section
    title, or a "Table 3" label -- which is also the form the cards' own locators take. These labels are
    read off the source, never off the card, so a card that claims "Table 3" can be checked against where
    its numbers actually are.

    Tables are kept, here as everywhere in this file. Locators point at them ("Table 1"), and an extractor
    that drops them reports the numbers in them as absent from the paper."""
    path = Path(path)
    if path.suffix != '.xml':
        return [('PDF 第 %d 页' % i, re.sub(r'\s+', ' ', page).strip())
                for i, page in enumerate(pdf_text(path).split('\f'), 1) if page.strip()]
    raw = path.read_text(encoding='utf-8', errors='replace')
    raw = re.sub(r'</?(?:%s)(?:\s[^>]*)?>' % '|'.join(INLINE), '', raw)
    cuts = [(0, '文章开头（题目、作者、摘要）')]
    # `<title ...>`, not `<title-group>` or `<article-title>`: matching those swallows the whole front
    # matter into one label.
    for m in re.finditer(r'<title(?:\s[^>]*)?>(.*?)</title>', raw, re.S):
        cuts.append((m.start(), '小节「%s」' % label_of(m.group(1))))
    for m in re.finditer(r'<label(?:\s[^>]*)?>(.*?)</label>', raw, re.S):
        name = label_of(m.group(1), 24)
        if re.match(r'(?:Table|Figure|Fig\.?|Scheme|Box)\b', name, re.I):
            cuts.append((m.start(), '%s 一带' % name.rstrip('.')))
    cuts.sort()
    out = []
    for (start, label), (end, _) in zip(cuts, cuts[1:] + [(len(raw), '')]):
        body = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', raw[start:end])).strip()
        if body:
            out.append((label, body))
    return out


def text_of(path):
    """The whole source as one run of text, for asking whether it says a thing anywhere at all."""
    return ' '.join(body for _, body in segments(path))


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


def prose(passage, step=0.5):
    """How sentence-like a passage is: letters per digit, in coarse steps.

    A fact with a single number ("about 0.6 nm thick") matches that number anywhere, and in a PDF the
    densest place for a bare number is a figure's axis labels, which pdftotext renders as a drift of
    digits. Among passages that carry the fact equally well, the one that reads like a sentence is the one
    the fact was written from. Coarse steps so this only breaks ties and never outranks coverage."""
    letters = sum(c.isalpha() for c in passage)
    digits = sum(c.isdigit() for c in passage)
    return round(letters / (1 + digits) / step)


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
        scored.append((score, prose(passage), -len(passage), passage))
    scored.sort(reverse=True)
    out = []
    for score, _, _, passage in scored:
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
    return out or ([(1, scored[0][3])] if scored else [])


def best_located(segs, numbers, named, keep=2):
    """The best passages across a labelled source, each with the page or heading it sits under.

    Scoring runs inside a segment and the winners are merged, so a passage is always reported with a
    place a reader can turn to."""
    cands = []
    for label, text in segs:
        for score, passage in best_passages(text, numbers, named, keep=keep):
            cands.append((score, prose(passage), -len(passage), label, passage))
    cands.sort(reverse=True)
    out = []
    for score, _, _, label, passage in cands:
        if out and score < 2:
            break
        core = passage[len(passage) // 3:len(passage) // 3 + 110]
        if any(core in kept or kept[len(kept) // 3:len(kept) // 3 + 110] in passage
               for _, _, kept in out):
            continue
        out.append((score, label, passage))
        if len(out) >= keep or score == len(numbers) + len(named):
            break
    return out


def page_gap(locator, where):
    """When the card claims a page and the search found another one, say which.

    Not an error: a card's "p. 5" may be the page of the journal version or of the main text alone, while
    the file we hold is the arXiv PDF with its figures and supplement bound in. But a reviewer should see
    the disagreement here, not discover it while pointing at a page in a meeting."""
    if not locator or not where or not where.startswith('PDF 第'):
        return None
    claimed = set()
    for m in re.finditer(r'pp?\.?\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?', locator):
        first, last = int(m.group(1)), int(m.group(2) or m.group(1))
        claimed.update(range(min(first, last), max(first, last) + 1))
    page = int(re.search(r'\d+', where).group(0))
    if claimed and page not in claimed:
        return '卡片记的是 p. %s，而这段在 PDF 第 %d 页（两套页码可能不同，要人确认）' % (
            '/'.join(str(n) for n in sorted(claimed)), page)
    return None


def probe(cards, held):
    """Per fact: which of its numbers and named terms are in the source, which are not, and where.

    `where` is the page or heading the best passage sits under -- a place, not the passage itself. The
    passages are the paper's own words and several of these papers are not ours to redistribute, so what
    is recorded here, and committed, carries no source text at all."""
    report = {}
    sources_text = {}
    for name, card in sorted(cards.items()):
        row = held.get(card['paper'] or '', {})
        entry = report.setdefault(name, dict(paper=card['paper'], facts=[]))
        if not row.get('held'):
            entry['unverifiable'] = row.get('reason', '源文件未取得')
            continue
        if card['paper'] not in sources_text:
            segs = segments(row['file'])
            sources_text[card['paper']] = (segs, ' '.join(b for _, b in segs))
        segs, text = sources_text[card['paper']]
        for fact in card['facts']:
            numbers, named = tokens(fact.get('text', ''))
            missing_n = [t for t in numbers if not found(t, text)]
            missing_t = [t for t in named if not found(t, text)]
            best = best_located(segs, numbers, named, keep=1)
            if not numbers and not named:
                # Nothing in this fact can be looked for: it states a shape or a trend in words only
                # ("both vHs peaks are present and unsplit"). Calling that a pass would be this tool
                # rubber-stamping its own blind spot, which is worse than having no tool.
                verdict = 'no_tokens'
            elif missing_n or missing_t:
                verdict = 'check'
            else:
                verdict = 'pass'
            where = best[0][1] if best else None
            note = page_gap(fact.get('locator'), where)
            entry['facts'].append(dict(
                id=fact.get('id'), locator=fact.get('locator'),
                numbers=len(numbers), named=len(named),
                missing_numbers=missing_n, missing_terms=missing_t,
                where=where, found_here=best[0][0] if best else 0,
                verdict=verdict, **({'page_note': note} if note else {})))
    return report


def tally(report):
    """How many facts were actually checked, as opposed to merely not flagged."""
    counts = dict(facts=0, passed=0, flagged=0, no_tokens=0, unverifiable_cards=0)
    for entry in report.values():
        if entry.get('unverifiable'):
            counts['unverifiable_cards'] += 1
            continue
        for fact in entry['facts']:
            counts['facts'] += 1
            counts[{'pass': 'passed', 'check': 'flagged'}.get(fact['verdict'], 'no_tokens')] += 1
    return counts


QA = (ROOT / 'runs').resolve().parent / 'qa'
BAR = '-' * 78


def sheet_for(card_name, card, row, segs, report):
    """What a reviewer needs to check one card against the paper, as one readable file."""
    out = ['证据核对 · %s' % card_name, BAR,
           '论文  ：%s' % (card['citation'] or '（卡片未记引文）'),
           '链接  ：%s' % row.get('link', ''),
           '许可  ：%s' % (card['license'] or '（未标）')]
    if row.get('held'):
        out += ['本地副本：%s' % row['file'],
                '        sha256 %s · %d 字节 · 取自 %s' % (row['sha256'][:16], row['bytes'], row['url']),
                '这个文件夹里：%s 就是论文原件，论文核对.html 是能直接读的渲染版（都由 '
                'python -m review_system.stock 放进来）' % Path(row['file']).name]
    else:
        out += ['本地副本：**未取得** —— %s' % row.get('reason', ''),
                '        这张卡的事实无法机械核验，只能你自己点开链接看。']
    out += ['', '怎么用这份文件：每条事实下面是**原文里带着它的数字与专名的那一段**，照抄未改，',
            '前面标着它在原文的**第几页**（PDF）或**哪个小节、哪张表**（全文 XML）——这个位置是从',
            '源文件里读出来的，不是抄卡片上的。翻到那一页搜那个数字就能对上。',
            '对不上就是问题，请记进 REVIEW_ISSUES.md。', '']

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
        if not numbers and not named:
            out += ['  这条没有数字也没有专名，**程序核不了**：它说的是定性的事（形状、趋势、有没有）。',
                    '    请照上面「卡片记的位置」自己读原文判断，结论写进 REVIEW_ISSUES.md。', '']
            continue
        out.append('  要找的：数字 %s；专名 %s' % (numbers or '无', named or '无'))
        passages = best_located(segs, numbers, named)
        for score, label, passage in passages:
            out.append('  在原文的位置：%s' % label)
            gap = page_gap(fact.get('locator'), label)
            if gap:
                out.append('  注意：%s' % gap)
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
    segs_by_paper, written, by_card = {}, 0, {}
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
        if row.get('held') and card['paper'] not in segs_by_paper:
            segs_by_paper[card['paper']] = segments(row['file'])
        body = sheet_for(name, card, row, segs_by_paper.get(card['paper'], []), report.get(name, {}))
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
            flags = [f for f in entry['facts'] if f['verdict'] == 'check']
            blind = [f for f in entry['facts'] if f['verdict'] == 'no_tokens']
            bad += len(flags)
            print('  %-26s %d 条事实，%d 条对不上%s'
                  % (name, len(entry['facts']), len(flags),
                     '，%d 条没有可核验的词' % len(blind) if blind else ''))
            for f in flags:
                print('      %s 缺数字 %s 缺专名 %s' % (f['id'], f['missing_numbers'], f['missing_terms']))
        out = MANIFEST.with_name('source-probe.json')
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        c = tally(report)
        print('逐条结果写到', out)
        print('合计 %d 条事实：%d 条在原文里核到、%d 条对不上、%d 条没有数字也没有专名（程序核不了，要人读），'
              '另有 %d 张卡因为源文件未取得而整张无法核验'
              % (c['facts'], c['passed'], c['flagged'], c['no_tokens'], c['unverifiable_cards']))
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
