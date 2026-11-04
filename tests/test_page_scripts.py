"""A page must carry every element its own scripts reach for, or the page renders half-empty in silence.

Each script fetches its data and writes it into elements it looks up by id. A missing element is not an
error anyone sees: the script writes nothing and that part of the page is simply blank, which is what the
2026-10-28 demo looked like. Moving markup between pages is exactly when this breaks, and 分类与方法,
审核 and 审核队列 were moved into 方法与审核 (system.html) on 2026-11-04.

These tests read the ids out of the scripts a page loads and require the page to provide them, so markup
that moves without its script -- or a script added to a page without its markup -- fails here.
"""
import re
import unittest
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / 'docs'

# `const $=id=>document.getElementById(id)` is the house helper; the rest look elements up directly.
WANTED = (re.compile(r'\$\(\s*[\'"]([A-Za-z0-9_-]+)[\'"]\s*\)'),
          re.compile(r'getElementById\(\s*[\'"]([A-Za-z0-9_-]+)[\'"]\s*\)'),
          re.compile(r'querySelector(?:All)?\(\s*[\'"]#([A-Za-z0-9_-]+)[\'"]\s*\)'))


def ids_wanted(js):
    """The ids a script expects the page to provide: what it looks up, less what it renders itself.

    cards.js writes a detail panel containing id="flag" and then reads it back, so an id the script's own
    markup carries is its business, not the page's."""
    body = js.read_text(encoding='utf-8')
    looked_up = {m for pattern in WANTED for m in pattern.findall(body)}
    rendered = set(re.findall(r'id="([A-Za-z0-9_-]+)"', body))
    # `if($('families'))` says the script already copes with the element being absent
    guarded = set(re.findall(r'if\s*\(\s*(?:\$|document\.getElementById)\(\s*[\'"]([A-Za-z0-9_-]+)[\'"]',
                             body))
    return looked_up - rendered - guarded


def pages():
    for page in sorted(DOCS.glob('*.html')):
        html = page.read_text(encoding='utf-8')
        scripts = [DOCS / src.split('?')[0]
                   for src in re.findall(r'<script[^>]+src="([^"]+)"', html)]
        yield page, html, [s for s in scripts if s.exists()]


class PageScriptTests(unittest.TestCase):

    def test_every_page_carries_the_elements_its_scripts_write_into(self):
        for page, html, scripts in pages():
            present = set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))
            for js in scripts:
                missing = sorted(ids_wanted(js) - present)
                self.assertEqual(missing, [], '%s 载入了 %s，但页面上没有它要写的元素：%s'
                                 % (page.name, js.name, '、'.join(missing)))

    def test_no_script_declares_a_global_that_another_on_the_same_page_also_declares(self):
        """Two `const escapeHTML` on one page is a TypeError that stops both scripts. audit.js declared
        its own until it joined 方法与审核; the others are all wrapped."""
        top = re.compile(r'^(?:const|let|var|function)\s+([A-Za-z_$][\w$]*)', re.M)
        for page, _html, scripts in pages():
            seen = {}
            for js in scripts:
                for name in top.findall(js.read_text(encoding='utf-8')):
                    self.assertNotIn(name, seen,
                                     '%s 上 %s 与 %s 都声明了顶层的 %s'
                                     % (page.name, js.name, seen.get(name), name))
                    seen[name] = js.name

    def test_the_merged_page_has_all_four_sections(self):
        html = (DOCS / 'system.html').read_text(encoding='utf-8')
        for anchor in ('method', 'system', 'review', 'audit'):
            self.assertIn('id="%s"' % anchor, html, '方法与审核 少了 #%s 这一节' % anchor)

    def test_the_emptied_pages_still_point_somewhere_real(self):
        """review.html and audit.html keep their addresses because PROJECT_STATUS 的历史段落链着它们。"""
        target = (DOCS / 'system.html').read_text(encoding='utf-8')
        for name, anchor in (('review.html', 'review'), ('audit.html', 'audit')):
            html = (DOCS / name).read_text(encoding='utf-8')
            self.assertIn('url=system.html#' + anchor, html)
            self.assertIn('id="%s"' % anchor, target)


if __name__ == '__main__':
    unittest.main()
