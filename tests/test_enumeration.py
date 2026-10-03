"""Instance enumerators: deterministic proposals, no duplicates of the manifest, and every sampled proposal the
family accepts passes the independent checker."""
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import checkers  # noqa: E402
import enumerators  # noqa: E402
import family_engine  # noqa: E402
import verify_all  # noqa: E402
from task_families import FAMILIES, kit  # noqa: E402

CAPACITY = json.loads((ROOT / 'docs/data/enumeration-capacity.json').read_text(encoding='utf-8'))
PROPOSALS = enumerators.propose(ROOT)


class ProposalTests(unittest.TestCase):
    def test_every_enumerator_targets_a_registered_family(self):
        self.assertTrue(set(enumerators.ENUMERATORS) <= set(FAMILIES))
        self.assertTrue(all(f in checkers.CHECKERS for f in enumerators.ENUMERATORS))

    def test_ids_unique_and_deterministic(self):
        ids = [s['id'] for specs in PROPOSALS.values() for s in specs]
        self.assertEqual(len(ids), len(set(ids)))
        again = enumerators.propose(ROOT)
        self.assertEqual({f: [s['id'] for s in v] for f, v in again.items()}, {f: [s['id'] for s in v] for f, v in PROPOSALS.items()})

    def test_structures_are_committed_assets_with_source(self):
        for s in enumerators.load_structures(ROOT):
            self.assertTrue((ROOT / 'docs' / s['asset']).exists(), s['pdb'])
            self.assertTrue(s['source'].startswith('https://') and s['license'], s['pdb'])

    def test_manifest_instances_are_recognised_as_duplicates(self):
        manifest = json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))
        existing = {enumerators.signature(x) for x in manifest['items']}
        torsion = [x for x in manifest['items'] if x['family'] == 'backbone_torsion'][0]
        twin = [s for s in PROPOSALS['backbone_torsion'] if s['pdb'] == torsion['pdb'] and s['residue'] == torsion['residue']
                and s['torsion'] == torsion['torsion']]
        self.assertEqual(len(twin), 1)
        self.assertIn(enumerators.signature(twin[0]), existing)

    def test_fret_proposals_offer_r0_on_both_sides(self):
        for s in PROPOSALS['fret_efficiency'][:200]:
            self.assertTrue(len(s['R0_choices']) >= 2)


class SampleTests(unittest.TestCase):
    def test_small_sample_builds_and_passes_the_independent_checker(self):
        picked = []
        for family, specs in PROPOSALS.items():
            picked += sorted(specs, key=lambda s: kit.digest('test', s['id']))[:4]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'manifest.json'
            path.write_text(json.dumps(dict(items=picked), ensure_ascii=False), encoding='utf-8')
            family_engine.run(path, Path(tmp) / 'run', 'test-seed')
            report = verify_all.verify(*verify_all.load(run=Path(tmp) / 'run'))
        self.assertGreater(report['checked'], 10)
        self.assertEqual(report['passed'], report['checked'], report['failed'])

    def test_fret_reaches_every_target_rank(self):
        spec = [s for s in PROPOSALS['fret_efficiency'] if s['pdb'] == '6LYZ'][0]
        got = set()
        for target in (1, 2, 3, 4):
            built = FAMILIES['fret_efficiency']['build'](dict(spec, target_position=target), ROOT, 'rank-test')
            got.add(built['rank']['achieved'] == target)
        self.assertEqual(got, {True})


class PublishedCapacityTests(unittest.TestCase):
    def test_capacity_probe_is_clean(self):
        t = CAPACITY['totals']
        self.assertEqual(t['checker_pass'], t['checker_checked'])
        self.assertEqual(t['checker_checked'], t['accepted'])
        self.assertTrue(t['position_balance_ok'])
        self.assertEqual(CAPACITY['model_calls'], 0)
        self.assertEqual({r['family'] for r in CAPACITY['rows']}, set(enumerators.ENUMERATORS))
        counts = Counter()
        for f, specs in PROPOSALS.items():
            counts[f] = len(specs)
        for r in CAPACITY['rows']:
            self.assertLessEqual(r['proposals'], counts[r['family']])


class FamilyHardeningTests(unittest.TestCase):
    """Problems the enumeration probes found (2026-10-04) stay fixed."""

    def test_strict_rank_rejects_unreachable_targets(self):
        with self.assertRaises(ValueError):
            kit.require_rank(dict(strict_rank=True), 4, 2)
        kit.require_rank(dict(strict_rank=True), 3, 3)
        kit.require_rank({}, 4, 2)                                     # hand-written specs keep the nearest-rank fallback

    def test_scattering_q_must_be_stated_exactly(self):
        spec = [s for s in PROPOSALS['guinier_intensity']][0]
        with self.assertRaises(ValueError):
            FAMILIES['guinier_intensity']['build'](dict(spec, q_per_nm=spec['q_per_nm'] + 0.0012, strict_rank=False), ROOT, 'q-test')

    def test_capsid_questions_use_the_major_shell_protein_only(self):
        comps = {(s['assembly'], s['component']) for s in PROPOSALS['capsid_architecture']}
        self.assertIn(('6CGR-T', 'VP5'), comps)
        self.assertNotIn(('6CGR-T', 'VP26'), comps)                     # 900 hexon-only copies would give a false T = 15
        self.assertFalse(any(s['assembly'].startswith('1SVA') for s in PROPOSALS['capsid_architecture']))   # SV40: pentamers only

    def test_checkers_know_silicon(self):
        from checkers import families as fam, migrated
        self.assertIn('Si', fam.RADII)
        self.assertIn('Si', migrated.RADII)

    def test_molecule_bonds_skip_hydrogen_and_name_connectivity(self):
        spec = PROPOSALS['named_bond_distance'][0]
        self.assertNotIn('H', [a['element'] for a in spec['atoms']])
        self.assertIn('is bonded to', spec['bond'])


if __name__ == '__main__':
    unittest.main()
