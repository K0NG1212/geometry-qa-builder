"""Portable checks for the quantum x 1-10 nm batch (quantum-nm-v04-001/002):
QNP007-011, QNI005-009. Reads only committed docs/assets/qa/*.xyz and
*-input.txt files (never runs/, which is gitignored and not present on a
fresh clone), and recomputes every answer with a fresh, independent
implementation.
"""
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


def radius_of_gyration(rows):
    coords = [r[1] for r in rows]
    n = len(coords)
    cx = sum(c[0] for c in coords) / n
    cy = sum(c[1] for c in coords) / n
    cz = sum(c[2] for c in coords) / n
    ssq = sum((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 for x, y, z in coords)
    return math.sqrt(ssq / n)


def extract_float(pattern, text):
    m = re.search(pattern, text)
    assert m, 'pattern not found: ' + pattern
    return float(m.group(1))


class GlobalExtentChecks(unittest.TestCase):
    def test_qnp007_majhub(self):
        rows = read_xyz('QNP007-MAJHUB.xyz')
        self.assertEqual(len(rows), 41)
        d, pair = dmax_scan(rows)
        self.assertAlmostEqual(d, 10.0003, places=3)
        self.assertEqual(pair, (10, 30))

    def test_qnp008_jimhoc(self):
        rows = read_xyz('QNP008-JIMHOC.xyz')
        self.assertEqual(len(rows), 57)
        d, pair = dmax_scan(rows)
        self.assertAlmostEqual(d, 11.8784, places=3)
        self.assertEqual(pair, (15, 40))

    def test_qnp009_kegpoc(self):
        rows = read_xyz('QNP009-KEGPOC.xyz')
        self.assertEqual(len(rows), 64)
        d, pair = dmax_scan(rows)
        self.assertAlmostEqual(d, 14.0870, places=3)
        self.assertEqual(pair, (23, 62))

    def test_all_global_extents_are_1_to_10_nm(self):
        for fname, natoms in [('QNP007-MAJHUB.xyz', 41), ('QNP008-JIMHOC.xyz', 57), ('QNP009-KEGPOC.xyz', 64)]:
            rows = read_xyz(fname)
            d, _ = dmax_scan(rows)
            self.assertTrue(10.0 <= d < 100.0, f'{fname}: dmax={d} A not in [10,100) A (i.e. [1,10) nm)')


class RadiusOfGyrationChecks(unittest.TestCase):
    def test_qnp010_kewgid(self):
        rows = read_xyz('QNP010-KEWGID.xyz')
        self.assertEqual(len(rows), 48)
        rg = radius_of_gyration(rows)
        self.assertAlmostEqual(rg, 4.2467, places=3)

    def test_qnp011_pekzag(self):
        rows = read_xyz('QNP011-PEKZAG.xyz')
        self.assertEqual(len(rows), 70)
        rg = radius_of_gyration(rows)
        self.assertAlmostEqual(rg, 4.6156, places=3)


class OrbitalGapChecks(unittest.TestCase):
    def test_qni005_galpal_pbe_gap(self):
        text = (QA_DIR / 'QNI005-input.txt').read_text(encoding='utf-8')
        homo = extract_float(r'occupied energies \(eV\): HOMO \(last value of the full list\) = (-?\d+\.\d+)', text)
        lumo = extract_float(r'unoccupied energies \(eV\): LUMO \(first value of the full list\) = (-?\d+\.\d+)', text)
        self.assertAlmostEqual(homo, -5.61075, places=4)
        self.assertAlmostEqual(lumo, -1.63809, places=4)
        self.assertAlmostEqual(lumo - homo, 3.97266, places=4)

    def test_qni006_mehloa_pbe_vs_pbe0(self):
        text = (QA_DIR / 'QNI006-input.txt').read_text(encoding='utf-8')
        homo_pbe = extract_float(r'PBE\+vdW\(vacuum\) occupied energies \(eV\): (-?\d+\.\d+) is the HOMO', text)
        lumo_pbe = extract_float(r'PBE\+vdW\(vacuum\) unoccupied energies \(eV\): (-?\d+\.\d+) is the LUMO', text)
        homo_pbe0 = extract_float(r'PBE0\(vacuum\) occupied energies \(eV\): (-?\d+\.\d+) is the HOMO', text)
        lumo_pbe0 = extract_float(r'PBE0\(vacuum\) unoccupied energies \(eV\): (-?\d+\.\d+) is the LUMO', text)
        gap_pbe = lumo_pbe - homo_pbe
        gap_pbe0 = lumo_pbe0 - homo_pbe0
        self.assertAlmostEqual(gap_pbe, 3.15075, places=4)
        self.assertAlmostEqual(gap_pbe0, 5.15452, places=4)
        self.assertGreater(gap_pbe0, gap_pbe)

    def test_qni007_majhub_pbe0_vs_gw(self):
        text = (QA_DIR / 'QNI007-input.txt').read_text(encoding='utf-8')
        homo_pbe0 = extract_float(r'PBE0\(vacuum\) occupied energies \(eV\): (-?\d+\.\d+) is the HOMO', text)
        lumo_pbe0 = extract_float(r'PBE0\(vacuum\) unoccupied energies \(eV\): (-?\d+\.\d+) is the LUMO', text)
        homo_gw = extract_float(r'G0W0@PBE0\(vacuum, CBS\) occupied energies \(eV\): (-?\d+\.\d+) is the HOMO', text)
        lumo_gw = extract_float(r'G0W0@PBE0\(vacuum, CBS\) unoccupied energies \(eV\): (-?\d+\.\d+) is the LUMO', text)
        gap_pbe0 = lumo_pbe0 - homo_pbe0
        gap_gw = lumo_gw - homo_gw
        self.assertAlmostEqual(gap_pbe0, 3.88347, places=4)
        self.assertAlmostEqual(gap_gw, 6.83291, places=4)
        self.assertGreater(gap_gw, gap_pbe0)

    def test_qni008_ezutau_vs_zogvew(self):
        text = (QA_DIR / 'QNI008-input.txt').read_text(encoding='utf-8')
        homo_e = extract_float(r'EZUTAU PBE\+vdW\(vacuum\) occupied energies \(eV\): (-?\d+\.\d+) is the HOMO', text)
        lumo_e = extract_float(r'EZUTAU PBE\+vdW\(vacuum\) unoccupied energies \(eV\): (-?\d+\.\d+) is the LUMO', text)
        homo_z = extract_float(r'ZOGVEW PBE\+vdW\(vacuum\) occupied energies \(eV\): (-?\d+\.\d+) is the HOMO', text)
        lumo_z = extract_float(r'ZOGVEW PBE\+vdW\(vacuum\) unoccupied energies \(eV\): (-?\d+\.\d+) is the LUMO', text)
        gap_e = lumo_e - homo_e
        gap_z = lumo_z - homo_z
        self.assertAlmostEqual(gap_e, 4.26593, places=4)
        self.assertAlmostEqual(gap_z, 2.31492, places=4)
        # The larger molecule (ZOGVEW, 79 atoms) has the SMALLER gap - a genuine
        # counter-example to any naive size-gap generalization from 2 points.
        self.assertGreater(gap_e, gap_z)

    def test_qni009_jimhoc_pbe_vs_pbe0(self):
        text = (QA_DIR / 'QNI009-input.txt').read_text(encoding='utf-8')
        homo_pbe = extract_float(r'PBE\+vdW\(vacuum\) occupied energies \(eV\): (-?\d+\.\d+) is the HOMO', text)
        lumo_pbe = extract_float(r'PBE\+vdW\(vacuum\) unoccupied energies \(eV\): (-?\d+\.\d+) is the LUMO', text)
        homo_pbe0 = extract_float(r'PBE0\(vacuum\) occupied energies \(eV\): (-?\d+\.\d+) is the HOMO', text)
        lumo_pbe0 = extract_float(r'PBE0\(vacuum\) unoccupied energies \(eV\): (-?\d+\.\d+) is the LUMO', text)
        gap_pbe = lumo_pbe - homo_pbe
        gap_pbe0 = lumo_pbe0 - homo_pbe0
        self.assertAlmostEqual(gap_pbe, 3.57563, places=4)
        self.assertAlmostEqual(gap_pbe0, 5.29643, places=4)
        self.assertGreater(gap_pbe0, gap_pbe)


class CatalogEntryChecks(unittest.TestCase):
    def test_ten_quantum_nm_entries_present_and_reasoning_scale_in_cell(self):
        cat = json.loads((ROOT / 'docs' / 'data' / 'catalog.json').read_text(encoding='utf-8'))
        by_id = {q['id']: q for q in cat['questions']}
        ids = ['QNP007', 'QNI007', 'QNP008', 'QNP009', 'QNP010', 'QNP011', 'QNI005', 'QNI006', 'QNI008', 'QNI009']
        for qid in ids:
            self.assertIn(qid, by_id, f'{qid} missing from catalog.json')
            q = by_id[qid]
            self.assertEqual(q['domain'], 'quantum')
            self.assertTrue(1.0 <= q['reasoningSizeNm'] < 10.0, f'{qid} reasoningSizeNm={q["reasoningSizeNm"]} not in [1,10) nm')
            self.assertIn(q['batchId'], ('quantum-nm-v04-001', 'quantum-nm-v04-002'))
            self.assertTrue(Path(ROOT / 'docs' / q['inputDownload']).exists())


if __name__ == '__main__':
    unittest.main()
