import unittest, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDB = ROOT / 'docs' / 'assets' / 'bio' / '1CRN.pdb'


def read_atoms(path, name):
    rows = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.startswith('ATOM') and line[12:16].strip() == name:
            resi = int(line[22:26])
            x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
            rows[resi] = (x, y, z)
    return rows


class DisulfideChecks(unittest.TestCase):
    def setUp(self):
        self.sg = read_atoms(PDB, 'SG')

    def test_three_sg_pairs_present(self):
        for resi in [3, 4, 16, 26, 32, 40]:
            self.assertIn(resi, self.sg)

    def test_ssbond_distances_match_file_reported_values(self):
        pairs = [((3, 40), 2.00), ((4, 32), 2.04), ((16, 26), 2.05)]
        for (a, b), reported in pairs:
            d = math.dist(self.sg[a], self.sg[b])
            self.assertAlmostEqual(d, reported, delta=0.01)

    def test_pair_3_40_and_4_32_cluster_under_one_nm(self):
        pts = [self.sg[r] for r in (3, 40, 4, 32)]
        best = max(math.dist(pts[i], pts[j]) for i in range(4) for j in range(i + 1, 4))
        self.assertLess(best, 10.0)  # angstrom

    def test_all_three_disulfides_exceed_one_nm_together(self):
        pts = list(self.sg.values())
        best = max(math.dist(pts[i], pts[j]) for i in range(len(pts)) for j in range(i + 1, len(pts)))
        self.assertGreater(best, 10.0)  # angstrom


class HelixCrossProteinChecks(unittest.TestCase):
    def test_i_plus_4_spacing_close_to_lysozyme_value(self):
        ca = read_atoms(PDB, 'CA')
        d = math.dist(ca[9], ca[13])
        # bio-nm-v04-003 BNP009 (6LYZ Ca27-Ca31) = 6.248 A
        self.assertAlmostEqual(d, 6.248, delta=0.3)


if __name__ == '__main__':
    unittest.main()
