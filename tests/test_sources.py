"""A fact said to come from a paper must be findable in that paper.

Before this, an evidence card's only backing was a prose locator ("Main text; Fig. 3a") and our word that
the fact was read off the paper. Nobody could check it: the paper was not in the question folder and there
was no sentence to search for. These tests pin the machinery that replaced that -- the source is fetched
and hashed, every number and named term in a fact is looked for in the source's own text, and a fact whose
numbers are nowhere in the paper is reported rather than passed.

They run offline against the manifest written by `python -m review_system.sources --fetch`.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from review_system import sources                                         # noqa: E402

MANIFEST = ROOT / 'reviews' / 'source-manifest.json'
PROBE = ROOT / 'reviews' / 'source-probe.json'


def manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))['papers'] if MANIFEST.exists() else {}


class MatchingTests(unittest.TestCase):
    """What counts as the paper saying a thing."""

    def test_a_residue_is_the_same_residue_however_the_paper_spaces_it(self):
        text = 'the activation gate spans 22 Å (C-C distance at Thr 112) in the open state'
        self.assertTrue(sources.found('Thr112', text))
        self.assertTrue(sources.found('Thr112', text.replace('Thr 112', 'Threonine 112')))

    def test_a_number_is_not_matched_inside_a_longer_number(self):
        self.assertFalse(sources.found('12', 'reference 1234 and 512 entries'))
        self.assertTrue(sources.found('12', 'diameters in the range of 12-18 A'))

    def test_a_fact_the_paper_does_not_support_is_not_matched(self):
        text = 'The mouth has a 30-A opening and inner diameters down to 20 A.'
        self.assertFalse(sources.found('47', text))
        self.assertFalse(sources.found('Phe427', text))

    def test_tokens_are_the_checkable_part_of_a_fact(self):
        numbers, named = sources.tokens('A ring of seven Phe427 side chains leaves a hole of only 6 A.')
        self.assertIn('6', numbers)
        self.assertIn('Phe427', named)
        self.assertNotIn('A', named, 'single letters match everything and check nothing')

    def test_a_passage_carrying_the_whole_fact_beats_one_carrying_a_stray_number(self):
        text = ('Jiang Jiansen 12 California NanoSystems Institute. ... Underneath the clamp are the '
                'throat, an enlarged (~18 A) chamber, and the tube formed by the 14-stranded barrel '
                'with inner diameters in the range of 12-18 A.')
        best = sources.best_passages(text, ['12', '14', '18'], [])
        self.assertTrue(best)
        self.assertIn('14-stranded', best[0][1])
        self.assertEqual(best[0][0], 3)


class ExtractionTests(unittest.TestCase):

    def test_markup_inside_a_word_closes_up(self):
        """NH<sub>2</sub> is the word NH2. The first probe reported it missing from a paper about it."""
        xml = ROOT / 'reviews' / '_t.xml'
        xml.write_text('<p>the NH<sub>2</sub> stretching mode</p>', encoding='utf-8')
        try:
            self.assertIn('NH2', sources.text_of(xml))
        finally:
            xml.unlink()

    def test_tables_are_kept(self):
        """Locators point at tables; an extractor that drops them calls their numbers absent."""
        xml = ROOT / 'reviews' / '_t2.xml'
        xml.write_text('<table-wrap><td>101</td></table-wrap>', encoding='utf-8')
        try:
            self.assertTrue(sources.found('101', sources.text_of(xml)))
        finally:
            xml.unlink()


@unittest.skipUnless(MANIFEST.exists(), 'still需要先跑 --fetch')
class HeldSourceTests(unittest.TestCase):

    def test_every_card_cites_a_paper_we_can_name(self):
        for name, card in sources.read_cards().items():
            self.assertTrue(card['paper'], '%s 的引文里找不到 arXiv/PMC/DOI 标识' % name)

    def test_a_paper_we_hold_is_the_file_we_recorded(self):
        import hashlib
        for ident, row in manifest().items():
            if not row.get('held'):
                continue
            path = Path(row['file'])
            if not path.exists():
                continue                                 # data drive not mounted on this machine
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row['sha256'],
                             '%s 的本地副本和清单里的 sha256 对不上' % ident)

    def test_a_paper_we_do_not_hold_says_why_and_keeps_its_link(self):
        for ident, row in manifest().items():
            if row.get('held'):
                continue
            self.assertTrue(row.get('reason'), '%s 未取得却没写原因' % ident)
            self.assertTrue(row.get('link'), '%s 未取得却没留链接' % ident)

    @unittest.skipUnless(PROBE.exists(), 'still需要先跑 --probe')
    def test_no_fact_of_a_held_paper_is_unsupported(self):
        bad = []
        for name, entry in json.loads(PROBE.read_text(encoding='utf-8')).items():
            if entry.get('unverifiable'):
                continue
            bad += ['%s %s 缺 %s %s' % (name, f['id'], f['missing_numbers'], f['missing_terms'])
                    for f in entry['facts'] if f['verdict'] != 'pass']
        self.assertEqual(bad, [])

    @unittest.skipUnless(PROBE.exists(), 'still需要先跑 --probe')
    def test_an_unverifiable_card_is_reported_as_such_not_passed(self):
        report = json.loads(PROBE.read_text(encoding='utf-8'))
        unverifiable = [n for n, e in report.items() if e.get('unverifiable')]
        for name in unverifiable:
            self.assertEqual(report[name]['facts'], [], '%s 没有源文件却列出了核验结果' % name)


if __name__ == '__main__':
    unittest.main()
