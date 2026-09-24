"""Inference family: first-order energy change along a specified deformation path.

Physical relation supplied in the question: F_i = -dE/dr_i. Along the straight path
r(lambda) = r_A + lambda (r_B - r_A), dE/dlambda at B = -sum_i F_i(B) . (r_B - r_A).
Geometry is necessary: removing either structure removes the displacement.
This is a local directional derivative, never E(B) - E(A) or a stability claim.
"""
import json
import math
from decimal import Decimal, localcontext
from . import kit

VERSION = '0.1.0'


def force_table(elements, forces):
    rows = ['%d %s %.6f %.6f %.6f' % (i + 1, e, *f) for i, (e, f) in enumerate(zip(elements, forces))]
    return 'row element Fx Fy Fz (eV/angstrom), total PBE0+MBD force at B\n' + '\n'.join(rows) + '\n'


def parse_forces(text, n):
    rows = [line.split() for line in text.splitlines()[1:] if line.strip()]
    if len(rows) != n or any(len(r) != 5 or int(r[0]) != i + 1 for i, r in enumerate(rows)):
        raise ValueError('Force table rows do not match atoms')
    return [r[1] for r in rows], [tuple(Decimal(x) for x in r[2:]) for r in rows]


def build(spec, root, seed):
    path = root / 'docs' / spec['asset']
    raw = path.read_bytes()
    data = json.loads(raw)
    if data['coordinate_unit'] != 'angstrom' or data['force_unit'] != 'eV/angstrom':
        raise ValueError('Unsupported units')
    a_text = kit.xyz_text(data['elements'], data['reference_xyz'], 'A: %s (DFTB3+MBD optimized reference), angstrom' % data['reference_id'])
    b_text = kit.xyz_text(data['elements'], data['displaced_xyz'], 'B: %s (paired displaced structure), angstrom' % data['displaced_id'])
    f_text = force_table(data['elements'], data['forces_at_displaced'])
    ea, pa = kit.parse_xyz(a_text)
    eb, pb = kit.parse_xyz(b_text)
    ef, fd = parse_forces(f_text, len(pa))
    if not ea == eb == ef:
        raise ValueError('Atom order differs between A, B and forces')
    with localcontext() as ctx:
        ctx.prec = 40
        da = [[Decimal(x) for x in line.split()[1:]] for line in a_text.splitlines()[2:]]
        db = [[Decimal(x) for x in line.split()[1:]] for line in b_text.splitlines()[2:]]
        delta = [[y - x for x, y in zip(r, s)] for r, s in zip(da, db)]
        if not any(x for r in delta for x in r):
            raise ValueError('Zero displacement')
        s_exact = sum(f * d for fs, ds in zip(fd, delta) for f, d in zip(fs, ds))
        heavy = sum(f * d for e, fs, ds in zip(ea, fd, delta) if e != 'H' for f, d in zip(fs, ds))
        per_atom = [sum(f * d for f, d in zip(fs, ds)) for fs, ds in zip(fd, delta)]
    fl = [[float(x) for x in r] for r in fd]
    dl = [[float(x) for x in r] for r in delta]
    s_float = math.fsum(f * d for fs, ds in zip(fl, dl) for f, d in zip(fs, ds))
    if abs(s_float - float(s_exact)) > 1e-9:
        raise ValueError('Float and decimal projections disagree')
    # A_to_B: path from A, derivative at lambda = 1 (at B).  B_to_A: path from B toward A,
    # derivative at lambda = 0 (also at B); reversing the direction flips the sign.
    direction = spec.get('direction', 'A_to_B')
    if direction not in ('A_to_B', 'B_to_A'):
        raise ValueError('Unsupported path direction')
    sign = 1 if direction == 'A_to_B' else -1
    derivative = -s_exact * sign
    candidates = [
        dict(rule='sign_convention', value=-derivative, plausibility=3,
             reason='把力当作能量梯度（漏掉 F = −∂E/∂r 的负号），或忽略题目给定的路径方向。'),
        dict(rule='heavy_atoms_only', value=-heavy * sign, plausibility=2,
             reason='只累加重原子，忽略氢原子的受力与位移。'),
        dict(rule='trapezoid_energy_estimate', value=-s_exact * sign / 2, plausibility=2,
             reason='按 A 处受力为零的梯形估计给出能量差，而题目问的是 B 处的导数。'),
        dict(rule='abs_projection_sum', value=sum(abs(x) for x in per_atom), plausibility=2,
             reason='逐原子取投影绝对值后相加，丢失相互抵消。'),
        dict(rule='magnitude_product', value=math.fsum(kit.norm(f) * kit.norm(d) for f, d in zip(fl, dl)), plausibility=2,
             reason='只乘力与位移的模长，忽略夹角。'),
    ]
    decimals, tol, sep = 4, '0.00005', '0.0500'
    chosen, rejected, goal, rank = kit.choose_numeric(derivative, candidates, decimals=decimals, tolerance=tol,
                                                      min_separation=sep, seed=seed, context=spec['id'], target=spec.get('target_position'))
    options, audit = kit.label_numeric(derivative, chosen, decimals=decimals, unit='eV', seed=seed, context=spec['id'],
                                       correct_reason='B 处沿给定路径方向的导数 = −Σ F_i(B)·(路径方向位移)；十进制与浮点实现一致。')
    key = kit.validate_numeric(options, derivative, decimals=decimals, tolerance=tol, min_separation=sep, unit='eV')
    path = ('r_i(λ) = r_i(A) + λ[r_i(B) − r_i(A)], what is dE/dλ at λ = 1 (that is, at B)' if sign > 0 else
            'r_i(λ) = r_i(B) + λ[r_i(A) − r_i(B)], which starts at B and moves toward A, what is dE/dλ at λ = 0 (that is, at B)')
    question = ('Structures A and B of the same molecule share atom order and one Cartesian frame (angstrom). '
                'The table gives the total PBE0+MBD force on every atom at B (eV/angstrom), with F_i = −∂E/∂r_i. '
                'Along the straight path %s, in eV? Do not realign, mass-weight or normalize the displacement.') % path
    return dict(
        question=question,
        scope=spec['scope'],
        inputs=[dict(name='A.xyz', format='xyz', unit='angstrom', text=a_text),
                dict(name='B.xyz', format='xyz', unit='angstrom', text=b_text),
                dict(name='forces_B.txt', format='force-table', unit='eV/angstrom', text=f_text)],
        numeric=dict(value=kit.display(derivative, decimals), unit='eV', decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected,
        rank=dict(target=goal, achieved=rank),
        checks=dict(decimal_projection_S_eV=str(s_exact), float_projection_S_eV=s_float,
                    derivative_eV=str(derivative), direction=direction, atom_order_consistent=True,
                    source_ids=[data['reference_id'], data['displaced_id']], force_key=data['force_key'],
                    limits='局部方向导数，不是 E(B)−E(A)，也不证明 A 是 PBE0+MBD 极小点。'),
        scales=dict(input_nm=kit.dmax(pb) / 10, reasoning_nm=kit.dmax(pb) / 10,
                    reasoning_definition='全部原子参与：B 的最大原子间距'),
        input_hashes={spec['asset']: kit.sha256(raw)})
