import ast
import copy
import json
import math
import unittest
from pathlib import Path

import checkers
import verify_all

ROOT = Path(__file__).resolve().parents[1]
WORKBENCH = json.loads((ROOT / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
PACKETS = {p['id']: p for p in WORKBENCH['student_packets']}
KEYS = {k['id']: k for k in WORKBENCH['teacher_answers']}


def pair(id):
    return copy.deepcopy(PACKETS[id]), copy.deepcopy(KEYS[id])


def run_family(packet, key):
    """Hand-made packets have no source asset, so call the family checker directly."""
    return checkers.CHECKERS[packet['family']](packet, key)


def fails(packet, key, fragment=''):
    result = checkers.check(packet, key)
    return result['status'] == 'fail' and fragment in result['problem']


def numeric_packet(id, family, question, name, text, options, unit, value, decimals, label):
    packet = dict(id=id, family=family, question=question, scope='test',
                  inputs=[dict(name=name, format='pdb-excerpt' if name.endswith('.pdb') else 'xyz', unit='angstrom', text=text)],
                  options=[dict(label=l, value=v, unit=unit) for l, v in zip('ABCD', options)])
    key = dict(id=id, family=family, correct_label=label, input_hashes={},
               numeric_answer=dict(value=value, unit=unit, decimals=decimals, tolerance=str(0.5 * 10 ** -decimals)))
    return packet, key


def pdb_line(serial, name, res, resnum, xyz):
    return 'ATOM  %5d  %-3s %3s A%4d    %8.3f%8.3f%8.3f  1.00  0.00           %s' % (serial, name, res, resnum, *xyz, name[0])


class IndependenceTests(unittest.TestCase):
    def test_checkers_do_not_import_generation_code(self):
        banned = {'task_families', 'family_engine', 'template_engine', 'choice_engine', 'tools'}
        for path in sorted((ROOT / 'checkers').glob('*.py')) + [ROOT / 'verify_all.py']:
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                        [node.module or ''] if isinstance(node, ast.ImportFrom) else []
                for name in names:
                    self.assertNotIn(name.split('.')[0], banned, '%s imports %s' % (path.name, name))

    def test_every_family_has_a_checker(self):
        registry = json.loads((ROOT / 'templates/registry.json').read_text(encoding='utf-8'))
        engine = {f for t in registry['templates'] for f in t['engine_families']}
        self.assertEqual(engine, set(checkers.CHECKERS))

    def test_published_batch_passes(self):
        report = verify_all.verify(WORKBENCH['student_packets'], WORKBENCH['teacher_answers'], {})
        self.assertEqual(report['failed'], [])
        self.assertEqual(report['passed'], len(WORKBENCH['teacher_answers']))
        self.assertEqual(report['model_calls'], 0)


class HandComputedTests(unittest.TestCase):
    def test_square_extent_and_rg(self):
        xyz = '4\nsquare\nC 0 0 0\nC 1 0 0\nC 1 1 0\nC 0 1 0\n'
        q = 'For the supplied finite point set, compute the maximum Euclidean distance over all unordered pairs.'
        p, k = numeric_packet('T1', 'extent_choice_v2', q, 's.xyz', xyz, ['1.0000', '1.2000', '1.4142', '2.0000'],
                              'angstrom', '1.4142', 4, 'C')
        self.assertEqual(run_family(p, k)['label'], 'C')
        self.assertTrue(fails(p, k, 'No source asset'))
        q = 'Compute the equal-weight radius of gyration of all supplied sites. Do not use mass weights.'
        p, k = numeric_packet('T2', 'extent_choice_v2', q, 's.xyz', xyz, ['0.5000', '0.7071', '1.0000', '1.4142'],
                              'angstrom', '0.7071', 4, 'B')
        self.assertEqual(run_family(p, k)['label'], 'B')

    def test_water_like_angle(self):
        t = math.radians(104.5)
        xyz = '3\nw\nH 0.96 0 0\nO 0 0 0\nH %.10f %.10f 0\n' % (0.96 * math.cos(t), 0.96 * math.sin(t))
        q = 'Atoms H1–O2–H3 form the water angle (H1 = row 1, O2 = row 2, H3 = row 3). What is the H1–O2–H3 bond angle at O2?'
        p, k = numeric_packet('T3', 'named_bond_angle', q, 'w.xyz', xyz, ['100.00', '104.50', '109.47', '120.00'],
                              'degree', '104.50', 2, 'B')
        self.assertEqual(run_family(p, k)['label'], 'B')
        k['correct_label'] = 'C'
        with self.assertRaises(checkers.CheckError):
            run_family(p, k)

    def test_iupac_torsion_sign(self):
        pts = [('C', 1, (1, 0, 0)), ('N', 2, (0, 0, 0)), ('CA', 2, (0, 1, 0)), ('C', 2, (0, 1, 1))]
        text = '\n'.join(pdb_line(i + 1, n, 'GLY', r, xyz) for i, (n, r, xyz) in enumerate(pts)) + '\nEND\n'
        q = 'Compute the backbone torsion φ of Gly2, defined by atoms C(1)–N(2)–CA(2)–C(2), using the IUPAC sign convention.'
        p, k = numeric_packet('T4', 'backbone_torsion', q, 'x.pdb', text, ['-90.0', '0.0', '45.0', '90.0'],
                              'degree', '-90.0', 1, 'A')
        self.assertEqual(run_family(p, k)['label'], 'A')      # the mirror image (+90) would be wrong


class MutationTests(unittest.TestCase):
    def test_wrong_key_label_or_value(self):
        p, k = pair('FA-ANG-BCD')
        k['correct_label'] = 'A'
        self.assertTrue(fails(p, k, 'Key label'))
        p, k = pair('FA-ANG-BCD')
        k['numeric_answer']['value'] = '116.04'
        self.assertTrue(fails(p, k, 'Numeric key'))

    def test_duplicate_or_wrong_precision_options(self):
        p, k = pair('FA-FP-QM7X-7001')
        right = next(o for o in p['options'] if o['label'] == k['correct_label'])
        next(o for o in p['options'] if o['label'] != k['correct_label'])['value'] = right['value']
        self.assertTrue(fails(p, k, 'Duplicate'))
        p, k = pair('FA-FP-QM7X-7001')
        p['options'][1]['value'] = p['options'][1]['value'] + '0'
        self.assertTrue(fails(p, k, 'decimals'))

    def test_changed_coordinate_changes_answer(self):
        p, k = pair('FA-ANG-WP6')
        lines = p['inputs'][0]['text'].splitlines()
        e, x, y, z = lines[2].split()                                  # row 1 = vertex C1
        lines[2] = '%s %.3f %s %s' % (e, float(x) + 0.2, y, z)
        p['inputs'][0]['text'] = '\n'.join(lines) + '\n'
        self.assertTrue(fails(p, k))

    def test_torsion_excerpt_must_be_verbatim(self):
        p, k = pair('FA-TOR-1UBQ-V26')
        text = p['inputs'][0]['text']
        first = next(l for l in text.splitlines() if l.startswith('ATOM') and l[12:16].strip() == 'O')
        p['inputs'][0]['text'] = text.replace(first, first[:30] + '%8.3f' % (float(first[30:38]) + 0.5) + first[38:])
        self.assertTrue(fails(p, k, 'copied unchanged'))

    def test_missing_physical_conditions_fail(self):
        p, k = pair('FA-EXT-NACL')
        p['question'] = p['question'].replace('(Cl = 17, Na = 11)', '')
        self.assertTrue(fails(p, k, 'weights'))
        p, k = pair('FA-FP-QM7X-7002')
        p['question'] = p['question'].replace(', which starts at B and moves toward A', '')
        self.assertTrue(fails(p, k, 'direction'))
        p, k = pair('FA-FP-QM7X-7001')
        p['question'] = p['question'].replace('F_i = −∂E/∂r_i', 'F_i')
        self.assertTrue(fails(p, k, 'relation'))

    def test_extinction_options_must_hold(self):
        p, k = pair('FA-EXT-DIAMOND')
        wrong = next(o for o in p['options'] if o['label'] != k['correct_label'])
        wrong['value'] = '(2 0 0)'                                     # also extinct in diamond
        self.assertTrue(fails(p, k, 'exactly 1'))

    def test_design_candidates_and_leaks(self):
        p, k = pair('FA-CONF-7050-max_dipole')
        files = {i['name']: i for i in p['inputs']}
        files['candidate_A.xyz']['text'], files['candidate_D.xyz']['text'] = \
            files['candidate_D.xyz']['text'], files['candidate_A.xyz']['text']
        self.assertTrue(fails(p, k, 'Key label'))
        p, k = pair('FA-CONF-7050-max_dipole')
        p['inputs'][1]['text'] = p['inputs'][1]['text'].replace('candidate A', 'Geom-m7050-i1-c4-opt', 1)
        self.assertTrue(fails(p, k, 'identifiers'))
        p, k = pair('FA-CONF-7050-max_dipole')
        p['inputs'][1]['text'] = p['inputs'][0]['text']                # candidate A = S0
        self.assertTrue(fails(p, k))

    def test_answer_key_fields_and_hash(self):
        p, k = pair('FC-QNP007')
        p['options'][0]['is_correct'] = True
        self.assertTrue(fails(p, k, 'Answer-key fields'))
        p, k = pair('FC-QNP007')
        k['input_hashes'] = {x: '0' * 64 for x in k['input_hashes']}
        self.assertTrue(fails(p, k, 'hash mismatch'))
        p, k = pair('FC-QNP007')
        k['family'] = 'named_bond_angle'
        self.assertTrue(fails(p, k, 'belong together'))


if __name__ == '__main__':
    unittest.main()
