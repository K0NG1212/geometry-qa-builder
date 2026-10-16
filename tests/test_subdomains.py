"""Draft two-level sub-domain tree (templates/subdomain-draft.json) and its pixel map (tools/subdomain_map.py)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import subdomain_map  # noqa: E402

TAX = json.loads((ROOT / 'templates/subdomain-draft.json').read_text(encoding='utf-8'))
TREE = subdomain_map.Tree(TAX)


class TreeTests(unittest.TestCase):
    def test_two_levels_with_complete_fields(self):
        self.assertEqual(TAX['status'], 'draft')
        self.assertEqual([d['id'] for d in TAX['domains']], ['physics', 'chemistry', 'materials', 'biology'])
        ids = [x['id'] for d in TAX['domains'] for x in d['l1']] + list(TREE.leaf)
        self.assertEqual(len(ids), len(set(ids)))
        for d in TAX['domains']:
            self.assertGreaterEqual(len(d['l1']), 6, d['id'])
            for one in d['l1']:
                self.assertTrue(one['scales'] and set(one['scales']) <= set(subdomain_map.SCALES), one['id'])
                self.assertGreaterEqual(len(one['leaves']), 2, one['id'])
                for k in ('name', 'data_sources', 'selection_criterion'):
                    self.assertTrue(one[k].strip(), (one['id'], k))
                self.assertTrue(all(leaf['id'].startswith(one['id']) and leaf['name'] for leaf in one['leaves']))

    def test_assignment_targets_are_leaves(self):
        a = TAX['assignment']
        for table in ('pdb', 'cod', 'cod_names', 'family', 'paper'):
            self.assertTrue(set(a[table].values()) <= set(TREE.leaf), table)


class PixelMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = subdomain_map.build()

    def test_every_active_question_lands_in_a_meaningful_pixel(self):
        s = self.map['summary']
        self.assertEqual(s['questions_outside_meaningful_pixels'], [])
        self.assertEqual(sum(p['questions'] for p in self.map['pixels']), s['active_questions'])
        self.assertEqual(sum(p['questions'] for p in self.map['leaves']), s['active_questions'])

    def test_object_not_technique(self):
        def leaf(**q):
            return TREE.question(dict(dict(id='T', question='', answer='', source='', paper='pdb-bio-nm', family='fret_efficiency',
                                           domain='biology'), **q))
        self.assertEqual(leaf(title='溶菌酶 6LYZ · 两端 FRET 效率'), 'B1a')
        self.assertEqual(leaf(title='tRNA 1EHZ · A76–A35 FRET 效率'), 'B7b')
        self.assertEqual(leaf(title='HSV-1 衣壳 6CGR · 六邻体数', family='capsid_architecture'), 'B6a')
        self.assertEqual(TREE.question(dict(id='T', title='QM7-X 7029 转动', question='', answer='', source='', paper='qm7x',
                                            family='rotational_line', domain='quantum')), 'P5a')

    def test_map_carries_the_tree_and_every_question_title(self):
        self.assertEqual([d['id'] for d in self.map['tree']], [d['id'] for d in TAX['domains']])
        leaves = [lf['id'] for d in self.map['tree'] for one in d['l1'] for lf in one['leaves']]
        self.assertEqual(leaves, list(TREE.leaf))
        ids = {i for p in self.map['leaves'] for i in p['ids']}
        self.assertEqual(set(self.map['titles']), ids)
        self.assertTrue(all(t and a in ('perception', 'inference', 'design') for t, a in self.map['titles'].values()))

    def test_sunburst_page_is_linked_and_reads_the_map(self):
        page = (ROOT / 'docs/subdomains.html').read_text(encoding='utf-8')
        self.assertIn('subdomains.js', page)
        self.assertIn('data/subdomain-map.json', (ROOT / 'docs/subdomains.js').read_text(encoding='utf-8'))
        for nav in ('index.html', 'cards.html', 'system.html'):
            self.assertIn('href="subdomains.html"', (ROOT / 'docs' / nav).read_text(encoding='utf-8'), nav)

    def test_published_map_matches_the_repository(self):
        published = json.loads((ROOT / subdomain_map.OUT).read_text(encoding='utf-8'))
        self.assertEqual(published, json.loads(json.dumps(self.map)))


if __name__ == '__main__':
    unittest.main()
