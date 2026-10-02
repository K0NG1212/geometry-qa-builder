"""Independent checkers for the vortex-lattice (quantum) and cholesteric (chemistry) families, 100-1000 nm.
No generation code is imported. Vortex maps: the primitive cell is recovered from the coordinates (checkers.moire.moire_cell)
and density, field, flux and the first Bragg peak follow from the cell area. Director fields: the directors are projected on the
plane normal to the axis (first to last site), the angle is unwrapped modulo π and fitted linearly; the slope gives the pitch and
its sign (in a right-handed frame whose third axis points along the travel direction) gives the handedness.
"""
import math
import re
import numpy as np
from .common import need, find, verify_hashes, judge_numeric, rounded
from .moire import moire_cell


def same_as_asset(packet, key):
    by_name = {p.name: p for p in verify_hashes(key).values()}
    for inp in packet['inputs']:
        need(inp['name'] in by_name and by_name[inp['name']].read_bytes() == inp['text'].encode('utf-8'), 'Input differs: ' + inp['name'])


def conditions(q, phrase):
    need('Model conditions:' in q and phrase in q, 'Paper-parameter model conditions not stated')


# ------------------------------------------------------------------ vortex lattices
def vortex_cell(inp):
    lines = inp['text'].splitlines()
    rows = [l.split() for l in lines[2:] if l.strip()]
    need(lines[0].strip().isdigit() and int(lines[0]) == len(rows) and all(len(r) == 3 and r[0] == 'V' for r in rows), 'Rows must be "V x y"')
    return moire_cell(np.asarray([[float(r[1]), float(r[2])] for r in rows]))


def vortex_quantity(packet, key):
    same_as_asset(packet, key)
    q = packet['question']
    conditions(q, 'one superconducting flux quantum per vortex')
    a, area = vortex_cell(packet['inputs'][0])                 # nm, nm^2 per vortex
    if 'vortex lattice spacing' in q:
        value = a
    elif 'per square micrometre' in q:
        value = 1e6 / area
    elif 'magnetic induction B' in q:
        m = find(r'Φ0 = h/\(2e\) = ([\d.]+) × 10⁻¹⁵ Wb', q, 'Flux quantum not stated')
        value = float(m.group(1)) * 1e-15 / (area * 1e-18) * 1e3
    elif 'How much magnetic flux does each vortex carry' in q:
        b = float(find(r'B = ([\d.]+) mT', q, 'Field not stated').group(1))
        value = b * 1e-3 * area * 1e-18 * 1e15
    else:
        need('first-order Bragg peak' in q and 'q = 4π sinθ/λ' in q, 'Unknown quantity')
        value = 2 * math.pi * a / area * 1000                  # |b1| = 2π a / cell area, in um^-1
    return dict(judge_numeric(packet, key, value), parameters=dict(spacing_nm=a, cell_nm2=area), method='primitive cell from vortex centres')


def vortex_design(packet, key):
    same_as_asset(packet, key)
    q = packet['question']
    conditions(q, 'one superconducting flux quantum per vortex')
    cells = {i['name']: vortex_cell(i) for i in packet['inputs']}
    field = {}
    for o in packet['options']:
        m = re.fullmatch(r'.*\(([\d.]+) mT\) \((\S+)\)', o['value'])
        need(m is not None and m.group(2) in cells, 'Option does not name a field and a supplied file')
        field[m.group(2)] = (o['label'], float(m.group(1)))
    s = re.search(r'spacing is closest to ([\d.]+) nm', q)
    k = re.search(r'Bragg peak .* is closest to ([\d.]+) μm⁻¹', q)
    d = re.search(r'at least ([\d.]+) vortices per square micrometre', q)
    need(sum(x is not None for x in (s, k, d)) == 1, 'Design goal not stated exactly once')
    if d:
        t = float(d.group(1))
        ok = [n for n, (a, area) in cells.items() if 1e6 / area >= t]
        need(ok, 'No field meets the density')
        win = min(ok, key=lambda n: field[n][1])
    else:
        t = float((s or k).group(1))
        prop = {n: (a if s else 2 * math.pi * a / area * 1000) for n, (a, area) in cells.items()}
        ranked = sorted(prop, key=lambda n: abs(prop[n] - t))
        need(abs(prop[ranked[1]] - t) > abs(prop[ranked[0]] - t) + 1e-6, 'Tie')
        win = ranked[0]
    need(key['correct_label'] == field[win][0], 'Key label disagrees with recomputed choice')
    return dict(label=field[win][0], parameters={n: dict(spacing_nm=c[0]) for n, c in cells.items()}, method='primitive cells; goal rule')


# ------------------------------------------------------------------ cholesteric director fields
def helix(inp):
    lines = inp['text'].splitlines()
    rows = [l.split() for l in lines[2:] if l.strip()]
    need(lines[0].strip().isdigit() and int(lines[0]) == len(rows) and all(len(r) == 7 and r[0] == 'site' for r in rows), 'Bad director file')
    pos = np.asarray([[float(v) for v in r[1:4]] for r in rows])
    n = np.asarray([[float(v) for v in r[4:]] for r in rows])
    u = pos[-1] - pos[0]
    length = np.linalg.norm(u)
    u /= length
    e1 = n[0] - (n[0] @ u) * u
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)                                      # (e1, e2, u) right-handed
    phi = np.arctan2(n @ e2, n @ e1)
    phi = np.unwrap(2 * phi) / 2                              # director angle is defined modulo π
    s = (pos - pos[0]) @ u
    slope = np.polyfit(s, phi, 1)[0]
    need(np.abs(phi - np.polyval(np.polyfit(s, phi, 1), s)).max() < 1e-6, 'Twist is not uniform')
    return float(2 * math.pi / abs(slope)), (1 if slope > 0 else -1)


def indices(q):
    m = re.search(r'ne = ([\d.]+), no = ([\d.]+)', q)
    return (float(m.group(1)), float(m.group(2))) if m else None


def cholesteric_quantity(packet, key):
    same_as_asset(packet, key)
    q = packet['question']
    conditions(q, 'the director twists uniformly about a straight helix axis')
    p, hand = helix(packet['inputs'][0])
    if 'What are the handedness and the helical pitch' in q:
        need('right thumb pointing along the direction of travel' in q, 'Handedness rule not stated')
        want = '%s, pitch %s nm' % ('right-handed' if hand > 0 else 'left-handed', rounded(p, 1))
        hits = [o['label'] for o in packet['options'] if o['value'] == want]
        need(len(hits) == 1 and key['correct_label'] == hits[0], 'Key disagrees with recomputed handedness/pitch')
        return dict(label=hits[0], parameters=dict(pitch_nm=p, hand=hand), method='projected angle fit')
    if 'What is the helical pitch p' in q:
        value = p
    elif 'What is the helical twisting power HTP' in q:
        c = float(find(r'contains ([\d.]+) wt% of the chiral dopant', q, 'Concentration not stated').group(1))
        value = 1000 / (p * c / 100)
    else:
        ix = indices(q)
        if ix:
            need('(ne + no)/2' in q, 'Index rule not stated')
            n_avg, dn = sum(ix) / 2, ix[0] - ix[1]
        else:
            need('average refractive index 1.6' in q, 'Index not stated')
            n_avg, dn = 1.6, None
        if 'central wavelength' in q:
            value = n_avg * p
        else:
            need('width Δλ' in q and dn is not None, 'Unknown optical quantity')
            value = dn * p
    return dict(judge_numeric(packet, key, value), parameters=dict(pitch_nm=p, hand=hand), method='projected angle fit')


def cholesteric_design(packet, key):
    same_as_asset(packet, key)
    q = packet['question']
    conditions(q, 'the director twists uniformly about a straight helix axis')
    ix = indices(q)
    films = {}
    for inp in packet['inputs']:
        p, hand = helix(inp)
        if inp['name'].startswith('clc-E44'):
            need(ix is not None, 'E44 indices not stated')
            n_avg = sum(ix) / 2
        else:
            need('average refractive index 1.6' in q, 'Coating index not stated')
            n_avg = 1.6
        films[inp['name']] = dict(lam=n_avg * p, hand=hand, conc=(float(re.search(r'R5011-([\d.]+)wt', inp['name']).group(1))
                                                                   if 'R5011' in inp['name'] else None))
    labels = {}
    for o in packet['options']:
        m = re.search(r'\((\S+\.txt)\)$', o['value'])
        need(m is not None and m.group(1) in films, 'Option does not name a supplied file')
        labels[m.group(1)] = o['label']
    close = re.search(r'centred as close as possible to ([\d.]+) nm', q)
    below = re.search(r'centred at or below ([\d.]+) nm', q)
    need((close is None) != (below is None), 'Design goal not stated exactly once')
    if close:
        t = float(close.group(1))
        pool = {k: v for k, v in films.items() if 'helix is left-handed' not in q or v['hand'] < 0}
        need(pool, 'No candidate has the required handedness')
        ranked = sorted(pool, key=lambda k: abs(pool[k]['lam'] - t))
        need(len(ranked) == 1 or abs(pool[ranked[1]]['lam'] - t) > abs(pool[ranked[0]]['lam'] - t) + 1e-6, 'Tie')
        win = ranked[0]
    else:
        t = float(below.group(1))
        ok = [k for k, v in films.items() if v['lam'] <= t]
        need(ok and all(films[k]['conc'] is not None for k in ok), 'No candidate meets the limit')
        win = min(ok, key=lambda k: films[k]['conc'])
    need(key['correct_label'] == labels[win], 'Key label disagrees with recomputed choice')
    return dict(label=labels[win], parameters={k: dict(reflection_nm=round(v['lam'], 2), hand=v['hand']) for k, v in films.items()},
                method='projected angle fit per file; goal rule')


CHECKERS = {'vortex_geometry': vortex_quantity, 'vortex_inference': vortex_quantity, 'vortex_design': vortex_design,
            'cholesteric_geometry': cholesteric_quantity, 'cholesteric_optics': cholesteric_quantity, 'cholesteric_design': cholesteric_design}
