"""The question-generation system page (docs/system.html) is generated from the repository and must not drift."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import export_system  # noqa: E402
from task_families import FAMILIES  # noqa: E402

PUBLISHED = json.loads((ROOT / 'docs/data/system.json').read_text(encoding='utf-8'))


class SystemPageTests(unittest.TestCase):
    def test_published_data_matches_the_repository(self):
        self.assertEqual(export_system.build(), PUBLISHED)      # rerun tools/export_system.py after changing code or data

    def test_every_family_has_a_checker_route_and_registry_row(self):
        self.assertEqual({f['id'] for f in PUBLISHED['families']}, set(FAMILIES))
        for f in PUBLISHED['families']:
            self.assertTrue(f['checker'] and f['registry_id'], f['id'])
            self.assertIn(f['route'], PUBLISHED['routes'])

    def test_step_files_exist(self):
        for s in PUBLISHED['steps']:
            for f in s['files']:
                self.assertFalse(f.get('missing'), f['path'])

    def test_page_claims_no_model_calls(self):
        self.assertEqual(PUBLISHED['summary']['model_calls'], 0)
        self.assertEqual(PUBLISHED['summary']['independent_passed'], PUBLISHED['summary']['independent_checked'])


if __name__ == '__main__':
    unittest.main()
