"""Source coverage: every denominator has a provenance, and the document cannot drift from the numbers.

The advisor asked (2026-11-09) why each source was chosen and whether it covers the structure space of a
given data object as much as possible. The answer is a document, DATA_SOURCES.md, and a computed file,
docs/data/source-coverage.json. Both can rot, and in opposite ways:

  - the numbers rot when a question is added and nobody re-runs the builder, so the build is re-run here and
    compared with what is published;
  - the prose rots when the numbers change and the paragraph still quotes the old ones, so the headline
    figures in the document are checked against the computed file;
  - and a denominator with no provenance is the worst case of all, because it looks like a measurement.
    Every external number must say whether it was queried from the source's own service or cited from its
    paper, and nothing here touches the network: the fetched facts are cached in docs/content.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from review_system import datasources  # noqa: E402

PUBLISHED = json.loads((ROOT / 'docs/data/source-coverage.json').read_text(encoding='utf-8'))
COUNTS = json.loads((ROOT / 'docs/content/external-counts.json').read_text(encoding='utf-8'))
FACTS = json.loads((ROOT / 'docs/content/pdb-entry-facts.json').read_text(encoding='utf-8'))
DOC = (ROOT / 'DATA_SOURCES.md').read_text(encoding='utf-8')
CATALOG = json.loads((ROOT / 'docs/data/catalog.json').read_text(encoding='utf-8'))


class ProvenanceTests(unittest.TestCase):
    def test_every_external_number_says_where_it_came_from(self):
        for source, record in COUNTS['sources'].items():
            self.assertTrue(record['name'].strip(), source)
            self.assertTrue(record['counts'], source)
            for key, entry in record['counts'].items():
                where = (source, key)
                self.assertIsInstance(entry['n'], int, where)
                self.assertGreater(entry['n'], 0, where)
                self.assertIn(entry['provenance'], ('api', 'cited'), where)
                if entry['provenance'] == 'api':
                    self.assertTrue(entry['query'].strip(), where)      # re-runnable
                else:
                    self.assertTrue(entry['reference'].strip(), where)  # and attributable
                    self.assertRegex(entry['read_on'], r'^\d{4}-\d{2}-\d{2}$', str(where))

    def test_only_the_sources_we_are_allowed_to_query_were_queried(self):
        """The download authorisation (2026-11-04) covers RCSB PDB, COD and Europe PMC. Anything else may be
        cited from its own publication but must not be fetched, so an 'api' number under, say, PubChem would
        mean the authorisation was exceeded."""
        allowed = {'rcsb_pdb', 'cod'}
        for source, record in COUNTS['sources'].items():
            if source in allowed:
                continue
            kinds = {entry['provenance'] for entry in record['counts'].values()}
            self.assertEqual(kinds, {'cited'}, '%s 不在下载授权名单里，数字只能引用' % source)

    def test_the_cached_rcsb_facts_are_what_the_service_returned_not_a_guess(self):
        self.assertRegex(FACTS['fetched_on'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertTrue(FACTS['rejected_candidates'], '应当记下被 RCSB 否掉的候选编号')
        for entry, fact in FACTS['entries'].items():
            self.assertRegex(entry, r'^[0-9][A-Za-z0-9]{3}$')
            self.assertTrue(fact['method'].strip(), entry)
            self.assertTrue(fact['title'].strip(), entry)
            self.assertIsInstance(fact['ec1'], list, entry)
        # the id-shaped strings in our own metadata that are not PDB entries have to stay out
        for bogus in ('00WT', '7001'):
            self.assertNotIn(bogus, FACTS['entries'], bogus + ' 不是 PDB 条目')


class CoverageTests(unittest.TestCase):
    def test_the_published_numbers_are_what_the_builder_produces(self):
        self.assertEqual(datasources.build(FACTS['entries'], COUNTS), PUBLISHED,
                         '重新跑 python -m review_system.datasources')

    def test_every_question_is_attributed_to_exactly_one_source(self):
        active = sum(1 for q in CATALOG['questions'] if q['lifecycle'] == 'active')
        self.assertEqual(PUBLISHED['questions_total'], active)
        self.assertEqual(sum(PUBLISHED['questions_by_source'].values()), active)

    def test_a_numerator_never_exceeds_its_denominator(self):
        pdb, cod, qm = PUBLISHED['rcsb_pdb'], PUBLISHED['cod'], PUBLISHED['qm7x']
        for stratum in pdb['ec_strata']:
            self.assertLessEqual(stratum['ours'], stratum['in_source'], stratum['ec'])
        self.assertLessEqual(pdb['resolution']['at_or_below_2A'], pdb['resolution']['known'])
        self.assertLessEqual(cod['space_groups_used'], cod['space_groups_possible'])
        self.assertLessEqual(qm['distinct_molecules'], qm['formulae_in_source'])
        self.assertLessEqual(PUBLISHED['sampl9']['hosts_used'], PUBLISHED['sampl9']['hosts_in_challenge'])

    def test_the_pdb_entries_counted_are_the_ones_rcsb_confirmed(self):
        self.assertEqual(PUBLISHED['rcsb_pdb']['distinct_entries'], len(PUBLISHED['rcsb_pdb']['entries']))
        for entry in PUBLISHED['rcsb_pdb']['entries']:
            self.assertIn(entry, FACTS['entries'], entry)

    def test_the_strata_are_the_ones_the_subdomain_tree_declares(self):
        """B1 says it takes a representative per EC class, so all seven classes have to be reported --
        including the ones with nothing in them, which is the whole point of the measurement."""
        tree = json.loads((ROOT / 'templates/subdomain-draft.json').read_text(encoding='utf-8'))
        b1 = next(o for d in tree['domains'] for o in d['l1'] if o['id'] == 'B1')
        self.assertIn('EC', b1['selection_criterion'])
        self.assertEqual([s['ec'] for s in PUBLISHED['rcsb_pdb']['ec_strata']], list('1234567'))


class DocumentTests(unittest.TestCase):
    def headline(self, pattern):
        found = re.search(pattern, DOC)
        self.assertIsNotNone(found, '文档里找不到：' + pattern)
        return int(found.group(1).replace(' ', '').replace(',', ''))

    def test_the_document_quotes_the_computed_numbers(self):
        self.assertEqual(self.headline(r'\| RCSB PDB \| (\d+) \|'), PUBLISHED['questions_by_source']['rcsb_pdb'])
        self.assertEqual(self.headline(r'\| COD \| (\d+) \|'), PUBLISHED['questions_by_source']['cod'])
        self.assertEqual(self.headline(r'\| QM7-X \| (\d+) \|'), PUBLISHED['questions_by_source']['qm7x'])
        self.assertEqual(self.headline(r'\*\*合计\*\* \| \*\*(\d+)\*\*'), PUBLISHED['questions_total'])
        self.assertEqual(self.headline(r'用到的条目 \| \*\*(\d+) 个\*\*'), PUBLISHED['rcsb_pdb']['distinct_entries'])
        self.assertEqual(self.headline(r'不同空间群 \| \*\*(\d+) / 230\*\*'), PUBLISHED['cod']['space_groups_used'])
        self.assertEqual(self.headline(r'用到的分子 \| \*\*(\d+) 个\*\*'), PUBLISHED['qm7x']['distinct_molecules'])

    def test_an_empty_stratum_is_named_in_the_document(self):
        empty = [s for s in PUBLISHED['rcsb_pdb']['ec_strata'] if not s['ours']]
        self.assertTrue(empty, '若将来补齐了，这条测试要跟着改')
        lines = DOC.splitlines()
        for stratum in empty:
            # the EC table's rows start with the bare class number, as "| 2 转移酶 | 45 156 | **0** | ✗ **空缺** |"
            row = [l for l in lines
                   if l.startswith('| %s ' % stratum['ec']) and '**0**' in l and '空缺' in l]
            self.assertTrue(row, 'EC %s 是空的，文档必须把它列为空缺' % stratum['ec'])

    def test_the_document_separates_itself_from_the_licence_audit(self):
        self.assertIn('LICENSING.md', DOC)
        self.assertIn('许可', DOC)

    def test_the_document_explains_why_coverage_is_measured_over_strata(self):
        self.assertIn('分层', DOC)
        self.assertIn('0.02%', DOC)          # the number that makes the naive reading useless

    def test_the_document_names_the_alternatives_the_advisor_asked_about(self):
        for alternative in ('CSD', 'ICSD', 'AlphaFold', 'PubChem', 'QM9', 'Materials Project'):
            self.assertIn(alternative, DOC, alternative + ' 没有写为什么没用')

    def test_the_gaps_are_the_same_four_in_the_document_and_on_the_site(self):
        site = json.loads((ROOT / 'docs/content/sources.json').read_text(encoding='utf-8'))
        self.assertEqual(len(site['gaps']), 4)
        for gap in site['gaps']:
            for field in ('zh', 'en'):
                self.assertTrue(gap[field].strip())
        self.assertIn('四个诚实的缺口', DOC)


class SitePageTests(unittest.TestCase):
    def test_the_legend_page_has_a_sources_section_that_reads_the_computed_file(self):
        html = (ROOT / 'docs/legend.html').read_text(encoding='utf-8')
        js = (ROOT / 'docs/legend.js').read_text(encoding='utf-8')
        self.assertIn('id="sources"', html)
        self.assertIn('DATA_SOURCES.md', html)                 # the full argument is one click away
        self.assertIn("fetch('data/source-coverage.json')", js)
        self.assertIn('ec_strata', js)

    def test_every_source_on_the_site_says_why_covers_misses_and_alternatives(self):
        site = json.loads((ROOT / 'docs/content/sources.json').read_text(encoding='utf-8'))
        self.assertEqual(site['status'], 'draft')
        keys = {s['key'] for s in site['sources']}
        self.assertTrue({'rcsb_pdb', 'cod', 'qm7x', 'sampl9', 'papers'} <= keys)
        for source in site['sources']:
            for field in ('why', 'covers', 'misses', 'alternatives'):
                for lang in ('zh', 'en'):
                    self.assertTrue(source['%s_%s' % (field, lang)].strip(), (source['key'], field, lang))


if __name__ == '__main__':
    unittest.main()
