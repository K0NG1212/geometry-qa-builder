import copy
import unittest
import builder as b
from test_builder import fixtures
from builder_modules.m6_export import module as m
from pathlib import Path
class ExportTests(unittest.TestCase):
    def test_output_contract_rejects_private_answer_fields(self):
        schema=b.read(Path(m.__file__).with_name('schema.json'))
        public={'synthetic':True,'candidates_only':True,'items':[{'qa_id':'Q1','question':'distance?','model_input':'coordinates','assets':[]}]}
        b.validate(public,schema)
        public['items'][0]['reference_answer']='private'
        with self.assertRaises(ValueError):b.validate(public,schema)
