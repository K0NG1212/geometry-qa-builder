import copy
import unittest
import builder as b
from test_builder import fixtures
from builder_modules.m4_construction import module as m
class ConstructionTests(unittest.TestCase):
    def test_known_angle_and_translation(self):
        q={'verifier':{'kind':'xyz_angle','source_id':'X','atom_indices':[1,2,3],'tolerance':0.1},'units':'degree','answer_numeric':90}
        for text in ('3\nfixture\nH 1 0 0\nH 0 0 0\nH 0 1 0','3\nfixture\nH 5 4 4\nH 4 4 4\nH 4 5 4'):
            self.assertAlmostEqual(m.geometry(b,q,{'X':{'text':text}})['computed'],90)
        q['verifier']['atom_indices']=[1,1,3]
        with self.assertRaisesRegex(ValueError,'indices'):m.geometry(b,q,{'X':{'text':text}})
