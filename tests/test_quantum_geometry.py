"""Portable checks for the q02-force-v04-002 quantum batch (QNP002-006, QNI001-004).
Reads only committed docs/assets/qa/*.xyz and *-input.txt files (never runs/,
which is gitignored and not present on a fresh clone), and recomputes every
answer with a fresh, independent implementation.
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


def dist(a, b):
    return math.dist(a, b)


def angle_deg(a, vertex, b):
    u = [x - y for x, y in zip(a, vertex)]
    v = [x - y for x, y in zip(b, vertex)]
    dot = sum(p * q for p, q in zip(u, v))
    nu = math.sqrt(sum(p * p for p in u))
    nv = math.sqrt(sum(p * p for p in v))
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (nu * nv)))))


def parse_force_table(text):
    """Parse 'row atomic_number Fx Fy Fz' lines following a given header line."""
    rows = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 5 and all(_is_number(p) for p in parts):
            row = int(parts[0])
            rows[row] = (float(parts[2]), float(parts[3]), float(parts[4]))
    return rows


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def force_projection(ref_xyz, disp_xyz, forces_by_row):
    total = 0.0
    for i, ((_, r), (_, s)) in enumerate(zip(ref_xyz, disp_xyz), start=1):
        fx, fy, fz = forces_by_row[i]
        dx, dy, dz = s[0] - r[0], s[1] - r[1], s[2] - r[2]
        total += fx * dx + fy * dy + fz * dz
    return total


class PerceptionDistanceChecks(unittest.TestCase):
    def test_qnp004_nn_distance(self):
        rows = read_xyz('QNP004-7002-opt.xyz')
        self.assertEqual(len(rows), 11)
        self.assertEqual(rows[4][0], 'N')
        self.assertEqual(rows[5][0], 'N')
        self.assertAlmostEqual(dist(rows[4][1], rows[5][1]), 1.187247758, places=6)

    def test_qnp002_so_distance(self):
        rows = read_xyz('QNP002-7035-opt.xyz')
        self.assertEqual(len(rows), 17)
        self.assertEqual(rows[2][0], 'S')
        self.assertEqual(rows[3][0], 'O')
        self.assertAlmostEqual(dist(rows[2][1], rows[3][1]), 1.461565269, places=6)

    def test_qnp003_ccl_distance(self):
        rows = read_xyz('QNP003-7070-opt.xyz')
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0][0], 'Cl')
        self.assertEqual(rows[1][0], 'C')
        self.assertAlmostEqual(dist(rows[0][1], rows[1][1]), 1.737175201, places=6)

    def test_qnp006_cn_distance(self):
        rows = read_xyz('QNP006-7122-opt.xyz')
        self.assertEqual(len(rows), 11)
        self.assertEqual(rows[4][0], 'C')
        self.assertEqual(rows[6][0], 'N')
        self.assertAlmostEqual(dist(rows[4][1], rows[6][1]), 1.40133892, places=6)


class PerceptionAngleChecks(unittest.TestCase):
    def test_qnp005_oso_angle(self):
        rows = read_xyz('QNP005-7040-opt.xyz')
        self.assertEqual(len(rows), 16)
        self.assertEqual(rows[2][0], 'S')
        self.assertEqual(rows[3][0], 'O')
        self.assertEqual(rows[4][0], 'O')
        ang = angle_deg(rows[3][1], rows[2][1], rows[4][1])
        self.assertAlmostEqual(ang, 121.9601735, places=3)


class InferenceForceProjectionChecks(unittest.TestCase):
    def test_qni001_7002_projection_opposes(self):
        a = read_xyz('QNI001-7002-A.xyz')
        b = read_xyz('QNI001-7002-B.xyz')
        text = (QA_DIR / 'QNI001-input.txt').read_text(encoding='utf-8')
        forces = parse_force_table(text)
        self.assertEqual(len(forces), 11)
        s = force_projection(a, b, forces)
        self.assertAlmostEqual(s, -0.4352795772, places=6)
        self.assertLess(s, 0)

    def test_qni002_7035_projection_opposes(self):
        a = read_xyz('QNI002-7035-A.xyz')
        b = read_xyz('QNI002-7035-B.xyz')
        text = (QA_DIR / 'QNI002-input.txt').read_text(encoding='utf-8')
        forces = parse_force_table(text)
        self.assertEqual(len(forces), 17)
        s = force_projection(a, b, forces)
        self.assertAlmostEqual(s, -5.5319173445, places=6)
        self.assertLess(s, 0)

    def test_qni003_7040_d1_vs_d2(self):
        a = read_xyz('QNI003-7040-A.xyz')
        d1 = read_xyz('QNI003-7040-d1.xyz')
        d2 = read_xyz('QNI003-7040-d2.xyz')
        text = (QA_DIR / 'QNI003-input.txt').read_text(encoding='utf-8')
        d1_block, d2_block = text.split('Forces at d2')
        forces_d1 = parse_force_table(d1_block)
        forces_d2 = parse_force_table('Forces at d2' + d2_block)
        self.assertEqual(len(forces_d1), 16)
        self.assertEqual(len(forces_d2), 16)
        s_d1 = force_projection(a, d1, forces_d1)
        s_d2 = force_projection(a, d2, forces_d2)
        self.assertAlmostEqual(s_d1, -11.8341124224, places=5)
        self.assertAlmostEqual(s_d2, -5.0423222646, places=5)
        self.assertGreater(abs(s_d1), abs(s_d2))


class InferenceDipoleChecks(unittest.TestCase):
    def test_qni004_dipole_magnitude_decreases(self):
        text = (QA_DIR / 'QNI004-input.txt').read_text(encoding='utf-8')
        vecs = re.findall(r'vDIP \(x,y,z\) = \[([^\]]+)\]', text)
        self.assertEqual(len(vecs), 2)
        opt_v = [float(x) for x in vecs[0].split(',')]
        d1_v = [float(x) for x in vecs[1].split(',')]
        mag_opt = math.sqrt(sum(x * x for x in opt_v))
        mag_d1 = math.sqrt(sum(x * x for x in d1_v))
        self.assertAlmostEqual(mag_opt, 0.9173500511, places=6)
        self.assertAlmostEqual(mag_d1, 0.8124573237, places=6)
        self.assertLess(mag_d1, mag_opt)


class CatalogEntryChecks(unittest.TestCase):
    def test_nine_quantum_entries_present_and_reasoning_scale_in_cell(self):
        cat = json.loads((ROOT / 'docs' / 'data' / 'catalog.json').read_text(encoding='utf-8'))
        by_id = {q['id']: q for q in cat['questions']}
        ids = ['QNP004', 'QNI001', 'QNP002', 'QNI002', 'QNP005', 'QNI003', 'QNP003', 'QNI004', 'QNP006']
        for qid in ids:
            self.assertIn(qid, by_id, f'{qid} missing from catalog.json')
            q = by_id[qid]
            self.assertEqual(q['domain'], 'quantum')
            self.assertTrue(0.1 <= q['reasoningSizeNm'] < 1.0)
            self.assertEqual(q['batchId'], 'q02-force-v04-002')
            self.assertTrue(Path(ROOT / 'docs' / q['inputDownload']).exists())


if __name__ == '__main__':
    unittest.main()
