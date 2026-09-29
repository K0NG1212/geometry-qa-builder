"""Independent checkers for the families migrated from legacy calculators (roadmap A5).
No generation code is imported; parameters are read from the question text.
"""
import cmath
import itertools
import math
import re
import numpy as np
from decimal import Decimal, localcontext
from .common import need, find, read_xyz, verify_hashes, judge_numeric, LABELS

RADII = {'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'S': 1.05, 'Cl': 1.02, 'P': 1.07, 'F': 0.57}


def dec_dist(p, q):
    with localcontext() as ctx:
        ctx.prec = 40
        return sum((Decimal(str(a)) - Decimal(str(b))) ** 2 for a, b in zip(p, q)).sqrt()


def pdb_atoms(text):
    out = {}
    for line in text.splitlines():
        if line.startswith('ATOM'):
            out[(line[12:16].strip(), line[17:20].strip().title(), int(line[22:26]))] = tuple(float(line[c:c + 8]) for c in (30, 38, 46))
    return out


def verbatim(packet_text, key, prefix=('ATOM', 'SSBOND')):
    [path] = verify_hashes(key).values()
    source = {l.rstrip() for l in path.read_text(encoding='utf-8').splitlines()}
    need(all(l in source for l in packet_text.splitlines() if l.startswith(prefix)), 'Excerpt lines not copied unchanged from the source')
    return path


# ------------------------------------------------------------------ bond distance
def named_bond_distance(packet, key):
    q = packet['question']
    [inp] = packet['inputs']
    if inp['format'] == 'pdb-excerpt':
        named = re.findall(r'([A-Z0-9]+)\(([A-Z][a-z]{2})(\d+)\)', q)
        need(len(named) == 2, 'Question must name exactly two PDB atoms')
        atoms = pdb_atoms(inp['text'])
        points = [atoms.get((n, r, int(k))) for n, r, k in named]
        need(all(points), 'Named atoms missing from excerpt')
        elements = [n[0] for n, _, _ in named]
        if 'SSBOND' in q:
            pair = {int(k) for _, _, k in named}
            ss = [l for l in inp['text'].splitlines() if l.startswith('SSBOND')]
            need(any({int(l[17:21]), int(l[31:35])} == pair for l in ss), 'SSBOND record for the named pair missing')
        verbatim(inp['text'], key)
    else:
        named = re.findall(r'(\w+) \(row (\d+)\)', q)
        need(len(named) == 2, 'Question must name exactly two atoms by row')
        rows = read_xyz(inp['text'])
        picked = [rows[int(r) - 1] for _, r in named]
        elements, points = [e for e, _ in picked], [p for _, p in picked]
        need(all(n.startswith(e) for (n, _), e in zip(named, elements)), 'Atom names disagree with XYZ elements')
        verify_hashes(key)
    d = dec_dist(*points)
    need(float(d) <= 1.25 * (RADII[elements[0]] + RADII[elements[1]]), 'Named atoms are not bonded')
    return dict(judge_numeric(packet, key, d), parameters=dict(atoms=named), method='Decimal distance; own bonding rule')


# ------------------------------------------------------------------ crystal
def cell_table(packet):
    [inp] = [i for i in packet['inputs'] if i['format'] == 'fractional-cell-table']
    lines = inp['text'].splitlines()
    a = float(find(r'cubic a = ([\d.]+) angstrom', lines[0], 'Cell edge missing').group(1))
    rows = [(r[0], [float(x) for x in r[1:]]) for r in (l.split() for l in lines[1:] if l.strip())]
    return a, rows


def periodic_dists(a, centre, pts, images=True):
    out = []
    for f in pts:
        for t in (itertools.product((-1, 0, 1), repeat=3) if images else [(0, 0, 0)]):
            d = a * math.sqrt(sum((x + s - c) ** 2 for x, s, c in zip(f, t, centre)))
            if d > 1e-6:
                out.append(d)
    return sorted(out)


def coordination_shell(packet, key):
    q = packet['question']
    need('infinite and periodic' in q, 'Periodicity not stated')
    a, rows = cell_table(packet)
    centre = [float(x) for x in find(r'at fractional \(([-\d.]+), ([-\d.]+), ([-\d.]+)\)', q, 'Centre position missing').groups()]
    part = find(r'how many (other )?(μ4-)?([A-Z][a-z]?) atoms', q, 'Partner species missing')
    element, mu4 = part.group(3), bool(part.group(2))

    def is_node(f):     # an O with four Zn within 2.4 angstrom, periodic images included
        return sum(1 for d in periodic_dists(a, f, [g for e, g in rows if e == 'Zn']) if d <= 2.4) == 4

    partners = [f for e, f in rows if e == element and (not mu4 or is_node(f))]
    need(any(max(abs(x - c) for x, c in zip(f, centre)) < 1e-4 for e, f in rows), 'No atom at the stated centre position')
    dists = periodic_dists(a, centre, partners)
    d1 = dists[0]
    n1 = sum(1 for d in dists if d - d1 <= 1e-3)
    verdicts = []
    for o in packet['options']:
        n, d = find(r'^(\d+) at ([\d.]+) Å$', o['value'], 'Option must read "N at D Å"').groups()
        verdicts.append(int(n) == n1 and abs(float(d) - d1) <= 0.0005 + 1e-9)
    need(sum(verdicts) == 1, '%d options match the nearest shell (need exactly 1)' % sum(verdicts))
    label = LABELS[verdicts.index(True)]
    need(key['correct_label'] == label, 'Key label %s != recomputed %s' % (key['correct_label'], label))
    verify_hashes(key)
    return dict(label=label, recomputed='%d at %.4f Å' % (n1, d1), parameters=dict(partner=element, mu4_node=mu4),
                method='own periodic neighbour search over 27 cells')


def first_diffraction_peak(packet, key):
    q = packet['question']
    weights = {k: int(v) for k, v in re.findall(r'([A-Z][a-z]?) = (\d+)', find(r'weights \(([^)]*)\)', q, 'Weights missing').group(1))}
    lam = float(find(r'wavelength ([\d.]+) Å', q, 'Wavelength missing').group(1))
    a, rows = cell_table(packet)
    need({e for e, _ in rows} == set(weights), 'Weights must cover the elements present')
    total = sum(weights[e] for e, _ in rows)
    best = None
    for h, k, l in itertools.product(range(6), repeat=3):
        if (h, k, l) == (0, 0, 0):
            continue
        s = lam * math.sqrt(h * h + k * k + l * l) / (2 * a)
        if s > 1:
            continue
        f = abs(sum(weights[e] * cmath.exp(2j * math.pi * (h * x + k * y + l * z)) for e, (x, y, z) in rows)) / total
        if f > 1e-6 and (best is None or s < best[0] - 1e-12):
            best = (s, (h, k, l))
    angle = 2 * math.degrees(math.asin(best[0]))
    verify_hashes(key)
    return dict(judge_numeric(packet, key, angle), parameters=dict(weights=weights, wavelength_A=lam, reflection=best[1]),
                method='all (h k l) up to 5 with own structure-factor sum')


# ------------------------------------------------------------------ scattering
def fret_efficiency(packet, key):
    q = packet['question']
    sites = re.findall(r"atom (\S+) of (?:nucleotide )?([A-Z][a-z]{0,2})(\d+)", q)
    need(len(sites) == 2, 'Donor and acceptor atoms must be named')
    r0 = float(find(r'R0 = ([\d.]+) nm', q, 'Foerster radius missing').group(1))
    [inp] = packet['inputs']
    atoms = pdb_atoms(inp['text'])
    pts = [atoms.get((n, r, int(k))) for n, r, k in sites]
    need(all(pts), 'Donor or acceptor atom missing from excerpt')
    verbatim(inp['text'], key)
    r = float(dec_dist(*pts)) / 10
    e = 1 / (1 + (r / r0) ** 6)
    return dict(judge_numeric(packet, key, e), parameters=dict(sites=sites, R0_nm=r0, r_nm=r), method='straight-line distance; Foerster law')


def guinier_intensity(packet, key):
    q = packet['question']
    qv = float(find(r'q = ([\d.]+) nm', q, 'q missing').group(1))
    need('identical point scatterer' in q, 'Scatterer model not stated')
    [inp] = packet['inputs']
    if inp['format'] == 'centroid-table':      # labelled point table: every row is one scatterer
        pts = [tuple(float(x) for x in l.split()[2:5]) for l in inp['text'].splitlines()[1:] if l.strip()]
    else:
        pts = [tuple(float(c) for c in p) for _, p in read_xyz(inp['text'])]
    n = len(pts)
    # Pair identity Rg^2 = sum_{i<j} d_ij^2 / N^2 (the generator uses the centroid form); chunked numpy for large N.
    arr = np.asarray(pts)
    s = math.fsum(float((((arr[i:i + 500, None, :] - arr[None, :, :]) ** 2).sum(axis=2)).sum()) for i in range(0, n, 500)) / 2
    rg = math.sqrt(s) / n / 10
    need(qv * rg <= 1.3, 'q*Rg above the Guinier validity limit')
    [path] = verify_hashes(key).values()
    if path.suffix in ('.xyz', '.txt'):   # reduced assembly asset: the input must be that file verbatim
        need(path.read_bytes() == inp['text'].encode('utf-8'), 'XYZ differs from the published reduced asset')
        return dict(judge_numeric(packet, key, math.exp(-(qv * rg) ** 2 / 3)), parameters=dict(q_per_nm=qv, rg_nm=rg, atoms=n),
                    method='pair-distance Rg; Guinier law')
    # Provenance: the XYZ must be exactly the non-hydrogen main-altloc ATOM records of the named chains.
    chains = find(r'chains ([A-Z]+)\)', q, 'Chains missing').group(1)
    src = [tuple(float(l[c:c + 8]) for c in (30, 38, 46)) for l in path.read_text(encoding='utf-8').split('ENDMDL')[0].splitlines()
           if l.startswith('ATOM') and l[21] in chains and l[16] in ' A' and (l[76:78].strip() or l[12:16].strip()[0]).upper() != 'H']
    need(len(src) == n and max(abs(x - y) for p, s2 in zip(pts, src) for x, y in zip(p, s2)) < 1e-6,
         'XYZ does not reproduce the source heavy atoms')
    return dict(judge_numeric(packet, key, math.exp(-(qv * rg) ** 2 / 3)), parameters=dict(q_per_nm=qv, rg_nm=rg, atoms=n),
                method='pair-distance Rg; Guinier law')


CHECKERS = {'named_bond_distance': named_bond_distance, 'coordination_shell': coordination_shell,
            'first_diffraction_peak': first_diffraction_peak, 'fret_efficiency': fret_efficiency,
            'guinier_intensity': guinier_intensity}


# ------------------------------------------------------------------ large assemblies
def assembly_points(packet, key):
    [inp] = packet['inputs']
    [path] = verify_hashes(key).values()
    need(path.read_bytes() == inp['text'].encode('utf-8'), 'Input differs from the published reduced asset')
    if inp['format'] == 'xyz':
        rows = read_xyz(inp['text'])
        return [e for e, _ in rows], np.asarray([[float(c) for c in p] for _, p in rows])
    rows = [l.split() for l in inp['text'].splitlines()[1:] if l.strip()]
    return [r[0] for r in rows], np.asarray([[float(x) for x in r[2:5]] for r in rows])


def selection(packet, key):
    labels, pts = assembly_points(packet, key)
    m = re.search(r'Select all points labelled (\S+?)\.', packet['question'])
    if m:
        pts = pts[[l == m.group(1) for l in labels]]
    else:
        need('Select all supplied points' in packet['question'], 'Point selection not stated')
    need(len(pts) >= 2, 'Selection is empty')
    return pts


def assembly_extent(packet, key):
    pts = selection(packet, key)
    best, pair = -1.0, None
    for i in range(0, len(pts), 700):                # own chunking; Decimal on the winning pair
        d2 = ((pts[i:i + 700, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
        k = int(d2.argmax())
        if d2.flat[k] > best:
            best, pair = float(d2.flat[k]), (i + k // len(pts), k % len(pts))
    d = dec_dist(pts[pair[0]].tolist(), pts[pair[1]].tolist()) / 10
    return dict(judge_numeric(packet, key, d), parameters=dict(points=len(pts)), method='chunked brute force + Decimal pair')


def assembly_rg(packet, key):
    pts = selection(packet, key)
    n = len(pts)
    s = math.fsum(float((((pts[i:i + 500, None, :] - pts[None, :, :]) ** 2).sum(axis=2)).sum()) for i in range(0, n, 500)) / 2
    return dict(judge_numeric(packet, key, math.sqrt(s) / n / 10), parameters=dict(points=n), method='pair-distance identity')


def capsid_architecture(packet, key):
    q = packet['question']
    labels, _ = assembly_points(packet, key)
    trimer = re.search(r'major capsid protein (\S+) forms trimeric pseudo-hexameric capsomers', q)
    if trimer:
        need('12 pentamers at the vertices are formed by a different protein' in q, 'Penton composition not stated')
        n = sum(1 for l in labels if l == trimer.group(1))
        need(n > 0 and n % 30 == 0, 'Copy number is not 30(T-1)')
        t = n // 3 // 10 + 1                           # trimers = 10(T-1)
        need('triangulation number' in q, 'Unknown architecture question')
        return dict(judge_numeric(packet, key, t), parameters=dict(component=trimer.group(1), copies=n, T=t),
                    method='count copies; trimeric capsomers = 10(T-1)')
    component = find(r'shell formed by (\S+?)\?', q, 'Shell component not stated').group(1)
    n = sum(1 for l in labels if l == component)
    need(n > 0 and n % 60 == 0, 'Copy number is not a multiple of 60')
    t = n // 60
    if 'triangulation number' in q:
        value = t
    elif 'hexameric capsomers' in q:
        value = 10 * (t - 1)
    else:
        need('total number of capsomers' in q, 'Unknown architecture question')
        value = 12 + 10 * (t - 1)
    return dict(judge_numeric(packet, key, value), parameters=dict(component=component, copies=n, T=t),
                method='count copies; Caspar–Klug relations')


CHECKERS.update(assembly_extent=assembly_extent, assembly_rg=assembly_rg, capsid_architecture=capsid_architecture)


# ------------------------------------------------------------------ whole-particle scattering
# The generator uses the Debye pair sum. Here the orientation average of |sum_j exp(i q.r_j)|^2 is
# integrated directly over directions with a product Gauss-Legendre (cos theta) x uniform (phi)
# rule whose degree exceeds q * (particle diameter) + 30, where the plane-wave expansion has converged.
def orientation_average(pts_nm, q):
    centred = pts_nm - pts_nm.mean(axis=0)
    degree = int(q * 2 * np.sqrt((centred ** 2).sum(axis=1)).max()) + 30
    x, w = np.polynomial.legendre.leggauss(degree // 2 + 2)
    phi = 2 * np.pi * np.arange(degree + 2) / (degree + 2)
    s = np.sqrt(1 - x ** 2)
    dirs = np.stack([np.outer(s, np.cos(phi)).ravel(), np.outer(s, np.sin(phi)).ravel(), np.repeat(x, len(phi))], axis=1)
    weights = np.repeat(w, len(phi)) / 2 / len(phi)
    total = 0.0
    for i in range(0, len(dirs), 256):
        amp = np.exp(1j * q * (dirs[i:i + 256] @ centred.T)).sum(axis=1)
        total += math.fsum(weights[i:i + 256] * np.abs(amp) ** 2)
    return total / len(pts_nm) ** 2


def scattering_points(packet, key):
    q = packet['question']
    need('identical point scatterer' in q, 'Scatterer model not stated')
    need('q = 4π sinθ/λ' in q, 'q convention not stated')
    return selection(packet, key) / 10


def debye_intensity(packet, key):
    pts = scattering_points(packet, key)
    qv = float(find(r'at q = ([\d.]+) nm⁻¹', packet['question'], 'q missing').group(1))
    value = orientation_average(pts, qv)
    return dict(judge_numeric(packet, key, value), parameters=dict(q_per_nm=qv, points=len(pts)),
                method='direct orientation average (Gauss-Legendre x uniform phi quadrature)')


def scattering_q_design(packet, key):
    pts = scattering_points(packet, key)
    target = float(find(r'first falls to ([\d.]+)\.', packet['question'], 'Target intensity missing').group(1))
    centred = pts - pts.mean(axis=0)
    rg = math.sqrt(float((centred ** 2).sum(axis=1).mean()))
    f = lambda q: orientation_average(pts, q) - target
    # Own search: march in steps of 0.013/Rg from q = 0 to the first sign change, then regula falsi (Illinois).
    step, lo, flo = 0.013 / rg, 0.0, 1.0 - target
    need(flo > 0, 'Target must be below I(0)/I(0) = 1')
    hi = step
    while f(hi) > 0:
        lo, hi = hi, hi + step
        need(hi * rg < 12, 'No crossing found below q*Rg = 12')
    flo, fhi, side = f(lo), f(hi), 0
    for _ in range(100):
        mid = (lo * fhi - hi * flo) / (fhi - flo)
        fm = f(mid)
        if abs(fm) < 1e-13 or hi - lo < 1e-12:
            break
        if fm > 0:
            lo, flo = mid, fm
            fhi, side = (fhi / 2, 1) if side == 1 else (fhi, 1)
        else:
            hi, fhi = mid, fm
            flo, side = (flo / 2, -1) if side == -1 else (flo, -1)
    return dict(judge_numeric(packet, key, mid), parameters=dict(target=target, rg_nm=rg, points=len(pts)),
                method='orientation-average quadrature; march + Illinois regula falsi')


CHECKERS.update(debye_intensity=debye_intensity, scattering_q_design=scattering_q_design)


# ------------------------------------------------------------------ secondary structure from phi/psi
def _dihedral(p0, p1, p2, p3):
    """Signed dihedral from plane normals: acos for the magnitude, triple product for the sign."""
    b1, b2, b3 = np.subtract(p1, p0), np.subtract(p2, p1), np.subtract(p3, p2)
    n1, n2 = np.cross(b1, b2), np.cross(b2, b3)
    angle = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(n1, n2) / (np.linalg.norm(n1) * np.linalg.norm(n2)))))))
    return -angle if float(np.dot(np.cross(n1, n2), b2)) < 0 else angle


def secondary_structure(packet, key):
    q = packet['question']
    need('IUPAC' in q and '360° periodicity' in q, 'Sign convention or periodic distance not stated')
    m = find(r'dihedrals φ and ψ of ([A-Z][a-z]{2})(\d+)', q, 'Residue not named')
    n = int(m.group(2))
    refs = [(name.strip(), float(a.replace('−', '-')), float(b.replace('−', '-')))
            for name, a, b in re.findall(r'([\w\- α-ωΑ-Ω]+?) \(φ ([+−-]?\d+)°, ψ ([+−-]?\d+)°\)', q)]
    refs = [(name.split(': ')[-1].lstrip(', '), a, b) for name, a, b in refs]
    need(len(refs) == 4, 'Expected four reference conformations')
    [inp] = packet['inputs']
    atoms = {}
    for line in inp['text'].splitlines():
        if line.startswith('ATOM'):
            atoms[(line[12:16].strip(), int(line[22:26]))] = tuple(float(line[c:c + 8]) for c in (30, 38, 46))
    for a in (('C', n - 1), ('N', n), ('CA', n), ('C', n), ('N', n + 1)):
        need(a in atoms, 'Backbone atom %s(%d) missing' % a)
    phi = _dihedral(atoms[('C', n - 1)], atoms[('N', n)], atoms[('CA', n)], atoms[('C', n)])
    psi = _dihedral(atoms[('N', n)], atoms[('CA', n)], atoms[('C', n)], atoms[('N', n + 1)])
    wrap = lambda x: (x + 180) % 360 - 180
    dist = {name: math.hypot(wrap(phi - a), wrap(psi - b)) for name, a, b in refs}
    best = min(dist, key=dist.get)
    need(sorted(dist.values())[1] - dist[best] > 5, 'Nearest reference not decisive')
    need(sorted(o['value'] for o in packet['options']) == sorted(dist), 'Options are not exactly the reference conformations')
    hits = [o['label'] for o in packet['options'] if o['value'] == best]
    need(key['correct_label'] == hits[0], 'Key label disagrees with recomputed class')
    # Provenance and evidence: excerpt lines verbatim; the entry's HELIX/SHEET record must agree with the class.
    [path] = verify_hashes(key).values()
    source = path.read_text(encoding='utf-8').splitlines()
    lines = set(l.rstrip() for l in source)
    need(all(l in lines for l in inp['text'].splitlines() if l.startswith('ATOM')), 'Excerpt lines are not copied unchanged')
    chain = inp['text'].splitlines()[0][21]
    kinds = {l[:5] for l in source if (l.startswith('HELIX') and l[19] == chain and int(l[21:25]) <= n <= int(l[33:37]))
             or (l.startswith('SHEET') and l[21] == chain and int(l[22:26]) <= n <= int(l[33:37]))}
    need(kinds in ({'HELIX'}, {'SHEET'}), 'No unique HELIX/SHEET record for the residue')
    need(('α-helix' in best and 'right' in best) if kinds == {'HELIX'} else best == 'β-strand', 'Class disagrees with the entry record')
    return dict(label=hits[0], parameters=dict(phi=phi, psi=psi, distances=dist, record=sorted(kinds)[0]),
                method='acos dihedrals; nearest reference; HELIX/SHEET evidence')


CHECKERS.update(secondary_structure=secondary_structure)
