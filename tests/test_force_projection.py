import unittest
from builder_modules.m4_construction.force_projection import calculate
class ForceTests(unittest.TestCase):
 def run_calc(self,r,b,f,**kw):return calculate(r,b,f,coordinate_unit='angstrom',force_unit='eV/angstrom',same_frame=True,same_atom_order=True,**kw)
 def test_sign_zero_and_translation(self):
  self.assertEqual(self.run_calc([[0,0,0]],[[1,0,0]],[[-2,0,0]])['classification'],'opposes')
  self.assertEqual(self.run_calc([[0,0,0]],[[1,0,0]],[[2,0,0]])['classification'],'reinforces')
  self.assertEqual(self.run_calc([[0,0,0]],[[1,0,0]],[[0,2,0]])['classification'],'near_zero')
  self.assertEqual(self.run_calc([[5,5,5]],[[6,5,5]],[[-2,0,0]])['force_dot_displacement_eV'],-2)
 def test_cancellation_and_invalid(self):
  self.assertEqual(self.run_calc([[0,0,0],[0,0,0]],[[1,0,0],[1,0,0]],[[2,0,0],[-2,0,0]])['classification'],'near_zero')
  with self.assertRaises(ValueError):self.run_calc([[0,0,0]],[[0,0,0]],[[2,0,0]])
  with self.assertRaises(ValueError):self.run_calc([[0,0,0]],[[1,0,0]],[[float('nan'),0,0]])
  with self.assertRaises(ValueError):calculate([[0,0,0]],[[1,0,0]],[[1,0,0]],coordinate_unit='bohr',force_unit='eV/angstrom',same_frame=True,same_atom_order=True)
