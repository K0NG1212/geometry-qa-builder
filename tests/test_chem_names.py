"""Chemical naming from connectivity (task_families/chem_names.py), checked against molecules whose structures are known
from their source names: thioureas and sulfones in QM7-X, ammonium / sulfonate / viologen guests and the carboxylated
WP6 host in SAMPL9. Enumerated bond and angle questions must use these names."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checkers  # noqa: E402
import enumerators  # noqa: E402
from task_families import chem_names, kit, rotational  # noqa: E402

MOLECULES = {m['molecule']: m for m in enumerators.load_molecules(ROOT)}


def names(molecule, charge=None):
    m = MOLECULES[molecule]
    elements, points = kit.parse_xyz((ROOT / 'docs' / m['asset']).read_text(encoding='utf-8-sig'))
    return chem_names.Molecule(elements, points, m['charge'] if charge is None else charge)


class NamingTests(unittest.TestCase):
    def test_every_molecule_has_a_charge_and_every_heavy_atom_a_name(self):
        for molecule, m in MOLECULES.items():
            self.assertIsInstance(m['charge'], int, molecule)
            n = names(molecule)
            self.assertEqual([i + 1 for i, e in enumerate(n.elements) if e != 'H' and n.names[i] is None], [], molecule)

    def test_thiourea_and_alkene(self):
        n = names('QM7X-7029')          # CH3-CH=CH-NH-C(=S)-NH2
        self.assertEqual(n.names[4], 'thiourea carbon (C=S)')
        self.assertEqual(n.names[5], 'thiocarbonyl sulfur (C=S)')
        self.assertEqual(n.names[6], 'thioamide NH2 nitrogen')
        self.assertEqual((n.bond_order(1, 2), n.bond_order(4, 5), n.bond_order(3, 4)), (2, 2, 1))
        self.assertEqual(n.bond(4, 5), 'the double C=S bond between C5, the thiourea carbon (C=S), and S6, the thiocarbonyl '
                                       'sulfur (C=S)')

    def test_sulfur_oxyacid_family(self):
        self.assertEqual(names('QM7X-7033').names[3], 'sulfone sulfur (SO2)')
        n = names('QM7X-7038')          # sulfonamide: S=O double bonds, no zwitterionic resonance form
        self.assertEqual((n.names[3], n.names[4], n.names[6]), ('sulfonamide sulfur (SO2)', 'sulfonyl oxygen (S=O)',
                                                                'sulfonamide nitrogen (NH2)'))
        self.assertEqual(n.bond_order(3, 4), 2)
        self.assertEqual(names('QM7X-7043').names[6], 'sulfonic acid hydroxyl oxygen (S–OH)')
        g8 = names('SAMPL9-WP6-G8')     # benzyl(dimethyl)ammonio-propanesulfonate zwitterion
        self.assertEqual(g8.names[16], 'sulfonate sulfur (SO3⁻)')
        self.assertEqual({g8.bond_order(13, 16), g8.bond_order(14, 16), g8.bond_order(15, 16)}, {'delocalized'})
        self.assertEqual(g8.names[12], 'quaternary ammonium nitrogen (N+)')
        self.assertEqual(g8.bond_order(0, 1), 'aromatic')

    def test_viologen_needs_the_stated_charge(self):
        g13 = names('SAMPL9-WP6-G13')   # 1,1'-dimethyl-4,4'-bipyridinium, charge +2
        self.assertEqual(g13.names[12], 'pyridinium nitrogen (N+) in the 6-membered ring')
        self.assertEqual(g13.bond_order(8, 9), 1)                 # inter-ring bond stays single
        self.assertEqual(g13.bond_order(0, 4), 'aromatic')
        quinoid = names('SAMPL9-WP6-G13', charge=0)               # connectivity alone gives the neutral quinoid form
        self.assertEqual(quinoid.bond_order(8, 9), 2)
        with self.assertRaises(ValueError):
            names('SAMPL9-WP6-G1', charge=0)                      # an NH3 group on four neighbours must be a cation

    def test_rings_ammonium_silyl_and_carboxylate(self):
        self.assertEqual(names('SAMPL9-WP6-G7').names[0], 'methylene carbon (CH2) in the 6-membered ring')
        self.assertEqual(names('SAMPL9-WP6-G7').names[6], 'ammonium nitrogen (NH3+)')
        self.assertEqual(names('SAMPL9-WP6-G4').names[5], 'silicon of the trimethylsilyl group')
        self.assertEqual(names('QM7X-7208').names[6], 'methylene carbon (CH2) in the 3-membered ring')
        wp6 = names('SAMPL9-WP6')
        self.assertEqual(sum(v == 'carboxylate carbon (COO⁻)' for v in wp6.names.values()), 12)


class UseTests(unittest.TestCase):
    def test_enumerated_bonds_and_angles_are_named(self):
        proposals = enumerators.propose(ROOT, ['named_bond_distance', 'named_bond_angle'])
        for s in proposals['named_bond_distance']:
            self.assertTrue(s['bond'].startswith('the ') and ' bond between ' in s['bond'], s['id'])
            self.assertNotIn('is bonded to', s['bond'])
        for s in proposals['named_bond_angle']:
            self.assertTrue(s['linkage'].startswith('the angle at '), s['id'])

    def test_design_candidates_are_named_and_checked(self):
        spec = json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))['items']
        spec = dict(next(x for x in spec if x['id'] == 'FA-ISO-7095-111'), target_position=2)
        built = rotational.build_isotopologue(spec, ROOT, 'test-seed')
        self.assertIn('H10 is bonded to C1, the methyl carbon (CH3)', built['question'])
        packet = dict(id=spec['id'], family=spec['family'], question=built['question'], inputs=built['inputs'], options=built['options'])
        key = dict(id=spec['id'], family=spec['family'], correct_label=built['correct_label'], numeric_answer=None,
                   input_hashes=built['input_hashes'])
        self.assertEqual(checkers.check(packet, key)['status'], 'pass')
        wrong = copy.deepcopy(packet)
        wrong['question'] = wrong['question'].replace('H10 is bonded to C1,', 'H10 is bonded to N2,')
        self.assertEqual(checkers.check(wrong, key)['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
