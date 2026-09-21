import unittest, importlib.util, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def load(name, file):
    s = importlib.util.spec_from_file_location(name, file)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

m = load('material_calc2', ROOT / 'tools' / 'recompute_materials_batch2.py')
MATERIALS_DIR = ROOT / 'docs' / 'assets' / 'materials'


class SymmetryExpansionChecks(unittest.TestCase):
    def test_mgo_and_cscl_row_counts_and_lattice(self):
        mgo = m.read_cubic_cif(MATERIALS_DIR / '1000053.cif')
        cscl = m.read_cubic_cif(MATERIALS_DIR / '9008789.cif')
        self.assertEqual(len(mgo['rows']), 8)
        self.assertEqual(len(cscl['rows']), 2)
        self.assertAlmostEqual(mgo['a_A'], 4.217, places=3)
        self.assertAlmostEqual(cscl['a_A'], 4.123, places=3)

    def test_strip_element_rejects_and_accepts(self):
        self.assertEqual(m.strip_element('Mg2+'), 'Mg')
        self.assertEqual(m.strip_element('O1'), 'O')
        with self.assertRaises(AssertionError):
            m.strip_element('2x')


class CoordinationChecks(unittest.TestCase):
    def test_mgo_octahedral_shell_matches_closed_form(self):
        mgo = m.read_cubic_cif(MATERIALS_DIR / '1000053.cif')
        shell = m.neighbors_for_row0(mgo)
        self.assertEqual(shell['coordination'], 6)
        self.assertAlmostEqual(shell['distance_A'], mgo['a_A'] / 2, places=9)

    def test_cscl_cube_corner_shell_matches_closed_form(self):
        cscl = m.read_cubic_cif(MATERIALS_DIR / '9008789.cif')
        if cscl['rows'][0]['element'] != 'Cs':
            cscl['rows'] = list(reversed(cscl['rows']))
        shell = m.neighbors_for_row0(cscl)
        self.assertEqual(shell['coordination'], 8)
        self.assertAlmostEqual(shell['distance_A'], cscl['a_A'] * math.sqrt(3) / 2, places=9)
        angles = shell['angles_deg']
        self.assertEqual(len(angles), 3)
        self.assertAlmostEqual(min(angles), 70.528779, places=5)
        self.assertAlmostEqual(max(angles), 180.0, places=5)


class StructureFactorChecks(unittest.TestCase):
    def test_cscl_equal_weight_limit_is_bcc_selection_rule(self):
        crystal = {'rows': [
            {'element': 'Cs', 'fractional': [0, 0, 0]},
            {'element': 'Cl', 'fractional': [0.5, 0.5, 0.5]},
        ]}
        odd = m.structure_factor(crystal, (1, 0, 0), {'Cs': 1, 'Cl': 1})
        even = m.structure_factor(crystal, (1, 1, 0), {'Cs': 1, 'Cl': 1})
        self.assertAlmostEqual(odd['intensity'], 0.0, places=9)
        self.assertAlmostEqual(even['amplitude'], 2.0, places=9)

    def test_cscl_unequal_weight_all_survive(self):
        crystal = {'rows': [
            {'element': 'Cs', 'fractional': [0, 0, 0]},
            {'element': 'Cl', 'fractional': [0.5, 0.5, 0.5]},
        ]}
        for hkl in [(1, 0, 0), (1, 1, 0), (1, 1, 1)]:
            f = m.structure_factor(crystal, hkl, {'Cs': 55, 'Cl': 17})
            self.assertGreater(f['amplitude'], 0)


if __name__ == '__main__':
    unittest.main()
