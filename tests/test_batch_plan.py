"""Batch-selection rule (provisional) and its gap analysis."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import batch_plan  # noqa: E402

RULE = json.loads((ROOT / 'templates/batch-selection-rule.json').read_text(encoding='utf-8'))
PLAN = json.loads((ROOT / 'docs/data/batch-plan.json').read_text(encoding='utf-8'))


class RuleTests(unittest.TestCase):
    def test_every_cell_has_a_tier_and_targets_add_up(self):
        cells = {'%s %s' % (d, b) for d in ('quantum', 'chemistry', 'materials', 'biology') for b in ('0.1-1', '1-10', '10-100', '100-1000')}
        self.assertEqual(set(RULE['cells']), cells)
        self.assertEqual(sum(RULE['tiers'][t]['target'] for t in RULE['cells'].values()), 1230)
        self.assertEqual(RULE['status'], 'provisional')

    def test_caps_can_reach_the_target(self):
        for name, t in RULE['tiers'].items():
            self.assertGreaterEqual(t['max_per_family'] * t['min_families'], t['target'], name)
            self.assertGreaterEqual(t['max_per_source'] * t['min_sources'], t['target'], name)
            self.assertLessEqual(t['max_per_family_source'], min(t['max_per_family'], t['max_per_source']), name)


class FlowTests(unittest.TestCase):
    CAPS = dict(max_per_family=5, max_per_source=3, max_per_family_source=2)

    def test_all_three_caps_act_together(self):
        pairs = {('f1', 's1'): 10, ('f1', 's2'): 10, ('f1', 's3'): 10, ('f2', 's1'): 10, ('f2', 's2'): 1}
        total, fams, srcs = batch_plan.max_flow(pairs, self.CAPS, 100)
        # pairs <= 2 each; sources s1, s2 <= 3 and s3 <= 2 (one pair) give at most 8; e.g. f1: 1 + 2 + 2, f2: 2 + 1.
        self.assertEqual(total, 8)
        self.assertEqual(sum(fams.values()), 8)
        self.assertTrue(all(v <= 5 for v in fams.values()))
        self.assertTrue(all(v <= 3 for v in srcs.values()))

    def test_target_caps_the_total(self):
        pairs = {('f%d' % i, 's%d' % j): 9 for i in range(5) for j in range(5)}
        self.assertEqual(batch_plan.max_flow(pairs, self.CAPS, 12)[0], 12)


class PublishedPlanTests(unittest.TestCase):
    def test_plan_is_current(self):
        self.assertEqual(batch_plan.plan(), PLAN)       # rerun tools/batch_plan.py after catalog, capacity or rule changes

    def test_plan_never_exceeds_targets(self):
        for c in PLAN['cells']:
            self.assertLessEqual(c['max_balanced'], c['max_selectable'])
            self.assertLessEqual(c['max_selectable'], c['target'])
            self.assertEqual(c['meets_rule'], not c['gaps'])


if __name__ == '__main__':
    unittest.main()
