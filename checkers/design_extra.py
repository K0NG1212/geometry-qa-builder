"""Independent checkers for diffraction_design, disulfide_design and fret_design. No generation code is imported;
parameters (weights, wavelengths, targets, windows, R0) are read from the question and options."""
import cmath
import itertools
import math
import re
from .common import need, find, verify_hashes, judge_numeric
from .migrated import pdb_atoms, verbatim, dec_dist


def parse_table(text):
    lines = text.splitlines()
    a = float(find(r'cubic a = ([\d.]+) angstrom', lines[0], 'Cell edge missing').group(1))
    return a, [(r[0], [float(x) for x in r[1:]]) for r in (l.split() for l in lines[1:] if l.strip())]


def first_d(a, rows, weights):
    need({e for e, _ in rows} <= set(weights), 'Weights must cover the elements present')
    total = sum(weights[e] for e, _ in rows)
    best = None
    for h, k, l in itertools.product(range(6), repeat=3):
        if (h, k, l) == (0, 0, 0):
            continue
        f = abs(sum(weights[e] * cmath.exp(2j * math.pi * (h * x + k * y + l * z)) for e, (x, y, z) in rows)) / total
        g = h * h + k * k + l * l
        if f > 1e-6 and (best is None or g < best):
            best = g
    return a / math.sqrt(best)


def weights_of(text):
    return {k: int(v) for k, v in re.findall(r'([A-Z][a-z]?) = (\d+)', text)}


def tth(d, lam):
    return 2 * math.degrees(math.asin(lam / (2 * d)))


def closest(values, target):
    ranked = sorted(values, key=lambda k: abs(values[k] - target))
    need(abs(values[ranked[1]] - target) > abs(values[ranked[0]] - target) + 1e-9, 'Tie for closest candidate')
    return ranked[0]


def diffraction_design(packet, key):
    q = packet['question']
    verify_hashes(key)
    need('lowest-angle reflection with non-zero intensity' in q and 'atomic numbers as angle-independent weights' in q, 'Rule not stated')
    if 'four crystals' in q:
        lam = float(find(r'wavelength ([\d.]+) Å', q, 'Wavelength missing').group(1))
        target = float(find(r'closest to 2θ = ([\d.]+)°', q, 'Target missing').group(1))
        block = find(r'Weights: (.+?)\. For X-rays', q, 'Weights missing').group(1)
        per = {name.strip(): weights_of(w) for name, w in re.findall(r'([^;:]+?): ((?:[A-Z][a-z]? = \d+(?:, )?)+)', block)}
        values = {}
        for inp in packet['inputs']:
            short = [o['value'].split(' (')[0] for o in packet['options'] if o['value'].endswith('(%s)' % inp['name'])]
            need(len(short) == 1 and short[0].strip() in per, 'Option/file/weights mismatch for ' + inp['name'])
            a, rows = parse_table(inp['text'])
            values[inp['name']] = tth(first_d(a, rows, per[short[0].strip()]), lam)
        win = closest(values, target)
        hits = [o['label'] for o in packet['options'] if o['value'].endswith('(%s)' % win)]
    else:
        weights = weights_of(find(r'Weights: ([^.]+)\.', q, 'Weights missing').group(1))
        [inp] = packet['inputs']
        a, rows = parse_table(inp['text'])
        d = first_d(a, rows, weights)
        target = float(find(r'2θ = ([\d.]+)°', q, 'Target missing').group(1))
        if 'What wavelength' in q:
            return dict(judge_numeric(packet, key, 2 * d * math.sin(math.radians(target / 2))), parameters=dict(d_A=d),
                        method='own structure-factor search; Bragg law')
        values = {}
        for o in packet['options']:
            lam = float(find(r'λ = ([\d.]+) Å', o['value'], 'Option wavelength missing').group(1))
            values[o['label']] = tth(d, lam) if lam < 2 * d else float('inf')
        hits = [closest(values, target)]
    need(len(hits) == 1 and key['correct_label'] == hits[0], 'Key label disagrees with recomputed choice')
    return dict(label=hits[0], parameters=dict(values={k: round(v, 4) for k, v in values.items()}), method='own structure-factor search; Bragg law')


def pair_atoms(option, atoms, atom_names):
    m = re.fullmatch(r'([A-Z][a-z]{0,2})(\d+)–([A-Z][a-z]{0,2})(\d+)', option)
    need(m is not None, 'Option is not a residue pair')
    out = []
    for name in atom_names:
        pts = [atoms.get((name, m.group(1), int(m.group(2)))), atoms.get((name, m.group(3), int(m.group(4))))]
        need(all(pts), 'Atom %s missing for %s' % (name, option))
        out.append(float(dec_dist(*pts)))
    return out


def disulfide_design(packet, key):
    q = packet['question']
    ca = [float(x) for x in find(r'Cα–Cα distance between ([\d.]+) and ([\d.]+) Å', q, 'Cα window missing').groups()]
    cb = [float(x) for x in find(r'Cβ–Cβ distance between ([\d.]+) and ([\d.]+) Å', q, 'Cβ window missing').groups()]
    need('both inclusive' in q, 'Window convention missing')
    [inp] = packet['inputs']
    verbatim(inp['text'], key)
    atoms = pdb_atoms(inp['text'])
    ok = []
    for o in packet['options']:
        dca, dcb = pair_atoms(o['value'], atoms, ('CA', 'CB'))
        if ca[0] <= dca <= ca[1] and cb[0] <= dcb <= cb[1]:
            ok.append(o['label'])
    need(len(ok) == 1, '%d pairs meet both windows' % len(ok))
    need(key['correct_label'] == ok[0], 'Key label disagrees with recomputed choice')
    return dict(label=ok[0], parameters=dict(CA=ca, CB=cb), method='Decimal distances; stated windows')


def fret_design(packet, key):
    q = packet['question']
    r0 = float(find(r'R0 = ([\d.]+) nm', q, 'R0 missing').group(1))
    target = float(find(r'as close as possible to ([\d.]+)\.', q, 'Target missing').group(1))
    atom = find(r'point at the (\S+) atom', q, 'Dye atom missing').group(1)
    need('point-dipole Förster law' in q, 'Model not stated')
    [inp] = packet['inputs']
    verbatim(inp['text'], key)
    atoms = pdb_atoms(inp['text'])
    eff = {}
    for o in packet['options']:
        r = pair_atoms(o['value'], atoms, (atom,))[0] / 10
        eff[o['label']] = 1 / (1 + (r / r0) ** 6)
    win = closest(eff, target)
    need(key['correct_label'] == win, 'Key label disagrees with recomputed choice')
    return dict(label=win, parameters=dict(efficiency={k: round(v, 4) for k, v in eff.items()}, R0_nm=r0), method='Decimal distances; Förster law')


CHECKERS = {'diffraction_design': diffraction_design, 'disulfide_design': disulfide_design, 'fret_design': fret_design}
