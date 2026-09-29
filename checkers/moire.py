"""Independent checkers for the twisted-bilayer-graphene moire families (quantum, 10-100 nm).
No generation code is imported. AA maps: primitive vectors are chosen from the nearest-neighbour vectors
and every site must be an integer combination of them; the cell area is their cross product (no sqrt(3)/2
formula). Atomistic patch: each layer's orientation comes from a six-fold phase average of its lattice
vectors (second neighbours), and the lattice constant from their length.
"""
import cmath
import math
import re
import numpy as np
from .common import need, find, read_xyz, verify_hashes, judge_numeric

TOL = 1e-5


def same_as_asset(packet, key):
    by_name = {p.name: p for p in verify_hashes(key).values()}
    for inp in packet['inputs']:
        need(inp['name'] in by_name and by_name[inp['name']].read_bytes() == inp['text'].encode('utf-8'),
             'Input differs from the published model: ' + inp['name'])


def aa_sites(inp):
    lines = inp['text'].splitlines()
    rows = [l.split() for l in lines[2:] if l.strip()]
    need(lines[0].strip().isdigit() and int(lines[0]) == len(rows), 'Map count invalid')
    need(all(len(r) == 3 and r[0] == 'AA' for r in rows), 'Rows must be "AA x y"')
    return np.asarray([[float(r[1]), float(r[2])] for r in rows])


def moire_cell(pts):
    c = int(np.argmin(np.linalg.norm(pts - pts.mean(axis=0), axis=1)))
    rel = pts - pts[c]
    d = np.linalg.norm(rel, axis=1)
    order = np.argsort(d)[1:]
    lam = d[order[0]]
    near = [rel[i] for i in order if d[i] - lam <= TOL]
    need(len(near) == 6, 'Not a triangular moire lattice around the centre site')
    best = None
    for i in range(6):
        for j in range(i + 1, 6):
            cross = abs(near[i][0] * near[j][1] - near[i][1] * near[j][0])
            if cross > 0.1 * lam * lam and (best is None or cross < best[0] - 1e-9):
                best = (cross, np.array([near[i], near[j]]))
    area, basis = best
    frac = np.linalg.solve(basis.T, rel.T).T
    need(np.abs(frac - np.round(frac)).max() < 1e-5, 'Sites are not one Bravais lattice')
    return float(lam), float(area)


def orientation(layer):
    """Six-fold phase average of the lattice vectors (second neighbours, length a) of one layer."""
    c = layer[np.argmin(np.linalg.norm(layer[:, :2] - layer[:, :2].mean(axis=0), axis=1))]
    rel = layer[:, :2] - c[:2]
    d = np.linalg.norm(rel, axis=1)
    first = np.sort(d)[1]
    second = d[d > first * 1.2].min()
    vecs = rel[np.abs(d - second) < 1e-4]
    need(len(vecs) == 6, 'Layer lattice vectors not found')
    z = sum(cmath.exp(6j * math.atan2(v[1], v[0])) for v in vecs)
    return math.degrees(cmath.phase(z)) / 6, float(second)


def electrons(q):
    if 'completely fills one set of spin- and valley-degenerate' in q or 'complete filling of one set of spin- and valley-degenerate' in q:
        return 4
    need('half filling of one set of spin- and valley-degenerate' in q, 'Filling not stated')
    return 2


def moire_quantity(packet, key):
    same_as_asset(packet, key)
    q = packet['question']
    inp = packet['inputs'][0]
    if inp['format'] == 'xyz':
        need('unstrained and rigidly twisted' in q, 'Rigid-twist assumption not stated')
        atoms = np.asarray([[float(c) for c in p] for _, p in read_xyz(inp['text'])])
        layers = sorted({round(float(z), 3) for z in atoms[:, 2]})
        need(len(layers) == 2, 'Expected two layers')
        (p0, a0), (p1, a1) = (orientation(atoms[np.abs(atoms[:, 2] - z) < 0.01]) for z in layers)
        theta = abs((p1 - p0 + 30) % 60 - 30)
        a = (a0 + a1) / 20                                # angstrom -> nm
        value = a / (2 * math.sin(math.radians(theta) / 2))
        return dict(judge_numeric(packet, key, value), parameters=dict(twist_deg=theta, a_nm=a),
                    method='six-fold phase average per layer')
    lam, area = moire_cell(aa_sites(inp))
    if 'What is the moiré period' in q:
        value = lam
    elif 'area of one moiré unit cell' in q:
        value = area
    elif 'twist angle between the two layers' in q:
        a = float(find(r'lattice constant is ([\d.]+) nm', q, 'Lattice constant missing').group(1))
        value = math.degrees(2 * math.asin(a / (2 * lam)))
    else:
        value = electrons(q) / area * 100
    return dict(judge_numeric(packet, key, value), parameters=dict(period_nm=lam, cell_area_nm2=area),
                method='primitive moire cell from AA sites')


def moire_design(packet, key):
    same_as_asset(packet, key)
    q = packet['question']
    cells = {inp['name']: moire_cell(aa_sites(inp)) for inp in packet['inputs']}
    m = re.search(r'closest to ([\d.]+) × 10¹² cm⁻²', q)
    p = re.search(r'moiré period is closest to ([\d.]+) nm', q)
    need((m is None) != (p is None), 'Design goal not stated exactly once')
    if m:
        t, e = float(m.group(1)), electrons(q)
        prop = {k: e / area * 100 for k, (lam, area) in cells.items()}
    else:
        t = float(p.group(1))
        prop = {k: lam for k, (lam, area) in cells.items()}
    ranked = sorted(prop, key=lambda k: abs(prop[k] - t))
    need(abs(prop[ranked[1]] - t) > abs(prop[ranked[0]] - t) + 1e-6, 'Tie for closest candidate')
    hits = [o['label'] for o in packet['options'] if o['value'].endswith('(%s)' % ranked[0])]
    need(len(hits) == 1, 'Winner not named by exactly one option')
    for o in packet['options']:
        name = re.search(r'\((\S+)\)$', o['value'])
        need(name is not None and name.group(1) in cells, 'Option does not name a supplied file')
    need(key['correct_label'] == hits[0], 'Key label disagrees with recomputed choice')
    return dict(label=hits[0], parameters=prop, method='per-file primitive moire cell; goal rule')


CHECKERS = {'moire_geometry': moire_quantity, 'moire_inference': moire_quantity, 'moire_design': moire_design}
