"""Independent checkers for hbond_geometry and hbond_criteria. No generation code is imported.

Atom rows, the asked quantity and the criteria are read from the question; distances use Decimal arithmetic and the
angle uses the law of cosines (the generator uses vector dot products). Bonding is checked with the checker's own
covalent radii; attached XYZ files must equal the hashed source assets.
"""
import math
import re
from decimal import localcontext
from .common import need, find, read_xyz, verify_hashes, judge_numeric, dist

RADII = {'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'S': 1.05, 'F': 0.57}
CONTACT = re.compile(r'([A-Z][a-z]?)(\d+)–([A-Z][a-z]?)(\d+)···([A-Z][a-z]?)(\d+)')


def bonded(a, b):
    return float(dist(a[1], b[1])) <= 1.25 * (RADII[a[0]] + RADII[b[0]])


def geometry(atoms, d, h, a):
    D, H, A = atoms[d - 1], atoms[h - 1], atoms[a - 1]
    need(H[0] == 'H' and D[0] in ('N', 'O') and A[0] in ('N', 'O', 'F'), 'Contact atoms have the wrong elements')
    need(bonded(D, H), 'Donor and hydrogen are not bonded')
    need(not bonded(H, A), 'Hydrogen is bonded to the acceptor')
    dh, ha, da = dist(D[1], H[1]), dist(H[1], A[1]), dist(D[1], A[1])
    with localcontext() as ctx:
        ctx.prec = 40
        cos = (dh * dh + ha * ha - da * da) / (2 * dh * ha)
    return dict(da=da, ha=ha, angle=math.degrees(math.acos(max(-1.0, min(1.0, float(cos))))))


def attached(packet, paths):
    sources = {p.read_bytes().decode('utf-8-sig') for p in paths.values()}
    for item in packet['inputs']:
        need(item['text'] in sources, 'Attached file %s differs from the source assets' % item['name'])


def hbond_geometry(packet, key):
    q = packet['question']
    rows = find(r'\(rows (\d+), (\d+) and (\d+), counted', q, 'Contact rows not stated')
    d, h, a = (int(x) for x in rows.groups())
    attached(packet, verify_hashes(key))
    [item] = packet['inputs']
    atoms = read_xyz(item['text'])
    g = geometry(atoms, d, h, a)
    if 'donor–acceptor distance' in q:
        value, what = g['da'], 'da'
    elif 'hydrogen–acceptor distance' in q:
        value, what = g['ha'], 'ha'
    else:
        need('angle at the hydrogen' in q, 'Asked quantity not recognised')
        value, what = g['angle'], 'angle'
    return dict(judge_numeric(packet, key, value), parameters=dict(rows=[d, h, a], quantity=what),
                method='Decimal distances; law of cosines; own covalent-radius bonding check')


def hbond_criteria(packet, key):
    q = packet['question']
    crit = find(r'H···A distance ≤ ([\d.]+) Å and D–H···A angle ≥ ([\d.]+)°', q, 'Criteria not stated')
    dmax, amin = float(crit.group(1)), float(crit.group(2))
    attached(packet, verify_hashes(key))
    files = {m.group(1): m.group(2) for m in re.finditer(r'conformer (\w+) = (conformer_\w+\.xyz)', q)}
    texts = {i['name']: i['text'] for i in packet['inputs']}
    verdicts = {}
    for o in packet['options']:
        m = CONTACT.search(o['value'])
        conf = find(r'in conformer (\w+)$', o['value'], 'Option does not name a conformer').group(1)
        need(conf in files and files[conf] in texts, 'Option names an unknown conformer')
        atoms = read_xyz(texts[files[conf]])
        d, h, a = int(m.group(2)), int(m.group(4)), int(m.group(6))
        need((atoms[d - 1][0], atoms[h - 1][0], atoms[a - 1][0]) == (m.group(1), m.group(3), m.group(5)), 'Option atoms do not match the file')
        g = geometry(atoms, d, h, a)
        verdicts[o['label']] = (float(g['ha']) <= dmax and g['angle'] >= amin, round(float(g['ha']), 4), round(g['angle'], 2))
    hits = [l for l, v in verdicts.items() if v[0]]
    need(len(hits) == 1, 'Exactly one option must meet both criteria (found %d)' % len(hits))
    need(key['correct_label'] == hits[0], 'Key label %s != recomputed %s' % (key['correct_label'], hits[0]))
    return dict(label=hits[0], parameters=dict(ha_max=dmax, angle_min=amin, verdicts=verdicts),
                method='Decimal distances; law of cosines; criteria read from the question')


CHECKERS = {'hbond_geometry': hbond_geometry, 'hbond_criteria': hbond_criteria}
