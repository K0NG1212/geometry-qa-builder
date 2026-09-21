import unittest, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDB = ROOT / 'docs' / 'assets' / 'bio' / '1BNA.pdb'


def read_atoms(path):
    rows = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.startswith('ATOM'):
            name = line[12:16].strip()
            chain = line[21]
            resi = int(line[22:26])
            x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
            rows[(chain, resi, name)] = (x, y, z)
    return rows


class WatsonCrickChecks(unittest.TestCase):
    def setUp(self):
        self.rows = read_atoms(PDB)

    def test_gc_pair_has_three_hbond_atoms_each_side(self):
        for name in ('N1', 'N2', 'O6'):
            self.assertIn(('A', 2, name), self.rows)
        for name in ('N3', 'O2', 'N4'):
            self.assertIn(('B', 23, name), self.rows)

    def test_three_hbond_distances_in_classic_range(self):
        pairs = [(('A', 2, 'N1'), ('B', 23, 'N3')),
                 (('A', 2, 'N2'), ('B', 23, 'O2')),
                 (('A', 2, 'O6'), ('B', 23, 'N4'))]
        for a, b in pairs:
            d = math.dist(self.rows[a], self.rows[b])
            self.assertTrue(2.5 < d < 3.1, f'{a}-{b} = {d}')

    def test_pair_atom_set_stays_under_one_nm(self):
        atoms = [self.rows[('A', 2, n)] for n in ('N1', 'N2', 'O6')]
        atoms += [self.rows[('B', 23, n)] for n in ('N3', 'O2', 'N4')]
        best = max(math.dist(atoms[i], atoms[j]) for i in range(6) for j in range(i + 1, 6))
        self.assertLess(best, 10.0)  # angstrom


if __name__ == '__main__':
    unittest.main()
