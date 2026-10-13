"""Question cards page (docs/cards.html) and its data (tools/export_cards.py -> docs/data/cards.json)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import export_cards  # noqa: E402


class CardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = export_cards.build()

    def test_published_cards_match_the_repository(self):
        published = json.loads((ROOT / export_cards.OUT).read_text(encoding='utf-8'))
        self.assertEqual(published, json.loads(json.dumps(self.data)))

    def test_one_card_per_active_question(self):
        catalog = json.loads((ROOT / 'docs/data/catalog.json').read_text(encoding='utf-8'))['questions']
        active = {q['id'] for q in catalog if q['lifecycle'] == 'active'}
        self.assertEqual({c['id'] for c in self.data['cards']}, active)
        self.assertEqual(self.data['choice'] + self.data['open'], len(active))

    def test_choice_cards_have_four_options_a_key_and_a_reason_for_each(self):
        for c in self.data['cards']:
            if c['format'] != 'choice':
                self.assertTrue(c['answer'] and c['legacy'], c['id'])
                continue
            self.assertEqual([o['label'] for o in c['options']], list('ABCD'), c['id'])
            self.assertIn(c['correct'], 'ABCD')
            self.assertEqual(sorted(c['reasons']), list('ABCD'), c['id'])
            self.assertTrue(c['reasons'][c['correct']]['correct'], c['id'])
            self.assertTrue(all(r['reason'] for r in c['reasons'].values()), c['id'])

    def test_attachments_exist_or_are_inlined(self):
        for c in self.data['cards']:
            for f in c['files']:
                if 'url' in f:
                    self.assertTrue((ROOT / 'docs' / f['url']).is_file(), (c['id'], f['url']))
                else:
                    self.assertTrue(f.get('text') or f.get('note'), (c['id'], f['name']))

    def test_page_is_linked_and_loads_its_script(self):
        page = (ROOT / 'docs/cards.html').read_text(encoding='utf-8')
        self.assertIn('cards.js', page)
        self.assertIn('href="cards.html"', (ROOT / 'docs/index.html').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
