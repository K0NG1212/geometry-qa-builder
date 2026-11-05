"""Every stylesheet and script the site loads must be stamped with its own contents.

A browser that has been to the site keeps the copy it has until the URL changes, so an edited file reaches
nobody who has visited before unless its query string moves with it. Doing that by hand had already drifted:
38 of 57 references carried no stamp, and i18n.js carried two different hand-typed dates depending on the
page, which means two different cached copies of one file.

These tests pin what tools/stamp_assets.py guarantees: the stamp is the file's hash, so it cannot be a date
someone forgot to bump; one file is one stamp everywhere it is loaded; and nothing on the site loads an
asset with no stamp at all.
"""
import contextlib
import io
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
sys.path.insert(0, str(ROOT))

from tools import stamp_assets                                            # noqa: E402

PAGES = sorted(DOCS.glob('*.html'))
STAMPED = re.compile(r'(?:href|src)="([A-Za-z0-9_.-]+\.(?:css|js))\?v=([0-9a-f]{8})"')
BARE = re.compile(r'(?:href|src)="([A-Za-z0-9_.-]+\.(?:css|js))"')


def assets():
    return {p.name: stamp_assets.stamp(p) for p in sorted(DOCS.glob('*.css')) + sorted(DOCS.glob('*.js'))}


def run(*argv):
    """The tool, with its report kept out of the test output."""
    with contextlib.redirect_stdout(io.StringIO()):
        return stamp_assets.main(list(argv))


class StampTests(unittest.TestCase):

    def test_every_stamp_on_the_site_is_the_file_it_points_at(self):
        """The check the tool runs, run as a test: an edited asset fails the suite, not a reviewer's browser."""
        self.assertEqual(run('--check'), 0,
                         '有资源的版本号过期了，跑 python tools/stamp_assets.py 更新')

    def test_no_page_loads_an_asset_without_a_stamp(self):
        known = assets()
        for page in PAGES:
            for name in BARE.findall(page.read_text(encoding='utf-8')):
                if name in known:
                    self.fail('%s 里的 %s 没有版本号' % (page.name, name))

    def test_one_file_is_one_stamp_everywhere_it_is_loaded(self):
        """i18n.js was ?v=20261103c on five pages and ?v=20261103cb on three, so the same file was two
        different cached copies depending on which page the reader arrived from."""
        seen = {}
        for page in PAGES:
            for name, mark in STAMPED.findall(page.read_text(encoding='utf-8')):
                seen.setdefault(name, {}).setdefault(mark, []).append(page.name)
        for name, marks in seen.items():
            self.assertEqual(len(marks), 1,
                             '%s 在不同页面上有不同版本号：%s' % (name, marks))

    def test_a_changed_file_changes_its_stamp(self):
        css = DOCS / 'styles.css'
        before = stamp_assets.stamp(css)
        raw = css.read_bytes()
        try:
            css.write_bytes(raw + b'\n/* x */')
            self.assertNotEqual(before, stamp_assets.stamp(css))
            self.assertEqual(run('--check'), 1, '改了文件却没被 --check 发现')
        finally:
            css.write_bytes(raw)
        self.assertEqual(before, stamp_assets.stamp(css))

    def test_running_the_tool_again_rewrites_nothing(self):
        """A second run must be a no-op, so the command is safe to put in the routine. It writes, so the
        pages are put back if it turns out it did change something -- a failing test should not also
        leave the working tree edited."""
        self.assertEqual(run('--check'), 0, '先修好过期的版本号，再谈幂等')
        before = {p: p.read_bytes() for p in PAGES}
        try:
            self.assertEqual(run(), 0)
            for page, body in before.items():
                self.assertEqual(body, page.read_bytes(), '%s 被重复改写了' % page.name)
        finally:
            for page, body in before.items():
                if page.read_bytes() != body:
                    page.write_bytes(body)

    def test_data_files_are_left_alone(self):
        """docs/data/*.json is fetched by script, not cached as a page asset, and carries its own date."""
        for page in PAGES:
            self.assertNotIn('data/catalog.json?v=', page.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
