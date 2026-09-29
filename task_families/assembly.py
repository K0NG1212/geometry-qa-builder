"""Large biological assemblies (10-1000 nm): whole-particle size and capsid architecture.

Inputs are the reduced public assets built by tools/build_assembly_assets.py (one point per
residue, or per-chain centroids after the deposited icosahedral expansion). The reasoning
scale is the whole particle, so these questions genuinely sit in the 10-100 / 100-1000 nm
cells; local quantities such as neighbouring-subunit spacing (~5 nm) are deliberately not
used here because they would belong to the 1-10 nm cell.
"""
import json
import math
from decimal import Decimal, localcontext
import numpy as np
from . import kit

VERSION = '0.1.0'
ALLOWED_T = sorted({h * h + h * k + k * k for h in range(0, 8) for k in range(0, 8) if h + k > 0})


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


def build_capsid(spec, root, seed):
    """Caspar–Klug architecture from the copy number N of the shell protein: T = N / 60,
    capsomers = 10T + 2 (12 pentamers + 10(T-1) hexamers)."""
    text, fmt, labels, points, digest = load(root, spec)
    shell = select(labels, points, spec['component'])
    n = len(shell)
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
