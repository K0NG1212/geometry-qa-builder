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
PACKETS = {p['id']: p for p in verify_all.rehydrate(copy.deepcopy(WORKBENCH['student_packets']))}
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
        report = verify_all.verify(list(PACKETS.values()), WORKBENCH['teacher_answers'], {})
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


def mirror_text(text):
    lines = text.splitlines()
    rows = [line.split() for line in lines[2:]]
    return '\n'.join(lines[:2] + ['%s %s %s %.8f' % (r[0], r[1], r[2], -float(r[3])) for r in rows]) + '\n'


class StereoMutationTests(unittest.TestCase):
    def test_mirrored_x_changes_relationship(self):
        p, k = pair('FA-SREL-7208-ENAN')
        x = next(i for i in p['inputs'] if i['name'] == 'X.xyz')
        x['text'] = mirror_text(x['text'])          # mirror of the enantiomer = S0 configuration
        self.assertTrue(fails(p, k))

    def test_disclosure_and_key(self):
        p, k = pair('FA-SREL-7082-CONS')
        p['question'] = p['question'].replace('atom order may differ', 'atom order is the same')
        self.assertTrue(fails(p, k, 'disclose'))
        p, k = pair('FA-SPROP-7110')
        k['correct_label'] = next(l for l in 'ABCD' if l != k['correct_label'])
        self.assertTrue(fails(p, k, 'Key label'))

    def test_design_candidate_swap_and_margin(self):
        p, k = pair('FA-SDES-7033')
        files = {i['name']: i for i in p['inputs']}
        right = 'candidate_%s.xyz' % k['correct_label']
        other = next(n for n in files if n.startswith('candidate_') and n != right)
        files[right]['text'], files[other]['text'] = files[other]['text'], files[right]['text']
        self.assertTrue(fails(p, k, 'Key label'))
        p, k = pair('FA-SDES-7033')
        p['question'] = p['question'].replace('0.0434 eV (1 kcal/mol) lower', '0.5 eV (1 kcal/mol) lower')
        self.assertTrue(fails(p, k, 'need exactly 1'))


class MigratedMutationTests(unittest.TestCase):
    def test_excerpts_and_models_are_enforced(self):
        p, k = pair('FA-DIST-6LYZ-SS')
        p['inputs'][0]['text'] = '\n'.join(l for l in p['inputs'][0]['text'].splitlines() if not l.startswith('SSBOND')) + '\n'
        self.assertTrue(fails(p, k, 'SSBOND'))
        p, k = pair('FA-FRET-1UBQ')
        p['question'] = p['question'].replace('R0 = 2.50 nm', 'R0 = 3.50 nm')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-GUIN-1BNA')
        lines = p['inputs'][0]['text'].splitlines()
        p['inputs'][0]['text'] = '\n'.join([str(int(lines[0]) - 1)] + lines[1:-1]) + '\n'    # drop one atom
        self.assertTrue(fails(p, k, 'source heavy atoms'))

    def test_crystal_options_and_periodicity(self):
        p, k = pair('FA-COORD-MGO')
        p['question'] = p['question'].replace('infinite and periodic', 'finite')
        self.assertTrue(fails(p, k, 'Periodicity'))
        p, k = pair('FA-PEAK-CSCL')
        p['question'] = p['question'].replace('Cl = 17', 'Cl = 55')   # identical weights: (1 0 0) becomes extinct
        self.assertTrue(fails(p, k))


class ScatteringTests(unittest.TestCase):
    def test_two_point_orientation_average(self):
        import numpy as np
        from checkers.migrated import orientation_average
        for q, r in ((0.3, 7.0), (1.1, 4.0), (0.05, 90.0)):
            pts = np.array([[0.0, 0.0, 0.0], [r * 0.6, r * 0.8, 0.0]])
            self.assertAlmostEqual(orientation_average(pts, q), (1 + math.sin(q * r) / (q * r)) / 2, places=12)

    def test_debye_and_design_parameters_are_enforced(self):
        p, k = pair('FA-DEB-7ARQ-018')
        p['question'] = p['question'].replace('q = 0.180 nm⁻¹', 'q = 0.200 nm⁻¹')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-DEB-7ARQ-018')
        p['question'] = p['question'].replace('q = 4π sinθ/λ', 'q = 2 sinθ/λ')
        self.assertTrue(fails(p, k, 'convention'))
        p, k = pair('FA-QDES-7ARQ-050')
        p['question'] = p['question'].replace('first falls to 0.50.', 'first falls to 0.45.')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-QDES-7ARQ-SCAF-020')
        p['question'] = p['question'].replace('labelled scaffold', 'labelled staple')
        self.assertTrue(fails(p, k))


class SuperlatticeTests(unittest.TestCase):
    def test_reciprocal_lattice_of_a_hand_built_fcc_cluster(self):
        import itertools
        import numpy as np
        from checkers.superlattice import analyse
        a = 50.0
        basis = [(0, 0, 0), (0.5, 0.5, 0), (0.5, 0, 0.5), (0, 0.5, 0.5)]
        pts = np.array(sorted({((i + b[0]) * a, (j + b[1]) * a, (k + b[2]) * a) for i, j, k in itertools.product(range(-2, 3), repeat=3)
                               for b in basis if max(abs(i + b[0]), abs(j + b[1]), abs(k + b[2])) <= 2}))
        lat = analyse(pts)
        self.assertTrue(lat['fcc'])
        self.assertAlmostEqual(lat['nn'], a / math.sqrt(2), places=9)
        self.assertAlmostEqual(lat['volume'], a ** 3 / 4, places=6)
        self.assertAlmostEqual(lat['g'][0], 2 * math.pi * math.sqrt(3) / a, places=9)     # (111)
        self.assertAlmostEqual(lat['g'][1], 4 * math.pi / a, places=9)                    # (200); (100) is absent

    def test_parameters_and_files_are_enforced(self):
        p, k = pair('FA-SL-QSTAR-X')
        p['question'] = p['question'].replace('first (lowest-q)', 'second distinct')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-SL-GOLD-52')
        p['question'] = p['question'].replace('core diameter of 10.3 nm', 'core diameter of 13.0 nm')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-SL-DES-NN')
        p['question'] = p['question'].replace('closest to 45 nm', 'closest to 33 nm')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-SL-SHELL-X')
        lines = p['inputs'][0]['text'].splitlines()
        lines[2] = lines[2][:-1] + ('1' if lines[2][-1] != '1' else '2')      # move one particle by 1e-6 nm
        p['inputs'][0]['text'] = '\n'.join(lines) + '\n'
        self.assertTrue(fails(p, k, 'model crystallite'))


class OpalTests(unittest.TestCase):
    def test_hand_computed_bragg_snell(self):
        # Silica opal of the Sensors 2023 parameter table: D = 266 nm, n_eff = 1.35, 30 degrees -> ~545 nm (paper: ~547 nm).
        d111 = 266 * math.sqrt(2) / math.sqrt(3)
        self.assertAlmostEqual(2 * d111 * math.sqrt(1.35 ** 2 - 0.25), 544.7, delta=0.05)
        p, k = pair('FA-OP-PEAK-SIO2-30')
        self.assertEqual(checkers.check(p, k)['status'], 'pass')
        self.assertEqual(k['numeric_answer']['value'], '544.7')

    def test_optical_conditions_are_enforced(self):
        p, k = pair('FA-OP-PEAK-S3')
        p['question'] = p['question'].replace('medium of refractive index 1.00', 'medium of refractive index 1.33')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-OP-PEAK-S3')
        p['question'] = p['question'].replace('volume-weighted average of the squared refractive indices', 'average of the indices')
        self.assertTrue(fails(p, k, 'Effective-medium'))
        p, k = pair('FA-OP-PEAK-SIO2-30')
        p['question'] = p['question'].replace('at 30° from the film normal', 'at 40° from the film normal')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-OP-DIAM-S8')
        p['question'] = p['question'].replace('; neighbouring spheres touch', '')
        self.assertTrue(fails(p, k, 'Touching'))
        p, k = pair('FA-OP-DES-BELOW700')
        p['question'] = p['question'].replace('stays below 700 nm', 'stays below 800 nm')
        self.assertTrue(fails(p, k))


class MoireTests(unittest.TestCase):
    def test_hand_computed_moire(self):
        # Cao et al.: n_s = 4/A with A = (sqrt(3)/2) lambda^2; at 1.05 deg n_s/2 ~ 1.28e12 cm^-2 (paper: 1.2-1.6e12).
        lam = 0.246 / (2 * math.sin(math.radians(1.05) / 2))
        self.assertAlmostEqual(lam, 13.424, places=3)
        self.assertAlmostEqual(2 / (math.sqrt(3) / 2 * lam ** 2) * 100, 1.282, places=3)
        import numpy as np
        from checkers.moire import moire_cell
        pts = np.array([[lam * (i + j / 2), lam * j * math.sqrt(3) / 2] for i in range(-3, 4) for j in range(-3, 4)])
        period, area = moire_cell(pts)
        self.assertAlmostEqual(period, lam, places=9)
        self.assertAlmostEqual(area, math.sqrt(3) / 2 * lam ** 2, places=6)

    def test_conditions_are_enforced(self):
        p, k = pair('FA-MO-TWIST-D1')
        p['question'] = p['question'].replace('lattice constant is 0.246 nm', 'lattice constant is 0.142 nm')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-MO-NFULL-M1')
        p['question'] = p['question'].replace('completely fills one set', 'fills part of one set')
        self.assertTrue(fails(p, k, 'Filling'))
        p, k = pair('FA-MO-ATOMS-K110')
        p['question'] = p['question'].replace('unstrained and rigidly twisted', 'relaxed')
        self.assertTrue(fails(p, k, 'Rigid'))
        p, k = pair('FA-MO-DES-PERIOD')
        p['question'] = p['question'].replace('closest to 13.5 nm', 'closest to 17 nm')
        self.assertTrue(fails(p, k))


class EvidenceFamilyTests(unittest.TestCase):
    def test_secondary_structure_evidence_is_enforced(self):
        p, k = pair('FA-SS-1UBQ-43')
        self.assertEqual(checkers.check(p, k)['status'], 'pass')
        p['question'] = p['question'].replace('β-strand (φ −120°, ψ +130°)', 'β-strand (φ −75°, ψ +145°)').replace(
            'polyproline II (φ −75°, ψ +145°)', 'polyproline II (φ −120°, ψ +130°)')
        self.assertTrue(fails(p, k))                       # swapped reference centres change the nearest class
        p, k = pair('FA-SS-6LYZ-90')
        lines = p['inputs'][0]['text'].splitlines()
        lines[3] = lines[3][:31] + ('9' if lines[3][31] != '9' else '8') + lines[3][32:]
        p['inputs'][0]['text'] = '\n'.join(lines) + '\n'
        self.assertTrue(fails(p, k))

    def test_hostguest_uses_measured_table(self):
        p, k = pair('FA-HG-EV3')
        self.assertEqual(checkers.check(p, k)['status'], 'pass')
        p['question'] = p['question'].replace('pH 7.40', 'pH 5.0')
        self.assertTrue(fails(p, k, 'conditions'))
        p, k = pair('FA-HG-DES1')
        p['question'] = p['question'].replace('at least 2.0 kcal/mol', 'at least 0.5 kcal/mol')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-HG-EV1')
        p['options'][0]['value'] = p['options'][0]['value'].replace('(WP6-', '(WP6-X')
        self.assertTrue(fails(p, k))

    def test_quantum_dot_curve_is_read_from_question(self):
        p, k = pair('FA-QD-PEAK-C')
        self.assertEqual(checkers.check(p, k)['status'], 'pass')
        p['question'] = p['question'].replace('0.4277·λ', '0.4300·λ')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-QD-CONC-B')
        p['question'] = p['question'].replace('in a 1.0 cm cuvette', 'in a 0.5 cm cuvette')
        self.assertTrue(fails(p, k))

    def test_trimeric_capsid(self):
        p, k = pair('FA-ASM-T-6NCL')
        self.assertEqual(checkers.check(p, k)['status'], 'pass')
        self.assertEqual(k['numeric_answer']['value'], '169')
        p['question'] = p['question'].replace('12 pentamers at the vertices are formed by a different protein', 'pentamers are also Vp54')
        self.assertTrue(fails(p, k, 'Penton'))


class DesignGapTests(unittest.TestCase):
    def test_diffraction_design(self):
        for iid in ('FA-XD-CRYSTAL-CU', 'FA-XD-ANODE-MOF5', 'FA-XD-WAVE-MOF5'):
            p, k = pair(iid)
            self.assertEqual(checkers.check(p, k)['status'], 'pass', iid)
        p, k = pair('FA-XD-CRYSTAL-CU')
        p['question'] = p['question'].replace('closest to 2θ = 37.00°', 'closest to 2θ = 27.00°')
        self.assertTrue(fails(p, k))                          # NaCl (111) would win instead of MgO (111)
        p, k = pair('FA-XD-ANODE-NACL')
        p['question'] = p['question'].replace('closest to 2θ = 32.00°', 'closest to 2θ = 41.00°')
        self.assertTrue(fails(p, k))

    def test_disulfide_design_windows(self):
        p, k = pair('FA-DS-6LYZ')
        self.assertEqual(checkers.check(p, k)['status'], 'pass')
        p['question'] = p['question'].replace('between 4.4 and 6.8 Å', 'between 4.0 and 6.8 Å')
        self.assertTrue(fails(p, k, 'pairs meet'))            # Asp18–Leu25 (Cα 4.16 Å) now also qualifies

    def test_fret_design_r0(self):
        p, k = pair('FA-FD-1UBQ')
        self.assertEqual(checkers.check(p, k)['status'], 'pass')
        p['question'] = p['question'].replace('R0 = 2.5 nm', 'R0 = 3.5 nm')
        self.assertTrue(fails(p, k))


class ModelConditionTests(unittest.TestCase):
    def test_paper_parameter_questions_must_state_the_model_conditions(self):
        for iid in ('FA-SL-QSTAR-X', 'FA-SL-DES-GOLD', 'FA-OP-PEAK-S3', 'FA-OP-DES-820', 'FA-MO-NFULL-M1', 'FA-MO-DES-FULL', 'FA-QD-EPS-E'):
            p, k = pair(iid)
            self.assertEqual(checkers.check(p, k)['status'], 'pass', iid)
            start = p['question'].index('Model conditions:')
            end = p['question'].index('.', p['question'].index('the only measured input' if 'FA-QD' not in iid else 'ideal spherical cut'))
            p['question'] = p['question'][:start] + p['question'][end + 1:]
            self.assertTrue(fails(p, k, 'conditions'), iid)


if __name__ == '__main__':
    unittest.main()
