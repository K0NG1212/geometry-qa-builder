"""Independent geometry for crystal cells of any system (checker side; imports no generation code).

Different methods from the generator (task_families/cell.py):
  - geometry from the metric tensor G (distance^2 = df' G df) and its numerical inverse for d-spacings,
    instead of lattice and reciprocal vectors;
  - its own CIF expansion (character scanner for symmetry operations), used to confirm that the student
    table is exactly the symmetry-expanded source: a reader bug in the generator cannot hide behind a
    checker that only trusts the table.
"""
import math
import re
from fractions import Fraction

import numpy as np

from .common import need, find

HEADER = re.compile(r'cell a = ([\d.]+) b = ([\d.]+) c = ([\d.]+) angstrom, alpha = ([\d.]+) beta = ([\d.]+) gamma = ([\d.]+) degree')
MATCH_TOL = 2e-4      # fractional: table vs own CIF expansion (the generator snaps 0.3333 to 1/3)


def parse_table(text):
    """(params or None, rows) from a fractional-cell table; params is None for the cubic header."""
    lines = text.splitlines()
    rows = [(r[0], [float(x) for x in r[1:]]) for r in (l.split() for l in lines[1:] if l.strip())]
    m = HEADER.search(lines[0])
    if not m:
        return None, rows
    return dict(zip(('a', 'b', 'c', 'alpha', 'beta', 'gamma'), (float(x) for x in m.groups()))), rows


def metric(p):
    ca, cb, cg = (math.cos(math.radians(p[k])) for k in ('alpha', 'beta', 'gamma'))
    a, b, c = p['a'], p['b'], p['c']
    return np.array([[a * a, a * b * cg, a * c * cb], [a * b * cg, b * b, b * c * ca], [a * c * cb, b * c * ca, c * c]])


def distance(G, f, g):
    v = np.array(g, dtype=float) - np.array(f, dtype=float)
    return math.sqrt(float(v @ G @ v))


def d_spacing(Ginv, hkl):
    h = np.array(hkl, dtype=float)
    return 1 / math.sqrt(float(h @ Ginv @ h))


def _value(token):
    return float(token.split('(')[0])


def _symop(text):
    """Character scanner: returns three (coefficients over x, y, z; translation) with fractions."""
    out = []
    for part in text.replace(' ', '').lower().split(','):
        coeff, shift, sign, number = [Fraction(0)] * 3, Fraction(0), 1, ''
        for ch in part + '+':
            if ch in 'xyz':
                coeff['xyz'.index(ch)] += sign * (Fraction(number) if number else 1)
                number, sign = '', 1
            elif ch in '+-':
                if number:
                    shift += sign * Fraction(number)
                number, sign = '', (1 if ch == '+' else -1)
            elif ch != '*':
                number += ch
        out.append((coeff, shift))
    need(len(out) == 3, 'Bad symmetry operation: ' + text)
    return out


def cif_cell(path):
    """Cell parameters and the symmetry-expanded atoms of a CIF, read with this module's own parser."""
    text = path.read_text(encoding='utf-8')
    params = {k: _value(find(r'_cell_(?:length|angle)_%s\s+(\S+)' % k, text, 'CIF lacks ' + k).group(1))
              for k in ('a', 'b', 'c', 'alpha', 'beta', 'gamma')}
    ops, sites = [], []
    tags, state = [], None                        # state: None (outside a loop), 'tags', 'rows'
    for raw in text.splitlines():
        line = raw.strip()
        if line == 'loop_':
            tags, state = [], 'tags'
            continue
        if line.startswith('_'):
            if state == 'tags':
                tags.append(line)
            else:
                state = None                      # a plain data item after the rows ends the loop
            continue
        if state is None or not line or line.startswith('#'):
            continue
        state = 'rows'
        values = re.findall(r"'[^']*'|\"[^\"]*\"|\S+", line)
        if len(values) != len(tags):
            continue
        row = dict(zip(tags, (v.strip('\'"') for v in values)))
        op = row.get('_symmetry_equiv_pos_as_xyz') or row.get('_space_group_symop_operation_xyz')
        if op:
            ops.append(_symop(op))
        if '_atom_site_fract_x' in row:
            element = re.match(r'[A-Z][a-z]?', row.get('_atom_site_type_symbol') or row['_atom_site_label']).group(0)
            sites.append((element, [_value(row['_atom_site_fract_' + k]) for k in 'xyz']))
    need(ops and sites, 'CIF symmetry operations or sites not found')
    atoms = []
    for element, f in sites:
        for op in ops:
            g = [(float(sum(c * x for c, x in zip(coeff, f)) + shift)) % 1.0 for coeff, shift in op]
            if not any(e == element and all(min(abs(x - y), 1 - abs(x - y)) < MATCH_TOL for x, y in zip(g, h)) for e, h in atoms):
                atoms.append((element, g))
    return params, atoms


def same_cell(params, rows, path):
    """The student table must be exactly the symmetry-expanded CIF (parameters and every atom)."""
    src_params, src_atoms = cif_cell(path)
    need(all(abs(params[k] - src_params[k]) < 1e-4 for k in params), 'Cell parameters differ from the CIF')
    need(len(rows) == len(src_atoms), 'Table has %d atoms, the expanded CIF %d' % (len(rows), len(src_atoms)))
    for e, f in rows:
        need(any(e == s and all(min(abs(x - y) % 1, 1 - abs(x - y) % 1) < MATCH_TOL for x, y in zip(f, g)) for s, g in src_atoms),
             'Table atom %s %s not in the expanded CIF' % (e, f))
    return len(src_atoms)
