import copy
import json
import unittest
from collections import Counter
from pathlib import Path

from tools.admit_family_instances import admit
from tools.plan_coverage import plan
from builder_modules.m0_scope.coverage import summarize

ROOT = Path(__file__).resolve().parents[1]
read = lambda p: json.loads((ROOT / p).read_text(encoding='utf-8'))
CATALOG = read('docs/data/catalog.json')
WORKBENCH = read('docs/data/family-workbench.json')
INDEPENDENT = read('docs/data/independent-check.json')
AMAP = read('templates/admission-map.json')
POLICY = read('builder_modules/m0_scope/prototype-policy.json')
REGISTRY = read('templates/registry.json')
BY_ID = {q['id']: q for q in CATALOG['questions']}


class AdmissionMapTests(unittest.TestCase):
    def test_every_instance_mapped_once_and_counts_deduplicated(self):
        instances = [e['instance'] for e in AMAP['instances']]
        self.assertEqual(Counter(instances), Counter(t['id'] for t in WORKBENCH['teacher_answers']))
        actions = Counter(e['action'] for e in AMAP['instances'])
        self.assertEqual(actions['reformat'], 18)
        # Only new and supersede entries create counted records; the 42 screened legacy items stay.
        counted = [q for q in CATALOG['questions'] if q.get('familyInstance') and q['lifecycle'] == 'active']
        self.assertEqual(len(counted), actions['new'] + actions['supersede'])
        self.assertEqual(CATALOG['lifecycleCounts']['active'], 42 + actions['new'] + actions['supersede'])

    def test_new_records_are_complete_and_provisional(self):
        for e in AMAP['instances']:
            if e['action'] == 'reformat':
                continue
            q = BY_ID[e['catalog_id']]
            self.assertEqual(q['admission'], 'provisional_auto_verified')
            self.assertEqual((q['lifecycle'], q['status'], q['prototypeScreeningPassed']), ('active', 'pending_human_audit', True))
            self.assertEqual(q['independentCheck'], 'pass')
            for field in ['question', 'completeInput', 'answer', 'rubric', 'source', 'learningObjective', 'attachments']:
                self.assertTrue(q[field], (q['id'], field))
            for a in q['attachments']:
                self.assertTrue((ROOT / 'docs' / a['url']).is_file(), a['url'])
            self.assertTrue((ROOT / 'docs' / q['inputDownload']).is_file())
            self.assertGreater(q['reasoningSizeNm'], 0)
            if q['ability'] == 'design':      # dataset ids would let a model look the property up
                self.assertNotIn('Geom-', (ROOT / 'docs' / q['inputDownload']).read_text(encoding='utf-8'))

    def test_superseded_and_reformatted_legacy_records(self):
        for e in AMAP['instances']:
            if e['action'] == 'supersede':
                old = BY_ID[e['supersedes']]
                self.assertEqual((old['lifecycle'], old['supersededBy']), ('archived', e['catalog_id']))
            if e['action'] == 'reformat':
                legacy = BY_ID[e['catalog_id']]
                self.assertEqual(legacy['lifecycle'], 'active')
                links = [v for v in legacy['familyVersions'] if v['instance'] == e['instance']]
                self.assertEqual(len(links), 1)
                self.assertFalse(links[0]['counted'])

    def test_admission_is_idempotent_and_guarded(self):
        once, files = admit(CATALOG, WORKBENCH, INDEPENDENT, AMAP, CATALOG['updated'])
        self.assertEqual(once, CATALOG)
        for rel, text in files.items():
            self.assertEqual((ROOT / 'docs' / rel).read_text(encoding='utf-8'), text)
        failed = copy.deepcopy(INDEPENDENT)
        failed['results'][0]['status'] = 'fail'
        with self.assertRaisesRegex(ValueError, 'independent checker'):
            admit(CATALOG, WORKBENCH, failed, AMAP, '2026-09-29')
        dup = copy.deepcopy(AMAP)
        dup['instances'].append(dict(dup['instances'][0]))
        with self.assertRaisesRegex(ValueError, 'exactly once'):
            admit(CATALOG, WORKBENCH, INDEPENDENT, dup, '2026-09-29')
        bad = copy.deepcopy(AMAP)
        next(e for e in bad['instances'] if e['action'] == 'reformat')['catalog_id'] = 'QNP002'   # rework, not active
        with self.assertRaisesRegex(ValueError, 'Reformat target'):
            admit(CATALOG, WORKBENCH, INDEPENDENT, bad, '2026-09-29')


class CoveragePlanTests(unittest.TestCase):
    def test_plan_matches_progress_and_routes(self):
        result = plan(CATALOG, POLICY, REGISTRY)
        progress = summarize(CATALOG, POLICY)
        self.assertEqual(len(result['cells']), 16)
        self.assertEqual(result['summary']['current_total'], progress['screened_total'])
        self.assertEqual(result['summary']['provisional_total'],
                         sum(e['action'] != 'reformat' for e in AMAP['instances']))
        self.assertEqual(read('docs/data/coverage-plan.json'), result)
        cell = next(c for c in result['cells'] if c['domain'] == 'biology' and c['cell'] == '0.1-1')
        self.assertIn('backbone_torsion', [r['family'] for r in cell['abilities']['perception']['routes']])
        for c in result['cells']:
            for ability, v in c['abilities'].items():
                for r in v['routes']:
                    t = next(x for x in REGISTRY['templates'] if x['id'] == r['family'])
                    self.assertEqual(t['ability'], ability)
                    self.assertIn(c['domain'], t['domains'])
                    self.assertIn(c['cell'], t['scale_cells'])
                    if r['kind'] == 'ready':
                        self.assertTrue(t['independent_checker'])
        large = [c for c in result['cells'] if c['cell'] in ('10-100', '100-1000')]
        self.assertTrue(all(v['best_route'] == 'none' for c in large for v in c['abilities'].values()))


if __name__ == '__main__':
    unittest.main()
