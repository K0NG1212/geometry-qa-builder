import copy
import unittest
import builder as b
from test_builder import fixtures
from builder_modules.m5_quality import module as m
class QualityTests(unittest.TestCase):
    def test_review_must_cover_all_candidates(self):
        bundle,stages=fixtures()
        m.validate(b,stages['review'],bundle,stages,{})
        with self.assertRaisesRegex(ValueError,'coverage'):m.validate(b,{'reviews':[]},bundle,stages,{})
