import unittest, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDB = ROOT / 'docs' / 'assets' / 'bio' / '6LYZ.pdb'


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

    def test_all_eight_sg_present(self):
        for resi in [6, 30, 64, 76, 80, 94, 115, 127]:
            self.assertIn(resi, self.sg)

    def test_ssbond_distances_match_file_reported_values(self):
        # (residue pair, distance reported in this entry's own SSBOND record)
        pairs = [((6, 127), 2.03), ((30, 115), 2.04), ((64, 80), 2.01), ((76, 94), 2.11)]
        for (a, b), reported in pairs:
            d = math.dist(self.sg[a], self.sg[b])
            self.assertAlmostEqual(d, reported, delta=0.01)

    def test_disulfide_cluster_span_under_one_nm(self):
        # Cys64/76/80/94 SG atoms must stay within a 0.1-1 nm reasoning span
        # (this is what makes the BNI005 comparison task valid for that cell).
        pts = [self.sg[r] for r in (64, 76, 80, 94)]
        best = max(math.dist(pts[i], pts[j]) for i in range(4) for j in range(i + 1, 4))
        self.assertLess(best, 10.0)  # angstrom
        self.assertGreater(best, 1.0)

    def test_full_eight_sg_span_exceeds_one_nm(self):
        # confirms why all four disulfides cannot be asked about in one
        # 0.1-1 nm-cell question together
        pts = list(self.sg.values())
        best = max(math.dist(pts[i], pts[j]) for i in range(len(pts)) for j in range(i + 1, len(pts)))
        self.assertGreater(best, 10.0)  # angstrom, i.e. > 1 nm


class HelixChecks(unittest.TestCase):
    def setUp(self):
        self.ca = read_atoms(PDB, 'CA')

    def test_adjacent_residue_spacing_near_typical_value(self):
        d = math.dist(self.ca[27], self.ca[28])
        self.assertAlmostEqual(d, 3.8, delta=0.3)

    def test_i_plus_4_spacing_consistent_across_two_samples(self):
        d1 = math.dist(self.ca[27], self.ca[31])
        d2 = math.dist(self.ca[28], self.ca[32])
        self.assertAlmostEqual(d1, d2, delta=0.2)
        self.assertGreater(d1, math.dist(self.ca[27], self.ca[28]))


if __name__ == '__main__':
    unittest.main()
