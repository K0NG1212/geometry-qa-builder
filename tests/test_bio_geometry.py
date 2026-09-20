import unittest,importlib.util,math
from pathlib import Path
spec=importlib.util.spec_from_file_location('bio_calc',Path(__file__).resolve().parents[1]/'tools/recompute_bio_batch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class GeometryChecks(unittest.TestCase):
 def test_known_triangle(self):
  r=m.metrics([{'xyz':p} for p in [(0,0,0),(3,0,0),(0,4,0)]])
  self.assertAlmostEqual(r['rg_A'],math.sqrt(50/9));self.assertEqual(r['diameter_A'],5);self.assertEqual(r['diameter_pair'],[2,3])
 def test_rigid_frame_and_scaling(self):
  points=[(0,0,0),(3,0,0),(0,4,0),(2,1,5)]
  original=m.metrics([{'xyz':p} for p in points])
  transformed=m.metrics([{'xyz':[-2*y+100,2*x-30,2*z+20]} for x,y,z in points])
  for k in ['rg_A','diameter_A','end_to_end_A']:self.assertAlmostEqual(transformed[k],2*original[k])
if __name__=='__main__':unittest.main()
