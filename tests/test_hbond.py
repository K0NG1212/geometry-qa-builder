"""Hydrogen-bond families (hbond_geometry, hbond_criteria) on the 3-hydroxy-2-butenamide conformers, and their checker."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checkers  # noqa: E402
from task_families import hbond, kit, chem_names  # noqa: E402

MANIFEST = {x['id']: x for x in json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))['items']}
SEED = 'test-seed'


def build(instance, target=1, **change):
    spec = dict(MANIFEST[instance], target_position=target, **change)
    fn = hbond.build_geometry if spec['family'] == 'hbond_geometry' else hbond.build_criteria
    return spec, fn(spec, ROOT, SEED)


def check(spec, built, **packet_change):
    packet = dict(id=spec['id'], family=spec['family'], question=built['question'], inputs=built['inputs'], options=built['options'])
    packet.update(packet_change)
    key = dict(id=spec['id'], family=spec['family'], correct_label=built['correct_label'], numeric_answer=built['numeric'],
               input_hashes=built['input_hashes'])
    return checkers.check(packet, key)


class GeometryTests(unittest.TestCase):
    def test_known_values_match_the_legacy_answers(self):
        self.assertEqual(build('FA-HBG-TWO-OO')[1]['numeric']['value'], '2.538')    # HBP001: 2.538116731 angstrom
        self.assertEqual(build('FA-HBG-FIVE-HN')[1]['numeric']['value'], '1.926')   # HBI002 answer: H...N 1.926478
        self.assertEqual(build('FA-HBG-FOUR-ANG')[1]['numeric']['value'], '128.6')  # HBI002 answer: 128.561836 degrees

    def test_every_position_passes_the_checker(self):
        for instance in ('FA-HBG-TWO-OO', 'FA-HBG-FIVE-HN', 'FA-HBG-FOUR-ANG', 'FA-HBC-SET1', 'FA-HBC-SET2'):
            for target in (1, 2, 3, 4):
                spec, built = build(instance, target)
                self.assertEqual(check(spec, built)['status'], 'pass', (instance, target))

    def test_rejects_wrong_atoms(self):
        with self.assertRaises(ValueError):
            build('FA-HBG-TWO-OO', contact=[6, 4, 14])        # row 4 H is on carbon, not on the donor O6
        with self.assertRaises(ValueError):
            build('FA-HBG-TWO-OO', contact=[6, 5, 6])

    def test_amide_nitrogen_is_named(self):
        elements, points = kit.parse_xyz((ROOT / 'docs/assets/qa/HBP002-S0005.xyz').read_text(encoding='utf-8'))
        self.assertEqual(chem_names.Molecule(elements, points, 0).names[10], 'amide NH2 nitrogen')


class CriteriaTests(unittest.TestCase):
    def test_close_donor_acceptor_with_hydrogen_pointing_away_is_a_distractor(self):
        spec, built = build('FA-HBC-SET1')
        rules = {a['value']: a['rule'] for a in built['option_audit']}
        self.assertEqual(rules['O6–H5···O14 in conformer TWO'], 'correct')
        self.assertEqual(rules['O5–H14···O6 in conformer THREE'], 'donor_acceptor_close')

    def test_candidate_near_a_threshold_is_refused(self):
        cands = MANIFEST['FA-HBC-SET2']['candidates'][:3] + [dict(conformer='FOUR', contact=[3, 5, 13])]   # 128.6 degrees vs 130
        with self.assertRaises(ValueError):
            build('FA-HBC-SET2', candidates=cands)

    def test_checker_rejects_tampering(self):
        spec, built = build('FA-HBC-SET1')
        looser = built['question'].replace('H···A distance ≤ 2.2 Å and D–H···A angle ≥ 130°', 'H···A distance ≤ 3.8 Å and D–H···A angle ≥ 5°')
        self.assertEqual(check(spec, built, question=looser)['status'], 'fail')
        moved = copy.deepcopy(built['inputs'])
        moved[0]['text'] = moved[0]['text'].replace('O 1.2197', 'O 1.3197')
        self.assertEqual(check(spec, built, inputs=moved)['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
