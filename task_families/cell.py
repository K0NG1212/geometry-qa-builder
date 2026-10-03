"""Crystal cells of any crystal system for the periodic families (coordination shell, first peak, extinction).

The cubic path in crystal.py / extinction.py is kept unchanged so that existing instances stay byte-identical.
Specs with source_kind 'cif_general' use this module instead:
  read_cif    CIF reader that applies every symmetry operation of the file (no eval; fractions parsed by hand)
  GeneralCell lattice matrix (a along x, b in the xy plane), Cartesian coordinates, d-spacings from reciprocal vectors
  CubicCell   the old arithmetic (a * x and a / sqrt(h^2 + k^2 + l^2)) behind the same interface
The student table states all six cell parameters in its first line.
"""
import math
import re
from fractions import Fraction

POSITION_TOL = 1e-4          # fractional: symmetry images closer than this are one atom
SNAP_TOL = 1e-4              # fractional: 0.3333 / 0.6667 / 0.1667 written by CIF authors -> exact multiples of 1/12
# CIF tokens: a quote closes only when followed by whitespace, so O'Neill inside '...' stays one token.
QUOTES = ('\'', '"')
TOKEN = re.compile(r"'(?:[^']|'(?=\S))*'(?=\s|$)|\"(?:[^\"]|\"(?=\S))*\"(?=\s|$)|\S+")


def _number(token):
    """CIF number with an optional standard uncertainty, e.g. 3.2494(2)."""
    return float(re.sub(r'\(\d+\)$', '', token))


def _loops(text):
    """Every loop_ of the file as (tags, rows); quoted values are kept whole."""
    lines = [l for l in text.splitlines() if not l.lstrip().startswith('#')]
    out, i = [], 0
    while i < len(lines):
        if lines[i].strip() != 'loop_':
            i += 1
            continue
        i += 1
        tags = []
        while i < len(lines) and lines[i].strip().startswith('_'):
            tags.append(lines[i].strip())
            i += 1
        tokens = []
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('_', 'loop_', 'data_')):
            tokens += [t[1:-1] if t[0] in QUOTES and len(t) > 1 else t for t in TOKEN.findall(lines[i])]
            i += 1
        if tags and len(tokens) % len(tags) == 0:
            out.append((tags, [tokens[j:j + len(tags)] for j in range(0, len(tokens), len(tags))]))
    return out


def _operation(text):
    """'-x+y, 1/2+z, ...' -> three (coefficients, translation) with exact fractions."""
    parts = [p.strip().replace(' ', '') for p in text.split(',')]
    if len(parts) != 3:
        raise ValueError('Symmetry operation must have three components: %r' % text)
    out = []
    for part in parts:
        coeff, shift = [Fraction(0)] * 3, Fraction(0)
        for sign, term in re.findall(r'([+-]?)([^+-]+)', part):
            s = -1 if sign == '-' else 1
            var = term[-1].lower() if term[-1].lower() in 'xyz' else None
            if var:
                factor = term[:-1].rstrip('*')
                coeff['xyz'.index(var)] += s * (Fraction(factor) if factor else 1)
            else:
                shift += s * Fraction(term)
        out.append((coeff, shift))
    return out


def _element(symbol, label):
    m = re.match(r'([A-Z][a-z]?)', symbol or label)
    if not m:
        raise ValueError('No element in %r / %r' % (symbol, label))
    return m.group(1)


def snap(x):
    """Special positions are often written truncated (0.3333 for 1/3), which breaks the symmetry of |F| at the
    1e-3 level (e.g. ZnO (1 0 0) versus (1 -1 0)). Values within SNAP_TOL of a multiple of 1/12 are made exact."""
    k = round(x * 12)
    return k / 12 if abs(x - k / 12) < SNAP_TOL else x


def read_cif(path):
    """Cell parameters and every atom of the conventional cell (symmetry applied, duplicates merged)."""
    text = path.read_text(encoding='utf-8')
    params = {}
    for key in ('a', 'b', 'c'):
        params[key] = _number(re.search(r'^_cell_length_%s\s+(\S+)' % key, text, re.M).group(1))
    for key in ('alpha', 'beta', 'gamma'):
        params[key] = _number(re.search(r'^_cell_angle_%s\s+(\S+)' % key, text, re.M).group(1))
    ops, sites = None, None
    for tags, rows in _loops(text):
        op_tag = next((t for t in tags if t in ('_symmetry_equiv_pos_as_xyz', '_space_group_symop_operation_xyz')), None)
        if op_tag:
            ops = [_operation(r[tags.index(op_tag)]) for r in rows]
        if '_atom_site_fract_x' in tags:
            sites = []
            for r in rows:
                get = lambda t: r[tags.index(t)] if t in tags else None
                occupancy = get('_atom_site_occupancy')
                if occupancy not in (None, '.', '?') and abs(_number(occupancy) - 1) > 1e-6:
                    raise ValueError('Partial occupancy is not supported: %s' % get('_atom_site_label'))
                sites.append((_element(get('_atom_site_type_symbol'), get('_atom_site_label')),
                              [snap(_number(get('_atom_site_fract_%s' % k))) for k in 'xyz']))
    if not ops or not sites:
        raise ValueError('CIF lacks symmetry operations or atom sites')
    atoms = []
    for element, f in sites:
        for op in ops:
            g = [(float(sum(c * x for c, x in zip(coeff, f))) + float(shift)) % 1.0 for coeff, shift in op]
            g = [0.0 if x > 1 - POSITION_TOL / 10 else x for x in g]
            if not any(e == element and all(min(abs(x - y), 1 - abs(x - y)) < POSITION_TOL for x, y in zip(g, h)) for e, h in atoms):
                atoms.append((element, g))
    atoms.sort(key=lambda a: (a[0], a[1]))
    return params, atoms


class GeneralCell:
    kind = 'general'
    images = range(-2, 3)                    # periodic images searched for neighbour shells

    def __init__(self, a, b, c, alpha, beta, gamma):
        self.params = dict(a=a, b=b, c=c, alpha=alpha, beta=beta, gamma=gamma)
        ca, cb, cg = (math.cos(math.radians(x)) for x in (alpha, beta, gamma))
        sg = math.sin(math.radians(gamma))
        cy = (ca - cb * cg) / sg
        self.vectors = [(a, 0.0, 0.0), (b * cg, b * sg, 0.0), (c * cb, c * cy, c * math.sqrt(1 - cb * cb - cy * cy))]
        A, B, C = self.vectors
        volume = _dot(A, _cross(B, C))
        self.reciprocal = [tuple(x / volume for x in _cross(B, C)), tuple(x / volume for x in _cross(C, A)),
                           tuple(x / volume for x in _cross(A, B))]
        self.longest = max(a, b, c)

    def cart(self, f):
        return [sum(f[i] * self.vectors[i][k] for i in range(3)) for k in range(3)]

    def d(self, hkl):
        g = [sum(hkl[i] * self.reciprocal[i][k] for i in range(3)) for k in range(3)]
        return 1 / math.sqrt(_dot(g, g))

    def header(self, name, n):
        p = self.params
        return ('%s; cell a = %.5f b = %.5f c = %.5f angstrom, alpha = %.3f beta = %.3f gamma = %.3f degree; '
                '%d atoms; element x y z (fractional)') % (name, p['a'], p['b'], p['c'], p['alpha'], p['beta'], p['gamma'], n)

    def describe(self):
        return 'one conventional cell (cell parameters in the first line of the table)'


class CubicCell:
    kind = 'cubic'
    images = (-1, 0, 1)

    def __init__(self, a):
        self.a = a
        self.longest = a

    def cart(self, f):
        return [self.a * x for x in f]

    def d(self, hkl):
        return self.a / math.sqrt(sum(x * x for x in hkl))

    def describe(self):
        return 'one conventional cubic cell'


def is_cubic(params):
    """Metrically cubic cell: such CIFs use the cubic path (cubic table header and the centring-rule misconceptions)."""
    return (abs(params['a'] - params['b']) < 1e-6 and abs(params['a'] - params['c']) < 1e-6
            and all(abs(params[k] - 90) < 1e-6 for k in ('alpha', 'beta', 'gamma')))


def general_table(cell, rows, name):
    lines = [cell.header(name, len(rows))] + ['%s %.8f %.8f %.8f' % (e, *f) for e, f in rows]
    return '\n'.join(lines) + '\n'


def _dot(u, v):
    return sum(x * y for x, y in zip(u, v))


def _cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
