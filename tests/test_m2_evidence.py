import copy
import unittest
import builder as b
from test_builder import fixtures
from builder_modules.m2_evidence import module as m
class EvidenceTests(unittest.TestCase):
    def test_direct_validator_rejects_invented_quote(self):
        bundle,stages=fixtures();data=stages['evidence']
        m.validate(b,data,bundle,{}, {})
        data['records'][0]['source_refs'][0]['quote']='not in the source'
        with self.assertRaisesRegex(ValueError,'quotation'):m.validate(b,data,bundle,{}, {})
