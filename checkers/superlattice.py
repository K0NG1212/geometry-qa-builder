"""Independent checkers for the nanoparticle-superlattice families (materials, 10-100 nm).
No generation code is imported. The lattice is recovered from the coordinates alone: a primitive
basis is chosen among the nearest-neighbour vectors (smallest cell volume), every particle must sit
on an integer combination of it, and Bragg positions come from the reciprocal lattice, not from
d-spacing formulas.
"""
import itertools
import math
import re
import numpy as np
from .common import need, find, read_xyz, verify_hashes, judge_numeric, rounded

TOL = 1e-4     # nm


def points(inp):
    return np.asarray([[float(c) for c in p] for _, p in read_xyz(inp['text'])])


def same_as_asset(packet, key):
    paths = verify_hashes(key)
    by_name = {p.name: p for p in paths.values()}
    for inp in packet['inputs']:
        need(inp['name'] in by_name and by_name[inp['name']].read_bytes() == inp['text'].encode('utf-8'),
             'Input differs from the published model crystallite: ' + inp['name'])


def analyse(pts):
    c = int(np.argmin(np.linalg.norm(pts - pts.mean(axis=0), axis=1)))
    rel = pts - pts[c]
    d = np.linalg.norm(rel, axis=1)
    order = np.argsort(d)[1:]
    nn = d[order[0]]
    first = [i for i in order if d[i] - nn <= TOL]
    vecs = rel[first]
    best = None
    for i, j, k in itertools.combinations(range(len(vecs)), 3):
        vol = abs(np.linalg.det(vecs[[i, j, k]]))
        if vol > 0.05 * nn ** 3 and (best is None or vol < best[0] - 1e-6 * nn ** 3):   # skip (numerically) coplanar triples
            best = (vol, vecs[[i, j, k]])
    need(best is not None, 'No primitive basis among nearest-neighbour vectors')
    vol, basis = best
    frac = np.linalg.solve(basis.T, rel.T).T
    need(np.abs(frac - np.round(frac)).max() < 1e-5, 'Particles do not lie on one Bravais lattice')
    recip = 2 * math.pi * np.linalg.inv(basis).T
    norms = sorted(float(np.linalg.norm(np.array(h) @ recip)) for h in itertools.product(range(-4, 5), repeat=3) if any(h))
    g = []                                   # distinct |G| values; symmetry-equivalent vectors agree to ~1e-8 relative
    for x in norms:
        if not g or x - g[-1] > 1e-6 * x:
            g.append(x)
    # Shells for the centre particle (count, mean distance)
    shells = []
    for i in order:
        if shells and d[i] - shells[-1][1] <= TOL:
            shells[-1][0].append(d[i])
        else:
            shells.append(([d[i]], d[i]))
    shells = [(len(s), sum(s) / len(s)) for s, _ in shells]
    fcc = shells[0][0] == 12 and shells[1][0] == 6 and abs(shells[1][1] / shells[0][1] - math.sqrt(2)) < 1e-5
    return dict(nn=float(nn), volume=float(vol), g=g, shells=shells, fcc=fcc)


def superlattice_shell(packet, key):
    same_as_asset(packet, key)
    need('nearest the centroid' in packet['question'], 'Centre particle not defined')
    lat = analyse(points(packet['inputs'][0]))
    n, dist = lat['shells'][0]
    want = '%d at %s nm' % (n, rounded(dist, 2))
    hits = [o['label'] for o in packet['options'] if o['value'] == want]
    need(len(hits) == 1, 'Recomputed shell %s matches %d options' % (want, len(hits)))
    need(key['correct_label'] == hits[0], 'Key label disagrees with recomputed shell')
    for o in packet['options']:
        m = re.fullmatch(r'(\d+) at ([\d.]+) nm', o['value'])
        need(m is not None, 'Option not in "N at D nm" form')
    return dict(label=hits[0], parameters=dict(count=n, distance_nm=dist), method='shells around the centroid particle')


def superlattice_quantity(packet, key):
    same_as_asset(packet, key)
    q = packet['question']
    lat = analyse(points(packet['inputs'][0]))
    if 'conventional cubic unit cell' in q:
        need(lat['fcc'], 'Lattice is not face-centred cubic; conventional cell undefined here')
        value = (4 * lat['volume']) ** (1 / 3)
    elif 'close-packed' in q:
        value = 2 * math.pi / lat['g'][0]                  # densest planes = shortest reciprocal vector
    elif 'first (lowest-q) Bragg reflection' in q:
        need('q = 4π sinθ/λ' in q and 'identical point scatterers' in q, 'q convention or scatterer model missing')
        value = lat['g'][0]
    elif 'second distinct Bragg reflection' in q:
        need('q = 4π sinθ/λ' in q and 'identical point scatterers' in q, 'q convention or scatterer model missing')
        value = lat['g'][1]
    else:
        core = float(find(r'core diameter of ([\d.]+) nm', q, 'Core diameter missing').group(1))
        need('percentage of the total volume is gold' in q, 'Unknown quantity')
        value = (4 / 3) * math.pi * (core / 2) ** 3 / lat['volume'] * 100      # one particle per primitive cell
    return dict(judge_numeric(packet, key, value), parameters=dict(nn_nm=lat['nn'], primitive_volume_nm3=lat['volume']),
                method='primitive basis from coordinates; reciprocal lattice')


def superlattice_design(packet, key):
    same_as_asset(packet, key)
    q = packet['question']
    props = {}
    for inp in packet['inputs']:
        lat = analyse(points(inp))
        props[inp['name']] = dict(nn=lat['nn'], q=lat['g'][0], volume=lat['volume'])
    m = re.search(r'closest to q = ([\d.]+) nm⁻¹', q)
    n = re.search(r'nearest-neighbour spacing of the particles is closest to ([\d.]+) nm', q)
    f = re.search(r'at least ([\d.]+) % of the volume is gold \(solid gold cores of diameter ([\d.]+) nm', q)
    need(sum(x is not None for x in (m, n, f)) == 1, 'Design goal not stated exactly once')
    if m or n:
        prop, t = ('q', float(m.group(1))) if m else ('nn', float(n.group(1)))
        ranked = sorted(props, key=lambda k: abs(props[k][prop] - t))
        need(abs(props[ranked[1]][prop] - t) > abs(props[ranked[0]][prop] - t) + 1e-6, 'Tie for closest candidate')
        winner = ranked[0]
    else:
        t, core = float(f.group(1)), float(f.group(2))
        gold = {k: (4 / 3) * math.pi * (core / 2) ** 3 / v['volume'] * 100 for k, v in props.items()}
        ok = [k for k in props if gold[k] >= t]
        need(ok, 'No candidate satisfies the constraint')
        winner = max(ok, key=lambda k: props[k]['nn'])
    hits = [o['label'] for o in packet['options'] if o['value'].endswith('(%s)' % winner)]
    need(len(hits) == 1, 'Winning file named by %d options' % len(hits))
    need(len({o['value'] for o in packet['options']}) == 4, 'Duplicate options')
    for o in packet['options']:
        name = re.search(r'\((\S+\.xyz)\)$', o['value'])
        need(name is not None and name.group(1) in props, 'Option does not name a supplied file')
    need(key['correct_label'] == hits[0], 'Key label disagrees with recomputed choice')
    return dict(label=hits[0], parameters={k: dict(v) for k, v in props.items()}, method='per-file lattice analysis; goal rule')


CHECKERS = {'superlattice_shell': superlattice_shell, 'superlattice_metric': superlattice_quantity,
            'superlattice_saxs': superlattice_quantity, 'superlattice_design': superlattice_design}
