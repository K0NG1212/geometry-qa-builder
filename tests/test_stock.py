"""The paper has to be in the question's folder, and the folder has to say where in it to look.

A central store of papers is not what a reviewer opens: they open one question. These tests pin what
`review_system.stock` puts next to a question -- the document itself, and a reading copy that names the
local file, gives every checkable fact a page or heading, and links to it.

They run offline; the ones that need the data drive skip without it.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from review_system import sources, stock                                     # noqa: E402

QA = sources.QA


class ReadingCopyTests(unittest.TestCase):

    card = dict(citation='Someone et al., Journal 1, 1 (2020)', license='CC BY 4.0',
                paper='arXiv:1234.5678',
                facts=[dict(id='E1', locator='p. 2', text='The gate opens to 22 A at Thr112.'),
                       dict(id='E2', locator='Fig. 1', text='Both peaks are present and unsplit.')])
    row = dict(held=True, file=r'D:\somewhere\paper.pdf', sha256='ab' * 32, bytes=1234,
               url='https://arxiv.org/pdf/1234.5678', link='https://arxiv.org/abs/1234.5678')
    segs = [('PDF 第 1 页', 'nothing of interest here'),
            ('PDF 第 2 页', 'an activation gate opening of 22 Å between Threonine 112 carbons')]

    def page(self):
        return stock.reading_copy('card', self.card, self.row,
                                  self.segs, dict(facts=[dict(id='E1', verdict='pass'),
                                                         dict(id='E2', verdict='no_tokens')]), 'QNI001')

    def test_it_names_the_file_sitting_in_the_same_folder(self):
        self.assertIn('paper.pdf', self.page())

    def test_a_checkable_fact_gets_a_place_and_a_link_to_it(self):
        html = self.page()
        self.assertIn('PDF 第 2 页', html)
        self.assertIn('href="paper.pdf#page=2"', html)

    def test_a_fact_with_nothing_to_look_for_says_so_instead_of_claiming_a_place(self):
        html = self.page()
        self.assertIn('这条没有数字也没有专名', html)
        self.assertIn('程序核不了', html)

    def test_the_passage_is_highlighted_in_the_paper_s_own_text(self):
        html = self.page()
        self.assertEqual(html.count('<mark>'), html.count('</mark>'))
        self.assertGreaterEqual(html.count('<mark>'), 1)

    def test_a_pdf_page_links_to_the_page_but_a_heading_links_inside_this_file(self):
        self.assertEqual(stock.jump('PDF 第 7 页', 'paper.pdf'), 'paper.pdf#page=7')
        self.assertTrue(stock.jump('PDF 第 7 页', 'paper.xml').startswith('#'))
        self.assertTrue(stock.jump('小节「Results」', 'paper.xml').startswith('#'))

    def test_markup_in_the_paper_is_escaped_once(self):
        """The text goes through the highlighter, so a stray < in the paper must not become a tag."""
        out = stock.mark_passages('a < b and <i>mid</i> end', ['<i>mid</i>'])
        self.assertIn('&lt; b', out)
        self.assertIn('<mark>&lt;i&gt;mid&lt;/i&gt;</mark>', out)

    def test_a_paper_we_could_not_fetch_is_not_dressed_up_as_present(self):
        row = dict(held=False, reason='付费墙', link='https://doi.org/10')
        html = stock.reading_copy('card', self.card, row, [], {}, 'QNI001')
        self.assertIn('未取得', html)
        self.assertIn('付费墙', html)
        self.assertNotIn('本文件夹里的原件', html)


class PlaceTests(unittest.TestCase):

    def test_a_second_copy_costs_nothing_when_the_drive_allows_a_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'paper.pdf'
            src.write_bytes(b'%PDF-1.4 ...')
            dest = Path(tmp) / 'q' / 'source' / 'paper.pdf'
            self.assertIn(stock.place(src, dest), ('linked', 'copied'))
            self.assertEqual(dest.read_bytes(), src.read_bytes())
            self.assertEqual(stock.place(src, dest), 'already')       # idempotent, no second write


@unittest.skipUnless(QA.exists(), '数据盘没挂上')
class StockedFoldersTests(unittest.TestCase):
    """What is actually sitting in the question folders now."""

    def folders(self):
        import json
        cards = sources.read_cards()
        for folder in sorted(QA.iterdir()):
            info = folder / 'info.json'
            if not info.exists():
                continue
            name = (json.loads(info.read_text(encoding='utf-8')).get('originality') or {}).get('card')
            if name in cards:
                yield folder, name, cards[name]

    def test_every_evidence_question_holds_the_paper_or_says_why_not(self):
        import json
        held = json.loads(sources.MANIFEST.read_text(encoding='utf-8'))['papers']
        for folder, name, card in self.folders():
            row = held.get(card['paper'] or '', {})
            source = folder / 'source'
            if not row.get('held'):
                self.assertIn('未取得', (source / 'SOURCE_CHECK.txt').read_text(encoding='utf-8'),
                              '%s 没有原件，核对单里也没说' % folder.name)
                continue
            self.assertTrue((source / Path(row['file']).name).exists(),
                            '%s 里没有论文原件' % folder.name)
            self.assertTrue((source / stock.READING).exists(), '%s 里没有阅读版' % folder.name)

    def test_the_paper_in_a_question_folder_is_byte_for_byte_the_one_we_recorded(self):
        import hashlib
        import json
        held = json.loads(sources.MANIFEST.read_text(encoding='utf-8'))['papers']
        for folder, name, card in self.folders():
            row = held.get(card['paper'] or '', {})
            local = folder / 'source' / Path(row.get('file', 'x')).name
            if not row.get('held') or not local.exists():
                continue
            self.assertEqual(hashlib.sha256(local.read_bytes()).hexdigest(), row['sha256'],
                             '%s 里的论文和清单对不上' % folder.name)

    def test_no_paper_text_escaped_into_the_repository(self):
        """The reading copies carry the papers' own words; they live on the data drive, never in git."""
        self.assertFalse(list(ROOT.rglob(stock.READING)), '仓库里出现了阅读版')
        self.assertFalse((ROOT / 'reviews' / 'paper-sources').exists())


if __name__ == '__main__':
    unittest.main()
