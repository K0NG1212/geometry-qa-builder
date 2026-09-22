import copy
import math
import tempfile
import unittest
from pathlib import Path
import template_engine as t


class TemplateEngineTests(unittest.TestCase):
    def test_known_geometry_and_pair_identity(self):
        text='3\nknown 3-4-5 triangle\nC 0 0 0\nC 3 0 0\nC 0 4 0\n'
        points=t.parse_xyz(text)
        self.assertEqual(t.calculate(points,'global_extent'),5)
        self.assertAlmostEqual(t.calculate(points,'equal_weight_rg'),math.sqrt(50/9))
        self.assertAlmostEqual(float(t.verify_decimal(text,'equal_weight_rg')),math.sqrt(50/9))

    def test_translation_rotation_and_reordering(self):
        a=[(0,0,0),(3,0,0),(0,4,0)]
        b=[(-y+17,x-9,z+2) for x,y,z in reversed(a)]
        for family in ['global_extent','equal_weight_rg']:
            self.assertAlmostEqual(t.calculate(a,family),t.calculate(b,family))

    def test_reject_malformed_and_nonfinite(self):
        for text in ['2\ncomment\nC 0 0 0\n','2\ncomment\nC nan 0 0\nC 0 0 0','2\ncomment\nC 0 0 0 extra\nC 1 0 0']:
            with self.assertRaises(ValueError):t.parse_xyz(text)

    def test_tied_extrema_and_coincident_sites(self):
        pts=[(-1,0,0),(1,0,0),(0,-1,0),(0,1,0)]
        self.assertEqual(t.calculate(pts,'global_extent'),2)
        self.assertEqual(t.calculate([(0,0,0),(0,0,0)],'equal_weight_rg'),0)

    def test_numeric_grading_is_finite_unit_aware_and_bounded(self):
        self.assertTrue(t.score_numeric({'value':19.5698,'unit':'angstrom'},19.5698,.00005))
        for response in [{'value':19.5699,'unit':'angstrom'},{'value':1.95698,'unit':'nm'},
                         {'value':float('nan'),'unit':'angstrom'},{'value':True,'unit':'angstrom'},'19.5698']:
            self.assertFalse(t.score_numeric(response,19.5698,.00005))

    def test_real_batch_is_reproducible_and_does_not_leak_answers(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'new'
            report=t.run(t.ROOT/'templates/pilot-manifest.json',out)
            self.assertEqual(report['count'],12);self.assertEqual(report['passed'],12)
            students=json.loads((out/'student-packets.json').read_text(encoding='utf-8'))
            for s in students:
                self.assertNotIn('short_answer',s);self.assertNotIn('source',s);self.assertNotIn('explanation',s)
            with self.assertRaisesRegex(ValueError,'exists'):t.run(t.ROOT/'templates/pilot-manifest.json',out)

    def test_unknown_template_rejected(self):
        with self.assertRaises(ValueError):t.calculate([(0,0,0),(1,0,0)],'not_registered')
