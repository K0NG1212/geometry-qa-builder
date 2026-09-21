import unittest, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XYZ = ROOT / 'docs' / 'assets' / 'qa' / 'DMBCD.xyz'


def read_xyz(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    n = int(lines[0])
    rows = []
    for line in lines[2:2 + n]:
        elem, x, y, z = line.split()
        rows.append((elem, float(x), float(y), float(z)))
    return rows


def angle_acos(a, vertex, b):
    u = [x - y for x, y in zip(a, vertex)]
    v = [x - y for x, y in zip(b, vertex)]
    dot = sum(p * q for p, q in zip(u, v))
    nu = math.sqrt(sum(p * p for p in u))
    nv = math.sqrt(sum(p * p for p in v))
    return math.degrees(math.acos(max(-1, min(1, dot / (nu * nv)))))


def angle_atan2(a, vertex, b):
    u = [x - y for x, y in zip(a, vertex)]
    v = [x - y for x, y in zip(b, vertex)]
    cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    cross_mag = math.sqrt(sum(c * c for c in cross))
    dot = sum(x * y for x, y in zip(u, v))
    return math.degrees(math.atan2(cross_mag, dot))


class DMBCDGeometryChecks(unittest.TestCase):
    def setUp(self):
        rows = read_xyz(XYZ)
        self.xyz = [(x, y, z) for _, x, y, z in rows]

    def idx(self, i):
        return self.xyz[i - 1]

    def test_atom_count(self):
        self.assertEqual(len(self.xyz), 189)

    def test_bridging_angle_matches_published_bcd_value(self):
        c4, o3, c37 = self.idx(4), self.idx(46), self.idx(37)
        angle = angle_acos(c4, o3, c37)
        self.assertAlmostEqual(angle, 116.0251189, places=5)

    def test_two_angle_formulas_agree(self):
        c3, o2, cme = self.idx(3), self.idx(44), self.idx(45)
        a1 = angle_acos(c3, o2, cme)
        a2 = angle_atan2(c3, o2, cme)
        self.assertAlmostEqual(a1, a2, places=9)

    def test_ether_bond_lengths_are_chemically_reasonable(self):
        o2, cme, c3 = self.idx(44), self.idx(45), self.idx(3)
        d1 = math.dist(o2, cme)
        d2 = math.dist(c3, o2)
        # sp3 C-O single bonds are typically 1.40-1.45 angstrom
        self.assertTrue(1.35 < d1 < 1.50)
        self.assertTrue(1.35 < d2 < 1.50)


class AngleFormulaChecks(unittest.TestCase):
    def test_right_angle(self):
        a, vertex, b = (1, 0, 0), (0, 0, 0), (0, 1, 0)
        self.assertAlmostEqual(angle_acos(a, vertex, b), 90.0)
        self.assertAlmostEqual(angle_atan2(a, vertex, b), 90.0)


if __name__ == '__main__':
    unittest.main()
