import copy
import json
import unittest
from collections import Counter
from pathlib import Path

from tools.admit_family_instances import admit
from tools.extend_admission_map import metadata_overrides, repair_metadata, MIXED_MOLECULE_FAMILIES
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
FEASIBILITY = read('templates/scale-feasibility.json')
BY_ID = {q['id']: q for q in CATALOG['questions']}
MANIFEST = {s['id']: s for s in read('templates/family-manifest.json')['items']}
STRUCTURES = read('templates/structures.json')


class AdmissionMapTests(unittest.TestCase):
    def test_every_instance_mapped_once_and_counts_deduplicated(self):
        instances = [e['instance'] for e in AMAP['instances']]
        self.assertEqual(Counter(instances), Counter(t['id'] for t in WORKBENCH['teacher_answers']))
        actions = Counter(e['action'] for e in AMAP['instances'])
        self.assertEqual(actions['reformat'], 0)       # the 18 reformat links became supersede entries (user, 2026-10-14)
        # Only new and supersede entries create counted records. Of the 42 screened legacy items, those superseded with a
        # stated reason or retired by the format check (2026-10-13) leave the active set; each keeps its reason.
        counted = [q for q in CATALOG['questions'] if q.get('familyInstance') and q['lifecycle'] == 'active']
        self.assertEqual(len(counted), actions['new'] + actions['supersede'])
        left = [e['supersedes'] for e in AMAP['instances'] if e.get('reason')] + [e['id'] for e in AMAP.get('retire', [])]
        self.assertEqual(len(left), len(set(left)))
        for qid in left:
            self.assertEqual(BY_ID[qid]['lifecycle'], 'archived', qid)
            self.assertIn('格式检查', BY_ID[qid]['lifecycleReason'], qid)
        self.assertEqual(CATALOG['lifecycleCounts']['active'], 42 - len(left) + actions['new'] + actions['supersede'])

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
            self.assertEqual((ROOT / 'docs' / rel).read_bytes(), text.encode('utf-8'))   # some legacy assets are CRLF
        failed = copy.deepcopy(INDEPENDENT)
        failed['results'][0]['status'] = 'fail'
        with self.assertRaisesRegex(ValueError, 'independent checker'):
            admit(CATALOG, WORKBENCH, failed, AMAP, '2026-09-29')
        dup = copy.deepcopy(AMAP)
        dup['instances'].append(dict(dup['instances'][0]))
        with self.assertRaisesRegex(ValueError, 'exactly once'):
            admit(CATALOG, WORKBENCH, INDEPENDENT, dup, '2026-09-29')
        bad = copy.deepcopy(AMAP)
        fake = next(e for e in bad['instances'] if e['action'] == 'supersede')
        fake.update(action='reformat', catalog_id='QNP002')     # a reformat link must target an active legacy record
        with self.assertRaisesRegex(ValueError, 'Reformat target'):
            admit(CATALOG, WORKBENCH, INDEPENDENT, bad, '2026-09-29')


class SourceMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rebuilt, _ = admit(CATALOG, WORKBENCH, INDEPENDENT, AMAP, CATALOG['updated'])
        cls.records = {q['familyInstance']: q for q in rebuilt['questions'] if q.get('familyInstance')}

    def test_mixed_molecule_admission_follows_the_registered_source(self):
        molecules = {(r['molecule'], r['asset']): r for r in STRUCTURES['molecules']}
        seen = set()
        for instance, q in self.records.items():
            spec = MANIFEST.get(instance, {})
            if not instance.startswith('EN-') or spec.get('family') not in MIXED_MOLECULE_FAMILIES or not spec.get('molecule'):
                continue
            row = molecules[(spec['molecule'], spec['asset'])]
            sampl9 = 'sampl9' in row['source'].lower()
            expected_paper = 'sampl9' if sampl9 else 'qm7x'
            self.assertEqual((q['domain'], q['paper']), (row['domain'], expected_paper), instance)
            self.assertEqual(q['source'], spec['source'], instance)
            self.assertIn('CC BY 4.0', q['attribution'], instance)
            self.assertIn('SAMPL9' if sampl9 else 'QM7-X', q['attribution'], instance)
            if sampl9:
                self.assertNotIn('QM7-X', q['attribution'], instance)
            seen.add(expected_paper)
        self.assertEqual(seen, {'sampl9', 'qm7x'})

    def test_assembly_admission_uses_the_actual_point_set_and_domain(self):
        assemblies = {r['asset']: r for r in STRUCTURES['assemblies']}
        checked = 0
        for instance, q in self.records.items():
            spec = MANIFEST.get(instance, {})
            if spec.get('asset') not in assemblies or not spec.get('assembly'):
                continue
            row = assemblies[spec['asset']]
            self.assertEqual(q['domain'], row['domain'], instance)
            self.assertEqual(q['paper'], 'pdb-dna-origami' if row['pdb'] == '7ARQ' else 'pdb-bio-nm', instance)
            if 'deposited' in Path(row['asset']).name:
                self.assertIn(row['scope'], q['attribution'], instance)
                self.assertIn('RCSB PDB', q['attribution'], instance)
                self.assertIn('CC0', q['attribution'], instance)
            checked += 1
        self.assertGreater(checked, 0)

    def test_new_dna_fret_metadata_uses_pdb_nucleic_source(self):
        row = next(r for r in STRUCTURES['structures'] if r['kind'] == 'nucleic')
        for family in ('fret_efficiency', 'fret_design'):
            metadata = metadata_overrides(dict(row, id='EN-DNA-FRET-REGRESSION', family=family), STRUCTURES)
            self.assertEqual((metadata['domain'], metadata['paper']), ('chemistry', 'pdb-bio-nm'))
            self.assertIn('RCSB PDB', metadata['attribution'])
            self.assertIn('ATOM', metadata['attribution'])
            self.assertIn('虚拟 FRET', metadata['attribution'])

    def test_repairs_preserve_ids_and_handwritten_scientific_overrides(self):
        spec = next(s for s in MANIFEST.values() if s['id'].startswith('EN-SAMPL9-') and s['family'] in MIXED_MOLECULE_FAMILIES)
        entry = dict(instance=spec['id'], catalog_id='QNP999', action='new', title='kept',
                     learningObjective='hand-written scientific objective', sizeDefinition='hand-written scale definition')
        original = dict(families={}, instances=[entry])
        repaired, changed = repair_metadata(original, {spec['id']: spec}, STRUCTURES)
        got = repaired['instances'][0]
        self.assertEqual((got['instance'], got['catalog_id']), (entry['instance'], 'QNP999'))
        self.assertEqual((got['learningObjective'], got['sizeDefinition']),
                         ('hand-written scientific objective', 'hand-written scale definition'))
        self.assertNotIn('domain', original['instances'][0])
        self.assertEqual(changed, [spec['id']])
        # Stereo tasks retain their scientific chemistry classification even though QM7-X is a quantum dataset.
        self.assertEqual(metadata_overrides(dict(spec, family='stereo_relationship'), STRUCTURES), {})



class CoveragePlanTests(unittest.TestCase):
    def test_plan_matches_progress_and_routes(self):
        result = plan(CATALOG, POLICY, REGISTRY, FEASIBILITY)
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
                    self.assertNotIn('%s %s' % (c['domain'], c['cell']), t.get('excluded_cells', []))
                    if r['kind'] == 'ready':
                        self.assertTrue(t['independent_checker'])
        # Every empty or short cell has a researched feasibility note with sourced options.
        for c in result['cells']:
            if c['current'] < c['target']:
                self.assertIsNotNone(c['feasibility'], (c['domain'], c['cell']))
        for note in FEASIBILITY['cells']:
            self.assertIn(note['route'], FEASIBILITY['evidence_routes'])
            self.assertTrue(all(src['url'].startswith('https://') and src['license'] for src in note['sources']))
        large = [c for c in result['cells'] if c['cell'] in ('10-100', '100-1000')]
        # A4: chemistry and biology large cells have checked routes (design = measurement-q design, pending L1);
        # quantum and materials large cells have none yet.
        for c in large:
            ready = {a for a, v in c['abilities'].items() if v['best_route'] == 'ready'}
            expected = {'perception', 'inference', 'design'}       # every large cell now has checked routes (2026-10-03)
            self.assertEqual(ready, expected, (c['domain'], c['cell']))


class AnswerPositionTests(unittest.TestCase):
    """What a model could win by always answering the same letter. The capacity probe checks this on the
    proposals (tests/test_enumeration.py); here it is checked on the bank that is actually published, which is
    what a benchmark result would be read off."""

    def counts(self):
        active = {q['familyInstance'] for q in CATALOG['questions']
                  if q['lifecycle'] == 'active' and q.get('familyInstance')}
        out = {}
        for t in WORKBENCH['teacher_answers']:
            if t['id'] in active:
                out.setdefault(t['family'], Counter())[t['correct_label']] += 1
        return out

    def test_no_family_leans_on_one_position(self):
        for family, c in self.counts().items():
            n = sum(c.values())
            worst = max(abs(c.get(label, 0) - n / 4) for label in 'ABCD')
            self.assertLessEqual(worst, max(4, 0.15 * n), '%s %s' % (family, dict(c)))     # production tolerance

    def test_always_answering_one_letter_stays_near_chance(self):
        total = Counter()
        for c in self.counts().values():
            total += c
        best = max(total.values()) / sum(total.values())
        self.assertLessEqual(best, 0.30, dict(total))               # chance is 0.25; 0.30 is the batch tolerance


if __name__ == '__main__':
    unittest.main()
