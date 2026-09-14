import copy
import unittest
import builder as b
from test_builder import fixtures
from builder_modules.m1_materials import module as m
import tempfile
from pathlib import Path
from types import SimpleNamespace
class MaterialsTests(unittest.TestCase):
    def test_normalize_and_preserve_source_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'paper.txt').write_text('Original scientific statement',encoding='utf-8')
            (root/'a.xyz').write_text('2\nNo unit claim\nH 0 0 0\nH 0 0 2',encoding='utf-8')
            args=SimpleNamespace(source=[str(root/'paper.txt')],xyz=[str(root/'a.xyz')],paper_id='test',title='fixture',url='',synthetic=True,out=str(root/'bundle.json'))
            m.prepare(b,args); bundle=b.read(args.out)
            self.assertEqual(len(bundle['sources']),2)
            self.assertIn('lines 1-1',bundle['sources'][0]['location'])
            self.assertNotIn('angstrom',bundle['sources'][1]['location'])
            with self.assertRaisesRegex(ValueError,'exists'):m.prepare(b,args)
    def test_false_unit_reference_rejected(self):
        bundle,stages=fixtures()
        units={'assets':[{'source_id':'S0002','unit':'angstrom','source_refs':[{'source_id':'S0001','quote':'invented'}],'checked_by':'test','notes':''}]}
        with self.assertRaisesRegex(ValueError,'quotation'):m.check_units(b,units,bundle)
