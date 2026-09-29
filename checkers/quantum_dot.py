"""Independent checker for the CdSe quantum-dot families (quantum, 1-10 nm).
No generation code is imported. The sizing polynomial and extinction law are read from the question text;
the diameter is the largest atom-atom distance (own chunked search + Decimal on the winning pair); the peak
is the real root of the quartic in the stated range (numpy.roots, not bisection).
"""
import math
import re
import numpy as np
from .common import need, find, read_xyz, verify_hashes, judge_numeric
from .migrated import dec_dist


def same_as_asset(packet, key):
    by_name = {p.name: p for p in verify_hashes(key).values()}
    for inp in packet['inputs']:
        need(inp['name'] in by_name and by_name[inp['name']].read_bytes() == inp['text'].encode('utf-8'), 'Input differs: ' + inp['name'])


def curve(q):
    m = find(r'D = ([\d.e-]+)·λ⁴ − ([\d.e-]+)·λ³ \+ ([\d.e-]+)·λ² − ([\d.]+)·λ \+ ([\d.]+)', q, 'Sizing polynomial not stated')
    c = [float(m.group(1)), -float(m.group(2)), float(m.group(3)), -float(m.group(4)), float(m.group(5))]
    lo, hi = (float(x) for x in find(r'valid for (\d+)–(\d+) nm', q, 'Validity range not stated').groups())
    e = find(r'ε = (\d+)·D\^([\d.]+)', q, 'Extinction law not stated')
    need('largest distance between any two atoms' in q, 'Size definition not stated')
    return c, lo, hi, float(e.group(1)), float(e.group(2))


def diameter(text):
    a = np.asarray([[float(v) for v in p] for _, p in read_xyz(text)])
    best, pair = -1.0, None
    for i in range(0, len(a), 400):
        d2 = ((a[i:i + 400, None, :] - a[None, :, :]) ** 2).sum(axis=2)
        k = int(d2.argmax())
        if d2.flat[k] > best:
            best, pair = float(d2.flat[k]), (i + k // len(a), k % len(a))
    return float(dec_dist(a[pair[0]].tolist(), a[pair[1]].tolist())) / 10


def peak(c, lo, hi, d):
    roots = [float(r.real) for r in np.roots([c[0], c[1], c[2], c[3], c[4] - d]) if abs(r.imag) < 1e-9 and lo <= r.real <= hi]
    need(len(roots) == 1, 'Sizing curve has %d roots in range' % len(roots))
    return roots[0]


def qdot_quantity(packet, key):
    same_as_asset(packet, key)
    q = packet['question']
    c, lo, hi, e0, ex = curve(q)
    d = diameter(packet['inputs'][0]['text'])
    if 'first excitonic absorption peak?' in q:
        value = peak(c, lo, hi, d)
    elif 'molar extinction coefficient' in q:
        value = e0 * d ** ex / 1e5
    else:
        a = float(find(r'absorbance of ([\d.]+) at the first excitonic peak', q, 'Absorbance missing').group(1))
        l = float(find(r'in a ([\d.]+) cm cuvette', q, 'Path length missing').group(1))
        need('µM' in q, 'Unit missing')
        value = a / (e0 * d ** ex * l) * 1e6
    return dict(judge_numeric(packet, key, value), parameters=dict(D_nm=d), method='Decimal Dmax; quartic roots')


def qdot_design(packet, key):
    same_as_asset(packet, key)
    q = packet['question']
    c, lo, hi, e0, ex = curve(q)
    d = {inp['name']: diameter(inp['text']) for inp in packet['inputs']}
    lam = {k: peak(c, lo, hi, v) for k, v in d.items()}
    close = re.search(r'peak is closest to ([\d.]+) nm', q)
    beyond = re.search(r'smallest particle whose first excitonic absorption peak lies at or beyond ([\d.]+) nm', q)
    need((close is None) != (beyond is None), 'Design goal not stated exactly once')
    if close:
        t = float(close.group(1))
        ranked = sorted(lam, key=lambda k: abs(lam[k] - t))
        need(abs(lam[ranked[1]] - t) > abs(lam[ranked[0]] - t) + 1e-6, 'Tie')
        winner = ranked[0]
    else:
        t = float(beyond.group(1))
        ok = [k for k in lam if lam[k] >= t]
        need(ok, 'No candidate meets the target')
        winner = min(ok, key=lambda k: d[k])
    hits = [o['label'] for o in packet['options'] if o['value'] == winner]
    need(len(hits) == 1 and all(o['value'] in lam for o in packet['options']), 'Options must be the supplied file names')
    need(key['correct_label'] == hits[0], 'Key label disagrees with recomputed choice')
    return dict(label=hits[0], parameters=dict(D_nm=d, peak_nm=lam), method='per-file Dmax; quartic roots; goal rule')


CHECKERS = {'qdot_optics': qdot_quantity, 'qdot_design': qdot_design}
