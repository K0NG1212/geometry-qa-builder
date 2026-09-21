"""Portable checks for the chemistry x 1-10 nm batch (chem-nm-v04-001):
CNP007-011, CNI002-006. Reads only committed docs/assets/qa/*.xyz and
*-input.txt files (never runs/, which is gitignored and not present on a
fresh clone), and recomputes every answer with a fresh, independent
implementation.
"""
import json
import math
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


def dmax_scan(rows):
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


def dmin_scan(rows_a, rows_b):
    best = None
    best_pair = None
    for i, ra in enumerate(rows_a):
        for j, rb in enumerate(rows_b):
            d = math.dist(ra[1], rb[1])
            if best is None or d < best:
                best = d
                best_pair = (i + 1, j + 1)
    return best, best_pair


def radius_of_gyration(rows):
    coords = [r[1] for r in rows]
    n = len(coords)
    cx = sum(c[0] for c in coords) / n
    cy = sum(c[1] for c in coords) / n
    cz = sum(c[2] for c in coords) / n
    ssq = sum((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 for x, y, z in coords)
    return math.sqrt(ssq / n)


class GlobalExtentChecks(unittest.TestCase):
    def test_cnp007_chain_a(self):
        rows = read_xyz('CNP007-1AA5-chainA.xyz')
        self.assertEqual(len(rows), 132)
        d, pair = dmax_scan(rows)
        self.assertAlmostEqual(d, 19.5698, places=3)
        self.assertEqual(pair, (11, 132))

    def test_cnp008_chain_b(self):
        rows = read_xyz('CNP008-1AA5-chainB.xyz')
        self.assertEqual(len(rows), 132)
        d, pair = dmax_scan(rows)
        self.assertAlmostEqual(d, 19.2646, places=3)
        self.assertEqual(pair, (11, 132))

    def test_cnp009_dimer(self):
        rows = read_xyz('CNP009-1AA5-dimer.xyz')
        self.assertEqual(len(rows), 264)
        d, pair = dmax_scan(rows)
        self.assertAlmostEqual(d, 28.7192, places=3)
        self.assertEqual(pair, (11, 143))

    def test_all_global_extents_are_1_to_10_nm(self):
        for fname in ['CNP007-1AA5-chainA.xyz', 'CNP008-1AA5-chainB.xyz', 'CNP009-1AA5-dimer.xyz']:
            rows = read_xyz(fname)
            d, _ = dmax_scan(rows)
            self.assertTrue(10.0 <= d < 100.0, f'{fname}: dmax={d} A not in [10,100) A (i.e. [1,10) nm)')


class ClosestContactChecks(unittest.TestCase):
    def test_cnp010_interchain_contact(self):
        rows_a = read_xyz('CNP010-1AA5-chainA.xyz')
        rows_b = read_xyz('CNP010-1AA5-chainB.xyz')
        self.assertEqual(len(rows_a), 132)
        self.assertEqual(len(rows_b), 132)
        d, pair = dmin_scan(rows_a, rows_b)
        self.assertAlmostEqual(d, 2.0332, places=3)
        self.assertEqual(pair, (78, 86))
        # element identities of the attaining atoms
        self.assertEqual(rows_a[77][0], 'O')
        self.assertEqual(rows_b[85][0], 'H')


class RadiusOfGyrationChecks(unittest.TestCase):
    def test_cnp011_dimer_rg(self):
        rows = read_xyz('CNP011-1AA5-dimer.xyz')
        self.assertEqual(len(rows), 264)
        rg = radius_of_gyration(rows)
        self.assertAlmostEqual(rg, 8.2617, places=3)

    def test_cni004_chain_rg_comparison(self):
        rows_a = read_xyz('CNI004-1AA5-chainA.xyz')
        rows_b = read_xyz('CNI004-1AA5-chainB.xyz')
        rg_a = radius_of_gyration(rows_a)
        rg_b = radius_of_gyration(rows_b)
        self.assertAlmostEqual(rg_a, 6.4797, places=3)
        self.assertAlmostEqual(rg_b, 6.5288, places=3)
        # the two chains are close in Rg (weak evidence either way about asymmetry)
        self.assertLess(abs(rg_a - rg_b), 0.1)


class TerminalVsExtentChecks(unittest.TestCase):
    def _terminal_and_max(self, fname):
        rows = read_xyz(fname)
        # residue-1 CA is row 3, residue-7 CA is row 122 (1-based), per the
        # already-established terminal_rows in compute_chem_nm.py
        terminal = math.dist(rows[2][1], rows[121][1])
        dmax, _ = dmax_scan(rows)
        return terminal, dmax

    def test_cni002_chain_a(self):
        terminal, dmax = self._terminal_and_max('CNI002-1AA5-chainA.xyz')
        self.assertAlmostEqual(terminal, 13.8393, places=3)
        self.assertLess(terminal, dmax)

    def test_cni003_chain_b(self):
        terminal, dmax = self._terminal_and_max('CNI003-1AA5-chainB.xyz')
        self.assertAlmostEqual(terminal, 13.8115, places=3)
        self.assertLess(terminal, dmax)


class AssemblyArithmeticChecks(unittest.TestCase):
    def test_cni005_dimer_extent_less_than_sum(self):
        rows_a = read_xyz('CNI005-1AA5-chainA.xyz')
        rows_b = read_xyz('CNI005-1AA5-chainB.xyz')
        rows_dimer = read_xyz('CNI005-1AA5-dimer.xyz')
        dmax_a, _ = dmax_scan(rows_a)
        dmax_b, _ = dmax_scan(rows_b)
        dmax_dimer, _ = dmax_scan(rows_dimer)
        total = dmax_a + dmax_b
        self.assertAlmostEqual(total, 38.8344, places=2)
        self.assertLess(dmax_dimer, total)


class CatalogEntryChecks(unittest.TestCase):
    def test_ten_chem_nm_entries_present_and_reasoning_scale_in_cell(self):
        cat = json.loads((ROOT / 'docs' / 'data' / 'catalog.json').read_text(encoding='utf-8'))
        by_id = {q['id']: q for q in cat['questions']}
        ids = ['CNP007', 'CNP008', 'CNP009', 'CNP010', 'CNP011', 'CNI002', 'CNI003', 'CNI004', 'CNI005', 'CNI006']
        for qid in ids:
            self.assertIn(qid, by_id, f'{qid} missing from catalog.json')
            q = by_id[qid]
            self.assertEqual(q['domain'], 'chemistry')
            self.assertTrue(1.0 <= q['reasoningSizeNm'] < 10.0, f'{qid} reasoningSizeNm={q["reasoningSizeNm"]} not in [1,10) nm')
            self.assertEqual(q['batchId'], 'chem-nm-v04-001')
            self.assertTrue(Path(ROOT / 'docs' / q['inputDownload']).exists())


if __name__ == '__main__':
    unittest.main()
