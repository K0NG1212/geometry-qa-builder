"""Large assemblies (10-1000 nm): whole-particle size, capsid architecture and whole-particle scattering.

Inputs are the reduced public assets built by tools/build_assembly_assets.py (one point per
residue, or per-chain centroids after the deposited icosahedral expansion). The reasoning
scale is the whole particle, so these questions genuinely sit in the 10-100 / 100-1000 nm
cells; local quantities such as neighbouring-subunit spacing (~5 nm) are deliberately not
used here because they would belong to the 1-10 nm cell.
"""
import math
from decimal import Decimal, localcontext
import numpy as np
from . import kit

VERSION = '0.2.0'
ALLOWED_T = sorted({h * h + h * k + k * k for h in range(0, 16) for k in range(0, 16) if h + k > 0})


def load(root, spec):
    raw = (root / 'docs' / spec['asset']).read_bytes()
    text = raw.decode('utf-8')
    if spec['asset'].endswith('.xyz'):
        elements, points = kit.parse_xyz(text, max_atoms=20000)
        labels = elements
    else:
        rows = [line.split() for line in text.splitlines()[1:] if line.strip()]
        labels, points = [r[0] for r in rows], [tuple(float(x) for x in r[2:5]) for r in rows]
    fmt = 'xyz' if spec['asset'].endswith('.xyz') else 'centroid-table'
    return text, fmt, labels, points, kit.sha256(raw)


def select(labels, points, component):
    return [p for l, p in zip(labels, points) if component in (None, l)]


_DMAX = {}


def dmax_pair(points):
    """Chunked float search, then Decimal re-evaluation of the winning pair (cached per point set)."""
    cache_key = (len(points), points[0], points[-1], hash(tuple(points)))
    if cache_key in _DMAX:
        return _DMAX[cache_key]
    a = np.asarray(points, dtype=float)
    best, pair = -1.0, None
    for start in range(0, len(a), 1000):
        block = a[start:start + 1000]
        d2 = ((block[:, None, :] - a[None, :, :]) ** 2).sum(axis=2)
        i, j = np.unravel_index(np.argmax(d2), d2.shape)
        if d2[i, j] > best:
            best, pair = float(d2[i, j]), (start + int(i), int(j))
    with localcontext() as ctx:
        ctx.prec = 40
        exact = sum((Decimal(repr(points[pair[0]][k])) - Decimal(repr(points[pair[1]][k]))) ** 2 for k in range(3)).sqrt()
    if abs(float(exact) - math.sqrt(best)) > 1e-6:
        raise ValueError('Decimal re-evaluation disagrees')
    _DMAX[cache_key] = (float(exact), pair)
    return _DMAX[cache_key]


def rg(points):
    a = np.asarray(points, dtype=float)
    value = float(np.sqrt(((a - a.mean(axis=0)) ** 2).sum(axis=1).mean()))
    with localcontext() as ctx:
        ctx.prec = 40
        n = len(points)
        c = [sum(Decimal(repr(p[k])) for p in points) / n for k in range(3)]
        exact = (sum(sum((Decimal(repr(p[k])) - c[k]) ** 2 for k in range(3)) for p in points) / n).sqrt()
    if abs(float(exact) - value) > 1e-6:
        raise ValueError('Decimal centroid formula disagrees')
    return float(exact)


def size_candidates(points, others):
    a = np.asarray(points, dtype=float)
    radii = np.sqrt(((a - a.mean(axis=0)) ** 2).sum(axis=1))
    span = a.max(axis=0) - a.min(axis=0)
    r = rg(points)
    out = [dict(rule='bounding_box_diagonal', value=float(np.sqrt((span ** 2).sum())), plausibility=3,
                reason='用坐标轴对齐包围盒对角线代替实际最大间距。'),
           dict(rule='centroid_diameter', value=float(2 * radii.max()), plausibility=2, reason='用两倍最大中心距代替最大点对间距。'),
           dict(rule='largest_axis_span', value=float(span.max()), plausibility=2, reason='只取单一坐标轴上的最大跨度。'),
           dict(rule='mean_radius', value=float(radii.mean()), plausibility=2, reason='用中心距的算术平均。'),
           dict(rule='max_radius', value=float(radii.max()), plausibility=2, reason='用最大中心距（半径而非直径或均方根）。'),
           dict(rule='sphere_radius_from_rg', value=r * math.sqrt(5 / 3), plausibility=2, reason='按实心球关系 R = √(5/3)·Rg 换成半径。'),
           dict(rule='two_rg', value=2 * r, plausibility=1, reason='把回转半径乘二。'),
           dict(rule='radius_of_gyration', value=r, plausibility=1, reason='把回转半径当作所问的量。'),
           dict(rule='single_axis_rms', value=float(np.sqrt(((a - a.mean(axis=0)) ** 2).mean(axis=0).max())), plausibility=2,
                reason='只算了一个坐标轴方向的均方根离散度，而不是三维距离。')]
    if others is not None:
        out.append(dict(rule='wrong_selection', value=dmax_pair(others)[0], plausibility=3,
                        reason='用了全部组分的点，而题目只问指定组分。'))
    return out


def build_size(spec, root, seed, measure):
    text, fmt, labels, points, digest = load(root, spec)
    chosen = select(labels, points, spec.get('component'))
    others = points if spec.get('component') and len(chosen) < len(points) else None
    if measure == 'extent':
        value = dmax_pair(chosen)[0] / 10
        ask = 'the largest distance between any two of the selected points'
    else:
        value = rg(chosen) / 10
        ask = 'the equal-weight radius of gyration of the selected points (every point weighted equally)'
    cands = [dict(c, value=c['value'] / 10) for c in size_candidates(chosen, others)
             if not (measure == 'extent' and c['rule'] == 'radius_of_gyration') and not (measure == 'rg' and c['rule'] == 'two_rg')]
    if measure == 'rg':
        cands.append(dict(rule='max_distance', value=dmax_pair(chosen)[0] / 10, plausibility=1, reason='报告了最大点对间距。'))
    decimals, tol, sep = 2, '0.005', '0.30'
    picked, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=decimals, tolerance=tol, min_separation=sep, seed=seed,
                                                      context=spec['id'], lower=0, target=spec.get('target_position'),
                                                      distractor_separation='0.10')
    options, audit = kit.label_numeric(value, picked, decimals=decimals, unit='nm', seed=seed, context=spec['id'],
                                       correct_reason='按定义在所选点上计算（numpy 分块搜索 + Decimal 复核）。')
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=sep, unit='nm',
                               distractor_separation='0.10')
    which = ('all points labelled %s' % spec['component']) if spec.get('component') else 'all supplied points'
    question = ('%s Select %s. What is %s, in nanometres?' % (spec['context'], which, ask))
    dm = dmax_pair(chosen)[0] / 10
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name=spec['asset'].rsplit('/', 1)[1], format=fmt, unit='angstrom', text=text)],
        numeric=dict(value=kit.display(value, decimals), unit='nm', decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
        checks=dict(points=len(chosen), component=spec.get('component'), value_nm=value, dmax_nm=dm,
                    limits='约简表示（每残基一点或每链质心）上的几何量；不是溶液中的流体力学尺寸。'),
        scales=dict(input_nm=dmax_pair(points)[0] / 10, reasoning_nm=dm, reasoning_definition='所选点集的最大间距（整个颗粒）'),
        input_hashes={spec['asset']: digest})


def build_extent(spec, root, seed):
    return build_size(spec, root, seed, 'extent')


def build_rg(spec, root, seed):
    return build_size(spec, root, seed, 'rg')


def build_trimer_capsid(spec, text, fmt, points, shell, digest, seed):
    """Large dsDNA-virus capsids (e.g. PBCV-1): the major capsid protein forms trimeric pseudo-hexameric
    capsomers, 10(T-1) of them, and the 12 pentons are a different protein, so N = 30(T-1)."""
    n = len(shell)
    if n % 30 or n // 30 + 1 not in ALLOWED_T:
        raise ValueError('Major-capsid-protein copies are not 30(T-1) for an allowed T')
    t = n // 30 + 1
    near = sorted((x for x in ALLOWED_T if x != t), key=lambda x: (abs(x - t), x))
    cands = [dict(rule='monomer_60T_rule', value=n / 60, plausibility=3, reason='按单体外壳 N = 60T 计算（忽略三聚体壳粒）。'),
             dict(rule='trimers_as_60T', value=n / 180, plausibility=2, reason='把三聚体数当作 60T 个亚基。'),
             dict(rule='forgot_pentons', value=n / 30, plausibility=3, reason='漏掉 +1：三聚体壳粒只占 10(T−1)，五邻体另由其他蛋白构成。'),
             dict(rule='hexamer_rule', value=n / 60 + 1, plausibility=2, reason='把三聚体当成六聚体计（N = 60(T−1)）。')]
    cands += [dict(rule='neighbouring_allowed_T_%d' % x, value=x, plausibility=1, reason='相邻的允许三角剖分数 T=%d；与 N/30 + 1 不符。' % x)
              for x in near[:2]]
    picked, rejected, goal, rank = kit.choose_numeric(t, [c for c in cands if c['value'] == int(c['value'])], decimals=0,
                                                      tolerance='0.4', min_separation='0.9', seed=seed, context=spec['id'],
                                                      lower=0, target=spec.get('target_position'))
    options, audit = kit.label_numeric(t, picked, decimals=0, unit='', seed=seed, context=spec['id'],
                                       correct_reason='N = %d 个 %s，三聚体壳粒 N/3 = 10(T−1)，T = N/30 + 1 = %d。' % (n, spec['component'], t))
    key = kit.validate_numeric(options, t, decimals=0, tolerance='0.4', min_separation='0.9', unit='')
    question = ('%s Each row is one copy of a protein, labelled by component. In this capsid the major capsid protein %s forms trimeric '
                'pseudo-hexameric capsomers, and the 12 pentamers at the vertices are formed by a different protein. What is the '
                'triangulation number T of the icosahedral shell?' % (spec['context'], spec['component']))
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name=spec['asset'].rsplit('/', 1)[1], format=fmt, unit='angstrom', text=text)],
        numeric=dict(value=str(t), unit='', decimals=0, tolerance='0.4'),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
        checks=dict(copies=n, T=t, component=spec['component'], relation='trimeric capsomers: N = 3 × 10(T−1)',
                    limits='假设完整二十面体外壳（沉积的对称操作）；五邻体蛋白不计入 N。'),
        scales=dict(input_nm=dmax_pair(points)[0] / 10, reasoning_nm=dmax_pair(shell)[0] / 10,
                    reasoning_definition='整个外壳：所选组分点集的最大间距'),
        input_hashes={spec['asset']: digest})


def build_capsid(spec, root, seed):
    """Caspar–Klug architecture from the copy number N of the shell protein: T = N / 60,
    capsomers = 10T + 2 (12 pentamers + 10(T-1) hexamers)."""
    text, fmt, labels, points, digest = load(root, spec)
    shell = select(labels, points, spec['component'])
    n = len(shell)
    if spec.get('capsomer_form') == 'trimer':
        return build_trimer_capsid(spec, text, fmt, points, shell, digest, seed)
    if n % 60 or n // 60 not in ALLOWED_T:
        raise ValueError('Shell copy number is not 60T for an allowed T')
    t = n // 60
    ask = spec['ask']
    truth = {'T': t, 'capsomers': 10 * t + 2, 'hexons': 10 * (t - 1)}[ask]
    near = [x for x in ALLOWED_T if x != t]
    near.sort(key=lambda x: (abs(x - t), x))
    cands = {'T': [dict(rule='neighbouring_allowed_T_%d' % x, value=x, plausibility=2, reason='相邻的允许三角剖分数 T=%d；与 N/60 不符。' % x)
                   for x in near[:4]],
             'capsomers': [dict(rule='all_hexamers', value=n / 6, plausibility=3, reason='把所有亚基都当作六聚体。'),
                           dict(rule='all_pentamers', value=n / 5, plausibility=2, reason='把所有亚基都当作五聚体。'),
                           dict(rule='hexons_only', value=10 * (t - 1), plausibility=3, reason='只数了六邻体，漏掉 12 个五邻体。'),
                           dict(rule='pentons_only', value=12, plausibility=1, reason='只数了 12 个五邻体。'),
                           dict(rule='copies_as_capsomers', value=n, plausibility=1, reason='把亚基数当作壳粒数。')],
             'hexons': [dict(rule='all_capsomers', value=10 * t + 2, plausibility=3, reason='把五邻体也算作六邻体。'),
                        dict(rule='all_hexamers', value=n / 6, plausibility=3, reason='把所有亚基都当作六聚体。'),
                        dict(rule='pentons_as_hexons', value=12, plausibility=1, reason='报告了五邻体数。'),
                        dict(rule='hexon_subunits', value=n - 60, plausibility=2, reason='报告了六邻体中的亚基数而非六邻体数。')]}[ask]
    picked, rejected, goal, rank = kit.choose_numeric(truth, [c for c in cands if c['value'] == int(c['value'])], decimals=0,
                                                      tolerance='0.4', min_separation='0.9', seed=seed, context=spec['id'],
                                                      lower=0, target=spec.get('target_position'))
    options, audit = kit.label_numeric(truth, picked, decimals=0, unit='', seed=seed, context=spec['id'],
                                       correct_reason='N = %d 个 %s，T = N/60 = %d；五邻体 12 个，六邻体 10(T−1)。' % (n, spec['component'], t))
    key = kit.validate_numeric(options, truth, decimals=0, tolerance='0.4', min_separation='0.9', unit='')
    what = {'T': 'the triangulation number T of the icosahedral shell formed by %s' % spec['component'],
            'capsomers': 'the total number of capsomers (pentamers plus hexamers) in the shell formed by %s' % spec['component'],
            'hexons': 'the number of hexameric capsomers (hexons) in the shell formed by %s' % spec['component']}[ask]
    question = '%s Each row is one copy of a protein, labelled by component. What is %s?' % (spec['context'], what)
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name=spec['asset'].rsplit('/', 1)[1], format=fmt, unit='angstrom', text=text)],
        numeric=dict(value=str(truth), unit='', decimals=0, tolerance='0.4'),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
        checks=dict(copies=n, T=t, component=spec['component'], relation='Caspar–Klug: N = 60T; capsomers = 12 + 10(T−1)',
                    limits='假设完整二十面体外壳（沉积的对称操作）；不区分门户顶点等局部不对称。'),
        scales=dict(input_nm=dmax_pair(points)[0] / 10, reasoning_nm=dmax_pair(shell)[0] / 10,
                    reasoning_definition='整个外壳：所选组分点集的最大间距'),
        input_hashes={spec['asset']: digest})


# ------------------------------------------------------------------ whole-particle scattering (Debye)
_PAIRS = {}


def pair_distances(points):
    """All i<j distances in nm (cached per point set)."""
    cache_key = (len(points), points[0], points[-1], hash(tuple(points)))
    if cache_key not in _PAIRS:
        a = np.asarray(points, dtype=float) / 10
        rows = [np.sqrt(((a[i + 1:] - a[i]) ** 2).sum(axis=1)) for i in range(len(a) - 1)]
        _PAIRS[cache_key] = np.concatenate(rows)
    return _PAIRS[cache_key]


def debye(points, q):
    """Orientation-averaged I(q)/I(0) of identical point scatterers:
    [N + 2 sum_{i<j} sin(q r)/(q r)] / N^2 (q in nm^-1)."""
    n = len(points)
    if q == 0:
        return 1.0
    return (n + 2 * float(np.sinc(q * pair_distances(points) / math.pi).sum())) / n ** 2


def debye_check(points, q):
    """Second implementation: full N x N sum in row blocks with explicit sin(x)/x (diagonal = 1)."""
    a = np.asarray(points, dtype=float) / 10
    total = 0.0
    for start in range(0, len(a), 400):
        x = q * np.sqrt(((a[start:start + 400, None, :] - a[None, :, :]) ** 2).sum(axis=2))
        safe = np.where(x > 0, x, 1.0)
        total += math.fsum(np.where(x > 0, np.sin(safe) / safe, 1.0).sum(axis=1))
    return total / len(a) ** 2


def single_orientation(points, q):
    """|sum exp(i q x_j)|^2 / N^2 for q along the x axis only (no orientational average)."""
    x = np.asarray(points, dtype=float)[:, 0] / 10
    return float(abs(np.exp(1j * q * x).sum()) ** 2) / len(x) ** 2


def sphere(q, radius):
    x = q * radius
    return 1.0 if x == 0 else (3 * (math.sin(x) - x * math.cos(x)) / x ** 3) ** 2


def first_crossing(f, target, step, qmax):
    """Smallest q > 0 with f(q) = target: march in `step`, then bisect the bracketing interval."""
    lo, flo = 0.0, f(0.0)
    q = step
    while q <= qmax:
        fq = f(q)
        if (fq - target) * (flo - target) <= 0 and fq != flo:
            hi = q
            for _ in range(60):
                mid = (lo + hi) / 2
                fm = f(mid)
                if (fm - target) * (flo - target) > 0:
                    lo, flo = mid, fm
                else:
                    hi = mid
            return (lo + hi) / 2
        lo, flo, q = q, fq, q + step
    return None


def subject(spec, which):
    return '%s Select %s. Treat each selected point as an identical point scatterer (no form factor, no solvent).' % (
        spec['context'], which)


def axis_spread(points):
    a = np.asarray(points, dtype=float)
    return float(np.sqrt(((a - a.mean(axis=0)) ** 2).mean(axis=0).max())) / 10


def scatter_setup(spec, root):
    text, fmt, labels, points, digest = load(root, spec)
    chosen = select(labels, points, spec.get('component'))
    which = ('all points labelled %s' % spec['component']) if spec.get('component') else 'all supplied points'
    return text, fmt, chosen, which, rg(chosen) / 10, dmax_pair(chosen)[0] / 10, digest, dmax_pair(points)[0] / 10


def scatter_packet(spec, text, fmt, question, value, decimals, tol, unit, options, key, audit, rejected, goal, rank, checks,
                   whole, dm, digest):
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name=spec['asset'].rsplit('/', 1)[1], format=fmt, unit='angstrom', text=text)],
        numeric=dict(value=kit.display(value, decimals), unit=unit, decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
        checks=checks,
        scales=dict(input_nm=whole, reasoning_nm=dm, reasoning_definition='所选点集的最大间距（整个颗粒；探测长度 2π/q 同量级）'),
        input_hashes={spec['asset']: digest})


def build_debye(spec, root, seed):
    text, fmt, pts, which, radius, dm, digest, whole = scatter_setup(spec, root)
    q = spec['q_per_nm']
    value = debye(pts, q)
    if abs(value - debye_check(pts, q)) > 1e-9:
        raise ValueError('Debye implementations disagree')
    if q * radius <= 1.3:
        raise ValueError('Use guinier_intensity inside the Guinier range')
    n = len(pts)
    cands = [dict(rule='guinier_outside_range', value=math.exp(-(q * radius) ** 2 / 3), plausibility=3,
                  reason='在 qRg = %.2f > 1.3 处仍用 Guinier 近似。' % (q * radius)),
             dict(rule='uniform_sphere_same_rg', value=sphere(q, radius * math.sqrt(5 / 3)), plausibility=3,
                  reason='把颗粒当作 Rg 相同的均匀实心球（忽略实际形状）。'),
             dict(rule='single_orientation_x', value=single_orientation(pts, q), plausibility=2,
                  reason='只沿 x 轴取一个 q 方向，没有做取向平均。'),
             dict(rule='without_self_terms', value=(value * n * n - n) / (n * (n - 1)), plausibility=2,
                  reason='求和时漏掉 i = j 的自项，并按 N(N−1) 归一。'),
             dict(rule='amplitude_not_intensity', value=math.sqrt(value) if value > 0 else None, plausibility=2,
                  reason='报告了平方根（振幅比）而非强度比。'),
             dict(rule='s_convention', value=debye(pts, 2 * math.pi * q), plausibility=1,
                  reason='把 q = 4π sinθ/λ 当作 s = 2 sinθ/λ，在 2πq 处计算。'),
             dict(rule='q_divided_by_ten', value=debye(pts, q / 10), plausibility=1, reason='q 换算单位时多除以 10。'),
             dict(rule='sphere_radius_equals_rg', value=sphere(q, radius), plausibility=2,
                  reason='把回转半径直接当作均匀球的半径（应为 √(5/3)·Rg），强度偏大。'),
             dict(rule='guinier_single_axis_spread', value=math.exp(-(q * axis_spread(pts)) ** 2 / 3), plausibility=2,
                  reason='用 Guinier 近似，且把单一坐标轴的均方根离散度当作 Rg。')]
    decimals, tol, sep = 3, '0.0005', '0.020'
    chosen, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=decimals, tolerance=tol, min_separation=sep, seed=seed,
                                                      context=spec['id'], lower=0, upper=1, target=spec.get('target_position'),
                                                      distractor_separation='0.010')
    options, audit = kit.label_numeric(value, chosen, decimals=decimals, unit='', seed=seed, context=spec['id'],
                                       correct_reason='Debye 公式对全部点对取向平均：I/I0 = [N + 2Σ sin(qr)/(qr)]/N²，N = %d；qRg = %.2f。'
                                       % (n, q * radius))
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=sep, unit='',
                               distractor_separation='0.010')
    question = ('%s What is the orientation-averaged normalized scattering intensity I(q)/I(0) of the selected points at '
                'q = %.3f nm⁻¹ (q = 4π sinθ/λ)? Compute it exactly from all point pairs; q·Rg is above the Guinier range here.'
                % (subject(spec, which), q))
    checks = dict(points=n, q_per_nm=q, rg_nm=radius, q_rg=q * radius, dmax_nm=dm, probe_length_nm=2 * math.pi / q,
                  limits='等权点散射体（约简表示）；非实测 SAXS，不含溶剂层、形状因子与构象涨落。')
    return scatter_packet(spec, text, fmt, question, value, decimals, tol, '', options, key, audit, rejected, goal, rank, checks,
                          whole, dm, digest)


def build_q_design(spec, root, seed):
    """Inverse of build_debye: choose the measurement q at which I(q)/I(0) first falls to a target."""
    text, fmt, pts, which, radius, dm, digest, whole = scatter_setup(spec, root)
    t = spec['target']
    step, qmax = 0.02 / radius, 12 / radius
    value = first_crossing(lambda q: debye(pts, q), t, step, qmax)
    if value is None or abs(debye_check(pts, value) - t) > 1e-6:
        raise ValueError('No verified first crossing')
    decimals = 3 if value >= 0.1 else 4
    quantum = Decimal(1).scaleb(-decimals)
    sep = Decimal(str(0.05 * value)).quantize(quantum)
    tol = str(quantum / 2)
    root_of = lambda f: first_crossing(f, t, step, qmax)
    cands = [dict(rule='guinier_root', value=math.sqrt(3 * math.log(1 / t)) / radius, plausibility=3,
                  reason='用 Guinier 近似 exp(−q²Rg²/3) = 目标值反解 q（超出 Guinier 范围时不准）。'),
             dict(rule='uniform_sphere_root', value=root_of(lambda q: sphere(q, radius * math.sqrt(5 / 3))), plausibility=3,
                  reason='把颗粒当作 Rg 相同的均匀实心球求交点。'),
             dict(rule='single_orientation_root', value=root_of(lambda q: single_orientation(pts, q)), plausibility=2,
                  reason='只沿 x 轴一个方向计算强度，没有取向平均。'),
             dict(rule='target_as_amplitude', value=root_of(lambda q: math.sqrt(max(debye(pts, q), 0))), plausibility=2,
                  reason='把目标值当作振幅比（强度的平方根）求交点。'),
             dict(rule='reported_as_s', value=value / (2 * math.pi), plausibility=2,
                  reason='求对了交点，却以 s = 2 sinθ/λ（= q/2π）报告。'),
             dict(rule='dmax_sphere_root', value=root_of(lambda q: sphere(q, dm / 2)), plausibility=2,
                  reason='把颗粒当作直径等于最大尺寸的实心球。'),
             dict(rule='reported_per_angstrom', value=value / 10, plausibility=1, reason='以 Å⁻¹ 为单位的数值当作 nm⁻¹ 报告。'),
             dict(rule='sphere_radius_equals_rg_root', value=root_of(lambda q: sphere(q, radius)), plausibility=2,
                  reason='把回转半径直接当作均匀球的半径求交点（球偏小，q 偏大）。'),
             dict(rule='guinier_single_axis_root', value=math.sqrt(3 * math.log(1 / t)) / axis_spread(pts), plausibility=2,
                  reason='用 Guinier 反解，且把单一坐标轴的均方根离散度当作 Rg。')]
    chosen, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=decimals, tolerance=tol, min_separation=str(sep), seed=seed,
                                                      context=spec['id'], lower=0, target=spec.get('target_position'),
                                                      distractor_separation=str(sep / 2))
    options, audit = kit.label_numeric(value, chosen, decimals=decimals, unit='nm^-1', seed=seed, context=spec['id'],
                                       correct_reason='Debye 公式（全部点对、取向平均）从 q = 0 起步进并二分，得首次降到 %.2f 的 q。' % t)
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=str(sep), unit='nm^-1',
                               distractor_separation=str(sep / 2))
    question = ('%s A small-angle scattering measurement is to be set at the q where the orientation-averaged normalized intensity '
                'I(q)/I(0) of the selected points first falls to %.2f. Starting from q = 0, at which q (in nm⁻¹, q = 4π sinθ/λ) '
                'does I(q)/I(0) first reach %.2f? Compute the intensity exactly from all point pairs.' % (subject(spec, which), t, t))
    checks = dict(points=len(pts), target=t, q_star=value, q_rg=value * radius, rg_nm=radius, dmax_nm=dm,
                  design_note='设计 = 推断的逆问题：选择测量条件 q 使可观测量达到目标。',
                  limits='等权点散射体（约简表示）；非实测 SAXS。')
    return scatter_packet(spec, text, fmt, question, value, decimals, tol, 'nm^-1', options, key, audit, rejected, goal, rank,
                          checks, whole, dm, digest)
