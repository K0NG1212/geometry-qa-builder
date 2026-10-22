"""B2: the Europe PMC query builder and the table pre-screen (HANDOFF_2026-10-21 §1). No network access."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.dom import minidom
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from checkers import paper_sources  # noqa: E402
from tools import jats, prefilter_tables, search_papers  # noqa: E402

CONFIG = json.loads((ROOT / 'templates/paper-search.json').read_text(encoding='utf-8'))
KNOWN = {'PMC12415320': ('inputs/papers/vincent2025/vincent2025-PMC12415320.xml', 'Table 1'),
         'PMC11639902': ('inputs/papers/rando2025/rando2025-PMC11639902.xml', 'Table 1'),
         'PMC13022808': ('inputs/papers/chetry2026/chetry2026-PMC13022808.xml', '1')}


def article(*tables):
    return '<article><body><sec><title>R</title>%s</sec></body></article>' % ''.join(tables)


def table(label, caption, header, rows):
    th = ''.join('<th>%s</th>' % h for h in header)
    trs = ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % c for c in r) for r in rows)
    return ('<table-wrap id="t-%s"><label>%s</label><caption><p>%s</p></caption><table><thead><tr>%s</tr></thead>'
            '<tbody>%s</tbody></table></table-wrap>' % (label, label, caption, th, trs))


def screen(xml_text):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'x.xml'
        path.write_text(xml_text, encoding='utf-8')
        return prefilter_tables.screen(path)


ROWS = [['A', '1.2 × 10<sup>4</sup>'], ['B', '3.4'], ['C', '(5.6 ± 0.2)'], ['D', '7']]


class QueryTests(unittest.TestCase):
    def test_groups_are_and_ed_terms_or_ed_over_title_and_abstract(self):
        q = search_papers.query_string([['a b', 'c'], ['d']], 'OPEN_ACCESS:y')
        self.assertEqual(q, '(TITLE:"a b" OR ABSTRACT:"a b" OR TITLE:"c" OR ABSTRACT:"c") AND '
                            '(TITLE:"d" OR ABSTRACT:"d") AND OPEN_ACCESS:y')

    def test_bad_queries_are_refused(self):
        for groups in ([], [[]], [['say "x"']]):
            with self.assertRaises(ValueError):
                search_papers.query_string(groups, 'F')

    def test_config_is_complete(self):
        self.assertIn('LICENSE:"cc by"', CONFIG['filters'])
        self.assertIn('OPEN_ACCESS:y', CONFIG['filters'])
        self.assertTrue(all(groups and all(groups) for groups in CONFIG['queries'].values()))
        self.assertEqual(set(CONFIG['known_good']), set(KNOWN))


class RenderingTests(unittest.TestCase):
    def test_nested_superscripts_add_one_caret_in_both_readers(self):
        xml = '<p>mmol cm<sup>\n<sup>&#8211;3</sup>\n</sup> and 10<sup>5</sup></p>'
        self.assertEqual(jats.render(ET.fromstring(xml)), 'mmol cm^-3 and 10^5')
        self.assertEqual(paper_sources.text_of(minidom.parseString(xml).documentElement), 'mmol cm^-3 and 10^5')


class PrefilterTests(unittest.TestCase):
    def test_numbers_under_a_unit_header_are_kept(self):
        r = screen(article(table('Table 1', 'Results', ['Guest', 'K<sub>a</sub> [M<sup>−1</sup>]'], ROWS)))
        self.assertEqual([k['measured_columns'] for k in r['kept']], [['Ka [M^-1]']])

    def test_a_caption_may_carry_the_quantity(self):
        r = screen(article(table('Table 1', 'Association constants (K<sub>a</sub>, M<sup>−1</sup>)', ['Anion', 'BU1'], ROWS)))
        self.assertEqual(len(r['kept']), 1)

    def test_too_few_rows_no_numbers_or_no_quantity_are_dropped(self):
        cases = [table('Table 1', 'Results', ['Guest', 'K<sub>a</sub> [M<sup>−1</sup>]'], ROWS[:3]),
                 table('Table 2', 'Results', ['Guest', 'K<sub>a</sub> [M<sup>−1</sup>]'], [[a, 'n.d.'] for a, _ in ROWS]),
                 table('Table 3', 'Compounds', ['Entry', 'Code'], ROWS)]
        r = screen(article(*cases))
        self.assertEqual((r['tables'], r['kept']), (3, []))

    def test_unparsable_tables_are_recorded_not_fatal(self):
        bad = ('<table-wrap id="t9"><label>Table 9</label><table><tr><td rowspan="1">a</td><td>b</td></tr>'
               '<tr><td>c</td></tr></table></table-wrap>')
        r = screen(article(bad))
        self.assertEqual(len(r['unparsed']), 1)

    def test_keyword_tiers(self):
        self.assertEqual(prefilter_tables.tier('Association constants of hosts 1-4', ['Guest']), 'strong')
        self.assertEqual(prefilter_tables.tier('Results', ['Ka [M^-1]']), 'strong')
        self.assertEqual(prefilter_tables.tier('Data collection and refinement statistics', ['Value']), 'excluded')
        self.assertEqual(prefilter_tables.tier('Docking scores and binding affinity', ['Score']), 'excluded')
        self.assertEqual(prefilter_tables.tier('Comparison with other reported catalysts', ['Selectivity']), 'excluded')
        self.assertEqual(prefilter_tables.tier('Sample list', ['Mass (mg)']), 'shape_only')

    def test_a_screened_paper_takes_its_best_table_tier(self):
        r = screen(article(table('Table 1', 'Sample list', ['Entry', 'Mass (mg)'], ROWS),
                           table('Table 2', 'Association constants', ['Guest', 'BU1'], ROWS)))
        self.assertEqual([k['tier'] for k in r['kept']], ['shape_only', 'strong'])
        self.assertEqual(r['tier'], 'strong')

    @unittest.skipUnless(all((ROOT / p).exists() for p, _ in KNOWN.values()), 'paper XML not on this machine')
    def test_the_tables_behind_existing_design_questions_pass(self):
        for pmcid, (path, label) in KNOWN.items():
            kept = [k['label'] for k in prefilter_tables.screen(ROOT / path)['kept']]
            self.assertIn(label, kept, pmcid)


if __name__ == '__main__':
    unittest.main()
