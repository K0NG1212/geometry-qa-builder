import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import builder as b

def fixtures():
    bundle={'paper_id':'synthetic-software-fixture','title':'Synthetic parser and distance fixture, NOT a scientific paper','url':'','synthetic':True,
        'sources':[{'source_id':'S0001','location':'synthetic statement','origin':'test fixture','kind':'text',
            'text':'Synthetic software test only. The supplied two-atom coordinates use angstrom units. No physical stability claim is made.'},
            {'source_id':'S0002','location':'synthetic XYZ angstrom','origin':'test fixture','kind':'xyz','text':'2\nSynthetic, not a physical equilibrium structure\nH 0 0 0\nH 0 0 2\n'}], 'warnings':['Synthetic fixture; never include in benchmark.']}
    refs=[{'source_id':'S0001','quote':'The supplied two-atom coordinates use angstrom units.'}]
    evidence={'records':[{'evidence_id':'E001','objects':'Two synthetic atom coordinates','geometric_relation':'Pair distance',
        'scientific_result':'None: software test only','conditions':['Angstrom coordinates'],
        'limitations':['Not a scientific paper or equilibrium molecule'],'source_refs':refs,'asset_ids':['S0002']}],'exclusions':[]}
    tasks={'tasks':[{'task_id':'T001','evidence_ids':['E001'],'domain':'synthetic test','object_type':'two atoms',
        'input_scale':'two coordinates','reasoning_scale':'atom pair','ability':'perception','geometry_necessity':'Requires coordinate distance',
        'input_plan':'XYZ coordinates and distance question','validation_route':'xyz_distance','eligible':True,'unmet_requirements':[]}],'exclusions':[]}
    qa={'items':[{'qa_id':'Q001','task_id':'T001','evidence_ids':['E001'],'ability':'perception',
        'question':'What is the distance between atoms 1 and 2 in angstrom?',
        'model_input':'Use the supplied XYZ coordinates in angstrom; atoms are numbered from 1.',
        'input_asset_ids':['S0002'],'reference_answer':'2 angstrom','answer_numeric':2.0,'units':'angstrom',
        'answer_refs':refs,'rubric':'Compute Euclidean distance, tolerance 0.001 angstrom.',
        'limitations':['Software fixture only'],'verifier':{'kind':'xyz_distance','source_id':'S0002','atom_indices':[1,2],'tolerance':.001}}],'exclusions':[]}
    review={'reviews':[{'qa_id':'Q001','checks':{k:True for k in b.CHECKS['properties']},'issues':[],
        'notes':'Handwritten test fixture; not a GPT-6 result or expert review.'}]}
    return bundle,{'evidence':evidence,'tasks':tasks,'qa':qa,'review':review}

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name); self.run=self.root/'run'
        self.bundle,self.stages=fixtures()
        b.write(self.root/'bundle.json',self.bundle)
        b.init(self.root/'bundle.json',self.run)
        self.config=b.read(self.run/'config.json')
    def tearDown(self): self.tmp.cleanup()
    def complete(self):
        for s in b.STAGES: b.accept(self.run,self.stages[s],'handwritten-fixture','test_fixture')
        return b.report(self.run)
    def test_full_run_never_certifies(self):
        report=self.complete()
        self.assertEqual(report['pending_human_audit'],1)
        self.assertFalse(report['items'][0]['benchmark_ready'])
        self.assertTrue((self.run/'candidates.csv').exists())
    def test_fabricated_quote_rejected(self):
        self.stages['evidence']['records'][0]['source_refs'][0]['quote']='Fabricated claim'
        with self.assertRaisesRegex(ValueError,'quotation'): b.accept(self.run,self.stages['evidence'],'test','test')
    def test_missing_asset_rejected(self):
        self.stages['evidence']['records'][0]['asset_ids']=['not-present']
        with self.assertRaises(ValueError): b.accept(self.run,self.stages['evidence'],'test','test')
    def test_numeric_disagreement_flagged(self):
        self.stages['qa']['items'][0]['answer_numeric']=9
        self.assertEqual(self.complete()['items'][0]['status'],'needs_revision')
    def test_review_false_fails_closed(self):
        self.stages['review']['reviews'][0]['checks']['evidence_support']=False
        self.assertEqual(self.complete()['pending_human_audit'],0)
    def test_missing_review_rejected(self):
        for s in b.STAGES[:3]: b.accept(self.run,self.stages[s],'test','test')
        with self.assertRaisesRegex(ValueError,'coverage'): b.accept(self.run,{'reviews':[]},'test','test')
    def test_no_overwrite(self):
        with self.assertRaisesRegex(ValueError,'exists'): b.init(self.root/'bundle.json',self.run)
    def test_snapshot_tamper(self):
        c=b.read(self.run/'config.json'); c['model']='other'; b.write(self.run/'config.json',c)
        with self.assertRaisesRegex(ValueError,'snapshot'): b.packet(self.run)
    def test_stage_tamper(self):
        b.accept(self.run,self.stages['evidence'],'test','test')
        envelope=b.read(self.run/'evidence.json'); envelope['data']['exclusions']=['changed']; b.write(self.run/'evidence.json',envelope)
        with self.assertRaisesRegex(ValueError,'changed'): b.packet(self.run)
    def test_unknown_keys(self):
        self.stages['evidence']['run_shell']='malicious source instruction'
        with self.assertRaises(ValueError): b.accept(self.run,self.stages['evidence'],'test','test')
    def test_no_design_generation(self):
        b.accept(self.run,self.stages['evidence'],'test','test')
        self.stages['tasks']['tasks'][0]['ability']='design'
        with self.assertRaises(ValueError): b.accept(self.run,self.stages['tasks'],'test','test')
    def test_bad_indices(self):
        self.stages['qa']['items'][0]['verifier']['atom_indices']=[0,2]
        for s in b.STAGES[:2]: b.accept(self.run,self.stages[s],'test','test')
        with self.assertRaisesRegex(ValueError,'indices'): b.accept(self.run,self.stages['qa'],'test','test')
    def test_angle(self):
        sources={'X':{'text':'3\nfixture\nH 1 0 0\nH 0 0 0\nH 0 1 0'}}
        q={'verifier':{'source_id':'X','kind':'xyz_angle','atom_indices':[1,2,3],'tolerance':.1},'units':'degree','answer_numeric':90}
        self.assertTrue(b.geometry(q,sources)['passed'])
    def test_empty_pipeline(self):
        self.stages={'evidence':{'records':[],'exclusions':['No evidence']},'tasks':{'tasks':[],'exclusions':[]},'qa':{'items':[],'exclusions':[]},'review':{'reviews':[]}}
        self.assertEqual(self.complete()['count'],0)
    def test_response_incomplete(self):
        with self.assertRaises(ValueError): b.parse_response({'status':'incomplete','output':[]})
    def test_response_refusal(self):
        with self.assertRaises(ValueError): b.parse_response({'status':'completed','output':[{'content':[{'type':'refusal'}]}]})
    def test_request(self):
        stage,req=b.packet(self.run)
        self.assertEqual(req['model'],'gpt-6-astra')
        self.assertFalse(req['store'])
        self.assertEqual(req['text']['format']['schema'],b.SCHEMAS['evidence'])

if __name__=='__main__': unittest.main()
