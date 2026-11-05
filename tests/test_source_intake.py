"""Real A1 intake regressions: a protein title may describe the DNA junction it binds."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import fetch_a1, validate_a1


class PdbIntakeTests(unittest.TestCase):
    def test_ruva_is_a_protein_even_though_its_title_says_holliday_junction(self):
        text = (ROOT / 'docs/assets/bio/1HJP.pdb').read_text(encoding='utf-8')
        entry = {'title': 'HOLLIDAY JUNCTION BINDING PROTEIN RUVA'}
        self.assertEqual(fetch_a1.pdb_kind(entry, text), 'protein')
        rows = json.loads((ROOT / 'templates/structures.json').read_text(encoding='utf-8'))['structures']
        self.assertEqual(next(x for x in rows if x['pdb'] == '1HJP')['kind'], 'protein')

    def test_intake_rejects_the_former_ruva_nucleic_registration(self):
        with self.assertRaisesRegex(ValueError, 'nucleic'):
            validate_a1.check_structure('assets/bio/1HJP.pdb', 'A', 'nucleic')
        self.assertIn('186', validate_a1.check_structure('assets/bio/1HJP.pdb', 'A', 'protein'))

    def test_deposited_dna_is_recognised_and_accepted_as_nucleic(self):
        for pdb in ('355D', '1DCW', '1JUC'):
            with self.subTest(pdb=pdb):
                asset = 'assets/bio/%s.pdb' % pdb
                text = (ROOT / 'docs' / asset).read_text(encoding='utf-8')
                kind = fetch_a1.pdb_kind({'title': ''}, text)
                self.assertEqual(kind, 'nucleic')
                validate_a1.check_structure(asset, 'A', kind)


if __name__ == '__main__':
    unittest.main()
