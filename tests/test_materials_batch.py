import unittest,importlib.util
from pathlib import Path
from fractions import Fraction
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('material_calc','recompute_materials_batch.py');t=load('trace_export','export_public_trace.py')
class CrystalChecks(unittest.TestCase):
 def test_periodic_one_site_shell(self):
  c={'a_A':2,'rows':[{'element':'X','fractional':[0,0,0]}]};s=m.neighbors(c,'X');self.assertEqual(s['coordination'],6);self.assertEqual(s['distance_A'],2)
 def test_equal_and_unequal_phase_cancellation(self):
  c={'rows':[{'element':'A','fractional':[0,0,0],'fractional_exact':['0','0','0']},{'element':'B','fractional':[.5,0,0],'fractional_exact':['1/2','0','0']}]}
  self.assertEqual(m.structure_factor(c,(1,0,0),{'A':1,'B':1})['intensity'],0)
  self.assertEqual(m.structure_factor(c,(1,0,0),{'A':2,'B':1})['intensity'],1)
  self.assertEqual(m.structure_factor(c,(2,0,0),{'A':2,'B':1})['intensity'],9)
 def test_symmetry_terms_not_executable(self):
  self.assertEqual(m.expression('1/4-x',[Fraction(1,2),0,0]),Fraction(3,4))
  with self.assertRaises(ValueError):m.expression('__import__(x)',[0,0,0])
class TraceChecks(unittest.TestCase):
 def test_https_source_preserved(self):
  v={'url':'https://www.crystallography.net/cod/9008565.cif'};self.assertEqual(t.clean(v),v);self.assertFalse(t.contains_local_path(v))
 def test_local_paths_removed(self):
  for v in ['C:/Users/private/file','C:\\Users\\private\\file','file:///C:/private','input (D:/private)']:
   self.assertTrue(t.contains_local_path(v));self.assertEqual(t.clean(v),'[local path omitted]')
 def test_newline_is_not_windows_drive(self):
  v={'input':'fractional x,y,z:\n1 C 0 0 0'};self.assertFalse(t.contains_local_path(v));self.assertEqual(t.clean(v),v)
if __name__=='__main__':unittest.main()
