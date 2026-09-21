"""Portable checks for the materials x 1-10 nm batch (materials-nm-v04-001):
MNP006-010, MNI006-010. Reads only committed docs/assets/qa/*.xyz and
*-input.txt files (never runs/, which is gitignored and not present on a
fresh clone), and recomputes every answer with a fresh, independent
implementation.
"""
import cmath
import json
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA_DIR = ROOT / 'docs' / 'assets' / 'qa'


def read_xyz(path):
    lines = (QA_DIR / path).read_text(encoding='utf-8').splitlines()
    n = int(lines[0])
    rows = []
    for line in lines[2:2 + n]:
        parts = line.split()
        rows.append((parts[0], tuple(float(x) for x in parts[1:4])))
    return rows


def max_pairwise(rows):
    coords = [r[1] for r in rows]
    best = 0.0
    best_pair = None
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            d = math.dist(coords[i], coords[j])
            if d > best:
                best = d
                best_pair = (i + 1, j + 1)
    return best, best_pair


def d_spacing_nm(a_A, hkl):
    h, k, l = hkl
    return (a_A / math.sqrt(h * h + k * k + l * l)) / 10


def two_theta_deg(d_nm, wavelength_nm=0.15406, n=1):
    return 2 * math.degrees(math.asin(n * wavelength_nm / (2 * d_nm)))


def structure_factor_amplitude(rows, a_A, hkl, weights):
    h, k, l = hkl
    total = 0j
    for elem, (x, y, z) in rows:
        fx, fy, fz = x / a_A, y / a_A, z / a_A
        phase = 2 * math.pi * (h * fx + k * fy + l * fz)
        total += weights[elem] * cmath.exp(1j * phase)
    return abs(total)


class GlobalExtentChecks(unittest.TestCase):
    def test_mnp006_zif8_zn(self):
        rows = read_xyz('MNP006-ZIF8-Zn.xyz')
        self.assertEqual(len(rows), 12)
        d, pair = max_pairwise(rows)
        self.assertAlmostEqual(d, 17.8512, places=3)
        self.assertEqual(pair, (3, 12))

    def test_mnp007_mof5_zn(self):
        rows = read_xyz('MNP007-MOF5-Zn.xyz')
        self.assertEqual(len(rows), 32)
        d, pair = max_pairwise(rows)
        self.assertAlmostEqual(d, 23.9459, places=3)
        self.assertEqual(pair, (1, 32))

    def test_mnp010_mof5_full(self):
        rows = read_xyz('MNP010-MOF5-full.xyz')
        self.assertEqual(len(rows), 424)
        d, pair = max_pairwise(rows)
        self.assertAlmostEqual(d, 30.6102, places=3)
        self.assertEqual(pair, (233, 328))

    def test_all_global_extents_are_1_to_10_nm(self):
        for fname in ['MNP006-ZIF8-Zn.xyz', 'MNP007-MOF5-Zn.xyz', 'MNP010-MOF5-full.xyz']:
            rows = read_xyz(fname)
            d, _ = max_pairwise(rows)
            self.assertTrue(10.0 <= d < 100.0, f'{fname}: dmax={d} A not in [10,100) A (i.e. [1,10) nm)')


class PlaneSpacingChecks(unittest.TestCase):
    def test_mnp008_zif8_d110(self):
        d = d_spacing_nm(16.8303, (1, 1, 0))
        self.assertAlmostEqual(d, 1.190082, places=5)
        self.assertTrue(1.0 <= d < 10.0)

    def test_mnp009_mof5_d111(self):
        d = d_spacing_nm(25.8247, (1, 1, 1))
        self.assertAlmostEqual(d, 1.490990, places=5)
        self.assertTrue(1.0 <= d < 10.0)


class BraggAngleChecks(unittest.TestCase):
    def test_mni006_zif8_two_theta(self):
        d = d_spacing_nm(16.8303, (1, 1, 0))
        tt = two_theta_deg(d)
        self.assertAlmostEqual(tt, 7.42, places=1)

    def test_mni007_mof5_two_theta(self):
        d = d_spacing_nm(25.8247, (1, 1, 1))
        tt = two_theta_deg(d)
        self.assertAlmostEqual(tt, 5.92, places=1)
        # MOF-5's larger d-spacing must give a smaller angle than ZIF-8's
        tt_zif8 = two_theta_deg(d_spacing_nm(16.8303, (1, 1, 0)))
        self.assertLess(tt, tt_zif8)


class StructureFactorExtinctionChecks(unittest.TestCase):
    Z = {'Zn': 30, 'N': 7, 'C': 6, 'H': 1, 'O': 8}

    def test_mni008_zif8_body_centered_rule(self):
        rows = read_xyz('MNI008-ZIF8-full.xyz')
        self.assertEqual(len(rows), 204)
        f100 = structure_factor_amplitude(rows, 16.8303, (1, 0, 0), self.Z)
        f110 = structure_factor_amplitude(rows, 16.8303, (1, 1, 0), self.Z)
        f200 = structure_factor_amplitude(rows, 16.8303, (2, 0, 0), self.Z)
        f111 = structure_factor_amplitude(rows, 16.8303, (1, 1, 1), self.Z)
        # h+k+l odd -> absent; h+k+l even -> present (I-centering rule)
        self.assertLess(f100, 1e-6)
        self.assertLess(f111, 1e-6)
        self.assertAlmostEqual(f110, 331.5155, places=2)
        self.assertAlmostEqual(f200, 196.9412, places=2)

    def test_mni009_mof5_face_centered_rule(self):
        rows = read_xyz('MNI009-MOF5-full.xyz')
        self.assertEqual(len(rows), 424)
        f100 = structure_factor_amplitude(rows, 25.8247, (1, 0, 0), self.Z)
        f110 = structure_factor_amplitude(rows, 25.8247, (1, 1, 0), self.Z)
        f200 = structure_factor_amplitude(rows, 25.8247, (2, 0, 0), self.Z)
        f111 = structure_factor_amplitude(rows, 25.8247, (1, 1, 1), self.Z)
        # mixed parity -> absent; all-same parity -> present (F-centering rule)
        self.assertLess(f100, 1e-6)
        self.assertLess(f110, 1e-6)
        self.assertAlmostEqual(f200, 1874.1986, places=2)
        self.assertAlmostEqual(f111, 70.6477, places=2)

    def test_mni010_different_centering_types(self):
        # The point of MNI010: ZIF-8 (I-centered) and MOF-5 (F-centered) obey
        # genuinely different selection rules, confirmed independently here.
        zif8 = read_xyz('MNI008-ZIF8-full.xyz')
        mof5 = read_xyz('MNI009-MOF5-full.xyz')
        # (1,1,0): present for I-centering (h+k+l=2 even), absent for F-centering (mixed parity)
        f_zif8_110 = structure_factor_amplitude(zif8, 16.8303, (1, 1, 0), self.Z)
        f_mof5_110 = structure_factor_amplitude(mof5, 25.8247, (1, 1, 0), self.Z)
        self.assertGreater(f_zif8_110, 1.0)
        self.assertLess(f_mof5_110, 1e-6)


class CatalogEntryChecks(unittest.TestCase):
    def test_ten_materials_nm_entries_present_and_reasoning_scale_in_cell(self):
        cat = json.loads((ROOT / 'docs' / 'data' / 'catalog.json').read_text(encoding='utf-8'))
        by_id = {q['id']: q for q in cat['questions']}
        ids = ['MNP006', 'MNP007', 'MNP008', 'MNP009', 'MNP010', 'MNI006', 'MNI007', 'MNI008', 'MNI009', 'MNI010']
        for qid in ids:
            self.assertIn(qid, by_id, f'{qid} missing from catalog.json')
            q = by_id[qid]
            self.assertEqual(q['domain'], 'materials')
            self.assertTrue(1.0 <= q['reasoningSizeNm'] < 10.0, f'{qid} reasoningSizeNm={q["reasoningSizeNm"]} not in [1,10) nm')
            self.assertEqual(q['batchId'], 'materials-nm-v04-001')
            self.assertTrue(Path(ROOT / 'docs' / q['inputDownload']).exists())


if __name__ == '__main__':
    unittest.main()
