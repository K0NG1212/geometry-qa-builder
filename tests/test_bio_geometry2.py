import unittest, importlib.util, math
from pathlib import Path
spec = importlib.util.spec_from_file_location('bio_calc2', Path(__file__).resolve().parents[1] / 'tools/recompute_bio_batch2.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RgAndDiameterChecks(unittest.TestCase):
    def test_known_triangle(self):
        pts = [(0, 0, 0), (3, 0, 0), (0, 4, 0)]
        self.assertAlmostEqual(m.rg_centroid(pts), math.sqrt(50 / 9))
        d, i, j = m.full_scan_max(pts)
        self.assertEqual(d, 5)
        self.assertEqual({i, j}, {1, 2})

    def test_two_rg_methods_agree_on_known_points(self):
        pts = [(0, 0, 0), (3, 0, 0), (0, 4, 0), (2, 1, 5), (-1, -2, 3)]
        a = m.rg_centroid(pts)
        b = m.rg_pairwise_identity_decimal(pts)
        self.assertAlmostEqual(a, b, places=9)

    def test_rigid_transform_scaling(self):
        points = [(0, 0, 0), (3, 0, 0), (0, 4, 0), (2, 1, 5)]
        rg1 = m.rg_centroid(points)
        transformed = [[-2 * y + 100, 2 * x - 30, 2 * z + 20] for x, y, z in points]
        rg2 = m.rg_centroid(transformed)
        self.assertAlmostEqual(rg2, 2 * rg1)


class AngleChecks(unittest.TestCase):
    def test_right_angle_both_methods(self):
        # vertex at origin, arms along +x and +y: exactly 90 degrees
        a, vertex, b = (1, 0, 0), (0, 0, 0), (0, 1, 0)
        self.assertAlmostEqual(m.angle_acos(a, vertex, b), 90.0)
        self.assertAlmostEqual(m.angle_atan2(a, vertex, b), 90.0)

    def test_straight_line_both_methods(self):
        a, vertex, b = (-1, 0, 0), (0, 0, 0), (1, 0, 0)
        self.assertAlmostEqual(m.angle_acos(a, vertex, b), 180.0)
        self.assertAlmostEqual(m.angle_atan2(a, vertex, b), 180.0)

    def test_methods_agree_on_arbitrary_triangle(self):
        a, vertex, b = (2, 5, -1), (0, 0, 0), (-3, 1, 4)
        self.assertAlmostEqual(m.angle_acos(a, vertex, b), m.angle_atan2(a, vertex, b), places=9)


class FretChecks(unittest.TestCase):
    def test_efficiency_half_at_r_equals_r0(self):
        # E = 1/[1+(r/R0)^6] must equal 0.5 exactly when r == R0
        r0 = 3.5
        r = r0
        e = 1 / (1 + (r / r0) ** 6)
        self.assertAlmostEqual(e, 0.5)

    def test_efficiency_near_zero_far_beyond_r0(self):
        r0 = 3.5
        r = 7.234215712155672
        e = 1 / (1 + (r / r0) ** 6)
        self.assertLess(e, 0.02)
        self.assertGreater(e, 0.0)


if __name__ == '__main__':
    unittest.main()
