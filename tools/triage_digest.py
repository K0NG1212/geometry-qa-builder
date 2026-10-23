"""Reading aid for B3 triage (HANDOFF_2026-10-21 §1): one compact entry per strong-tier paper.

For every paper the pre-screen put in the strong tier: identifiers, title, the start of the abstract, and for each
strong table its caption, header row, row labels (first column) and measured columns. Nothing is judged here; the
digest only puts in front of the reader what a triage decision needs, with the PMCID to open the full text.

    python -I tools/triage_digest.py --prefilter runs/paper-prefilter-v08 --search runs/paper-search-v02 --xml inputs/paper-candidates --out runs/b3-digest-v01
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import jats  # noqa: E402

PER_FILE = 25


def plain(text, limit):
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html.unescape(text or ''))).strip()
    return text if len(text) <= limit else text[:limit] + ' …'


def entry(n, paper, abstract, xml_dir):
    lines = ['## %d. %s · %s · %s' % (n, paper['pmcid'], ','.join(paper['queries']), paper.get('year')),
             '', '**' + plain(paper.get('title'), 200) + '**', '', 'Abstract: ' + plain(abstract, 600), '']
    root = jats.load(ROOT / xml_dir / ('%s.xml' % paper['pmcid']))
    for t in paper['kept']:
        if t['tier'] != 'strong':
            continue
        grid = jats.table(root, t['label'])
        rows = [r[0] for r in grid[1:]]
        lines += ['- **%s** (%d rows): %s' % (t['label'], t['rows'], plain(t['caption'], 260)),
                  '  - header: ' + ' | '.join(grid[0])[:300],
                  '  - rows: ' + '; '.join(rows[:14])[:300] + (' …' if len(rows) > 14 else ''),
                  '  - measured: ' + '; '.join(t['measured_columns'])[:200]]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--prefilter', required=True)
    ap.add_argument('--search', required=True)
    ap.add_argument('--xml', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    out = ROOT / args.out
    if out.exists():
        raise SystemExit('Refusing to overwrite ' + args.out)
    papers = json.loads((ROOT / args.prefilter / 'prefilter.json').read_text(encoding='utf-8'))['papers']
    abstracts = {c['pmcid']: c.get('abstractText') for c in
                 json.loads((ROOT / args.search / 'candidates.json').read_text(encoding='utf-8'))}
    strong = sorted((p for p in papers if p.get('tier') == 'strong'), key=lambda p: (p['queries'][0], p['pmcid']))
    out.mkdir(parents=True)
    index = []
    for k in range(0, len(strong), PER_FILE):
        chunk = strong[k:k + PER_FILE]
        name = 'digest-%02d.md' % (k // PER_FILE + 1)
        text = ''.join(entry(k + i + 1, p, abstracts.get(p['pmcid']), args.xml) for i, p in enumerate(chunk))
        (out / name).write_text(text, encoding='utf-8')
        index.append(dict(file=name, papers=[p['pmcid'] for p in chunk]))
    (out / 'index.json').write_text(json.dumps(dict(prefilter=args.prefilter, papers=len(strong), files=index),
                                               indent=1) + '\n', encoding='utf-8')
    print('%d strong papers in %d files' % (len(strong), len(index)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
