"""Independent checkers for the families migrated from legacy calculators (roadmap A5).
No generation code is imported; parameters are read from the question text.
"""
import cmath
import itertools
import math
import re
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
    atoms = read_xyz(inp['text'])
    pts = [tuple(float(c) for c in p) for _, p in atoms]
    n = len(pts)
    # Pair identity Rg^2 = sum_{i<j} d_ij^2 / N^2 (the generator uses the centroid form).
    s = math.fsum((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2 for i, a in enumerate(pts) for b in pts[i + 1:])
    rg = math.sqrt(s) / n / 10
    need(qv * rg <= 1.3, 'q*Rg above the Guinier validity limit')
    # Provenance: the XYZ must be exactly the non-hydrogen main-altloc ATOM records of the named chains.
    [path] = verify_hashes(key).values()
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
