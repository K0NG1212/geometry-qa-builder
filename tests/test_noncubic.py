"""Non-cubic crystal cells (task_families/cell.py, checkers/cells.py): two independent CIF expansions agree, published
answers match known diffraction lines, and tampering with the cell or the atom list is caught."""
import copy
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checkers  # noqa: E402
import verify_all  # noqa: E402
from checkers import cells as checker_cells  # noqa: E402
from task_families import cell as generator_cells  # noqa: E402

WORKBENCH = json.loads((ROOT / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
PACKETS = {p['id']: p for p in verify_all.rehydrate(copy.deepcopy(WORKBENCH['student_packets']))}
KEYS = {k['id']: k for k in WORKBENCH['teacher_answers']}
NONCUBIC = ('9004141', '9004137', '2300112', '5000035')


def pair(iid):
    return copy.deepcopy(PACKETS[iid]), copy.deepcopy(KEYS[iid])


def fails(packet, key, fragment=''):
    r = checkers.check(packet, key)
    return r['status'] == 'fail' and fragment in r['problem']


class ExpansionTests(unittest.TestCase):
    def test_generator_and_checker_expand_every_cif_alike(self):
        for path in sorted((ROOT / 'docs/assets/materials').glob('*.cif')):
            gp, ga = generator_cells.read_cif(path)
            cp, ca = checker_cells.cif_cell(path)
            self.assertEqual(gp, cp, path.name)
            self.assertEqual(Counter(e for e, _ in ga), Counter(e for e, _ in ca), path.name)

    def test_known_compositions(self):
        expect = {'9004141': {'Ti': 2, 'O': 4}, '9004137': {'Ti': 8, 'O': 16}, '2300112': {'Zn': 2, 'O': 2}, '5000035': {'Si': 3, 'O': 6}}
        for cod, comp in expect.items():
            _, atoms = generator_cells.read_cif(ROOT / ('docs/assets/materials/%s.cif' % cod))
            self.assertEqual(dict(Counter(e for e, _ in atoms)), comp, cod)

    def test_truncated_special_positions_are_snapped(self):
        self.assertEqual(generator_cells.snap(0.3333), 1 / 3)
        self.assertEqual(generator_cells.snap(0.6667), 2 / 3)
        self.assertEqual(generator_cells.snap(0.3823), 0.3823)

    def test_metric_matches_lattice_vectors(self):
        for cod in NONCUBIC:
            params, atoms = generator_cells.read_cif(ROOT / ('docs/assets/materials/%s.cif' % cod))
            cell = generator_cells.GeneralCell(**params)
            G = checker_cells.metric(params)
            Ginv = __import__('numpy').linalg.inv(G)
            for hkl in ((1, 0, 0), (1, 1, 0), (1, -1, 1), (2, 1, 3)):
                self.assertAlmostEqual(cell.d(hkl), checker_cells.d_spacing(Ginv, hkl), places=9)
            f, g = atoms[0][1], [x + 0.37 for x in atoms[-1][1]]
            import math
            self.assertAlmostEqual(math.dist(cell.cart(f), cell.cart(g)), checker_cells.distance(G, f, g), places=9)


class PublishedTests(unittest.TestCase):
    def test_first_peaks_match_known_lines(self):
        # Cu K-alpha: rutile (110) 27.45 deg, zincite (100) 31.77 deg (standard powder patterns).
        self.assertAlmostEqual(float(KEYS['FA-PEAK-RUTILE']['numeric_answer']['value']), 27.45, delta=0.05)
        self.assertAlmostEqual(float(KEYS['FA-PEAK-ZNO']['numeric_answer']['value']), 31.77, delta=0.05)

    def test_noncubic_instances_pass(self):
        for iid in ('FA-COORD-RUTILE', 'FA-COORD-ZNO', 'FA-COORD-QUARTZ', 'FA-PEAK-RUTILE', 'FA-PEAK-ZNO', 'FA-PEAK-QUARTZ',
                    'FA-EXT-RUTILE', 'FA-EXT-BROOKITE', 'FA-EXT-ZNO'):
            self.assertEqual(checkers.check(*pair(iid))['status'], 'pass', iid)

    def test_rutile_shortest_bond_and_polyhedron_trap(self):
        p, k = pair('FA-COORD-RUTILE')
        right = [o['value'] for o in k['option_audit'] if o['is_correct']]
        self.assertEqual(right, ['4 at 1.947 Å'])                       # 4 short + 2 long Ti-O in distorted TiO6
        self.assertIn('whole_coordination_polyhedron', [o['rule'] for o in k['option_audit']])

    def test_no_symmetry_equivalent_distractor_pairs(self):
        for iid in ('FA-EXT-RUTILE', 'FA-EXT-BROOKITE', 'FA-EXT-ZNO'):
            p, k = pair(iid)
            params, rows = checker_cells.parse_table(p['inputs'][0]['text'])
            Ginv = __import__('numpy').linalg.inv(checker_cells.metric(params))
            ds = [round(checker_cells.d_spacing(Ginv, [int(x) for x in o['value'].strip('()').split()]), 6) for o in p['options']]
            amps = [round(o['relative_amplitude'], 6) for o in k['option_audit']]
            self.assertEqual(len(set(zip(ds, amps))), 4, iid)

    def test_tampering_is_caught(self):
        p, k = pair('FA-COORD-RUTILE')
        lines = p['inputs'][0]['text'].splitlines()
        p['inputs'][0]['text'] = '\n'.join(lines[:-1]) + '\n'                # drop one O atom
        self.assertTrue(fails(p, k))
        p, k = pair('FA-PEAK-ZNO')
        p['inputs'][0]['text'] = p['inputs'][0]['text'].replace('c = 5.20540', 'c = 5.30540')
        self.assertTrue(fails(p, k))
        p, k = pair('FA-EXT-ZNO')
        p['inputs'][0]['text'] = p['inputs'][0]['text'].replace('gamma = 120.000', 'gamma = 90.000')
        self.assertTrue(fails(p, k, 'differ from the CIF'))


if __name__ == '__main__':
    unittest.main()
