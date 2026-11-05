"""Stamp every stylesheet and script the site loads with a hash of its contents, so a reviewer never
runs an old copy.

  python tools/stamp_assets.py            # rewrite the stamps in docs/*.html
  python tools/stamp_assets.py --check    # change nothing; exit 1 if any stamp is out of date

GitHub Pages serves these files with a long cache lifetime, so a browser that has been to the site keeps
whatever it already has until the URL changes. The query string is what changes it. Doing that by hand is
what produced the state this replaces: of 57 references, 38 carried no stamp at all and the other 19 carried
five different hand-typed dates -- i18n.js was ?v=20261103c on five pages and ?v=20261103cb on three, so the
same file was two different cached copies depending on which page you arrived from.

The stamp is the first 8 hex of the sha256 of the file, so it is the file's identity rather than a date
someone has to remember to bump: edit a file and its stamp changes everywhere it is loaded, edit nothing and
the command rewrites nothing. tests/test_asset_stamps.py runs --check, so a stale stamp fails the suite
rather than reaching a reviewer's browser.

Only same-folder .css and .js are stamped. Data under docs/data/ is left alone: it is fetched by script
rather than cached as a page asset, and its own freshness is already a published field.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / 'docs'

# href="styles.css" / src="app.js?v=1234abcd" -- a bare name in the same folder, with or without a stamp.
ASSET = re.compile(r'(?P<attr>href|src)="(?P<file>[A-Za-z0-9_.-]+\.(?:css|js))(?:\?v=[0-9a-z]+)?"')


def stamp(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def rewrite(page, stamps):
    """The page with every asset reference carrying its file's current stamp, and what changed."""
    raw = page.read_text(encoding='utf-8')
    changed = []

    def one(m):
        name = m.group('file')
        if name not in stamps:                      # not an asset of ours; leave the reference alone
            return m.group(0)
        new = '%s="%s?v=%s"' % (m.group('attr'), name, stamps[name])
        if new != m.group(0):
            changed.append(name)
        return new

    return ASSET.sub(one, raw), changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true',
                        help='只检查，不写文件；有过期的就返回 1')
    args = parser.parse_args(argv)

    stamps = {p.name: stamp(p) for p in sorted(DOCS.glob('*.css')) + sorted(DOCS.glob('*.js'))}
    stale = {}
    for page in sorted(DOCS.glob('*.html')):
        body, changed = rewrite(page, stamps)
        if not changed:
            continue
        stale[page.name] = sorted(set(changed))
        if not args.check:
            # written back with newline='' so a CRLF page stays CRLF
            page.write_text(body, encoding='utf-8', newline='')

    if not stale:
        print('%d 个资源、%d 个页面，版本号都是最新的' % (stamps and len(stamps), len(list(DOCS.glob('*.html')))))
        return 0
    verb = '过期' if args.check else '已更新'
    for name, files in sorted(stale.items()):
        print('%s %s：%s' % (verb, name, '、'.join(files)))
    print('共 %d 个页面' % len(stale))
    return 1 if args.check else 0


if __name__ == '__main__':
    sys.exit(main())
