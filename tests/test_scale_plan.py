"""The 3000-question arithmetic must stay the data's arithmetic, not a number someone remembered.

The earlier version of this table was written by hand into a handoff and two of its figures had already
drifted (39 molecule structures where the run has 36; "about 330 structures" where today's per-structure
yield needs 420). These tests recompute the three ceilings from the published data and pin the meeting sheet
to them, so a stale number cannot be shown at a meeting again.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import export_scale_plan as scale  # noqa: E402

PLAN = json.loads((ROOT / 'docs/data/scale-plan.json').read_text(encoding='utf-8'))
CAPACITY = json.loads((ROOT / 'docs/data/enumeration-capacity.json').read_text(encoding='utf-8'))
BATCH = json.loads((ROOT / 'docs/data/batch-plan.json').read_text(encoding='utf-8'))
CATALOG = json.loads((ROOT / 'docs/data/catalog.json').read_text(encoding='utf-8'))
MEETING = (ROOT / 'MEETING_2026-11-04.md').read_text(encoding='utf-8')
ADMITTED = [q for q in CATALOG['questions'] if q.get('lifecycle') == 'active' and q.get('familyInstance')]


class ArithmeticTests(unittest.TestCase):
    def test_the_source_cap_is_recomputed_from_the_enumeration_rows(self):
        per_structure = {}
        for row in CAPACITY['rows']:
            per_structure[row['structure']] = per_structure.get(row['structure'], 0) + row['estimated_admissible']
        for cap in PLAN['source_caps']:
            self.assertEqual(cap['structures'], len(per_structure))
            self.assertEqual(cap['questions'], sum(min(cap['max_per_source'], v) for v in per_structure.values()))
            # The structures needed follow from today's yield per structure, not from the cap itself: a cap of
            # 8 does not mean every structure gives 8.
            self.assertEqual(cap['structures_for_target'], round(PLAN['target'] / cap['per_structure']))
            self.assertLess(cap['questions'], PLAN['target'])        # which is the point of the table

    def test_the_structure_count_matches_the_rows_not_the_listed_groups(self):
        # The capacity file lists its structures in four groups; the rows hold three more than the groups do,
        # and the rows are what the yield is computed over.
        self.assertEqual(PLAN['enumeration']['structures'], len({r['structure'] for r in CAPACITY['rows']}))
        self.assertEqual(PLAN['enumeration']['structures_by_kind'],
                         {k: len(v) for k, v in CAPACITY['structures'].items()})

    def test_the_family_ceiling_leaves_the_target_no_slack(self):
        cap = PLAN['family_cap']
        self.assertEqual(cap['max_per_family'], BATCH['rule']['global']['max_per_family'])
        self.assertEqual(cap['ceiling'], cap['max_per_family'] * cap['families'])
        self.assertEqual(cap['enumerable_ceiling'], cap['max_per_family'] * cap['enumerable_families'])
        self.assertEqual(cap['enumerable_families'], len({r['family'] for r in CAPACITY['rows']}))
        self.assertEqual(cap['enumerable_families'] + len(cap['database_without_enumerator'])
                         + cap['paper_driven'], cap['families'])      # every family is in exactly one group

    def test_the_paper_arithmetic_counts_only_hand_made_cards(self):
        papers = PLAN['papers']
        self.assertEqual(papers['questions'],
                         sum(1 for q in ADMITTED if q['paper'] not in scale.DATABASES))
        self.assertEqual(papers['papers'],
                         len({q['paper'] for q in ADMITTED if q['paper'] not in scale.DATABASES}))
        self.assertEqual(papers['papers_at_share'], round(papers['questions_at_share'] / papers['per_paper']))
        self.assertGreater(papers['papers_at_share'], 100)            # 30% from papers is out of reach

    def test_the_bank_and_the_gap_agree_with_the_catalog(self):
        self.assertEqual(PLAN['bank']['questions'], len(ADMITTED))
        self.assertEqual(PLAN['gap'], PLAN['target'] - len(ADMITTED))
        self.assertEqual(PLAN['selection_rule']['target'], BATCH['summary']['target'])
        self.assertNotEqual(PLAN['selection_rule']['target'], PLAN['target'])   # R1 still has to be done


class MeetingSheetTests(unittest.TestCase):
    def test_the_sheet_carries_the_generated_table_between_its_markers(self):
        self.assertIn(scale.BEGIN, MEETING)
        self.assertIn(scale.END, MEETING)
        block = MEETING.split(scale.BEGIN)[1].split(scale.END)[0]
        self.assertEqual(block.strip(), scale.table(PLAN).strip())

    def test_the_numbers_quoted_in_the_prose_are_the_computed_ones(self):
        caps = {c['max_per_source']: c for c in PLAN['source_caps']}
        for number in (PLAN['bank']['questions'], PLAN['target'],
                       caps[8]['structures_for_target'], caps[15]['structures_for_target'],
                       caps[8]['more_structures_needed'], PLAN['papers']['papers_at_share']):
            self.assertIn(str(number), MEETING, number)

    def test_rebuilding_the_plan_changes_nothing(self):
        built = scale.build()
        for key in sorted(set(built) | set(PLAN)):
            if key == 'date':
                continue
            self.assertEqual(built[key], PLAN[key], 'docs/data/scale-plan.json 过期：%s' % key)


if __name__ == '__main__':
    unittest.main()
