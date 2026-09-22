import copy
import json
import tempfile
import unittest
from pathlib import Path
import choice_engine as c

TEXT='3\ntriangle\nC 0 0 0\nC 3 0 0\nC 0 4 0\n'

class ChoiceTests(unittest.TestCase):
    def test_geometry_and_determinism(self):
        for family, expected in [('global_extent','5.0000'), ('equal_weight_rg','2.3570')]:
            a=c.construct(TEXT,family,'seed','id')
            self.assertEqual(a,c.construct(TEXT,family,'seed','id'))
            self.assertEqual(a[1]['correct_value'],expected)
            self.assertEqual(c.validate_options(a[0],expected),a[1]['correct_label'])
            for opt in a[0]:
                self.assertEqual(c.score_choice(opt['label'],a[1]['correct_label']),opt['value']==expected)

    def test_duplicate_tolerance_units_and_precision(self):
        options,_=c.construct(TEXT,'global_extent','seed','id')
        bad=copy.deepcopy(options);bad[1]['value']=bad[0]['value']
        with self.assertRaises(ValueError):c.validate_options(bad,5)
        bad=copy.deepcopy(options);bad[0]['unit']='nm'
        with self.assertRaises(ValueError):c.validate_options(bad,5)
        bad=copy.deepcopy(options);bad[0]['value']='nan'
        with self.assertRaises(ValueError):c.validate_options(bad,5)
        bad=[{'label':l,'value':v,'unit':'angstrom'} for l,v in zip('ABCD',['5.0000','5.0001','3.0000','4.0000'])]
        with self.assertRaises(ValueError):c.validate_options(bad,5)
        with self.assertRaises(ValueError):c.validate_options(options,999)

    def test_degenerate_geometry_fails_without_fabrication(self):
        text='2\ncoincident\nC 0 0 0\nC 0 0 0\n'
        with self.assertRaisesRegex(ValueError,'Fewer'):c.construct(text,'global_extent','s','id')

    def test_label_contract(self):
        for text in ['A',' a ','\nA\n']:self.assertTrue(c.score_choice(text,'A'))
        for text in ['A because','AB','B',None,{'answer':'A'},'Ａ']:self.assertFalse(c.score_choice(text,'A'))

    def test_seed_changes_mapping_but_not_correct_value(self):
        outputs=[c.construct(TEXT,'global_extent',str(i),'id') for i in range(20)]
        self.assertEqual({a['correct_label'] for _,a in outputs},set('ABCD'))
        self.assertEqual({a['correct_value'] for _,a in outputs},{'5.0000'})

    def test_all_real_inputs_and_separation(self):
        source=c.numeric.ROOT/'runs/template-pilot-v01'
        # Portable: produce source from versioned public inputs when ignored runs absent.
        import template_engine
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'numeric';template_engine.run(c.numeric.ROOT/'templates/pilot-manifest.json',source)
            out=Path(temp)/'choice';report=c.run(source,out)
            self.assertEqual(report['passed'],12);self.assertEqual(report['failures'],[])
            students=json.loads((out/'student-packets.json').read_text(encoding='utf-8'))
            for s in students:
                self.assertEqual(len(s['options']),4)
                self.assertEqual(set(s),{'id','derived_from','question','scope','input','options','response_format'})
                for opt in s['options']:self.assertEqual(set(opt),{'label','value','unit'})
            with self.assertRaisesRegex(ValueError,'exists'):c.run(source,out)
            packets=json.loads((source/'student-packets.json').read_text(encoding='utf-8'))
            packets[0]['input']['text']+='\n'
            (source/'student-packets.json').write_text(json.dumps(packets),encoding='utf-8')
            altered=c.run(source,Path(temp)/'altered')
            self.assertEqual(altered['passed'],11)
            self.assertIn('provenance',altered['failures'][0]['reason'])
