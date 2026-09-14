import copy
import unittest
import builder as b
from test_builder import fixtures
from builder_modules.m3_tasks import module as m
class TasksTests(unittest.TestCase):
    def test_direct_validator_rejects_missing_evidence(self):
        bundle,stages=fixtures();data=stages['tasks']
        m.validate(b,data,bundle,stages,{})
        data['tasks'][0]['evidence_ids']=['E999']
        with self.assertRaisesRegex(ValueError,'unavailable'):m.validate(b,data,bundle,stages,{})
