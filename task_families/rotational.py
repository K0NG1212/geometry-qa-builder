"""Rigid-rotor rotational spectroscopy of a supplied molecular geometry (quantum / chemistry, 0.1-1 and 1-10 nm).

rotational_line (inference): predict the frequency of one J = 1 <- 0 rotational transition (1_01, 1_11 or 1_10 <- 0_00)
    from the geometry: masses -> centre of mass -> inertia tensor -> principal moments -> rotational constants A >= B >= C
    -> the J = 1 level energies (B + C, A + C, A + B). The level formulas are standard rigid-rotor results and are not
    given in the question; masses, constants and the model are.
isotopologue_design (design, the inverse problem): choose the hydrogen atom whose H -> D substitution shifts a stated
    line the most, as when deciding which singly deuterated isotopologue to synthesise for a substitution (Kraitchman)
    structure. The shift depends on the distance from the principal axes, not simply on the distance from the centre of
    mass; the family records that shortcut.

Masses (most abundant isotopes, u) and constants are written in the question; principal moments come from a cyclic
Jacobi diagonalisation (the independent checker uses the closed-form cubic roots instead).
"""
import math
import re
from . import kit, chem_names

VERSION = '0.2.0'
MASS = {'H': '1.007825', 'D': '2.014102', 'C': '12.000000', 'N': '14.003074', 'O': '15.994915', 'F': '18.998403',
        'Si': '27.976927', 'P': '30.973762', 'S': '31.972071', 'Cl': '34.968853', 'Br': '78.918338', 'I': '126.904472'}
# Standard atomic weights (IUPAC abridged): the 'average masses' misconception.
AVERAGE = {'H': 1.008, 'C': 12.011, 'N': 14.007, 'O': 15.999, 'F': 18.998, 'Si': 28.085, 'P': 30.974, 'S': 32.06,
           'Cl': 35.45, 'Br': 79.904, 'I': 126.90}
PLANCK = '6.62607015e-34'          # J s (exact, SI 2019)
DALTON = '1.66053906660e-27'       # kg (CODATA 2018)
MAX_ATOMS = 60                     # broadband rotational spectroscopy reaches molecules of this size; larger hosts are left out
LINES = {
    '101': dict(label='1_01 ← 0_00', sum=('B', 'C'), kind='a-type', others=('111', '110')),
    '111': dict(label='1_11 ← 0_00', sum=('A', 'C'), kind='b-type', others=('101', '110')),
    '110': dict(label='1_10 ← 0_00', sum=('A', 'B'), kind='c-type', others=('101', '111')),
}
DESIGN_RATIO = 1.15                # the best substitution must exceed the runner-up by 15 % ...
DESIGN_MIN_MHZ = 0.5               # ... and by at least 0.5 MHz


def factor_mhz():
    """h / (8 pi^2) in MHz u angstrom^2."""
    return float(PLANCK) / (8 * math.pi ** 2 * float(DALTON) * 1e-20) / 1e6


def centre(masses, points):
    total = math.fsum(masses)
    return [math.fsum(m * p[k] for m, p in zip(masses, points)) / total for k in range(3)]


def tensor(masses, points, origin=None):
    c = centre(masses, points) if origin is None else origin
    t = [[0.0] * 3 for _ in range(3)]
    for m, p in zip(masses, points):
        r = kit.sub(p, c)
        rr = kit.dot(r, r)
        for i in range(3):
            for j in range(3):
                t[i][j] += m * ((rr if i == j else 0.0) - r[i] * r[j])
    return t


def jacobi(t, sweeps=50):
    """Eigenvalues and eigenvectors (columns of v) of a symmetric 3x3 matrix by cyclic Jacobi rotations."""
    a = [row[:] for row in t]
    v = [[float(i == j) for j in range(3)] for i in range(3)]
    for _ in range(sweeps):
        off = math.fsum(a[i][j] ** 2 for i in range(3) for j in range(3) if i != j)
        if off < 1e-26 * max(1.0, math.fsum(a[i][i] ** 2 for i in range(3))):
            break
        for p, q in ((0, 1), (0, 2), (1, 2)):
            if abs(a[p][q]) < 1e-300:
                continue
            theta = (a[q][q] - a[p][p]) / (2 * a[p][q])
            t_ = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1))
            c = 1 / math.sqrt(t_ * t_ + 1)
            s = t_ * c
            for k in range(3):
                akp, akq = a[k][p], a[k][q]
                a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
            for k in range(3):
                apk, aqk = a[p][k], a[q][k]
                a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
            for k in range(3):
                vkp, vkq = v[k][p], v[k][q]
                v[k][p], v[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    order = sorted(range(3), key=lambda i: a[i][i])
    return [a[i][i] for i in order], [[v[k][i] for k in range(3)] for i in order]


def constants(moments):
    """Rotational constants A >= B >= C in MHz from principal moments in u angstrom^2."""
    f = factor_mhz()
    a, b, c = sorted(moments)
    return dict(A=f / a, B=f / b, C=f / c)


def line(abc, key):
    x, y = LINES[key]['sum']
    return abc[x] + abc[y]


def masses_of(elements, table=MASS):
    return [float(table[e]) for e in elements]


def student_xyz(text):
    """The attached XYZ: count and atom rows unchanged, the dataset conformer id dropped from the comment line (an id
    would let a model look the molecule up; tests/test_admission.py)."""
    lines = text.split('\n')
    lines[1] = re.sub(r',? conformer \S+?(?=,|$)', '', lines[1])
    return '\n'.join(lines)


def load(spec, root):
    path = root / 'docs' / spec['asset']
    raw = path.read_bytes()
    text = student_xyz(raw.decode('utf-8-sig'))
    elements, points = kit.parse_xyz(text)
    if len(elements) > MAX_ATOMS:
        raise ValueError('Molecule larger than %d atoms: outside the rotational-spectroscopy scope' % MAX_ATOMS)
    if any(e not in MASS for e in elements):
        raise ValueError('No isotope mass for an element')
    return path, raw, text, elements, points


def model_text(elements):
    present = sorted(set(elements), key=lambda e: (e != 'C', e != 'H', e))
    masses = ', '.join('%s %s u' % (e, MASS[e]) for e in present)
    return ('Model conditions: a rigid rotor at exactly the supplied geometry (no vibrational averaging, no centrifugal '
            'distortion); masses of the most abundant isotopes: %s; rotational constants A ≥ B ≥ C are h/(8π²I) with '
            'I_a ≤ I_b ≤ I_c the principal moments of inertia about the centre of mass; h = 6.62607015×10⁻³⁴ J s, '
            '1 u = 1.66053906660×10⁻²⁷ kg.') % masses


def principal(elements, points, table=MASS):
    moments, axes = jacobi(tensor(masses_of(elements, table), points))
    return moments, axes


def decimals_for(value):
    return 1 if value >= 100 else 2


# ------------------------------------------------------------------ inference: predicted line frequency
def build_line(spec, root, seed):
    path, raw, text, elements, points = load(spec, root)
    key = spec['line']
    masses = masses_of(elements)
    moments, axes = principal(elements, points)
    if min(moments) <= 1e-6:
        raise ValueError('Linear or degenerate rotor')
    abc = constants(moments)
    nu = line(abc, key)
    # Cross-check: the moments are invariant under rotation of the input frame (trace and determinant).
    t = tensor(masses, points)
    trace = t[0][0] + t[1][1] + t[2][2]
    if abs(trace - sum(moments)) > 1e-8 * trace:
        raise ValueError('Principal moments do not reproduce the tensor trace')
    other = lambda k: line(abc, k)
    diag = sorted(t[i][i] for i in range(3))                        # tensor diagonal in the input frame, never diagonalised
    origin = tensor(masses, points, origin=[0.0, 0.0, 0.0])         # moments about the coordinate origin
    heavy = [i for i, e in enumerate(elements) if e != 'H']
    f = factor_mhz()
    candidates = [
        dict(rule='linear_rotor_2B', value=2 * abc['B'], plausibility=3 if key == '101' else 2,
             reason='套用线型分子公式 ν(J=1←0) = 2B，忽略了非对称陀螺 J = 1 能级按 K 分裂。'),
        dict(rule='four_pi_squared', value=2 * nu, plausibility=2, reason='转动常数写成 h/(4π²I)，结果大了一倍。'),
        dict(rule='hbar_instead_of_h', value=2 * math.pi * nu, plausibility=1, reason='用 ħ/(2I)（角频率）当作以 Hz 计的频率，大了 2π 倍。'),
        dict(rule='single_constant', value=abc[LINES[key]['sum'][0]], plausibility=1,
             reason='只取一个转动常数 %s，没有把两个常数相加。' % LINES[key]['sum'][0]),
        dict(rule='unrotated_tensor_diagonal', value=line(constants(diag), key), plausibility=3,
             reason='直接用输入坐标系中惯量张量的对角元当主转动惯量，没有对角化。'),
        dict(rule='origin_not_centre_of_mass', value=line(constants(jacobi(origin)[0]), key), plausibility=3,
             reason='对坐标原点而不是质心计算转动惯量（没有先平移到质心）。'),
        dict(rule='average_atomic_weights', value=line(constants(principal(elements, points, AVERAGE)[0]), key), plausibility=2,
             reason='用元素的标准原子量而不是题设的同位素质量。'),
        # Smaller-value mistake: sum(m r^2) about the centre of mass equals (I_a + I_b + I_c) / 2 >= I_c.
        dict(rule='polar_moment_as_I', value=2 * f / (sum(moments) / 2), plausibility=2,
             reason='把对质心的 Σmr²（极惯量，等于三个主惯量之和的一半）当作转动惯量，再按 2B 计算。'),
        dict(rule='equal_masses', value=line(constants(jacobi(tensor([1.0] * len(points), points))[0]), key), plausibility=1,
             reason='所有原子取相同质量（纯几何的惯量），没有质量加权。'),
    ]
    if heavy and len(heavy) < len(elements):
        hm = [masses[i] for i in heavy]
        hp = [points[i] for i in heavy]
        candidates.append(dict(rule='heavy_atoms_only', value=line(constants(jacobi(tensor(hm, hp))[0]), key), plausibility=2,
                               reason='只计重原子、忽略氢原子的贡献。'))
    for k in LINES[key]['others']:
        candidates.append(dict(rule='other_J1_level:%s' % k, value=other(k), plausibility=3,
                               reason='能级标号对错：算成 %s 跃迁（%s + %s）。' % (LINES[k]['label'], *LINES[k]['sum'])))
    decimals = decimals_for(nu)
    tol = kit.display(0.5 * 10 ** -decimals, decimals + 1)
    sep = kit.display(max(0.02 * nu, 20 * 10 ** -decimals), decimals)
    between = kit.display(max(0.01 * nu, 10 * 10 ** -decimals), decimals)
    chosen, rejected, goal, rank = kit.choose_numeric(nu, candidates, decimals=decimals, tolerance=tol, min_separation=sep,
                                                      seed=seed, context=spec['id'], lower=0, target=spec.get('target_position'),
                                                      distractor_separation=between)
    kit.require_rank(spec, goal, rank)
    options, audit = kit.label_numeric(nu, chosen, decimals=decimals, unit='MHz', seed=seed, context=spec['id'],
                                       correct_reason='质心 → 惯量张量 → Jacobi 对角化 → A、B、C → %s = %s + %s。' % (
                                           LINES[key]['label'], *LINES[key]['sum']))
    answer = kit.validate_numeric(options, nu, decimals=decimals, tolerance=tol, min_separation=sep, unit='MHz',
                                  distractor_separation=between)
    question = ('%s %s Predict the frequency of the J_KaKc = %s rotational transition of this molecule, in MHz.' % (
        spec['context'], model_text(elements), LINES[key]['label']))
    kappa = (2 * abc['B'] - abc['A'] - abc['C']) / (abc['A'] - abc['C'])
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name=path.name, format='xyz', unit='angstrom', text=text)],
        numeric=dict(value=kit.display(nu, decimals), unit='MHz', decimals=decimals, tolerance=tol),
        options=options, correct_label=answer, option_audit=audit, excluded_candidates=rejected,
        rank=dict(target=goal, achieved=rank),
        checks=dict(principal_moments_u_A2=moments, rotational_constants_MHz=abc, line=LINES[key]['label'],
                    line_kind=LINES[key]['kind'], ray_kappa=kappa, trace_invariant=True,
                    h_over_8pi2_MHz_uA2=f, centre_of_mass_offset_A=kit.norm(centre(masses, points)),
                    limits='刚性转子、平衡几何（QM7-X 为 DFTB3+MBD 优化，SAMPL9 为挑战赛结构）；不含振动平均与离心畸变，'
                           '与实测谱线可差约 1%%；不评估该跃迁的偶极强度（%s 跃迁需要相应的偶极分量）。' % LINES[key]['kind']),
        scales=dict(input_nm=kit.dmax(points) / 10, reasoning_nm=kit.dmax(points) / 10,
                    reasoning_definition='整分子转动惯量：分子最大原子间距'),
        input_hashes={spec['asset']: kit.sha256(raw)})


# ------------------------------------------------------------------ design: which H -> D substitution shifts a line the most
def substituted(elements, points, row, key, table=MASS):
    masses = masses_of(elements, table)
    masses[row] = float(MASS['D'])
    return line(constants(jacobi(tensor(masses, points))[0]), key)


def shifts(elements, points, key, rows):
    parent = line(constants(principal(elements, points)[0]), key)
    return parent, {r: substituted(elements, points, r, key) - parent for r in rows}


def build_isotopologue(spec, root, seed):
    path, raw, text, elements, points = load(spec, root)
    key = spec['line']
    rows = [r - 1 for r in spec['candidates']]
    if len(rows) != 4 or len(set(rows)) != 4 or any(not 0 <= r < len(elements) or elements[r] != 'H' for r in rows):
        raise ValueError('Exactly four distinct hydrogen rows required')
    parent, delta = shifts(elements, points, key, rows)
    ranked = sorted(rows, key=lambda r: -abs(delta[r]))
    best, runner = ranked[0], ranked[1]
    if abs(delta[best]) < DESIGN_RATIO * abs(delta[runner]) or abs(delta[best]) - abs(delta[runner]) < DESIGN_MIN_MHZ:
        raise ValueError('Winning substitution does not lead by the required margin')
    masses = masses_of(elements)
    com = centre(masses, points)
    far = max(rows, key=lambda r: math.dist(points[r], com))
    name = lambda r: 'H%d (row %d)' % (r + 1, r + 1)
    why = {}
    if far != best:
        why[far] = ('farthest_from_centre_of_mass', '离质心最远（%.2f Å），但谱线位移取决于到相应主轴的距离，不是到质心的距离。'
                    % math.dist(points[far], com), 3)
    for k in LINES[key]['others']:
        _, d2 = shifts(elements, points, k, rows)
        pick = max(rows, key=lambda r: abs(d2[r]))
        if pick != best and pick not in why:
            why[pick] = ('best_for_other_line:%s' % k, '对 %s 跃迁位移最大（%.2f MHz），看错了谱线。' % (LINES[k]['label'], d2[pick]), 3)
    for c in LINES[key]['sum']:
        parent_c = constants(principal(elements, points)[0])[c]
        moved = {}
        for r in rows:
            m = masses_of(elements)
            m[r] = float(MASS['D'])
            moved[r] = constants(jacobi(tensor(m, points))[0])[c] - parent_c
        pick = max(rows, key=lambda r: abs(moved[r]))
        if pick != best and pick not in why:
            why[pick] = ('best_for_single_constant:%s' % c, '只看转动常数 %s 的变化时它最大（%.2f MHz），忽略了谱线是两个常数之和。'
                         % (c, moved[pick]), 2)
    for r in rows:
        if r != best and r not in why:
            why[r] = ('smaller_shift', '谱线位移 %.2f MHz，小于正确项。' % delta[r], 2)
    others = [(why[r][0], name(r), why[r][1], why[r][2], r) for r in rows if r != best]
    order = kit.place(('correct', name(best), '取代后 %s 位移 %.2f MHz，最大（第二名 %.2f MHz）。' % (
        LINES[key]['label'], delta[best], delta[runner]), 3, best), others, spec.get('target_position'), seed, spec['id'],
        key=lambda q: q[1])
    options = [dict(label=l, value=q[1]) for l, q in zip(kit.LABELS, order)]
    answer = kit.validate_verdicts(options, [q[0] == 'correct' for q in order])
    audit = [dict(label=l, value=q[1], rule=q[0], reason=q[2], is_correct=q[0] == 'correct', shift_MHz=round(delta[q[4]], 4),
                  distance_from_centre_of_mass_A=round(math.dist(points[q[4]], com), 4)) for l, q in zip(kit.LABELS, order)]
    listed = ', '.join('H%d' % (r + 1) for r in sorted(rows))
    # Chemical identity of each candidate (advisor: name chemical entities, not rows); needs the stated total charge.
    names = chem_names.Molecule(elements, points, spec['charge'])
    where = [names.hydrogen(r) for r in sorted(rows)]
    if None in where:
        raise ValueError('A candidate hydrogen sits on an atom the naming rules do not recognise')
    question = ('%s %s You will record the rotational spectrum of one singly deuterated isotopologue: exactly one of the '
                'hydrogen atoms %s (rows counted from 1 after the two XYZ header lines) is replaced by deuterium, D %s u, at '
                'the same position. Candidates: %s. You want the largest change in the frequency of the J_KaKc = %s transition '
                'relative to the parent molecule (largest absolute shift). Exactly one candidate gives the largest shift. Which '
                'hydrogen should be substituted?') % (spec['context'], model_text(elements), listed, MASS['D'], '; '.join(where),
                                                      LINES[key]['label'])
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name=path.name, format='xyz', unit='angstrom', text=text)],
        numeric=None, options=options, correct_label=answer, option_audit=audit, excluded_candidates=[], rank=None,
        checks=dict(line=LINES[key]['label'], parent_line_MHz=parent, shifts_MHz={'H%d' % (r + 1): delta[r] for r in rows},
                    margin_ratio=abs(delta[best]) / abs(delta[runner]), required_ratio=DESIGN_RATIO,
                    margin_MHz=abs(delta[best]) - abs(delta[runner]), required_MHz=DESIGN_MIN_MHZ,
                    shortcut_diagnostics=dict(farthest_from_centre_of_mass_is_correct=far == best),
                    design_note='设计选择：为替代法（Kraitchman）结构测定选择单氘代位点；设计 = 谱线推断的逆问题。',
                    limits='刚性转子、几何不随同位素改变；不评估合成难度、谱线强度与超精细结构。'),
        scales=dict(input_nm=kit.dmax(points) / 10, reasoning_nm=kit.dmax(points) / 10,
                    reasoning_definition='整分子转动惯量：分子最大原子间距'),
        input_hashes={spec['asset']: kit.sha256(raw)})
