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
        # Rubric item counting on the texts of two former legacy questions (HBP002 several items; BNP011 one item).
        self.assertEqual(format_check.scored_items('1 point per distance (4); 1 for both classifications; 1 for distinguishing'), 3)
        self.assertEqual(format_check.scored_items('3 points: distance (3; 0.01 angstrom tolerance).'), 1)
        self.assertIn('two_binaries_combined', rules('CNI007'))
        self.assertIn('mirror_pair', rules('QNI024'))          # four-choice successor of QNP001 (2026-10-14)
        catalog = json.loads((ROOT / 'docs/data/catalog.json').read_text(encoding='utf-8'))['questions']
        active = {q['id'] for q in catalog if q['lifecycle'] == 'active'}
        self.assertTrue((set(format_check.REVIEWED) & active) <= set(self.items))
        retired = {q['id']: q for q in catalog if q['id'] in ('CNP005', 'MNP008', 'MNP009', 'HBI001', 'BNP011')}
        self.assertEqual(len(retired), 5)
        self.assertTrue(all(q['lifecycle'] == 'archived' and '格式检查' in q['lifecycleReason'] for q in retired.values()))

    def test_no_control_characters_in_the_tool(self):
        text = (ROOT / 'tools/format_check.py').read_text(encoding='utf-8')
        self.assertFalse([c for c in text if ord(c) < 32 and c not in '\n'])


if __name__ == '__main__':
    unittest.main()
