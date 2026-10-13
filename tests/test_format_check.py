"""Format check list (tools/format_check.py -> docs/data/format-check.json)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import format_check  # noqa: E402


class FormatCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = format_check.build()
        cls.items = {x['id']: x for x in cls.data['items']}

    def test_published_list_matches_the_repository(self):
        published = json.loads((ROOT / format_check.OUT).read_text(encoding='utf-8'))
        self.assertEqual(published, json.loads(json.dumps(self.data)))

    def test_every_open_card_is_flagged_high_with_a_suggestion(self):
        cards = json.loads((ROOT / 'docs/data/cards.json').read_text(encoding='utf-8'))['cards']
        for c in cards:
            if c['format'] == 'open':
                x = self.items[c['id']]
                self.assertEqual(x['worst'], 'high', c['id'])
                self.assertTrue(x['suggestion'], c['id'])

    def test_rules_on_known_cases(self):
        rules = lambda qid: {i['rule'] for i in self.items[qid]['issues']}
        self.assertIn('duplicate', rules('CNP005'))
        self.assertIn('formula_given', rules('MNP008'))
        self.assertIn('multi_part', rules('HBP002'))
        self.assertNotIn('multi_part', rules('BNP008'))          # one distance, rubric "3 points" for one item
        self.assertIn('two_binaries_combined', rules('CNI007'))
        self.assertIn('mirror_pair', rules('QNP001'))
        self.assertTrue(set(format_check.REVIEWED) <= set(self.items))

    def test_no_control_characters_in_the_tool(self):
        text = (ROOT / 'tools/format_check.py').read_text(encoding='utf-8')
        self.assertFalse([c for c in text if ord(c) < 32 and c not in '\n'])


if __name__ == '__main__':
    unittest.main()
