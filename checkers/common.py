"""Shared helpers for independent answer checkers.

Independence rule: nothing under checkers/ imports the question-generation code
(task_families, family_engine, template_engine, choice_engine or tools). A checker
sees only what the tested model sees (question text, attached inputs, options) plus
the answer key, and recomputes with its own implementation. Provenance checks may
read the public source asset named in the answer key and verify its SHA-256.
"""
import hashlib
import math
import re
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0'
LABELS = ['A', 'B', 'C', 'D']
# Answer-key vocabulary that must never appear in a student packet.
FORBIDDEN_KEYS = {'correct_label', 'is_correct', 'option_audit', 'reason', 'source_id', 'numeric_answer',
                  'explanation', 'excluded_candidates', 'rank', 'checks'}


class CheckError(Exception):
    """A check that fails; the message is reported verbatim."""


def need(condition, message):
    if not condition:
        raise CheckError(message)


def find(pattern, text, message, flags=0):
    match = re.search(pattern, text, flags)
    need(match is not None, message)
    return match


def read_xyz(text):
    """Returns [(element, (Decimal x, y, z))]; strict count and row format."""
    lines = text.splitlines()
    need(len(lines) >= 3 and lines[0].strip().isdigit(), 'XYZ header invalid')
    rows = [line.split() for line in lines[2:] if line.strip()]
    need(len(rows) == int(lines[0]), 'XYZ atom count does not match rows')
    atoms = []
    for row in rows:
        need(len(row) == 4 and row[0].isalpha(), 'XYZ row must be element x y z')
        coords = tuple(Decimal(v) for v in row[1:])
        need(all(c.is_finite() for c in coords), 'Nonfinite coordinate')
        atoms.append((row[0].capitalize(), coords))
    return atoms


def dist(p, q):
    with localcontext() as ctx:
        ctx.prec = 40
        return sum((a - b) ** 2 for a, b in zip(p, q)).sqrt()


def vec(p, q):
    """q - p as floats."""
    return [float(b) - float(a) for a, b in zip(p, q)]


def dot(u, v):
    return math.fsum(a * b for a, b in zip(u, v))


def cross(u, v):
    return [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]


def rounded(value, decimals):
    return Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def sha256_file(rel):
    path = (ROOT / 'docs' / rel).resolve()
    need(path.is_relative_to((ROOT / 'docs/assets').resolve()), 'Evidence asset outside docs/assets')
    need(path.exists(), 'Evidence asset missing: ' + rel)
    return hashlib.sha256(path.read_bytes()).hexdigest(), path


def verify_hashes(key):
    """Every reviewer-side asset named in the key must match its recorded SHA-256."""
    paths = {}
    for rel, digest in key['input_hashes'].items():
        actual, path = sha256_file(rel)
        need(actual == digest, 'Asset hash mismatch: ' + rel)
        paths[rel] = path
    return paths


def packet_shape(packet):
    need([o['label'] for o in packet['options']] == LABELS, 'Options must be exactly A, B, C, D')
    need(len({o['value'] for o in packet['options']}) == 4, 'Duplicate option values')
    leaked = FORBIDDEN_KEYS & _keys(packet)
    need(not leaked, 'Answer-key fields in student packet: ' + ', '.join(sorted(leaked)))


def _keys(obj):
    if isinstance(obj, dict):
        return set(obj) | set().union(*(_keys(v) for v in obj.values()))
    if isinstance(obj, list):
        return set().union(*(_keys(v) for v in obj)) if obj else set()
    return set()


def gap(a, b, period=None):
    d = abs(a - b)
    if period is not None:
        d = min(d % period, period - d % period)
    return d


def judge_numeric(packet, key, value, period=None):
    """Recomputed value vs. options and key: exactly one option equals the rounded value,
    the other three lie outside the tolerance, and key label / numeric key agree."""
    numeric = key['numeric_answer']
    decimals, tol = numeric['decimals'], Decimal(numeric['tolerance'])
    expected = rounded(value, decimals)
    exact = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
    units = {o.get('unit') for o in packet['options']}
    need(units == {numeric['unit']}, 'Option units differ from the answer unit')
    for o in packet['options']:
        need(re.fullmatch(r'-?\d+\.\d{%d}' % decimals, o['value']) is not None,
             'Option %s not shown with %d decimals' % (o['label'], decimals))
    hits = [o['label'] for o in packet['options'] if gap(Decimal(o['value']), exact, period) <= tol]
    need(len(hits) == 1, 'Recomputed value matches %d options (need exactly 1)' % len(hits))
    label = hits[0]
    shown = next(o['value'] for o in packet['options'] if o['label'] == label)
    need(Decimal(shown) == expected or (period and gap(Decimal(shown), expected, period) == 0),
         'Matching option %s is not the rounded recomputed value %s' % (shown, expected))
    need(Decimal(numeric['value']) == expected, 'Numeric key %s != recomputed %s' % (numeric['value'], expected))
    need(key['correct_label'] == label, 'Key label %s != recomputed label %s' % (key['correct_label'], label))
    nearest = min(gap(Decimal(o['value']), exact, period) for o in packet['options'] if o['label'] != label)
    q = Decimal('1e-10')
    return dict(recomputed=str(exact.quantize(q)), rounded=str(expected), label=label,
                nearest_distractor_gap=str(nearest.quantize(q)))
