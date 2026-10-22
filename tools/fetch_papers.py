"""Download the JATS full texts of a paper-search run (B2, HANDOFF_2026-10-21 §1). Run only after the user approved
the list: downloads always need an explicit yes (AGENTS.md).

Every candidate not already in inputs/papers/ is fetched from the official Europe PMC endpoint
(/{PMCID}/fullTextXML) into its own directory, inputs/paper-candidates/ (git-ignored, data only - nothing in it
is ever executed). SOURCES.json in that directory records URL, size, SHA-256 and date for every file, and the
failures. Existing files are kept, so an interrupted download can be resumed.

    python -I tools/fetch_papers.py --search runs/paper-search-v01 --out inputs/paper-candidates
"""
import argparse
import datetime
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--search', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--delay', type=float, default=0.3, help='seconds between requests')
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    record_path = out / 'SOURCES.json'
    record = json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else \
        dict(kind='paper_candidate_downloads', search=args.search, files={}, failures={})
    candidates = json.loads((ROOT / args.search / 'candidates.json').read_text(encoding='utf-8'))
    todo = [c for c in candidates if not c.get('already_used')]
    for n, c in enumerate(todo, 1):
        pmcid, target = c['pmcid'], out / ('%s.xml' % c['pmcid'])
        if target.exists() and pmcid in record['files']:
            continue
        try:
            with urllib.request.urlopen(URL % pmcid, timeout=120) as r:
                data = r.read()
            if not data.lstrip().startswith(b'<'):
                raise ValueError('response is not XML')
            target.write_bytes(data)
            record['files'][pmcid] = dict(url=URL % pmcid, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                                          license=c.get('license'), date=datetime.date.today().isoformat())
            record['failures'].pop(pmcid, None)
        except (OSError, ValueError, urllib.error.HTTPError) as error:
            record['failures'][pmcid] = '%s: %s' % (type(error).__name__, error)
        if n % 50 == 0:
            record_path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            print('%d / %d' % (n, len(todo)), flush=True)
        time.sleep(args.delay)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    total = sum(f['bytes'] for f in record['files'].values())
    print('files %d (%.1f MB), failures %d' % (len(record['files']), total / 1e6, len(record['failures'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
