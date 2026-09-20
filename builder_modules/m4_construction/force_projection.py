"""Supplementary Q02 calculator, not an automatically registered pipeline verifier.
Paired coordinates MUST already share atom order and Cartesian frame.
Returns force contraction at B with the specified A-to-B displacement, in eV;
this is NOT a finite energy difference or a stability certificate.
"""
import math

def calculate(reference, displaced, forces, *, coordinate_unit, force_unit, same_frame, same_atom_order, threshold=0.000001):
    if coordinate_unit!='angstrom' or force_unit!='eV/angstrom':raise ValueError('unsupported units')
    if same_frame is not True or same_atom_order is not True:raise ValueError('frame/order not confirmed')
    if not math.isfinite(threshold) or threshold<=0:raise ValueError('invalid threshold')
    if not reference or not len(reference)==len(displaced)==len(forces):raise ValueError('shape mismatch')
    for rows in [reference,displaced,forces]:
        if any(len(r)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in r) for r in rows):raise ValueError('invalid vectors')
    delta=[[b-a for a,b in zip(r,s)] for r,s in zip(reference,displaced)]
    if not any(x for r in delta for x in r):raise ValueError('zero displacement')
    value=math.fsum(f*d for fs,ds in zip(forces,delta) for f,d in zip(fs,ds))
    return {'force_dot_displacement_eV':value,'directional_energy_derivative_eV':-value,'classification':'opposes' if value < -threshold else 'reinforces' if value > threshold else 'near_zero','threshold_eV':threshold,'scope':'instantaneous projection at B along the specified A-to-B coordinate path; no stability claim'}
