"""Independent checkers for rotational_line and isotopologue_design. No generation code is imported.

Masses, h and the atomic mass unit are read from the question text; the attached XYZ must equal the hashed source asset.
The inertia tensor is accumulated in Decimal about the centre of mass, and the principal moments are the roots of its
characteristic cubic in closed (trigonometric) form; the generator diagonalises with Jacobi rotations instead.
"""
import math
import re
from decimal import Decimal, localcontext
from .common import need, find, read_xyz, verify_hashes, judge_numeric

# Rigid asymmetric rotor, J = 1 levels above 0_00 (Ka, Kc labels): the sum of the two constants about the axes
# perpendicular to the one the state rotates about.
J1_LEVELS = {'1_01': ('B', 'C'), '1_11': ('A', 'C'), '1_10': ('A', 'B')}
RATIO, MIN_MHZ = 1.15, 0.5       # design: the keyed substitution must lead clearly
SUPERSCRIPT = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789')


def model(question):
    block = find(r'masses of the most abundant isotopes: (.+?); rotational constants', question, 'Isotope masses not stated').group(1)
    masses = {e: Decimal(v) for e, v in re.findall(r'\b([A-Z][a-z]?) (\d+\.\d+) u', block)}
    need(masses, 'No masses parsed')
    h = find(r'h = ([\d.]+)×10⁻([⁰¹²³⁴⁵⁶⁷⁸⁹]+) J s', question, 'Planck constant not stated')
    u = find(r'1 u = ([\d.]+)×10⁻([⁰¹²³⁴⁵⁶⁷⁸⁹]+) kg', question, 'Atomic mass unit not stated')
    need('rigid rotor' in question and 'about the centre of mass' in question and 'h/(8π²I)' in question, 'Rotor model not stated')
    with localcontext() as ctx:
        ctx.prec = 40
        planck = Decimal(h.group(1)).scaleb(-int(h.group(2).translate(SUPERSCRIPT)))
        dalton = Decimal(u.group(1)).scaleb(-int(u.group(2).translate(SUPERSCRIPT)))
        factor = planck / (8 * Decimal(math.pi) ** 2 * dalton * Decimal('1e-20')) / Decimal(10) ** 6   # MHz u A^2
    return masses, float(factor)


def molecule(packet, key):
    [item] = [i for i in packet['inputs'] if i['format'] == 'xyz']
    paths = verify_hashes(key)
    need(len(paths) == 1, 'Exactly one source asset expected')
    [path] = paths.values()
    source = path.read_bytes().decode('utf-8-sig').split('\n')
    attached = item['text'].split('\n')
    # Count line and every atom row verbatim; only the comment line may differ (dataset ids are removed from it).
    need(len(attached) == len(source) and attached[0] == source[0] and attached[2:] == source[2:],
         'Attached XYZ differs from the source asset')
    need('Geom-' not in attached[1], 'Dataset conformer id in the attached comment line')
    return read_xyz(item['text'])


def principal_moments(atoms, masses):
    need({e for e, _ in atoms} <= set(masses), 'A mass is missing for an element present')
    with localcontext() as ctx:
        ctx.prec = 40
        w = [masses[e] for e, _ in atoms]
        total = sum(w)
        com = [sum(m * p[k] for m, (_, p) in zip(w, atoms)) / total for k in range(3)]
        t = [[Decimal(0)] * 3 for _ in range(3)]
        for m, (_, p) in zip(w, atoms):
            r = [p[k] - com[k] for k in range(3)]
            rr = sum(x * x for x in r)
            for i in range(3):
                for j in range(3):
                    t[i][j] += m * ((rr if i == j else 0) - r[i] * r[j])
    return eigen_symmetric([[float(x) for x in row] for row in t])


def eigen_symmetric(a):
    """Closed-form eigenvalues of a symmetric 3x3 matrix (trigonometric solution of the characteristic cubic)."""
    p1 = a[0][1] ** 2 + a[0][2] ** 2 + a[1][2] ** 2
    q = (a[0][0] + a[1][1] + a[2][2]) / 3
    p2 = (a[0][0] - q) ** 2 + (a[1][1] - q) ** 2 + (a[2][2] - q) ** 2 + 2 * p1
    if p2 == 0:
        return [q, q, q]
    p = math.sqrt(p2 / 6)
    b = [[(a[i][j] - (q if i == j else 0)) / p for j in range(3)] for i in range(3)]
    det = (b[0][0] * (b[1][1] * b[2][2] - b[1][2] * b[2][1]) - b[0][1] * (b[1][0] * b[2][2] - b[1][2] * b[2][0])
           + b[0][2] * (b[1][0] * b[2][1] - b[1][1] * b[2][0]))
    phi = math.acos(max(-1.0, min(1.0, det / 2))) / 3
    big = q + 2 * p * math.cos(phi)
    small = q + 2 * p * math.cos(phi + 2 * math.pi / 3)
    return sorted([small, 3 * q - big - small, big])


def rotational_constants(atoms, masses, factor):
    ia, ib, ic = principal_moments(atoms, masses)
    need(ia > 1e-6, 'Degenerate rotor')
    return dict(A=factor / ia, B=factor / ib, C=factor / ic)


def level(question):
    m = find(r'J_KaKc = (1_\d\d) ← 0_00', question, 'Transition not stated')
    need(m.group(1) in J1_LEVELS, 'Unsupported transition ' + m.group(1))
    return m.group(1)


def frequency(abc, label):
    x, y = J1_LEVELS[label]
    return abc[x] + abc[y]


def rotational_line(packet, key):
    q = packet['question']
    masses, factor = model(q)
    atoms = molecule(packet, key)
    label = level(q)
    abc = rotational_constants(atoms, masses, factor)
    return dict(judge_numeric(packet, key, frequency(abc, label)),
                parameters=dict(transition=label, constants_MHz={k: round(v, 4) for k, v in abc.items()}),
                method='Decimal centre of mass and inertia tensor; closed-form cubic eigenvalues; J=1 level table')


def isotopologue_design(packet, key):
    q = packet['question']
    masses, factor = model(q)
    deuterium = Decimal(find(r'deuterium, D (\d+\.\d+) u', q, 'Deuterium mass not stated').group(1))
    need('largest absolute shift' in q, 'Design objective not stated')
    atoms = molecule(packet, key)
    label = level(q)
    listed = [int(x) for x in re.findall(r'H(\d+)', find(r'hydrogen atoms ((?:H\d+(?:, )?)+) \(rows', q, 'Candidates not listed').group(1))]
    rows = {}
    for o in packet['options']:
        m = re.fullmatch(r'H(\d+) \(row (\d+)\)', o['value'])
        need(m is not None and m.group(1) == m.group(2), 'Option must name a hydrogen by its row')
        rows[o['label']] = int(m.group(2))
    need(sorted(rows.values()) == sorted(listed), 'Options differ from the listed candidates')
    need(all(1 <= r <= len(atoms) and atoms[r - 1][0] == 'H' for r in rows.values()), 'A candidate is not a hydrogen atom')
    parent = frequency(rotational_constants(atoms, masses, factor), label)
    shift = {}
    for l, r in rows.items():
        heavy = dict(masses, Dsub=deuterium)
        swapped = [('Dsub', p) if i == r - 1 else (e, p) for i, (e, p) in enumerate(atoms)]
        shift[l] = frequency(rotational_constants(swapped, heavy, factor), label) - parent
    ranked = sorted(shift, key=lambda l: -abs(shift[l]))
    first, second = abs(shift[ranked[0]]), abs(shift[ranked[1]])
    need(first >= RATIO * second and first - second >= MIN_MHZ, 'No clear largest shift')
    need(key['correct_label'] == ranked[0], 'Key label %s != recomputed %s' % (key['correct_label'], ranked[0]))
    return dict(label=ranked[0], parameters=dict(transition=label, parent_MHz=round(parent, 4),
                                                 shifts_MHz={l: round(v, 4) for l, v in shift.items()}),
                method='Decimal inertia tensor with the substituted mass; closed-form cubic eigenvalues')


CHECKERS = {'rotational_line': rotational_line, 'isotopologue_design': isotopologue_design}
