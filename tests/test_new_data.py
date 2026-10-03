"""Data added on 2026-10-03 (user-approved downloads): recorded hashes match the committed files, rejected files are gone,
and the new assemblies give the known capsid architectures."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKBENCH = json.loads((ROOT / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
KEYS = {k['id']: k for k in WORKBENCH['teacher_answers']}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SourceRecordTests(unittest.TestCase):
    def test_recorded_hashes_match(self):
        for rel in ('docs/assets/materials/sources-cod-2026-10-03.json', 'docs/assets/materials/sources-noncubic.json',
                    'docs/assets/bio/sources-2026-10-03.json'):
            record = json.loads((ROOT / rel).read_text(encoding='utf-8'))
            for name, info in record['files'].items():
                self.assertEqual(sha((ROOT / rel).parent / name), info['sha256'], name)
                self.assertTrue(info.get('citation') or info.get('title'), name)

    def test_rejected_cifs_are_not_kept(self):
        for cod in ('9001364', '2300380', '1576630'):          # partial occupancy: spinel, HKUST-1, UiO-66
            self.assertFalse((ROOT / ('docs/assets/materials/%s.cif' % cod)).exists(), cod)

    def test_assembly_assets_match_sources(self):
        record = json.loads((ROOT / 'docs/assets/families/assemblies/sources.json').read_text(encoding='utf-8'))
        for name, info in record['files'].items():
            self.assertEqual(hashlib.sha256((ROOT / 'docs/assets/families/assemblies' / name).read_bytes()).hexdigest(),
                             info['asset_sha256'], name)


class AssemblyAnswerTests(unittest.TestCase):
    def test_known_capsid_architectures(self):
        # SPMV and STNV are T = 1; CCMV T = 3 (32 capsomers, 20 hexamers); HK97 T = 7 (60 hexamers).
        expect = {'FA-ASM-T-1STM': '1', 'FA-ASM-CAPS-2BUK': '12', 'FA-ASM-T-1CWP': '3', 'FA-ASM-CAPS-1CWP': '32',
                  'FA-ASM-HEX-1CWP': '20', 'FA-ASM-T-2FT1': '7', 'FA-ASM-HEX-2FT1': '60'}
        for iid, value in expect.items():
            self.assertEqual(KEYS[iid]['numeric_answer']['value'], value, iid)

    def test_new_particles_sit_in_the_10_100_nm_cell(self):
        for pdb in ('1RYP', '1STM', '2BUK', '1CWP', '1SVA', '2FT1'):
            self.assertTrue(10 <= KEYS['FA-ASM-EXT-%s' % pdb]['scales']['reasoning_nm'] < 100, pdb)


if __name__ == '__main__':
    unittest.main()
