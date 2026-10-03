"""Model-based inference families for biomolecules (legacy FRET / Guinier calculators).

fret_efficiency: point donor/acceptor at named atoms, stated Foerster radius R0;
    E = 1 / (1 + (r/R0)^6) with r the straight-line donor-acceptor distance.
guinier_intensity: identical point scatterers at every supplied atom; Guinier
    approximation I(q)/I(0) = exp(-q^2 Rg^2 / 3), only posed where q*Rg <= 1.3.
The physical models are standard; the question states the model's inputs (R0, q,
scatterer assumption) but not the formulas, so applying the right relation is the task.
"""
import math
from . import kit

VERSION = '0.2.0'


def read_chain(text, chains):
    """First model, ATOM records of the given chains, main alternate location, no hydrogens."""
    atoms, lines = [], []
    for line in text.splitlines():
        if line.startswith('ENDMDL'):
            break
        if not line.startswith('ATOM') or line[21] not in chains or line[16] not in ' A':
            continue
        element = (line[76:78].strip() or line[12:16].strip()[0]).capitalize()
        if element == 'H':
            continue
        atoms.append(dict(chain=line[21], residue=int(line[22:26]), resname=line[17:20].strip(), name=line[12:16].strip(), element=element,
                          xyz=tuple(float(line[c:c + 8]) for c in (30, 38, 46))))
        lines.append(line.rstrip())
    return atoms, lines


def pick(atoms, residue, name):
    hits = [a for a in atoms if a['residue'] == residue and a['name'] == name]
    if len(hits) != 1:
        raise ValueError('Atom %s of residue %d not found exactly once' % (name, residue))
    return hits[0]


def fret(r, r0, power=6):
    return 1 / (1 + (r / r0) ** power)


def build_fret(spec, root, seed):
    raw = (root / 'docs' / spec['asset']).read_bytes()
    atoms, lines = read_chain(raw.decode('utf-8'), spec['chain'])
    d, a = pick(atoms, *spec['donor']), pick(atoms, *spec['acceptor'])
    r = math.dist(d['xyz'], a['xyz']) / 10                     # nm
    lo, hi = sorted((spec['donor'][0], spec['acceptor'][0]))
    markers = [a2 for a2 in atoms if a2['name'] == spec['path_atom'] and lo <= a2['residue'] <= hi]
    markers.sort(key=lambda m: m['residue'])
    path = None
    if [m['residue'] for m in markers] == list(range(lo, hi + 1)):
        path = math.fsum(math.dist(p['xyz'], q['xyz']) for p, q in zip(markers, markers[1:])) / 10
    ca = [x for x in atoms if x['residue'] == spec['acceptor'][0] and x['name'] == spec['path_atom']]
    near = min(math.dist(x['xyz'], y['xyz']) for x in atoms if x['residue'] == d['residue']
               for y in atoms if y['residue'] == a['residue']) / 10
    decimals, tol, sep = 3, '0.0005', '0.030'

    def attempt(r0):
        e = fret(r, r0)
        cands = [dict(rule='path_length_distance', value=fret(path, r0) if path else None, plausibility=3,
                      reason='用沿链骨架标记原子（%s）的路径长度代替空间直线距离。' % spec['path_atom']),
                 dict(rule='complement', value=1 - e, plausibility=2, reason='报告了 1−E（供体保留的比例）。'),
                 dict(rule='inverse_square_law', value=fret(r, r0, 2), plausibility=1, reason='用 (r/R0)^2 代替六次方依赖。'),
                 dict(rule='r_equals_R0_default', value=0.5, plausibility=2, reason='未计算距离，默认 r≈R0，直接取 E=0.5。'),
                 dict(rule='angstrom_nanometre_mixup', value=fret(r * 10, r0), plausibility=1, reason='r 用 Å 而 R0 用 nm，单位不一致。')]
        if near < r:
            # Larger-efficiency misconception: without it every mechanism falls below E when E > 0.5 and the correct
            # option is always the largest (found by the enumeration capacity probe, runs/enum-v02).
            cands.append(dict(rule='closest_atom_pair', value=fret(near, r0), plausibility=2,
                              reason='用两残基间最近的重原子对距离（%.3f nm）代替指定标记原子的间距。' % near))
        if ca and spec['acceptor'][1] != spec['path_atom']:
            cands.append(dict(rule='wrong_acceptor_atom', value=fret(math.dist(d['xyz'], ca[0]['xyz']) / 10, r0), plausibility=2,
                              reason='受体位置取成该残基的 %s 而非指定原子。' % spec['path_atom']))
        chosen, rejected, goal, rank = kit.choose_numeric(e, cands, decimals=decimals, tolerance=tol, min_separation=sep, seed=seed,
                                                          context=spec['id'], lower=0, upper=1, target=spec.get('target_position'),
                                                          distractor_separation='0.010')
        return r0, e, chosen, rejected, goal, rank

    # R0 is a stated model parameter. A spec may fix it (R0_nm) or list admissible stated values (R0_choices); the
    # family then takes the first value, in seeded order, whose options reach the batch's target answer rank, since
    # some ranks are reachable only below or only above E = 0.5.
    if 'R0_nm' in spec:
        options_r0 = [spec['R0_nm']]
    else:
        options_r0 = sorted(spec['R0_choices'], key=lambda x: kit.digest(seed, spec['id'], 'R0', str(x)))
    best = None
    for value in options_r0:
        try:
            got = attempt(value)
        except ValueError:
            continue
        if best is None or abs(got[5] - got[4]) < abs(best[5] - best[4]):
            best = got
        if got[5] == got[4]:
            break
    if best is None:
        raise ValueError('Fewer than three separated misconception distractors')
    r0, e, chosen, rejected, goal, rank = best
    options, audit = kit.label_numeric(e, chosen, decimals=decimals, unit='', seed=seed, context=spec['id'],
                                       correct_reason='r = %.4f nm（直线距离），E = 1/(1+(r/R0)^6)。' % r)
    key = kit.validate_numeric(options, e, decimals=decimals, tolerance=tol, min_separation=sep, unit='',
                               distractor_separation='0.010')
    name = lambda x: "%s of %s%s%d" % (x['name'], 'nucleotide ' if len(x['resname']) <= 2 else '', x['resname'].title(), x['residue'])
    question = ('The excerpt contains the ATOM records of chain %s of PDB entry %s (%s), copied unchanged. Model a FRET donor as a '
                'point at atom %s and an acceptor as a point at atom %s. Assume a Förster radius R0 = %.2f nm (orientation and '
                'spectral factors already included). What transfer efficiency does the Förster model predict?') % (
        spec['chain'], spec['pdb'], spec['context'], name(d), name(a), r0)
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name='%s-chain%s.pdb' % (spec['pdb'], spec['chain']), format='pdb-excerpt', unit='angstrom',
                     text='\n'.join(lines) + '\nEND\n')],
        numeric=dict(value=kit.display(e, decimals), unit='', decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
        checks=dict(distance_nm=r, R0_nm=r0, path_length_nm=path, efficiency=e,
                    limits='点偶极近似，R0 为题设值；不代表真实染料位置、连接臂或取向分布。'),
        scales=dict(input_nm=kit.dmax([x['xyz'] for x in atoms]) / 10, reasoning_nm=r,
                    reasoning_definition='供体–受体直线距离'),
        input_hashes={spec['asset']: kit.sha256(raw)})


def rg(points):
    c = [math.fsum(p[k] for p in points) / len(points) for k in range(3)]
    return math.sqrt(math.fsum(math.dist(p, c) ** 2 for p in points) / len(points))


def build_guinier(spec, root, seed):
    raw = (root / 'docs' / spec['asset']).read_bytes()
    if spec['asset'].endswith('.xyz'):          # reduced large assembly: supplied points as they are
        text = raw.decode('utf-8')
        points = kit.parse_xyz(text, max_atoms=20000)[1]
    elif spec['asset'].endswith('.txt'):        # labelled point table (e.g. 7ARQ nucleotides): every row
        text = raw.decode('utf-8')
        points = [tuple(float(x) for x in line.split()[2:5]) for line in text.splitlines()[1:] if line.strip()]
    else:
        atoms, _ = read_chain(raw.decode('utf-8'), spec['chains'])
        text = kit.xyz_text([a['element'] for a in atoms], [a['xyz'] for a in atoms],
                            '%s chains %s, non-hydrogen ATOM records (main alternate location), angstrom' % (spec['pdb'], spec['chains']))
        points = kit.parse_xyz(text)[1]
    radius = rg(points) / 10                                    # nm
    q = spec['q_per_nm']
    if round(q, 2) != q:     # the question prints q with 2 decimals; a finer q would make question and key disagree
        raise ValueError('q must be stated exactly with 2 decimals')
    if q * radius > 1.3:
        raise ValueError('q*Rg above the Guinier validity limit')
    value = math.exp(-(q * radius) ** 2 / 3)
    centre = [math.fsum(p[k] for p in points) / len(points) for k in range(3)]
    axis_rms = max(math.sqrt(math.fsum((p[k] - centre[k]) ** 2 for p in points) / len(points)) for k in range(3)) / 10
    dm = kit.dmax(points) / 10
    cands = [dict(rule='missing_one_third', value=math.exp(-(q * radius) ** 2), plausibility=3, reason='指数中漏掉 1/3。'),
             dict(rule='half_dmax_as_rg', value=math.exp(-(q * dm / 2) ** 2 / 3), plausibility=2, reason='把最大尺寸的一半当作回转半径。'),
             dict(rule='first_order_expansion', value=1 - (q * radius) ** 2 / 3, plausibility=2, reason='只取一阶展开 1−q²Rg²/3。'),
             dict(rule='linear_in_q', value=math.exp(-q * radius / 3), plausibility=1, reason='指数写成 −qRg/3，丢失平方。'),
             dict(rule='angstrom_nanometre_mixup', value=math.exp(-(q * radius * 10) ** 2 / 3), plausibility=1,
                  reason='Rg 用 Å 而 q 用 nm⁻¹，单位不一致。'),
             dict(rule='amplitude_not_intensity', value=math.sqrt(value), plausibility=2,
                  reason='报告了散射振幅比（强度的平方根）而非强度比。'),
             dict(rule='q_unit_conversion', value=math.exp(-(q / 10 * radius) ** 2 / 3), plausibility=1,
                  reason='q 换算单位时多除以 10（nm⁻¹ 当作 Å⁻¹ 处理）。'),
             dict(rule='single_axis_spread_as_rg', value=math.exp(-(q * axis_rms) ** 2 / 3), plausibility=2,
                  reason='把单一坐标轴方向的均方根离散度当作回转半径（偏小），强度因而偏大。')]
    decimals, tol, sep = 3, '0.0005', '0.020'
    chosen, rejected, goal, rank = kit.choose_numeric(value, cands, decimals=decimals, tolerance=tol, min_separation=sep, seed=seed,
                                                      context=spec['id'], lower=0, upper=1, target=spec.get('target_position'),
                                                      distractor_separation='0.010')
    kit.require_rank(spec, goal, rank)
    options, audit = kit.label_numeric(value, chosen, decimals=decimals, unit='', seed=seed, context=spec['id'],
                                       correct_reason='等权 Rg = %.4f nm，qRg = %.3f ≤ 1.3，I/I0 = exp(−q²Rg²/3)。' % (radius, q * radius))
    key = kit.validate_numeric(options, value, decimals=decimals, tolerance=tol, min_separation=sep, unit='',
                               distractor_separation='0.010')
    subject = (('The %s lists %s of %s (PDB %s). Treat each supplied point as an identical point scatterer.' %
                ('XYZ file' if spec['asset'].endswith('.xyz') else 'table', spec['representation'], spec['context'], spec['pdb']))
               if spec['asset'].endswith(('.xyz', '.txt')) else
               ('The XYZ file lists every non-hydrogen atom of %s (PDB %s, chains %s). Treat each supplied atom as an identical '
                'point scatterer.' % (spec['context'], spec['pdb'], spec['chains'])))
    question = ('%s In the Guinier approximation (which applies at this q), what is the normalized small-angle '
                'scattering intensity I(q)/I(0) at q = %.2f nm⁻¹?') % (subject, q)
    return dict(
        question=question, scope=spec['scope'],
        inputs=[dict(name=spec['asset'].rsplit('/', 1)[1] if spec['asset'].endswith(('.xyz', '.txt')) else '%s-heavy-atoms.xyz' % spec['pdb'],
                     format='centroid-table' if spec['asset'].endswith('.txt') else 'xyz', unit='angstrom', text=text)],
        numeric=dict(value=kit.display(value, decimals), unit='', decimals=decimals, tolerance=tol),
        options=options, correct_label=key, option_audit=audit, excluded_candidates=rejected, rank=dict(target=goal, achieved=rank),
        checks=dict(rg_nm=radius, q_per_nm=q, q_rg=q * radius, dmax_nm=dm, atoms=len(points),
                    limits='等权点散射体模型；非实测 SAXS，不含溶剂层与原子形状因子。'),
        scales=dict(input_nm=dm, reasoning_nm=dm, reasoning_definition='整个分子：最大原子间距'),
        input_hashes={spec['asset']: kit.sha256(raw)})
