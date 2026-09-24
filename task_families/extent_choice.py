"""Version 0.2 four-choice construction for the two existing size templates.

Same numeric answers as template_engine (reused, not re-derived). Distractors now
come from error mechanisms on both sides of the correct value (e.g. heavy-atom only
and axis span below Dmax; bounding-box diagonal and 2x max radius above), and the
correct value's numeric rank is balanced by seed so that "always pick the largest
(or smallest)" no longer answers the batch. Legacy choice_engine v0.1 runs are kept.
"""
import itertools
import math
from pathlib import Path
from . import kit
import template_engine as numeric

VERSION = '0.2.0'
MASS = {'H': 1.008, 'C': 12.011, 'N': 14.007, 'O': 15.999, 'S': 32.06, 'Cl': 35.45, 'Zn': 65.38,
        'P': 30.974, 'F': 18.998, 'Si': 28.085, 'Na': 22.990, 'Mg': 24.305}


def _rg(points, weights=None):
    w = weights or [1.0] * len(points)
    total = math.fsum(w)
    c = [math.fsum(wi * p[k] for wi, p in zip(w, points)) / total for k in range(3)]
    return math.sqrt(math.fsum(wi * math.dist(p, c) ** 2 for wi, p in zip(w, points)) / total)


VDW = {'H': 1.20, 'C': 1.70, 'N': 1.55, 'O': 1.52, 'S': 1.80, 'Cl': 1.75, 'Zn': 1.39, 'P': 1.80, 'F': 1.47,
       'Si': 2.10, 'Na': 2.27, 'Mg': 1.73}   # Bondi radii, Zn/Si/Na/Mg from the same compilation


def _extent_with_vdw(elements, points):
    best = max(((math.dist(points[i], points[j]), i, j) for i, j in itertools.combinations(range(len(points)), 2)))
    return best[0] + VDW[elements[best[1]]] + VDW[elements[best[2]]]


def candidates(elements, points, template):
    heavy = [p for e, p in zip(elements, points) if e != 'H']
    center = [math.fsum(p[k] for p in points) / len(points) for k in range(3)]
    radii = [math.dist(p, center) for p in points]
    pairs = [math.dist(a, b) for a, b in itertools.combinations(points, 2)]
    spans = [max(p[k] for p in points) - min(p[k] for p in points) for k in range(3)]
    rg = _rg(points)
    common = [dict(rule='mean_pair_distance', value=math.fsum(pairs) / len(pairs), plausibility=1,
                   reason='把全部点对距离的算术平均当作目标量。'),
              dict(rule='rms_pair_distance', value=math.sqrt(math.fsum(d * d for d in pairs) / len(pairs)), plausibility=1,
                   reason='用点对距离的均方根替代题目定义。')]
    if template == 'global_extent':
        return common + [
            dict(rule='radius_as_extent', value=rg, plausibility=1, reason='把等权回转半径误当最大点对间距。'),
            dict(rule='centroid_diameter', value=2 * max(radii), plausibility=2,
                 reason='用两倍最大中心距代替最大点对间距（前者 ≥ 后者，一般不相等）。'),
            dict(rule='first_last_rows', value=math.dist(points[0], points[-1]), plausibility=1,
                 reason='只算 XYZ 首末两行；行序不表示链端。'),
            dict(rule='heavy_atoms_only', value=numeric.calculate(heavy, 'global_extent') if len(heavy) > 1 else None,
                 plausibility=3, reason='忽略氢原子，只在重原子中找最大间距；题目要求全部点。'),
            dict(rule='bounding_box_diagonal', value=math.sqrt(math.fsum(s * s for s in spans)), plausibility=3,
                 reason='用坐标轴对齐包围盒对角线代替实际最大点对间距（前者 ≥ 后者）。'),
            dict(rule='largest_axis_span', value=max(spans), plausibility=2,
                 reason='只取单一坐标轴上的最大跨度，忽略斜向点对。'),
            dict(rule='two_largest_radii', value=sum(sorted(radii)[-2:]), plausibility=2,
                 reason='把两个最大中心距相加，默认最远两点位于质心两侧（该和 ≥ 实际最大间距）。'),
            dict(rule='with_vdw_radii', value=_extent_with_vdw(elements, points), plausibility=2,
                 reason='给最远点对两端再加范德华半径，报告“分子外形尺寸”而非点集最大间距。'),
        ]
    if template == 'equal_weight_rg':
        n = len(points)
        return common + [
            dict(rule='mean_radius', value=math.fsum(radii) / n, plausibility=2, reason='用中心距算术平均替代均方根。'),
            dict(rule='maximum_radius', value=max(radii), plausibility=1, reason='用最大中心距替代均方根。'),
            dict(rule='diameter_for_radius', value=2 * rg, plausibility=1, reason='把回转半径乘二，输出直径式量。'),
            dict(rule='mass_weighted', value=_rg(points, [MASS[e] for e in elements]), plausibility=3,
                 reason='使用原子质量加权；题目明确要求所有点等权。'),
            dict(rule='heavy_atoms_only', value=_rg(heavy) if len(heavy) > 1 else None, plausibility=3,
                 reason='只统计重原子，忽略氢。'),
            dict(rule='n_minus_one', value=math.sqrt(math.fsum(r * r for r in radii) / (n - 1)), plausibility=2,
                 reason='用 N−1 作分母（样本方差习惯），不是题目定义。'),
        ]
    raise ValueError('Unsupported template')


def build(spec, root, seed):
    path = root / 'docs' / spec['asset']
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    elements, points = kit.parse_xyz(text)
    template = spec['template']
    exact = numeric.verify_decimal(text, template)
    computed = numeric.calculate(points, template)
    if not math.isclose(computed, float(exact), abs_tol=1e-9, rel_tol=1e-12):
        raise ValueError('Numeric crosscheck failed')
    decimals, tol, sep = 4, '0.00005', '0.0500'
    chosen, rejected, goal, rank = kit.choose_numeric(exact, candidates(elements, points, template), decimals=decimals,
                                                      tolerance=tol, min_separation=sep, seed=seed,
                                                      context=spec['id'], lower=0, target=spec.get('target_position'))
    options, audit = kit.label_numeric(exact, chosen, decimals=decimals, unit='angstrom', seed=seed, context=spec['id'],
                                       correct_reason='template_engine 定义计算，并以十进制实现复核。')
    key = kit.validate_numeric(options, exact, decimals=decimals, tolerance=tol, min_separation=sep, unit='angstrom')
    registry = {t['id']: t for t in __import__('json').loads((root / 'templates/registry.json').read_text(encoding='utf-8'))['templates']}
    question = registry[template]['question'].replace(
        'Return only one value rounded to four decimal places and unit angstrom.', '').strip()
    return dict(
        question=question + ' Choose the correct value (angstrom, four decimals).',
        scope=spec['scope'],
        inputs=[dict(name=path.name, format='xyz', unit='angstrom', text=text)],
        numeric=dict(value=kit.display(exact, decimals), unit='angstrom', decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected,
        rank=dict(target=goal, achieved=rank),
        checks=dict(float_value=computed, decimal_crosscheck=str(exact), legacy_reference=spec.get('legacy_numeric_reference'),
                    legacy_agreement=abs(float(kit.display(exact, 4)) - spec['legacy_numeric_reference']) <= 0.0001
                    if spec.get('legacy_numeric_reference') is not None else None),
        scales=dict(input_nm=kit.dmax(points) / 10,
                    reasoning_nm=(computed if template == 'global_extent' else kit.dmax(points)) / 10,
                    reasoning_definition='全局点集：最大点对间距'),
        input_hashes={spec['asset']: kit.sha256(raw)})
