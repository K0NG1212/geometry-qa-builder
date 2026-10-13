"""Draft sub-domain taxonomy (templates/subdomain-draft.json) and its pixel map (tools/subdomain_map.py)."""
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import subdomain_map  # noqa: E402

TAX = json.loads((ROOT / 'templates/subdomain-draft.json').read_text(encoding='utf-8'))


class TaxonomyTests(unittest.TestCase):
    def test_six_subdomains_per_domain_with_complete_fields(self):
        self.assertEqual(TAX['status'], 'draft')
        self.assertEqual(Counter(s['domain'] for s in TAX['subdomains']),
                         {'quantum': 6, 'chemistry': 6, 'materials': 6, 'biology': 6})
        ids = [s['id'] for s in TAX['subdomains']]
        self.assertEqual(len(ids), len(set(ids)))
        for s in TAX['subdomains']:
            self.assertTrue(s['scales'] and set(s['scales']) <= set(subdomain_map.SCALES), s['id'])
            for k in ('name', 'scope', 'question_types', 'data_sources', 'selection_criterion'):
                self.assertTrue(s[k].strip(), (s['id'], k))

    def test_paper_routes_point_to_subdomains_of_the_same_domain(self):
        domain = {s['id']: s['domain'] for s in TAX['subdomains']}
        for d, routes in TAX['paper_routes'].items():
            self.assertTrue(all(domain[v] == d for v in routes.values()), d)


class PixelMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = subdomain_map.build()

    def test_every_active_question_lands_in_a_meaningful_pixel_of_its_domain(self):
        s = self.map['summary']
        self.assertEqual(s['questions_outside_meaningful_pixels'], [])
        self.assertEqual(sum(p['questions'] for p in self.map['pixels']), s['active_questions'])
        for p in self.map['pixels']:
            self.assertEqual(sum(p['abilities'].values()), p['questions'])

    def test_object_not_technique(self):
        assign = subdomain_map.Assigner(TAX)
        self.assertEqual(assign.biology('1UBQ', 'fret_efficiency'), 'B1')
        self.assertEqual(assign.biology('1EHZ', 'fret_efficiency'), 'B3')
        self.assertEqual(assign.biology('1UBQ', 'fret_design'), 'B2')
        self.assertEqual(assign.biology('6CGR', 'assembly_extent'), 'B4')

    def test_published_map_matches_the_repository(self):
        published = json.loads((ROOT / subdomain_map.OUT).read_text(encoding='utf-8'))
        self.assertEqual(published, json.loads(json.dumps(self.map)))


if __name__ == '__main__':
    unittest.main()
