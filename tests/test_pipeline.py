import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline as p
from test_builder import fixtures


class ModularTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run = self.root/'run'
        self.bundle, self.stages = fixtures()
        self.plan = copy.deepcopy(self.stages['qa'])
        for item in self.plan['items']:
            del item['answer_numeric']; del item['reference_answer']
            item['answer_text'] = None
        self.units = {'assets': [{'source_id': 'S0002', 'unit': 'angstrom',
            'source_refs': self.stages['evidence']['records'][0]['source_refs'],
            'checked_by': 'handwritten fixture', 'notes': 'Synthetic test only'}]}
        self.start()

    def start(self, units=True):
        p.b.write(self.root/'bundle.json', self.bundle)
        p.b.write(self.root/'units.json', self.units)
        p.init(self.root/'bundle.json', self.run, self.root/'units.json' if units else None)

    def tearDown(self):
        self.tmp.cleanup()

    def submit(self, data=None):
        request = p.packet(self.run)
        module = request['module']
        if data is None:
            data = self.plan if module == 'construction' else self.stages[module]
        path = self.root/'result.json'; p.b.write(path, data)
        return p.accept(self.run, path, 'handwritten-fixture', request['context_hash'], fixture=True)

    def prefix(self):
        self.submit(); self.submit()

    def test_complete_and_private_export(self):
        for _ in range(4): self.submit()
        p.export(self.run)
        qa = p.b.read(self.run/'qa.json')['data']['items'][0]
        self.assertEqual(qa['answer_numeric'], 2)
        inputs = p.b.read(self.run/'model-inputs.json')
        self.assertNotIn('reference_answer', json.dumps(inputs))
        self.assertNotIn('answer_refs', json.dumps(inputs))
        self.assertNotIn('Synthetic, not a physical equilibrium structure', json.dumps(inputs))
        self.assertFalse(p.b.read(self.run/'quality-report.json')['review_independent'])

    def test_resume_preserves_evidence_bytes(self):
        self.submit()
        before = (self.run/'evidence.json').read_bytes()
        self.assertEqual(p.packet(self.run)['module'], 'tasks')
        self.assertEqual(before, (self.run/'evidence.json').read_bytes())

    def test_stale_packet_rejected(self):
        old = p.packet(self.run)['context_hash']; self.submit()
        with self.assertRaisesRegex(ValueError, 'stale'):
            p.accept(self.run, self.root/'result.json', 'fixture', old)
        self.assertEqual(p.status(self.run)['next'], 'tasks')

    def test_bad_quote_recorded_and_retry(self):
        bad = copy.deepcopy(self.stages['evidence'])
        bad['records'][0]['source_refs'][0]['quote'] = 'invented quotation'
        with self.assertRaisesRegex(ValueError, 'quotation'): self.submit(bad)
        self.assertEqual(p.status(self.run)['failed_attempts'], 1)
        self.assertEqual(p.status(self.run)['next'], 'evidence')
        self.submit()

    def test_missing_units_blocks_numeric_construction(self):
        self.run = self.root/'no-units'; self.start(units=False)
        self.prefix()
        with self.assertRaisesRegex(ValueError, 'units unresolved'): self.submit()
        self.assertFalse((self.run/'qa.json').exists())

    def test_numeric_ai_answer_not_allowed(self):
        self.prefix(); self.plan['items'][0]['answer_text'] = '2 angstrom'
        with self.assertRaisesRegex(ValueError, 'must come from code'): self.submit()

    def test_invalid_indices_fail_without_qa(self):
        self.prefix(); self.plan['items'][0]['verifier']['atom_indices'] = [0, 2]
        with self.assertRaisesRegex(ValueError, 'indices'): self.submit()
        self.assertFalse((self.run/'qa.json').exists())

    def test_wrong_output_units_fail(self):
        self.prefix(); self.plan['items'][0]['units'] = 'nm'
        with self.assertRaisesRegex(ValueError, 'units'): self.submit()

    def test_prompt_change_detected(self):
        (self.run/'modules/evidence.md').write_text('different', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'snapshot'): p.status(self.run)

    def test_receipt_tamper_detected(self):
        self.prefix(); self.submit()
        receipt = p.b.read(self.run/'construction-receipt.json')
        receipt['plan']['items'][0]['question'] = 'changed'
        p.b.write(self.run/'construction-receipt.json', receipt)
        with self.assertRaisesRegex(ValueError, 'plan changed'): p.status(self.run)

    def test_fork_keeps_parent_and_invalidates_descendants(self):
        for _ in range(4): self.submit()
        p.export(self.run)
        before = (self.run/'qa.json').read_bytes()
        target = self.root/'branch'
        result = p.fork(self.run, target, 'construction')
        self.assertEqual(result['next'], 'construction')
        self.assertTrue((target/'tasks.json').exists())
        self.assertFalse((target/'qa.json').exists())
        self.assertFalse((target/'model-inputs.json').exists())
        self.assertEqual((self.run/'qa.json').read_bytes(), before)

    def test_incomplete_export_rejected(self):
        with self.assertRaisesRegex(ValueError, 'four complete'): p.export(self.run)

    def test_fork_inside_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            p.fork(self.run, self.run/'nested', 'evidence')

    def test_published_contracts_match_runtime(self):
        self.assertEqual(p.b.read(p.ROOT/'modules/construction.schema.json'), p.PLAN)
        self.assertEqual(p.b.read(p.ROOT/'modules/asset-units.schema.json'), p.UNITS)

    def test_frozen_runner_works(self):
        result = subprocess.run([sys.executable, str(self.run/'pipeline_snapshot.py'),
            'status', '--run', str(self.run)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['next'], 'evidence')

    def test_empty_output_not_certified(self):
        self.stages = {'evidence': {'records': [], 'exclusions': ['No evidence']},
            'tasks': {'tasks': [], 'exclusions': ['No tasks']}, 'review': {'reviews': []}}
        self.plan = {'items': [], 'exclusions': ['No usable input']}
        for _ in range(4): self.submit()
        p.export(self.run)
        self.assertEqual(p.status(self.run)['accepted_candidates'], 0)
        self.assertFalse(p.status(self.run)['benchmark_ready'])

    def test_review_failure_survives_export(self):
        self.stages['review']['reviews'][0]['checks']['geometry_required'] = False
        for _ in range(4): self.submit()
        p.export(self.run)
        self.assertEqual(p.b.read(self.run/'report.json')['items'][0]['status'], 'needs_revision')

    def test_malformed_json_is_logged(self):
        (self.root/'broken.json').write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            p.accept(self.run, self.root/'broken.json', 'unknown', p.packet(self.run)['context_hash'])
        self.assertEqual(p.status(self.run)['failed_attempts'], 1)
        failure = next((self.run/'attempts-v02').glob('*.json'))
        self.assertEqual(p.b.read(failure)['raw_result'], '{broken')

    def test_concurrent_import_blocked(self):
        (self.run/'.accept.lock').write_text('another process')
        with self.assertRaisesRegex(ValueError, 'another import'):
            self.submit()
        self.assertFalse((self.run/'evidence.json').exists())

    def test_orphan_stage_rejected(self):
        self.prefix()
        (self.run/'evidence.json').unlink()
        with self.assertRaisesRegex(ValueError, 'orphan'): p.status(self.run)


if __name__ == '__main__':
    unittest.main()
