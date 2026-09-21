"""Recompute geometry for the two new cubic COD CIFs used in
materials-cell-v04-002 (MgO periclase 1000053, CsCl 9008789).
Standard library only. Generalized symmetry-expansion reader (not the
fixed 8-row reader used by tools/recompute_materials_batch.py); still
limited to fully-occupied cubic CIFs with an explicit
_space_group_symop/_symmetry_equiv_pos loop.
Usage: python tools/recompute_materials_batch2.py CIF_DIRECTORY --out metrics.json
(CIF_DIRECTORY must contain 1000053.cif and 9008789.cif, e.g. docs/assets/materials/)
"""
from pathlib import Path
from fractions import Fraction as F
import re, shlex, itertools, math, json, argparse

def expression(text, point):
    text = text.replace(' ', '')
    parts = re.findall(r'[+-]?[^+-]+', text)
    if ''.join(parts) != text:
        raise ValueError('Unsupported symmetry expression: ' + text)
    value = F(0)
    for term in parts:
        sign = -1 if term.startswith('-') else 1
        t = term.lstrip('+-')
        if t in 'xyz' and len(t) == 1:
            v = point['xyz'.index(t)]
        elif re.fullmatch(r'\d+(?:/\d+)?', t):
            v = F(t)
        else:
            raise ValueError('Unsupported symmetry term: ' + term)
        value += sign * v
    return value % 1

def strip_element(label):
    m = re.match(r'^([A-Z][a-z]?)', label)
    assert m, 'Could not parse element symbol from ' + label
    return m.group(1)

def read_cubic_cif(path):
    lines = path.read_text(encoding='utf8').splitlines()
    def scalar(tag):
        vals = [shlex.split(l)[1] for l in lines if l.startswith(tag + ' ')]
        assert len(vals) == 1
        raw = vals[0].split('(')[0]
        return F(raw)
    a, b, c = [scalar('_cell_length_' + v) for v in 'abc']
    assert a == b == c, 'Not cubic'
    for ang in ['alpha', 'beta', 'gamma']:
        assert scalar('_cell_angle_' + ang) == 90
    sym_tag = None
    for cand in ['_space_group_symop_operation_xyz', '_symmetry_equiv_pos_as_xyz']:
        if cand in lines:
            sym_tag = cand
            break
    assert sym_tag, 'No symmetry loop found'
    idx = lines.index(sym_tag) + 1
    ops = []
    while idx < len(lines) and not lines[idx].startswith(('loop_', '_')):
        if lines[idx].strip():
            ops.append(lines[idx].strip().strip("'\""))
        idx += 1
    header_idx = lines.index('_atom_site_label') + 1
    headers = ['_atom_site_label']
    idx = header_idx
    while idx < len(lines) and lines[idx].startswith('_'):
        headers.append(lines[idx].strip())
        idx += 1
    col = {h: i for i, h in enumerate(headers)}
    label_i = col['_atom_site_label']
    x_i, y_i, z_i = col['_atom_site_fract_x'], col['_atom_site_fract_y'], col['_atom_site_fract_z']
    sites = []
    while idx < len(lines) and not lines[idx].startswith(('loop_', '_')):
        if lines[idx].strip():
            t = shlex.split(lines[idx])
            assert len(t) == len(headers), (lines[idx], headers)
            label = t[label_i]
            elem = strip_element(label)
            frac = tuple(F(t[i].split('(')[0]) for i in (x_i, y_i, z_i))
            sites.append((elem, label, frac))
        idx += 1
    rows = []
    for elem, label, p in sites:
        xyz = sorted({tuple(expression(e, p) for e in op.split(',')) for op in ops})
        for f in xyz:
            rows.append({
                'element': elem,
                'source_label': label,
                'fractional': [float(v) for v in f],
                'fractional_exact': [str(v) for v in f],
                'xyz_A': [float(a * v) for v in f],
            })
    return dict(a_A=float(a), a_exact=str(a), rows=rows, symmetry_operation_count=len(ops),
                cell_diagonal_nm=math.sqrt(3) * float(a) / 10)

def neighbors_for_row0(crystal):
    """Coordination shell around the first row's atom (its own site, translation 0)."""
    a = crystal['a_A']
    rows = crystal['rows']
    origin = rows[0]
    pts = []
    for j, r in enumerate(rows):
        for t in itertools.product([-1, 0, 1], repeat=3):
            v = [a * (f + n - o) for f, n, o in zip(r['fractional'], t, origin['fractional'])]
            d = math.sqrt(sum(x * x for x in v))
            if d > 1e-8:
                pts.append(dict(row=j + 1, element=r['element'], translation=list(t),
                                 vector_A=v, distance_A=d))
    pts.sort(key=lambda p: p['distance_A'])
    first = [x for x in pts if abs(x['distance_A'] - pts[0]['distance_A']) < 1e-8]
    angles = []
    for u, v in itertools.combinations(first, 2):
        dot = sum(x * y for x, y in zip(u['vector_A'], v['vector_A']))
        angles.append(math.degrees(math.acos(max(-1, min(1, dot / u['distance_A'] / v['distance_A'])))))
    like = [x for x in pts if x['element'] == origin['element']]
    same = [x for x in like if abs(x['distance_A'] - like[0]['distance_A']) < 1e-8] if like else []
    return dict(center_element=origin['element'], distance_A=pts[0]['distance_A'], coordination=len(first),
                neighbors=first, angles_deg=sorted(set(round(x, 6) for x in angles)),
                same_species_distance_A=(like[0]['distance_A'] if like else None),
                same_species_count=len(same))

def structure_factor(crystal, hkl, weights):
    real = imag = 0.0
    for r in crystal['rows']:
        phase = 2 * math.pi * sum(h * x for h, x in zip(hkl, r['fractional']))
        w = weights[r['element']]
        real += w * math.cos(phase)
        imag += w * math.sin(phase)
    amp = math.hypot(real, imag)
    return dict(real=real, imaginary=imag, amplitude=amp, intensity=real * real + imag * imag)

def d_spacing_nm(a_A, hkl):
    h, k, l = hkl
    return (a_A / math.sqrt(h * h + k * k + l * l)) / 10

def two_theta_deg(d_nm, wavelength_nm=0.15406, n=1):
    return 2 * math.degrees(math.asin(n * wavelength_nm / (2 * d_nm)))

def calculate(directory):
    mgo = read_cubic_cif(directory / '1000053.cif')
    cscl = read_cubic_cif(directory / '9008789.cif')
    assert len(mgo['rows']) == 8, len(mgo['rows'])
    assert len(cscl['rows']) == 2, len(cscl['rows'])

    out = {'mgo': mgo, 'cscl': cscl}

    mgo['coordination_shell'] = neighbors_for_row0(mgo)
    if cscl['rows'][0]['element'] != 'Cs':
        cscl['rows'] = list(reversed(cscl['rows']))
    cscl['coordination_shell'] = neighbors_for_row0(cscl)

    for hkl in [(1, 1, 1), (2, 0, 0), (2, 2, 0)]:
        key = ''.join(map(str, hkl))
        d = d_spacing_nm(mgo['a_A'], hkl)
        mgo.setdefault('d_spacings_nm', {})[key] = d
        mgo.setdefault('two_theta_deg', {})[key] = two_theta_deg(d)

    for hkl in [(1, 0, 0), (1, 1, 0), (1, 1, 1)]:
        key = ''.join(map(str, hkl))
        d = d_spacing_nm(cscl['a_A'], hkl)
        cscl.setdefault('d_spacings_nm', {})[key] = d
        cscl.setdefault('two_theta_deg', {})[key] = two_theta_deg(d)

    mgo['factors'] = {
        ''.join(map(str, h)): structure_factor(mgo, h, {'Mg': 12, 'O': 8})
        for h in [(1, 1, 1), (2, 0, 0), (2, 2, 0)]
    }
    mgo['equal_factors'] = {
        ''.join(map(str, h)): structure_factor(mgo, h, {'Mg': 1, 'O': 1})
        for h in [(1, 1, 1), (2, 0, 0)]
    }

    cscl['factors_caseA'] = {
        ''.join(map(str, h)): structure_factor(cscl, h, {'Cs': 55, 'Cl': 17})
        for h in [(1, 0, 0), (1, 1, 0), (1, 1, 1)]
    }
    cscl['factors_caseB_equal'] = {
        ''.join(map(str, h)): structure_factor(cscl, h, {'Cs': 1, 'Cl': 1})
        for h in [(1, 0, 0), (1, 1, 0), (1, 1, 1)]
    }

    checks = {}
    mg_o_expected = mgo['a_A'] / 2
    checks['mgo_nearest_A_formula_a_over_2'] = mg_o_expected
    checks['mgo_nearest_A_symmetry_expansion'] = mgo['coordination_shell']['distance_A']
    assert abs(mg_o_expected - mgo['coordination_shell']['distance_A']) < 1e-9

    cscl_expected = cscl['a_A'] * math.sqrt(3) / 2
    checks['cscl_nearest_A_formula_a_sqrt3_over_2'] = cscl_expected
    checks['cscl_nearest_A_symmetry_expansion'] = cscl['coordination_shell']['distance_A']
    assert abs(cscl_expected - cscl['coordination_shell']['distance_A']) < 1e-9

    out['checks'] = checks
    return out

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('directory', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = calculate(a.directory)
    a.out.write_bytes((json.dumps(result, indent=2) + '\n').encode())
    printable = {k: {kk: vv for kk, vv in v.items() if kk != 'rows'} for k, v in result.items() if k != 'checks'}
    printable['checks'] = result['checks']
    print(json.dumps(printable, indent=2))
