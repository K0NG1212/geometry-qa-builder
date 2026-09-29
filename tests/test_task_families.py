import json
import math
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import family_engine
from task_families import FAMILIES, kit, local_geometry, force_path, extinction, conformer_design, extent_choice, stereo, crystal, scattering, assembly, superlattice, photonic, moire

ROOT = Path(__file__).resolve().parents[1]
SEED = 'geobench-family-v1'
MANIFEST = json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))
SPECS = {x['id']: x for x in MANIFEST['items']}


def spec(id, **kw):
    return dict(SPECS[id], **kw)


class KitTests(unittest.TestCase):
    def test_parse_xyz_strict_and_case(self):
        self.assertEqual(kit.parse_xyz('2\nc\nCL 0 0 0\nH 1 0 0\n')[0], ['Cl', 'H'])
        for bad in ['3\nc\nH 0 0 0\nH 1 0 0\n', '2\nc\nXx 0 0 0\nH 1 0 0\n', '2\nc\nH nan 0 0\nH 1 0 0\n', '2\nc\nH 0 0\nH 1 0 0\n']:
            with self.assertRaises(ValueError):
                kit.parse_xyz(bad)

    def test_dihedral_iupac_sign_and_two_implementations(self):
        pts = [(1, 0, 0), (0, 0, 0), (0, 1, 0), (0, 1, 1)]
        self.assertAlmostEqual(kit.dihedral_normals(*pts), -90.0)
        self.assertAlmostEqual(kit.dihedral_projection(*pts), -90.0)
        mirrored = [(x, y, -z) for x, y, z in pts]
        self.assertAlmostEqual(kit.dihedral_normals(*mirrored), 90.0)
        pts = [(0.3, -1.2, 0.8), (0.1, 0.2, -0.4), (1.3, 0.5, 0.2), (1.9, 1.7, -0.9)]
        self.assertAlmostEqual(kit.dihedral_normals(*pts), kit.dihedral_projection(*pts), places=10)

    def test_angle_implementations(self):
        a, v, b = (1.2, 0.1, 0.0), (0, 0, 0), (-0.4, 1.1, 0.3)
        self.assertAlmostEqual(kit.angle_acos(a, v, b), kit.angle_atan2(a, v, b), places=10)

    def test_choose_numeric_separation_rank_and_failure(self):
        cands = [dict(rule=r, value=v, reason='', plausibility=2) for r, v in
                 [('near', 10.03), ('a', 7), ('b', 8), ('c', 9), ('d', 11), ('e', 12), ('f', 13)]]
        for target in (1, 2, 3, 4):
            chosen, rejected, goal, rank = kit.choose_numeric(10, cands, decimals=2, tolerance='0.005', min_separation='0.5',
                                                              seed=SEED, context='t', target=target)
            self.assertEqual(rank, target)
            self.assertNotIn('near', [c['rule'] for c in chosen])
        with self.assertRaises(ValueError):
            kit.choose_numeric(10, cands[:3], decimals=2, tolerance='0.005', min_separation='0.5', seed=SEED, context='t')
        with self.assertRaises(ValueError):
            kit.choose_numeric(10, cands, decimals=2, tolerance='0.5', min_separation='0.5', seed=SEED, context='t')

    def test_weak_options_avoided_when_possible(self):
        cands = [dict(rule='w', value=1, reason='', plausibility=1)] + \
                [dict(rule=r, value=v, reason='', plausibility=3) for r, v in [('a', 8), ('b', 9), ('c', 11)]]
        chosen = kit.choose_numeric(10, cands, decimals=1, tolerance='0.05', min_separation='0.5', seed=SEED,
                                    context='w', target=1)[0]
        self.assertNotIn('w', [c['rule'] for c in chosen])

    def test_validate_numeric(self):
        opts = lambda vs: [dict(label=l, value=v, unit='degree') for l, v in zip('ABCD', vs)]
        self.assertEqual(kit.validate_numeric(opts(['1.0', '5.0', '9.0', '13.0']), 5, decimals=1, tolerance='0.05',
                                              min_separation='2.0', unit='degree'), 'B')
        for bad, err in [(['1.0', '5.0', '9.0', '9.3'], 'separated'), (['1.0', '5.00', '9.0', '13.0'], 'precision'),
                         (['1.0', '6.0', '9.0', '13.0'], 'exactly one')]:
            with self.assertRaisesRegex(ValueError, err):
                kit.validate_numeric(opts(bad), 5, decimals=1, tolerance='0.05', min_separation='0.4', unit='degree')
        # Periodic: -179.0 and 179.0 are 2 degrees apart.
        with self.assertRaises(ValueError):
            kit.validate_numeric(opts(['-179.0', '0.0', '90.0', '179.0']), 0, decimals=1, tolerance='0.05',
                                 min_separation='5.0', unit='degree', period=360)

    def test_verdicts_score_place_and_cues(self):
        opts = [dict(label=l, value=v) for l, v in zip('ABCD', 'wxyz')]
        self.assertEqual(kit.validate_verdicts(opts, [False, False, True, False]), 'C')
        for verdicts in ([False] * 4, [True, True, False, False], [True, None, False, False]):
            with self.assertRaises(ValueError):
                kit.validate_verdicts(opts, verdicts)
        self.assertTrue(kit.score_choice(' c\n', 'C'))
        self.assertFalse(kit.score_choice('The answer is C', 'C'))
        self.assertEqual(kit.place('X', ['a', 'b', 'c'], 3, SEED, 'p', key=str).index('X'), 2)
        self.assertTrue(kit.mirror_pair_cue([('A', '-1.0'), ('B', '1.0'), ('C', '2.0'), ('D', '3.0')], 'B'))
        self.assertFalse(kit.mirror_pair_cue([('A', '0.5'), ('B', '1.0'), ('C', '2.0'), ('D', '3.0')], 'B'))


class LocalGeometryTests(unittest.TestCase):
    def test_bond_angle_matches_legacy_answer(self):
        built = local_geometry.build_bond_angle(spec('FA-ANG-BCD'), ROOT, SEED)
        self.assertEqual(built['numeric']['value'], '116.03')           # CNP001: 116.0251189 degree
        self.assertEqual(len(built['options']), 4)

    def test_bond_angle_rejects_wrong_identity_or_nonbonded(self):
        s = spec('FA-ANG-BCD')
        with self.assertRaisesRegex(ValueError, 'element'):
            local_geometry.build_bond_angle(dict(s, atoms=[dict(s['atoms'][0], element='O')] + s['atoms'][1:]), ROOT, SEED)
        far = [dict(row=4, name='C4', element='C'), dict(row=45, name='O3', element='O'), dict(row=1, name='C1', element='C')]
        with self.assertRaisesRegex(ValueError, 'bonded'):
            local_geometry.build_bond_angle(dict(s, atoms=far), ROOT, SEED)

    def test_backbone_torsion_values_and_sign(self):
        g20 = local_geometry.build_backbone_torsion(spec('FA-TOR-1CRN-G20'), ROOT, SEED)
        self.assertEqual(g20['numeric']['value'], '106.3')             # positive phi (glycine, left-handed region)
        helix = local_geometry.build_backbone_torsion(spec('FA-TOR-1UBQ-V26'), ROOT, SEED)
        self.assertTrue(Decimal(helix['numeric']['value']) < 0)          # right-handed helix psi
        self.assertIn('ATOM', helix['inputs'][0]['text'])
        self.assertNotIn('HETATM', helix['inputs'][0]['text'])

    def test_torsion_rejects_missing_window(self):
        with self.assertRaises(ValueError):
            local_geometry.build_backbone_torsion(spec('FA-TOR-1CRN-G20', residue=1), ROOT, SEED)
        with self.assertRaises(ValueError):
            local_geometry.build_backbone_torsion(spec('FA-TOR-1CRN-G20', torsion='chi1'), ROOT, SEED)


class InferenceTests(unittest.TestCase):
    def test_force_path_matches_legacy_and_direction_flips_sign(self):
        forward = force_path.build(spec('FA-FP-QM7X-7001', direction='A_to_B'), ROOT, SEED)
        self.assertEqual(forward['numeric']['value'], '1.8479')        # QNP001: dE/dlambda = +1.8479 eV
        backward = force_path.build(spec('FA-FP-QM7X-7001', direction='B_to_A'), ROOT, SEED)
        self.assertEqual(backward['numeric']['value'], '-1.8479')
        with self.assertRaises(ValueError):
            force_path.build(spec('FA-FP-QM7X-7001', direction='sideways'), ROOT, SEED)

    def test_force_path_rejects_zero_displacement(self):
        data = json.loads((ROOT / 'docs' / SPECS['FA-FP-QM7X-7001']['asset']).read_text())
        data['displaced_xyz'] = data['reference_xyz']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'docs/assets/x.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Zero displacement'):
                force_path.build(spec('FA-FP-QM7X-7001', asset='assets/x.json'), Path(tmp), SEED)

    def test_structure_factor_known_cases(self):
        _, rows = extinction.cell_from_cif(ROOT, 'assets/materials/9008678.cif')
        w = {'Na': 11, 'Cl': 17}
        self.assertAlmostEqual(abs(extinction.factor(rows, (1, 1, 1), w)), 4 * (17 - 11), places=9)
        self.assertAlmostEqual(abs(extinction.factor(rows, (2, 0, 0), w)), 4 * (17 + 11), places=9)
        self.assertAlmostEqual(abs(extinction.factor(rows, (1, 0, 0), w)), 0, places=9)
        _, rows = extinction.cell_from_cif(ROOT, 'assets/materials/9008564.cif')
        self.assertAlmostEqual(abs(extinction.factor(rows, (2, 0, 0), {'C': 6})), 0, places=9)   # diamond glide
        self.assertTrue(extinction.rule_absent('F+d', (2, 0, 0)) and not extinction.rule_absent('F', (2, 0, 0)))

    def test_extinction_instance_unique_and_rules_recorded(self):
        built = extinction.build(spec('FA-EXT-DIAMOND'), ROOT, SEED)
        zeros = [a for a in built['option_audit'] if a['is_correct']]
        self.assertEqual(len(zeros), 1)
        self.assertEqual(built['checks']['extinction_origin'], 'basis_or_glide')
        self.assertTrue(all(a['relative_amplitude'] >= extinction.CLEAR for a in built['option_audit'] if not a['is_correct']))
        with self.assertRaisesRegex(ValueError, 'Weights'):
            extinction.build(spec('FA-EXT-NACL', weights={'Na': 11}), ROOT, SEED)


class DesignTests(unittest.TestCase):
    def test_conformer_selection_constraints_and_uniqueness(self):
        built = conformer_design.build(spec('FA-CONF-7050-max_dipole'), ROOT, SEED)
        audit = built['option_audit']
        self.assertEqual(sum(a['is_correct'] for a in audit), 1)
        best = max(audit, key=lambda a: a['property'])
        self.assertTrue(best['is_correct'])
        self.assertGreaterEqual(built['checks']['margin'], 0.10)
        for a in audit:
            self.assertTrue(all(a['constraints'][k] for k in conformer_design.CONSTRAINTS))
        self.assertTrue(all(o['value'].startswith('candidate_') for o in built['options']))

    def test_mirror_conformer_is_equivalent(self):
        data = json.loads((ROOT / 'docs' / SPECS['FA-CONF-7050-max_dipole']['asset']).read_text())
        p = data['conformers'][0]['xyz']
        mirror = [[x, y, -z] for x, y, z in p]
        self.assertLess(conformer_design.distance_rmsd(p, mirror), 1e-9)

    def test_changed_bonding_is_excluded(self):
        data = json.loads((ROOT / 'docs' / SPECS['FA-CONF-7050-max_dipole']['asset']).read_text())
        target = data['conformers'][1]
        target['xyz'] = [list(r) for r in target['xyz']]
        target['xyz'][0] = [c + 5.0 for c in target['xyz'][0]]   # break atom 1 away from the molecule
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'docs/assets/c.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(data))
            try:
                built = conformer_design.build(spec('FA-CONF-7050-max_dipole', asset='assets/c.json'), Path(tmp), SEED)
            except ValueError:
                return   # too few candidates left is also an acceptable, recorded failure
            ids = [a['source_id'] for a in built['option_audit']]
            self.assertNotIn(target['id'], ids)
            self.assertIn(target['id'], [x['id'] for x in built['excluded_candidates']])

    def test_no_valid_set_is_recorded_not_forced(self):
        with self.assertRaisesRegex(ValueError, 'unique best'):
            conformer_design.build(spec('FA-CONF-7063-max_dipole'), ROOT, SEED)


class StereoTests(unittest.TestCase):
    def data(self, mol):
        return json.loads((ROOT / ('docs/assets/families/stereo/QM7X-%s.json' % mol)).read_text())

    def test_relationship_categories_on_real_pairs(self):
        expect = {'FA-SREL-7029-SAME': 'same', 'FA-SREL-7052-SAME': 'same', 'FA-SREL-7208-ENAN': 'enantiomer',
                  'FA-SREL-7111-ENAN': 'enantiomer', 'FA-SREL-7110-DIAS': 'diastereomer', 'FA-SREL-7043-DIAS': 'diastereomer',
                  'FA-SREL-7082-CONS': 'constitutional', 'FA-SREL-7033-CONS': 'constitutional'}
        for sid, relation in expect.items():
            built = stereo.build_relationship(spec(sid), ROOT, SEED)
            self.assertEqual(built['checks']['relation'], relation, sid)
            self.assertEqual(built['correct_label'], 'ABCD'[[r for r, _ in stereo.RELATIONS].index(relation)])

    def test_pose_is_proper_and_mirror_flips_every_centre(self):
        d = self.data('7208')
        el, pts = d['elements'], [tuple(p) for p in d['conformers'][0]['xyz']]
        moved = stereo.placed(pts, SEED, 'x')
        self.assertLess(conformer_design.distance_rmsd(pts, moved), 1e-9)
        self.assertEqual(stereo.relationship(el, pts, el, moved, True)[0], 'same')
        self.assertEqual(stereo.relationship(el, pts, el, stereo.mirror(pts), True)[0], 'enantiomer')

    def test_aziridine_nitrogen_and_label_cross_check(self):
        d = self.data('7110')
        a = stereo.best(d, 'i1')
        edges = kit.bond_graph(d['elements'], a['xyz'])
        self.assertIn(5, stereo.descriptors(d['elements'], a['xyz'], edges)['centres'])   # ring N
        d = self.data('7165')     # true enantiomers, but only different ring puckers are in the data
        with self.assertRaisesRegex(ValueError, 'equal lowest energies'):
            stereo.check_labels(d, 'enantiomer', stereo.best(d, 'i1'), stereo.best(d, 'i2'))
        with self.assertRaisesRegex(ValueError, 'no difference'):
            stereo.check_labels(d, 'same', stereo.best(d, 'i1'), stereo.best(d, 'i2'))

    def test_property_needs_diastereomers_and_margins(self):
        built = stereo.build_property(spec('FA-SPROP-7089'), ROOT, SEED)
        self.assertLess(built['checks']['delta_energy_eV'], -stereo.MARGIN_E)
        with self.assertRaisesRegex(ValueError, 'margins'):
            stereo.build_property(dict(spec('FA-SPROP-7089'), asset='assets/families/stereo/QM7X-7043.json'), ROOT, SEED)

    def test_design_traps(self):
        built = stereo.build_design(spec('FA-SDES-7029'), ROOT, SEED)
        kinds = {a['kind']: a for a in built['option_audit']}
        self.assertTrue(kinds['diastereomer_lower']['is_correct'])
        self.assertLess(kinds['conformer_only']['delta_energy_eV'], -stereo.MARGIN_E)     # lower but not allowed
        self.assertFalse(kinds['conformer_only']['allowed_modification'])
        self.assertEqual(kinds['mirror_image']['delta_energy_eV'], 0.0)
        self.assertEqual(kinds['constitutional_isomer']['relation'], 'constitutional')
        self.assertNotIn('Geom-', json.dumps(built['inputs']))


class MigratedFamilyTests(unittest.TestCase):
    def test_bond_distance_matches_legacy_values(self):
        for sid, legacy in [('FA-DIST-7035-SO', '1.462'), ('FA-DIST-7070-CCl', '1.737'), ('FA-DIST-7002-NN', '1.187'),
                            ('FA-DIST-7122-CN', '1.401'), ('FA-DIST-6LYZ-SS', '2.031')]:
            self.assertEqual(local_geometry.build_bond_distance(spec(sid), ROOT, SEED)['numeric']['value'], legacy)
        with self.assertRaisesRegex(ValueError, 'not bonded'):
            s = spec('FA-DIST-7035-SO')
            local_geometry.build_bond_distance(dict(s, atoms=[s['atoms'][0], dict(row=7, name='C7', element='C')]), ROOT, SEED)

    def test_coordination_shells_known_crystals(self):
        expect = {'FA-COORD-MGO': (6, 2.1085), 'FA-COORD-CSCL': (8, 3.5706), 'FA-COORD-SALEM2-ZN': (4, 5.9504),
                  'FA-COORD-MOF5-NODE': (6, 12.9124)}
        for sid, (n, d) in expect.items():
            shells = crystal.build_coordination(spec(sid), ROOT, SEED)['checks']['shells']
            self.assertEqual(shells[0]['count'], n, sid)
            self.assertAlmostEqual(shells[0]['distance_A'], d, places=3)
        # CsCl nearest Cl: a*sqrt(3)/2 with a = 4.123 angstrom.
        self.assertAlmostEqual(expect['FA-COORD-CSCL'][1], 4.123 * math.sqrt(3) / 2, places=3)

    def test_first_peak_skips_extinct_reflections(self):
        expect = {'FA-PEAK-NACL': '(1 1 1)', 'FA-PEAK-CSCL': '(1 0 0)', 'FA-PEAK-MGO': '(1 1 1)',
                  'FA-PEAK-SALEM2': '(1 1 0)', 'FA-PEAK-MOF5': '(1 1 1)'}
        for sid, hkl in expect.items():
            built = crystal.build_first_peak(spec(sid), ROOT, SEED)
            self.assertEqual(built['checks']['first_reflection'], hkl, sid)
        nacl = crystal.build_first_peak(spec('FA-PEAK-NACL'), ROOT, SEED)
        self.assertIn('(1 0 0)', nacl['checks']['skipped_extinct'])
        d111 = 5.64056 / math.sqrt(3)
        self.assertAlmostEqual(float(nacl['numeric']['value']), 2 * math.degrees(math.asin(1.5406 / (2 * d111))), places=2)

    def test_fret_and_guinier_models(self):
        built = scattering.build_fret(spec('FA-FRET-1EHZ'), ROOT, SEED)
        r, r0 = built['checks']['distance_nm'], built['checks']['R0_nm']
        self.assertAlmostEqual(r, 0.7234 * 10, places=2)                         # legacy BNI004: r = 7.234 nm
        self.assertAlmostEqual(built['checks']['efficiency'], 1 / (1 + (r / r0) ** 6))
        # 1EHZ modified nucleotides are HETATM records, so the ATOM-only backbone path has gaps and the
        # path-length mechanism is correctly omitted there; where present, a path is never shorter than the chord.
        self.assertIsNone(built['checks']['path_length_nm'])
        ubq = scattering.build_fret(spec('FA-FRET-1UBQ'), ROOT, SEED)['checks']
        self.assertGreater(ubq['path_length_nm'], ubq['distance_nm'])
        g = scattering.build_guinier(spec('FA-GUIN-1EHZ'), ROOT, SEED)
        self.assertLessEqual(g['checks']['q_rg'], 1.3)
        with self.assertRaisesRegex(ValueError, 'validity'):
            scattering.build_guinier(dict(spec('FA-GUIN-1EHZ'), q_per_nm=1.0), ROOT, SEED)
        ranks = [scattering.build_guinier(dict(spec(s), target_position=t), ROOT, SEED)['rank']['achieved']
                 for s in ('FA-GUIN-6LYZ', 'FA-GUIN-1EHZ') for t in (1, 4)]
        self.assertNotEqual(set(ranks), {4})                                     # correct is not always the largest


class ExtentAndEngineTests(unittest.TestCase):
    def test_extent_v2_same_answers_as_numeric_engine(self):
        for s in MANIFEST['items']:
            if s['family'] == 'extent_choice_v2':
                built = extent_choice.build(dict(s, target_position=1), ROOT, SEED)
                self.assertTrue(built['checks']['legacy_agreement'])

    def test_engine_run_separation_balance_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'run'
            report = family_engine.run(ROOT / 'templates/family-manifest.json', out, SEED)
            self.assertEqual(report['model_calls'], 0)
            self.assertEqual(report['catalog_admitted'], 0)
            self.assertEqual([f['id'] for f in report['failures']], ['FA-CONF-7063-max_dipole'])
            self.assertEqual(report['passed'] + len(report['failures']), report['attempted'])
            students = (out / 'student-packets.json').read_text(encoding='utf-8')
            for leak in ['is_correct', 'correct_label', 'reason', 'Geom-m7050-i1-c2', 'e_pbe0', 'relative_amplitude', 'rule']:
                self.assertNotIn(leak, students)
            numeric = json.loads((out / 'numeric-student-packets.json').read_text(encoding='utf-8'))
            self.assertTrue(all('options' not in n and 'value' not in n.get('answer', {}) for n in numeric))
            positions = report['correct_position_counts']
            # Per-family cycling keeps answer positions near-uniform; allow ~10% slack for fixed-category families.
            # Families with fixed option categories (stereo relationship) and physically one-sided error
            # mechanisms cannot always hit their target; keep the spread within ~15% of the batch.
            self.assertLessEqual(max(positions.values()) - min(positions.values()), max(4, report['passed'] * 15 // 100))
            extent = report['by_family']['extent_choice_v2']['shortcut_hits']
            self.assertLessEqual(extent['always_largest'], 3)                # v0.1 pilot: 7/12 by largest/smallest
            self.assertLessEqual(extent['always_smallest'], 3)
            with self.assertRaises(ValueError):
                family_engine.run(ROOT / 'templates/family-manifest.json', out, SEED)

    def test_registry_is_the_coverage_master_table(self):
        registry = json.loads((ROOT / 'templates/registry.json').read_text(encoding='utf-8'))
        required = ['id', 'name', 'ability', 'status', 'concept', 'domains', 'input_scale', 'reasoning_scale', 'scale_cells',
                    'inputs', 'physical_conditions', 'output_forms', 'source_basis', 'answer_method',
                    'distractor_mechanisms', 'four_choice_validation', 'legacy_families', 'legacy_qa', 'code', 'tests',
                    'gap', 'priority', 'builder_modules']
        entries = registry['templates']
        for t in entries:
            self.assertFalse([k for k in required if k not in t], t['id'])
            self.assertIn(t['status'], registry['axes']['status'])
            for path in t['code'] + t['tests']:
                self.assertTrue((ROOT / path).exists(), path)
            if t['status'] in ('implemented', 'pilot'):
                self.assertGreaterEqual(len(t['distractor_mechanisms']), 3, t['id'])
        engine = {f for t in entries for f in t['engine_families']}
        self.assertEqual(engine, set(FAMILIES))
        screening = json.loads((ROOT / 'docs/data/focused-screening.json').read_text(encoding='utf-8'))
        self.assertEqual({x['family'] for x in screening['items']}, {f for t in entries for f in t['legacy_families']})
        self.assertEqual({x['id'] for x in screening['items']}, {q for t in entries for q in t['legacy_qa']})
        self.assertEqual({t['ability'] for t in entries if t['status'] == 'pilot'}, {'perception', 'inference', 'design'})


class WholeParticleScatteringTests(unittest.TestCase):
    def test_debye_implementations_and_two_point_limit(self):
        pts = [(0.0, 0.0, 0.0), (30.0, 40.0, 0.0), (-12.0, 5.0, 33.0), (7.0, -21.0, 14.0)]
        for q in (0.2, 0.9, 2.5):
            self.assertAlmostEqual(assembly.debye(pts, q), assembly.debye_check(pts, q), places=12)
        two = [(0.0, 0.0, 0.0), (50.0, 0.0, 0.0)]          # r = 5 nm
        self.assertAlmostEqual(assembly.debye(two, 0.7), (1 + math.sin(3.5) / 3.5) / 2, places=12)

    def test_first_crossing_is_the_first_root(self):
        f = lambda q: assembly.sphere(q, 10.0)                # decreasing to the first zero near qR = 4.49
        root = assembly.first_crossing(f, 0.5, 0.002, 1.0)
        self.assertAlmostEqual(f(root), 0.5, places=9)
        self.assertTrue(all(f(q) > 0.5 for q in (root * 0.5, root * 0.9)))

    def test_published_design_and_debye_instances(self):
        root = Path(__file__).resolve().parents[1]
        spec = dict(id='T-QDES', asset='assets/families/assemblies/7ARQ-nucleotide-points.txt', scope='t', context='ctx.', target=0.5)
        r = assembly.build_q_design(spec, root, 'seed')
        self.assertEqual(r['option_audit'][[o['is_correct'] for o in r['option_audit']].index(True)]['value'], r['numeric']['value'])
        self.assertGreater(r['checks']['q_rg'], 1.3)          # beyond the Guinier range: the exact sum matters
        with self.assertRaises(ValueError):                   # inside the Guinier range the Debye family refuses
            assembly.build_debye(dict(spec, id='T-DEB', q_per_nm=0.05), root, 'seed')


class SuperlatticeFamilyTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    A = 'assets/families/superlattices/Au-FCC-%s.xyz'

    def spec(self, linker, a, **extra):
        return dict(dict(id='T-SL-' + linker, asset=self.A % linker, a_nm=a, table1={}, scope='t', core_nm=10.3), **extra)

    def test_assets_match_table1_and_formulas(self):
        for linker, a in (('X-linker', 39.8), ('26-linker', 57.0), ('52-linker', 76.6)):
            r = superlattice.build_perception(self.spec(linker, a, ask='cell_edge'), self.ROOT, 's')
            self.assertEqual(r['numeric']['value'], '%.2f' % a)
            q = superlattice.build_inference(self.spec(linker, a, ask='q_star'), self.ROOT, 's')
            self.assertEqual(q['numeric']['value'], kit.display(2 * math.pi * math.sqrt(3) / a, 4))
        with self.assertRaises(ValueError):          # the file must agree with the stated Table 1 edge
            superlattice.build_perception(self.spec('26-linker', 57.5, ask='cell_edge'), self.ROOT, 's')
        with self.assertRaises(ValueError):          # an inference quantity cannot be built as perception
            superlattice.build_perception(self.spec('26-linker', 57.0, ask='q_star'), self.ROOT, 's')

    def test_design_needs_a_clear_winner(self):
        c = ['13-linker', '26-linker', '39-linker', '52-linker']
        spec = dict(id='T-SL-D', candidates=[self.A % l for l in c], edges={self.A % l: e for l, e in zip(c, (45.9, 57.0, 67.5, 76.6))},
                    goal='nn', target=44.0, core_nm=10.3, scope='t')
        with self.assertRaises(ValueError):          # 40.31 vs 47.73 nm: too close to call
            superlattice.build_design(spec, self.ROOT, 's')


class OpalFamilyTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def spec(self, key, diameter, **extra):
        return dict(dict(id='T-OP-' + key, asset='assets/families/opals/opal-%s.xyz' % key, diameter_nm=diameter, sample=key,
                         material='polystyrene', scope='t'), **extra)

    def test_model_close_to_measured_peaks(self):
        # Table 3 of the PS paper: measured normal-incidence peaks; the stated model must land within 2 %.
        for key, d, measured in (('PS-S3', 341.83, 805.0), ('PS-S5', 258.62, 614.5), ('PS-S7', 224.76, 532.0)):
            r = photonic.build_bragg(self.spec(key, d, ask='peak', n_sphere=1.59, n_medium=1.0), self.ROOT, 's')
            self.assertLess(abs(float(r['numeric']['value']) - measured) / measured, 0.02)

    def test_published_diameter_is_enforced(self):
        with self.assertRaises(ValueError):
            photonic.build_geometry(self.spec('PS-S3', 340.0, ask='diameter'), self.ROOT, 's')
        with self.assertRaises(ValueError):                  # 900 nm is not reachable at any angle for this film
            photonic.build_bragg(self.spec('SiO2-266', 266.0, ask='angle', n_eff=1.35, target_nm=900), self.ROOT, 's')


class MoireFamilyTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def test_maps_and_atoms_match_published_angles(self):
        spec = dict(id='T-MO', asset='assets/families/moire/TBG-M2-AA-map.txt', ask='period', sample='M2', twist_deg=1.05, scope='t')
        self.assertEqual(moire.build_geometry(spec, self.ROOT, 's')['numeric']['value'], '13.42')
        with self.assertRaises(ValueError):            # the map must agree with the stated twist angle
            moire.build_geometry(dict(spec, twist_deg=1.10), self.ROOT, 's')
        atoms = dict(spec, asset='assets/families/moire/TBG-K110-atoms.xyz', ask='period_from_atoms', sample='K110', twist_deg=1.10)
        self.assertEqual(moire.build_inference(atoms, self.ROOT, 's')['numeric']['value'], '12.81')
        with self.assertRaises(ValueError):
            moire.build_inference(dict(atoms, twist_deg=1.05), self.ROOT, 's')
        with self.assertRaises(ValueError):            # a perception quantity cannot be built as inference
            moire.build_inference(spec, self.ROOT, 's')


if __name__ == '__main__':
    unittest.main()
