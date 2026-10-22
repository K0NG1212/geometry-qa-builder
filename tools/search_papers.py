"""Search Europe PMC for candidate papers (B2, HANDOFF_2026-10-21 §1). Metadata only - no full text is downloaded.

Queries and filters live in templates/paper-search.json. Each query is a list of term groups: a group is OR-ed
over TITLE and ABSTRACT, groups are AND-ed, and the shared filters (open access, CC BY, full text in Europe PMC,
no reviews, year range) are AND-ed onto every query. Every page is fetched with the official cursorMark paging.

The run directory (runs/paper-search-vNN/, never overwritten) keeps the config used, every query string with its
hit count and date, and candidates.json: one record per paper with the queries that found it. Papers already in
inputs/papers/ are marked, not dropped. The known_good papers (already turned into questions) must be found;
otherwise the run reports a recall failure, since a query set that loses them is too narrow.

    python tools/search_papers.py --out runs/paper-search-v01
"""
import argparse
import datetime
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'templates/paper-search.json'
FIELDS = ('pmcid', 'pmid', 'doi', 'title', 'authorString', 'journalTitle', 'pubYear', 'license', 'isOpenAccess',
          'inEPMC', 'hasSuppl', 'abstractText')


def phrase(term):
    if '"' in term:
        raise ValueError('Search terms may not contain double quotes: ' + term)
    return 'TITLE:"%s" OR ABSTRACT:"%s"' % (term, term)


def query_string(groups, filters):
    """AND of OR-groups over title and abstract, then the shared filters."""
    if not groups or any(not g for g in groups):
        raise ValueError('A query needs at least one non-empty term group')
    return ' AND '.join('(%s)' % ' OR '.join(phrase(t) for t in g) for g in groups) + ' AND ' + filters


def fetch(endpoint, query, cursor, page_size):
    url = endpoint + '?' + urllib.parse.urlencode(dict(query=query, format='json', resultType='core',
                                                       pageSize=page_size, cursorMark=cursor))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read().decode('utf-8'))
        except OSError:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def run_query(endpoint, query, page_size=500):
    results, cursor, hits = [], '*', None
    while True:
        page = fetch(endpoint, query, cursor, page_size)
        hits = page.get('hitCount', 0)
        batch = page.get('resultList', {}).get('result', [])
        results += batch
        nxt = page.get('nextCursorMark')
        if not batch or not nxt or nxt == cursor or len(results) >= hits:
            break
        cursor = nxt
    return hits, results


def used_pmcids(root):
    papers = root / 'inputs' / 'papers'
    return {m.group(0) for p in papers.rglob('*') if p.is_file() for m in [re.search(r'PMC\d+', p.name)] if m} \
        if papers.exists() else set()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True, help='new run directory, e.g. runs/paper-search-v01')
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    out = ROOT / args.out
    if out.exists():
        raise SystemExit('Refusing to overwrite ' + args.out)
    raw = (ROOT / CONFIG).read_bytes()
    cfg = json.loads(raw.decode('utf-8'))
    used = used_pmcids(ROOT)
    log, papers = [], {}
    for name, groups in cfg['queries'].items():
        q = query_string(groups, cfg['filters'])
        hits, results = run_query(cfg['endpoint'], q)
        log.append(dict(query=name, string=q, hit_count=hits, returned=len(results)))
        print('%-24s hits %5d  returned %5d' % (name, hits, len(results)))
        for r in results:
            key = r.get('pmcid')
            if not key:
                continue
            rec = papers.setdefault(key, {k: r.get(k) for k in FIELDS})
            rec.setdefault('queries', []).append(name)
    for key, rec in papers.items():
        rec['already_used'] = key in used
    missing = [k for k in cfg['known_good'] if k not in papers]
    out.mkdir(parents=True)
    (out / 'paper-search.json').write_bytes(raw)
    summary = dict(kind='paper_search_run', date=datetime.date.today().isoformat(), config=CONFIG,
                   queries=log, papers=len(papers), already_used=sum(r['already_used'] for r in papers.values()),
                   known_good_found=[k for k in cfg['known_good'] if k in papers], known_good_missing=missing,
                   model_calls=0, full_texts_downloaded=0)
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    rows = [papers[k] for k in sorted(papers)]
    (out / 'candidates.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('papers %d (already used %d); known good found %d/%d%s' % (
        len(papers), summary['already_used'], len(summary['known_good_found']), len(cfg['known_good']),
        '' if not missing else '; MISSING ' + ', '.join(missing)))
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
