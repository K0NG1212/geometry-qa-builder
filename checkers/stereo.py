"""Independent checkers for the stereochemistry ladder (no generation code imported).

Own implementations of: bonding (Cordero radii x 1.25), first-shell classes, stereo
elements (4-coordinate centres; pyramidal S/P; aziridine N; cis/trans at trigonal C=C /
C=N), a colour-refinement graph invariant, and rotation-invariant matching of supplied
structures to the hash-verified dataset extract (distance matrix + handedness), so that
properties are never looked up by label or id.
"""
import hashlib
import json
import math
from .common import need, find, read_xyz, verify_hashes, LABELS, vec, dot, cross

RADII = {'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'S': 1.05, 'Cl': 1.02, 'P': 1.07, 'F': 0.57}


def floats(atoms):
    return [e for e, _ in atoms], [tuple(float(c) for c in p) for _, p in atoms]


def bonds(el, pts):
    return {(i, j) for i in range(len(pts)) for j in range(i + 1, len(pts))
            if math.dist(pts[i], pts[j]) <= 1.25 * (RADII[el[i]] + RADII[el[j]])}


def adjacency(n, edges):
    adj = [set() for _ in range(n)]
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    return adj


def stereo_elements(el, pts, edges):
    adj = adjacency(len(el), edges)
    cls = [(el[i], tuple(sorted(el[j] for j in adj[i]))) for i in range(len(el))]
    centres, sides = {}, {}
    for i in range(len(el)):
        nb = sorted(adj[i])
        if len({cls[j] for j in nb}) != len(nb):
            continue
        ring3 = any(k in adj[j] for j in nb for k in nb if j != k)
        if len(nb) == 4 or (len(nb) == 3 and (el[i] in ('S', 'P') or (el[i] == 'N' and ring3))):
            u, v, w = (vec(pts[i], pts[j]) for j in nb[:3])
            t = dot(cross(u, v), w)
            if len(nb) == 3 and abs(t) < 0.1 * math.sqrt(dot(u, u) * dot(v, v) * dot(w, w)):
                continue
            centres[i] = t > 0
    trig = {i for i in range(len(el)) if (el[i] == 'C' and len(adj[i]) == 3) or (el[i] == 'N' and len(adj[i]) == 2)}
    for i, j in edges:
        if i in trig and j in trig:
            si, sj = sorted(adj[i] - {j}), sorted(adj[j] - {i})
            if (len(si) == 2 and cls[si[0]] == cls[si[1]]) or (len(sj) == 2 and cls[sj[0]] == cls[sj[1]]):
                continue
            # cis if the two reference substituents lie on the same side of the plane through
            # the double bond perpendicular to the substituent plane (sign of projections).
            axis = vec(pts[i], pts[j])
            a, b = vec(pts[i], pts[si[0]]), vec(pts[j], pts[sj[0]])
            pa = [x - dot(a, axis) / dot(axis, axis) * y for x, y in zip(a, axis)]
            pb = [x - dot(b, axis) / dot(axis, axis) * y for x, y in zip(b, axis)]
            sides[(i, j)] = dot(pa, pb) > 0
    return centres, sides


def invariant(el, edges, rounds=4):
    adj = adjacency(len(el), edges)
    colour = list(el)
    for _ in range(rounds):     # colour refinement; md5 keeps labels comparable across molecules
        colour = [hashlib.md5(repr((colour[i], sorted(colour[j] for j in adj[i]))).encode()).hexdigest()
                  for i in range(len(el))]
    return sorted(colour), sorted(len(a) for a in adj)


def relation(a, b, shared_order):
    (ea, pa), (eb, pb) = floats(a), floats(b)
    need(sorted(ea) == sorted(eb), 'Structures have different formulas')
    ga, gb = bonds(ea, pa), bonds(eb, pb)
    if not shared_order or ea != eb or ga != gb:
        need(invariant(ea, ga) != invariant(eb, gb), 'Cannot decide constitution without atom correspondence')
        return 'constitutional', {}
    (ca, sa), (cb, sb) = stereo_elements(ea, pa, ga), stereo_elements(eb, pb, gb)
    need(set(ca) == set(cb) and set(sa) == set(sb), 'Stereo elements differ: undecidable')
    inverted = [k for k in ca if ca[k] != cb[k]]
    switched = [k for k in sa if sa[k] != sb[k]]
    facts = dict(centres=sorted(ca), inverted=sorted(inverted), switched=[list(k) for k in sorted(switched)])
    if not inverted and not switched:
        return 'same', facts
    if ca and len(inverted) == len(ca) and not switched:
        return 'enantiomer', facts
    return 'diastereomer', facts


def dmatrix_gap(p, q):
    n = len(p)
    diffs = [math.dist(p[i], p[j]) - math.dist(q[i], q[j]) for i in range(n) for j in range(i + 1, n)]
    return math.sqrt(math.fsum(d * d for d in diffs) / len(diffs))


def find_in(atoms, data_list):
    """Try every hash-verified extract; returns (dataset, conformer, mirrored)."""
    for d in data_list:
        if floats(atoms)[0] == d['elements']:
            try:
                return (d,) + locate(atoms, d)
            except Exception:
                continue
    need(False, 'Structure not found in any dataset extract')


def locate(atoms, data):
    """Dataset conformer with the same internal geometry and handedness; or the exact mirror
    image of one (returned with mirrored=True: scalar properties equal by reflection symmetry)."""
    el, pts = floats(atoms)
    need(el == data['elements'], 'Atom order differs from the dataset extract')
    hits = []
    for c in data['conformers']:
        if dmatrix_gap(pts, c['xyz']) < 1e-5:
            same = stereo_elements(el, pts, bonds(el, pts))[0] == stereo_elements(el, c['xyz'], bonds(el, c['xyz']))[0]
            hits.append((c, not same))
    need(len(hits) >= 1, 'Structure not found in the dataset extract')
    exact = [h for h in hits if not h[1]]
    return exact[0] if exact else hits[0]


def files(packet):
    return {i['name']: read_xyz(i['text']) for i in packet['inputs']}


def datasets(key):
    return [json.loads(p.read_text(encoding='utf-8')) for p in verify_hashes(key).values()]


# ------------------------------------------------------------------ perception
OPTION_TEXT = {'same': 'the same compound', 'enantiomer': 'an enantiomer', 'diastereomer': 'a diastereomer',
               'constitutional': 'a constitutional isomer'}


def stereo_relationship(packet, key):
    q = packet['question']
    need('rigidly rotated' in q and 'atom order may differ' in q, 'Question must disclose the rotation and atom order')
    f = files(packet)
    need(set(f) == {'S0.xyz', 'X.xyz'}, 'Need S0.xyz and X.xyz')
    data = datasets(key)
    same_molecule = len(data) == 1
    rel, facts = relation(f['S0.xyz'], f['X.xyz'], same_molecule)
    if same_molecule:          # dataset labels must agree with the geometric verdict
        (c0, m0), (c1, m1) = locate(f['S0.xyz'], data[0]), locate(f['X.xyz'], data[0])
        need(not m0 and not m1, 'Supplied structures are not dataset structures')
        need((c0['isomer'] == c1['isomer']) == (rel == 'same'), 'Geometry disagrees with dataset stereoisomer labels')
    labels = [o['label'] for o in packet['options'] if o['value'].startswith(OPTION_TEXT[rel])]
    need(len(labels) == 1, 'Exactly one option must name the relationship')
    need(key['correct_label'] == labels[0], 'Key label %s != recomputed %s' % (key['correct_label'], labels[0]))
    return dict(label=labels[0], recomputed=rel, parameters=dict(same_dataset_molecule=same_molecule), facts=facts,
                method='own bond graph, stereo elements and colour-refinement invariant')


# ------------------------------------------------------------------ inference
def stereo_property_inference(packet, key):
    q = packet['question']
    margin_e = float(find(r'at least ([\d.]+) eV', q, 'Energy margin not stated').group(1))
    margin_mu = float(find(r'and ([\d.]+) e·Å in dipole', q, 'Dipole margin not stated').group(1))
    f = files(packet)
    [data] = datasets(key)
    rel, facts = relation(f['S0.xyz'], f['X.xyz'], True)
    need(rel == 'diastereomer', 'S0 and X must be diastereomers, found ' + rel)
    (c0, m0), (c1, m1) = locate(f['S0.xyz'], data), locate(f['X.xyz'], data)
    need(not m0 and not m1, 'Supplied structures are not dataset structures')
    de, dmu = c1['e_pbe0_mbd_eV'] - c0['e_pbe0_mbd_eV'], c1['dipole_eA'] - c0['dipole_eA']
    need(abs(de) >= margin_e and abs(dmu) >= margin_mu, 'Differences below the stated margins')
    verdicts = []
    for o in packet['options']:
        energy = find(r'X is (lower|higher) in energy', o['value'], 'Option lacks energy direction').group(1)
        dipole = find(r'has a (larger|smaller) dipole', o['value'], 'Option lacks dipole direction').group(1)
        verdicts.append((energy == 'higher') == (de > 0) and (dipole == 'larger') == (dmu > 0))
    need(sum(verdicts) == 1 and len({o['value'] for o in packet['options']}) == 4, 'Exactly one statement must hold')
    label = LABELS[verdicts.index(True)]
    need(key['correct_label'] == label, 'Key label %s != recomputed %s' % (key['correct_label'], label))
    return dict(label=label, recomputed=dict(delta_energy_eV=round(de, 6), delta_dipole_eA=round(dmu, 6)), facts=facts,
                method='structures matched to dataset by distance matrix and handedness; signs and margins recomputed')


# ------------------------------------------------------------------ design
def stereo_design_selection(packet, key):
    q = packet['question']
    margin = float(find(r'at least ([\d.]+) eV \(1 kcal/mol\) lower', q, 'Goal margin not stated').group(1))
    need('same atoms, same bonds' in q and 'conformation alone does not count' in q, 'Allowed modification not stated')
    f = files(packet)
    need(set(f) == {'S0.xyz'} | {'candidate_%s.xyz' % l for l in LABELS}, 'Need S0 and four candidates')
    data = datasets(key)
    main, s0, mirrored = find_in(f['S0.xyz'], data)
    need(not mirrored, 'S0 is not a dataset structure')
    verdicts, rows = [], {}
    for label in LABELS:
        cand = f['candidate_%s.xyz' % label]
        home, c, mir = find_in(cand, data)
        rel, _ = relation(f['S0.xyz'], cand, home is main)
        energy = c['e_pbe0_mbd_eV']                  # mirror image: equal by reflection symmetry
        ok = rel in ('enantiomer', 'diastereomer') and energy - s0['e_pbe0_mbd_eV'] <= -margin
        verdicts.append(ok)
        rows[label] = dict(relation=rel, delta_energy_eV=round(energy - s0['e_pbe0_mbd_eV'], 6), mirror_of_dataset=mir)
    need(sum(verdicts) == 1, '%d candidates satisfy constraint and goal (need exactly 1)' % sum(verdicts))
    label = LABELS[verdicts.index(True)]
    need(key['correct_label'] == label, 'Key label %s != recomputed %s' % (key['correct_label'], label))
    return dict(label=label, recomputed=label, options=rows,
                method='own relationship classification per candidate; energies by dataset matching or reflection symmetry')
