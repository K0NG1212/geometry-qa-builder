"""Periodic-crystal families migrated from the legacy materials calculators.

coordination_shell (perception): nearest shell of a named partner species around a named
    centre in the infinite crystal (periodic images included).
first_diffraction_peak (inference): lowest-angle reflection with non-zero kinematic
    intensity and its Bragg angle; needs the atomic positions (extinctions), not only a.
Both read the same fractional-coordinate table the student receives (see extinction.py).
"""
import itertools
import math
from . import kit
import sys
from .extinction import cell_from_xyz, table, parse_table, factor, rule_absent

VERSION = '0.1.0'
SHELL_TOL = 1e-3       # angstrom: distances closer than this belong to one shell


def load_cell(spec, root):
    raw = (root / 'docs' / spec['asset']).read_bytes()
    if spec['source_kind'] == 'cif':
        sys.path.insert(0, str(root / 'tools'))
        import recompute_materials_batch2 as legacy      # general cubic reader (e.g. 2-atom CsCl), reused unchanged
        crystal = legacy.read_cubic_cif(root / 'docs' / spec['asset'])
        a, rows = crystal['a_A'], [(r['element'], r['fractional']) for r in crystal['rows']]
    else:
        a, rows = cell_from_xyz(root, spec['asset'], spec['a'])
    text = table(a, rows, spec['name'])
    return a, parse_table(text), text, kit.sha256(raw)


def cart(a, f):
    return [a * x for x in f]


def matches(rule, rows, a, index):
    """rule: {element} or {element, bonded_to, count, cutoff} (e.g. the mu4-O of a Zn4O node)."""
    element, frac = rows[index]
    if element != rule['element']:
        return False
    if 'bonded_to' not in rule:
        return True
    near = sum(1 for e, f in rows for t in itertools.product((-1, 0, 1), repeat=3)
               if e == rule['bonded_to'] and 0 < math.dist(cart(a, frac), cart(a, [x + s for x, s in zip(f, t)])) <= rule['cutoff'])
    return near == rule['count']


def shells(a, rows, centre, partners, images=True):
    c = cart(a, rows[centre][1])
    found = []
    for j in partners:
        for t in (itertools.product((-1, 0, 1), repeat=3) if images else [(0, 0, 0)]):
            p = cart(a, [x + s for x, s in zip(rows[j][1], t)])
            d = math.dist(c, p)
            if d > 1e-6:
                found.append((d, p))
    found.sort()
    groups = []
    for d, p in found:
        if groups and d - groups[-1][0] <= SHELL_TOL:
            groups[-1][1].append(p)
        else:
            groups.append((d, [p]))
    return c, groups


def shell_option(n, d):
    return '%d at %s Å' % (n, kit.display(d, 3))


def build_coordination(spec, root, seed):
    a, rows, text, digest = load_cell(spec, root)
    centres = [i for i in range(len(rows)) if matches(spec['centre'], rows, a, i)]
    partners = [i for i in range(len(rows)) if matches(spec['partner'], rows, a, i)]
    if not centres or not partners:
        raise ValueError('Centre or partner rule matches nothing')
    centre = centres[0]
    c, groups = shells(a, rows, centre, partners)
    (d1, first), (d2, second) = groups[0], groups[1]
    inside = [g for g in shells(a, rows, centre, partners, images=False)[1] if abs(g[0] - d1) <= SHELL_TOL]
    n_in = len(inside[0][1]) if inside else 0
    candidates = [('second_shell', len(second), d2, 2, '报告了第二壳层（更远的一组）而非最近壳层。'),
                  ('no_periodic_images', n_in, d1, 3, '只数表中这一个晶胞内的原子，漏掉周期映像。'),
                  ('mixed_shells', len(second), d1, 1, '距离取最近壳层，个数却取第二壳层。'),
                  ('merged_first_two_shells', len(first) + len(second), d1, 1, '把前两个壳层合并计数。')]
    if spec['partner']['element'] != spec['centre']['element'] or 'bonded_to' in spec['partner']:
        same = [i for i in range(len(rows)) if rows[i][0] == rows[centre][0]]
        g = shells(a, rows, centre, same)[1]
        if g:
            candidates.append(('same_species_shell', len(g[0][1]), g[0][0], 2, '数成与中心同种元素的最近壳层。'))
    right = shell_option(len(first), d1)
    pool, rejected = [], []
    for rule, n, d, plaus, reason in candidates:
        text_opt = shell_option(n, d)
        if n <= 0 or text_opt == right or text_opt in [p[1] for p in pool]:
            rejected.append(dict(rule=rule, value=text_opt, reason='无效或与其他选项重复'))
        else:
            pool.append((rule, text_opt, reason, plaus))
    if len(pool) < 3:
        raise ValueError('Fewer than three distinct distractors')
    pool.sort(key=lambda p: (-p[3], kit.digest(seed, spec['id'], p[0])))
    chosen = pool[:3]
    rejected += [dict(rule=p[0], value=p[1], reason='有效但未选（可信度排序）') for p in pool[3:]]
    order = kit.place(('correct', right, '含周期映像的最近壳层：%d 个，距离 %.4f Å。' % (len(first), d1), 3),
                      chosen, spec.get('target_position'), seed, spec['id'], key=lambda p: p[0])
    options = [dict(label=l, value=p[1]) for l, p in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [p[0] == 'correct' for p in order])
    audit = [dict(label=l, value=p[1], rule=p[0], reason=p[2], is_correct=p[0] == 'correct') for l, p in zip(kit.LABELS, order)]
    shell_pts = [c] + first
    fx = rows[centre][1]
    question = ('The table lists every atom of one conventional cubic cell of %s. Treat the crystal as infinite and periodic. '
                'Around the %s at fractional (%.4f, %.4f, %.4f), how many %s form the nearest shell, and at what distance? '
                'Distances are rounded to 0.001 Å.') % (spec['name'], spec['centre_text'], fx[0], fx[1], fx[2], spec['partner_text'])
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name=spec['id'] + '-cell.txt', format='fractional-cell-table', unit='fractional; a in angstrom', text=text)],
        numeric=None, options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=None,
        checks=dict(centre_row=centre + 1, shells=[dict(distance_A=round(d, 6), count=len(p)) for d, p in groups[:3]],
                    in_cell_count=n_in, shell_tolerance_A=SHELL_TOL, a_A=a,
                    limits='理想晶胞坐标；壳层按 0.001 Å 容差归组；不涉及热振动或无序。'),
        scales=dict(input_nm=a / 10, reasoning_nm=kit.dmax(shell_pts) / 10,
                    reasoning_definition='中心原子与最近壳层全部原子的最大间距'),
        input_hashes={spec['asset']: digest})


def two_theta(d, wavelength):
    s = wavelength / (2 * d)
    return math.degrees(2 * math.asin(s)) if s <= 1 else None


def build_first_peak(spec, root, seed):
    a, rows, text, digest = load_cell(spec, root)
    weights, lam = spec['weights'], spec['wavelength_A']
    f000 = sum(weights[e] for e, _ in rows)
    refl = []
    for hkl in itertools.product(range(5), repeat=3):
        if hkl == (0, 0, 0) or not hkl[0] >= hkl[1] >= hkl[2]:
            continue
        d = a / math.sqrt(sum(x * x for x in hkl))
        tt = two_theta(d, lam)
        if tt is not None:
            refl.append(dict(hkl=hkl, d=d, tt=tt, rel=abs(factor(rows, hkl, weights)) / f000))
    refl.sort(key=lambda r: (r['tt'], r['hkl']))
    allowed = [r for r in refl if r['rel'] > 1e-6]
    first, second = allowed[0], allowed[1]
    if any(abs(r['tt'] - first['tt']) < 1e-9 and r is not first for r in allowed):
        raise ValueError('Two different reflections share the first angle')
    if 1e-6 < first['rel'] < 1e-3:
        raise ValueError('First reflection too weak to be unambiguous')
    show = lambda hkl: '(%d %d %d)' % hkl
    cands = [dict(rule='lowest_index_ignoring_extinction', value=refl[0]['tt'], plausibility=3,
                  reason='取最低指数反射 %s，未检查它是否消光。' % show(refl[0]['hkl']))] if refl[0] is not first else []
    for rule in ('P', 'I', 'F'):
        guess = next(r for r in refl if not rule_absent(rule, r['hkl']))
        if guess is not first:
            cands.append(dict(rule='assumed_lattice_rule:' + rule, value=guess['tt'], plausibility=3,
                              reason='按%s晶格规则判断，得到 %s；与实际坐标算出的结构因子不符。' % ({'P': '简单立方', 'I': '体心', 'F': '面心'}[rule], show(guess['hkl']))))
    cands += [dict(rule='theta_not_two_theta', value=first['tt'] / 2, plausibility=2, reason='报告了 θ 而非 2θ。'),
              dict(rule='second_allowed_peak', value=second['tt'], plausibility=2, reason='报告了第二个非零反射 %s。' % show(second['hkl'])),
              dict(rule='d_equals_a', value=two_theta(a, lam), plausibility=1, reason='把晶面间距当作晶格常数 a。')]
    decimals, tol, sep = 2, '0.005', '0.30'
    chosen, rejected, goal, rank = kit.choose_numeric(first['tt'], cands, decimals=decimals, tolerance=tol, min_separation=sep,
                                                      seed=seed, context=spec['id'], lower=0, upper=180,
                                                      target=spec.get('target_position'), distractor_separation='0.10')
    options, audit = kit.label_numeric(first['tt'], chosen, decimals=decimals, unit='degree', seed=seed, context=spec['id'],
                                       correct_reason='第一个 |F|≠0 的反射 %s，d = %.5f Å，2θ = 2 arcsin(λ/2d)。' % (show(first['hkl']), first['d']))
    key = kit.validate_numeric(options, first['tt'], decimals=decimals, tolerance=tol, min_separation=sep, unit='degree',
                               distractor_separation='0.10')
    wlist = ', '.join('%s = %s' % kv for kv in sorted(weights.items()))
    question = ('The table lists every atom of one conventional cubic cell of %s. Use the kinematic structure factor with atomic '
                'numbers as angle-independent weights (%s). For radiation of wavelength %.5f Å and first-order Bragg '
                'diffraction, at what angle 2θ does the lowest-angle reflection with non-zero intensity appear?') % (spec['name'], wlist, lam)
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name=spec['id'] + '-cell.txt', format='fractional-cell-table', unit='fractional; a in angstrom', text=text)],
        numeric=dict(value=kit.display(first['tt'], decimals), unit='degree', decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
        checks=dict(first_reflection=show(first['hkl']), d_A=first['d'], relative_amplitude=round(first['rel'], 6),
                    skipped_extinct=[show(r['hkl']) for r in refl if r['tt'] < first['tt']], wavelength_A=lam, a_A=a,
                    limits='运动学近似、零角度原子序数权重；不含原子散射因子角度依赖与仪器因素。'),
        scales=dict(input_nm=a / 10, reasoning_nm=first['d'] / 10, reasoning_definition='答案反射的晶面间距 d'),
        input_hashes={spec['asset']: digest})
