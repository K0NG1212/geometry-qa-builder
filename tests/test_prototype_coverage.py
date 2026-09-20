import unittest
from builder_modules.m0_scope.coverage import summarize,scale_bin
class CoverageTests(unittest.TestCase):
 def test_reasoning_axis_not_input_axis_and_status_gate(self):
  policy={'version':'test','domains':['chemistry'],'scale_bins_nm':[[.1,1],[1,10]],'target_per_cell':10,'ability_soft_targets':{'perception':3,'inference':3,'design':3}}
  q={'id':'X','domain':'chemistry','ability':'perception','reasoningSizeNm':.24,'inputSizeNm':1.44,'prototypeScreeningPassed':True,'status':'pending_human_audit'}
  result=summarize({'questions':[q],'counts':{'ready':0}},policy)
  self.assertEqual(result['cells'][0]['screened_count'],1);self.assertEqual(result['cells'][1]['screened_count'],0)
  for state in ['archived','backlog','rework']:
   q['lifecycle']=state
   self.assertEqual(summarize({'questions':[q],'counts':{'ready':0}},policy)['screened_total'],0)
  q['lifecycle']='active'
  self.assertEqual(summarize({'questions':[q],'counts':{'ready':0}},policy)['screened_total'],1)
  q['status']='needs_revision'
  self.assertEqual(summarize({'questions':[q],'counts':{'ready':0}},policy)['screened_total'],0)
 def test_boundaries_unknown_and_nonfinite(self):
  bins=[[.1,1],[1,10],[10,100],[100,1000]]
  self.assertEqual(scale_bin(1,bins),1);self.assertEqual(scale_bin(1000,bins),3)
  for value in [None,True,float('nan'),float('inf'),0,1001]:self.assertIsNone(scale_bin(value,bins))
