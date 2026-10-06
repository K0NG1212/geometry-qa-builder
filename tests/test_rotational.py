"""Rotational spectroscopy families (rotational_line, isotopologue_design): rigid-rotor physics on hand-checkable
cases, the independent checker against tampering, and the enumerator's scope and shortcut control."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checkers  # noqa: E402
import enumerators  # noqa: E402
from checkers import rotational as checker  # noqa: E402
from task_families import rotational, kit  # noqa: E402

MANIFEST = {x['id']: x for x in json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))['items']}


def packet_and_key(spec, built):
    packet = dict(id=spec['id'], family=spec['family'], question=built['question'], inputs=built['inputs'], options=built['options'])
    key = dict(id=spec['id'], family=spec['family'], correct_label=built['correct_label'], numeric_answer=built['numeric'],
               input_hashes=built['input_hashes'])
    return packet, key


def build(instance, target=1):
    spec = dict(MANIFEST[instance], target_position=target)
    family = rotational.build_line if spec['family'] == 'rotational_line' else rotational.build_isotopologue
    return spec, family(spec, ROOT, 'test-seed')


class RigidRotorTests(unittest.TestCase):
    def test_h_over_8_pi_squared(self):
        # Literature value of h/(8 pi^2) in MHz u angstrom^2: 505379.0 (from the exact h and CODATA 2018 u).
        self.assertAlmostEqual(rotational.factor_mhz(), 505379.0, delta=0.1)

    def test_planar_rotor_and_rotation_invariance(self):
        elements = ['O', 'H', 'H']
        points = [(0.0, 0.0, 0.1173), (0.0, 0.7572, -0.4692), (0.0, -0.7572, -0.4692)]
        moments, _ = rotational.principal(elements, points)
        self.assertAlmostEqual(moments[2], moments[0] + moments[1], places=10)        # planar: I_c = I_a + I_b
        c, s = math.cos(0.7), math.sin(0.7)
        turned = [(x * c - y * s, x * s + y * c, z + 3.0) for x, y, z in points]     # rotate and translate
        again, _ = rotational.principal(elements, turned)
        for a, b in zip(moments, again):
            self.assertAlmostEqual(a, b, places=9)
        atoms = [(e, tuple(kit.Decimal(repr(v)) for v in p)) for e, p in zip(elements, turned)]
        closed = checker.principal_moments(atoms, {e: kit.Decimal(v) for e, v in rotational.MASS.items()})
        for a, b in zip(moments, closed):
            self.assertAlmostEqual(a, b, places=8)

    def test_jacobi_and_closed_form_agree_on_every_molecule(self):
        for m in enumerators.load_molecules(ROOT):
            elements, points = kit.parse_xyz((ROOT / 'docs' / m['asset']).read_text(encoding='utf-8-sig'))
            if len(elements) > rotational.MAX_ATOMS:
                continue
            jac, _ = rotational.principal(elements, points)
            atoms = checker.read_xyz((ROOT / 'docs' / m['asset']).read_text(encoding='utf-8-sig'))
            closed = checker.principal_moments(atoms, {e: kit.Decimal(v) for e, v in rotational.MASS.items()})
            for a, b in zip(jac, closed):
                self.assertLess(abs(a - b), 1e-7 * b, m['molecule'])

    def test_j1_levels(self):
        abc = dict(A=5000.0, B=2000.0, C=1500.0)
        self.assertEqual([rotational.line(abc, k) for k in ('101', '111', '110')], [3500.0, 6500.0, 7000.0])
        self.assertEqual([checker.frequency(abc, k) for k in ('1_01', '1_11', '1_10')], [3500.0, 6500.0, 7000.0])


class FamilyTests(unittest.TestCase):
    def test_pilot_instances_pass_the_independent_checker(self):
        for instance in MANIFEST:
            if instance.startswith(('FA-ROT-', 'FA-ISO-')):
                for target in (1, 2, 3, 4):
                    spec, built = build(instance, target)
                    report = checkers.check(*packet_and_key(spec, built))
                    self.assertEqual(report['status'], 'pass', (instance, report.get('problem')))

    def test_question_states_the_model_but_not_the_level_formulas(self):
        spec, built = build('FA-ROT-7029-111')
        q = built['question']
        for text in ('H 1.007825 u', 'S 31.972071 u', 'h/(8π²I)', 'about the centre of mass', '1_11 ← 0_00'):
            self.assertIn(text, q)
        self.assertNotIn('A + C', q)
        self.assertEqual(built['numeric']['unit'], 'MHz')
        for instance in ('FA-ROT-7029-111', 'FA-ISO-7095-111'):      # dataset conformer ids stay out of the attachment
            text = build(instance)[1]['inputs'][0]['text']
            self.assertNotIn('Geom-', text)
            source = (ROOT / 'docs' / MANIFEST[instance]['asset']).read_text(encoding='utf-8').split('\n')
            self.assertEqual(text.split('\n')[2:], source[2:])

    def test_checker_rejects_tampering(self):
        spec, built = build('FA-ROT-G9-101')
        packet, key = packet_and_key(spec, built)
        wrong = dict(key, correct_label=next(l for l in 'ABCD' if l != key['correct_label']))
        self.assertEqual(checkers.check(packet, wrong)['status'], 'fail')
        heavier = dict(packet, question=packet['question'].replace('H 1.007825 u', 'H 2.014102 u'))
        self.assertEqual(checkers.check(heavier, key)['status'], 'fail')
        moved = copy.deepcopy(packet)
        moved['inputs'][0]['text'] = moved['inputs'][0]['text'].replace('C ', 'N ', 1)
        self.assertEqual(checkers.check(moved, key)['status'], 'fail')

    def test_design_needs_hydrogens_and_a_clear_winner(self):
        spec = dict(MANIFEST['FA-ISO-7095-111'], target_position=1)
        with self.assertRaises(ValueError):
            rotational.build_isotopologue(dict(spec, candidates=[1, 12, 14, 15]), ROOT, 's')      # row 1 is not H
        with self.assertRaises(ValueError):
            rotational.build_isotopologue(dict(spec, candidates=[9, 10, 12, 13]), ROOT, 's')     # near-equal shifts
        spec, built = build('FA-ISO-G13-111')
        packet, key = packet_and_key(spec, built)
        swapped = copy.deepcopy(packet)
        swapped['options'][0]['value'], swapped['options'][1]['value'] = packet['options'][1]['value'], packet['options'][0]['value']
        self.assertEqual(checkers.check(swapped, key)['status'], 'fail')

    def test_large_hosts_are_out_of_scope(self):
        host = next(m for m in enumerators.load_molecules(ROOT) if m['molecule'] == 'SAMPL9-WP6')
        spec = dict(id='T', asset=host['asset'], context=host['context'], scope='x', line='101', target_position=1)
        with self.assertRaises(ValueError):
            rotational.build_line(spec, ROOT, 's')


class EnumeratorTests(unittest.TestCase):
    def test_proposals_skip_hosts_and_control_the_shortcut(self):
        proposals = enumerators.propose(ROOT, ['rotational_line', 'isotopologue_design'])
        big = {m['molecule'] for m in enumerators.load_molecules(ROOT)
               if len(kit.parse_xyz((ROOT / 'docs' / m['asset']).read_text(encoding='utf-8-sig'))[0]) > rotational.MAX_ATOMS}
        self.assertTrue(big)
        self.assertFalse({s['molecule'] for v in proposals.values() for s in v} & big)
        lucky = 0
        for s in proposals['isotopologue_design']:
            elements, points = kit.parse_xyz((ROOT / 'docs' / s['asset']).read_text(encoding='utf-8-sig'))
            rows = [r - 1 for r in s['candidates']]
            _, d = rotational.shifts(elements, points, s['line'], rows)
            com = rotational.centre(rotational.masses_of(elements), points)
            lucky += max(rows, key=lambda r: abs(d[r])) == max(rows, key=lambda r: math.dist(points[r], com))
        self.assertLessEqual(lucky / len(proposals['isotopologue_design']), 0.25)
        self.assertGreater(lucky, 0)


if __name__ == '__main__':
    unittest.main()
