"""Check every link the published site hands a reviewer, so a clicked link never opens an empty page.

  python tools/check_links.py                 # internal links; exits 1 if any is broken
  python tools/check_links.py --list-external # also print the external sources, grouped by host
  python tools/check_links.py --online        # additionally request every external link (needs network)

Internal links are checked against the files and data in docs/: the target file must exist, ?instance= must name
an instance the published run contains, ?qa= a record in the catalog, ?unit= a unit in the review queue, and a
GitHub blob link must name a path that exists in the repository. A fragment must match an element id or a
data-view on the target page; pages that route on the fragment themselves (index.html, builder.html) resolve it
from data at runtime, so those fragments are counted apart instead of guessed at. External links (papers,
databases, licenses) are only listed unless --online is given, because reaching them needs network access.

Written after the 2026-10-28 meeting, where a workbench link opened empty during the demo: docs/families.js had a
hand-kept list of family names, three families were missing from it, and the 20 questions in those families all
had dead workbench links in the catalog and in the Excel review sheet.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
SITE = 'https://k0ng1212.github.io/geometry-qa-builder/'
REPO = 'https://github.com/K0NG1212/geometry-qa-builder/blob/main/'
# Keys whose value is a link. Values that do not look like one (dataset ids such as "landscape17", download
# file names such as "1UBQ.pdb") are skipped by LINKISH.
LINK_KEYS = {'url', 'trace', 'traceUrl', 'trace_url', 'batchReport', 'inputDownload', 'report', 'module_url',
             'checker_url', 'source', 'attributionLicenseUrl', 'repo'}
LINKISH = re.compile(r'^(?:https?://|[\w./-]+\.(?:html|json|txt|xyz|cif|pdb|xml|csv)(?:[?#]|$))')
QUERY_KEYS = ('instance', 'qa', 'unit')


def links_in_json(path):
    """Yield (where, link, None) for every link-valued string in one JSON file."""
    def walk(node, where):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, str) and k in LINK_KEYS and LINKISH.match(v.strip()):
                    yield '%s %s/%s' % (path.name, where, k), v.strip(), None
                else:
                    yield from walk(v, where + '/' + k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, where + '[%d]' % i)
    yield from walk(json.loads(path.read_text(encoding='utf-8')), '')


def links_in_html(path):
    """Yield (where, link, page) for every href / src attribute in one page."""
    for attr, value in re.findall(r'\b(href|src)="([^"]+)"', path.read_text(encoding='utf-8')):
        if not value.startswith(('mailto:', 'data:', 'javascript:')):
            yield '%s %s' % (path.name, attr), value, path


def published():
    """The data the pages read, so a link resolves the way a reader's browser resolves it."""
    read = lambda name: json.loads((DOCS / 'data' / name).read_text(encoding='utf-8'))
    catalog, family, queue = read('catalog.json'), read('family-workbench.json'), read('review-queue.json')
    return {'qa': {q['id'] for q in catalog['questions']},
            'instance': {t['id'] for t in family['teacher_answers']},
            'run': family['run'],
            'unit': {u['unit'] for u in queue['units']}}


def exists(path):
    """Whether docs/<path> exists, spelled exactly as the link spells it. Windows opens a file whatever its
    case, GitHub Pages does not, so a wrongly-cased link works here and 404s once published."""
    here = DOCS
    for part in path.split('/'):
        names = {p.name for p in here.iterdir()} if here.is_dir() else set()
        if part not in names:
            return False
        here = here / part
    return True


def fragment(page, name):
    """True if the fragment lands somewhere, False if nothing on the page carries it, None if the page's own
    script resolves fragments at runtime (builder.html#M5 picks a module out of the data this way)."""
    html = page.read_text(encoding='utf-8')
    if any(pattern % name in html for pattern in ('id="%s"', 'data-view="%s"', 'name="%s"')):
        return True
    for src in re.findall(r'<script[^>]+src="([^"]+)"', html):
        # tools/stamp_assets.py appends ?v=<hash>, which is not part of the path on disk
        js = page.parent / src.split('?')[0]
        if js.exists() and 'location.hash' in js.read_text(encoding='utf-8'):
            return None
    return False


def check(link, data, page=None):
    """None if the link resolves; 'external' / 'hash-routed' for the two kinds not resolved here; otherwise the
    reason it does not resolve."""
    if link.startswith(SITE):
        link = link[len(SITE):] or 'index.html'
    elif link.startswith(REPO):
        rest = urlsplit(link[len(REPO):]).path
        return None if (ROOT / rest).exists() else 'repository has no %s' % rest
    elif link.startswith(('http://', 'https://')):
        return 'external'
    parts = urlsplit(link)
    if not parts.path:                                    # a bare #fragment points inside the page it sits on
        if page is None:
            return 'link has no page to resolve against'
        target = page.relative_to(DOCS).as_posix()
    else:
        target = parts.path
    if not exists(target):
        return 'docs/%s does not exist (or is spelled with different case)' % target
    query = parse_qs(parts.query)
    for key in QUERY_KEYS:
        for value in query.get(key, []):
            if value not in data[key]:
                return '%s=%s is not in the published data (run %s)' % (key, value, data['run'])
    if parts.fragment and target.endswith('.html'):
        found = fragment(DOCS / target, parts.fragment)
        if found is None:
            return 'hash-routed'
        if not found:
            return '%s has no element id="%s"' % (target, parts.fragment)
    return None


def collect():
    for path in sorted((DOCS / 'data').glob('*.json')):
        yield from links_in_json(path)
    for path in sorted(DOCS.glob('*.html')):
        yield from links_in_html(path)


def run():
    """Return (broken, external, routed); broken is a list of (where, link, reason)."""
    data, broken, external, routed = published(), [], [], []
    for where, link, page in collect():
        reason = check(link, data, page)
        if reason == 'external':
            external.append((where, link))
        elif reason == 'hash-routed':
            routed.append((where, link))
        elif reason:
            broken.append((where, link, reason))
    return broken, external, routed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--list-external', action='store_true')
    ap.add_argument('--online', action='store_true', help='request every external link (needs network)')
    args = ap.parse_args(argv)
    broken, external, routed = run()
    total = sum(1 for _ in collect())
    print('links found %d: internal %d (broken %d), fragment resolved by the page itself %d, external %d'
          % (total, total - len(external) - len(routed), len(broken), len(routed), len(external)))
    for where, link, reason in broken:
        print('  BROKEN %s\n         %s - %s' % (link, where, reason))
    if args.list_external or args.online:
        for host, n in Counter(urlsplit(link).netloc for _, link in external).most_common():
            print('  %4d %s' % (n, host))
    if args.online:
        import urllib.request
        seen, bad = {}, 0
        for where, link in external:
            if link in seen:
                continue
            request = urllib.request.Request(link, method='HEAD', headers={'User-Agent': 'geometry-qa-link-check'})
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    seen[link] = response.status
            except Exception as e:                        # a publisher may refuse HEAD or rate-limit us
                seen[link] = repr(e)
                bad += 1
                print('  UNREACHABLE %s\n              %s - %s' % (link, where, seen[link]))
        print('external requested %d, unreachable %d' % (len(seen), bad))
    return 1 if broken else 0


if __name__ == '__main__':
    sys.exit(main())
