"""Shared mechanics for reusable task families: parsing, geometry kernels, rounding,
distractor selection, four-option validation and scoring. No model/API calls.

Families supply the science (what is asked, how the answer is computed, which
error mechanisms produce distractors); this module supplies the common checks so
that every family is validated the same way.
"""
import hashlib
import itertools
import math
from decimal import Decimal, ROUND_HALF_UP

LABELS = 'ABCD'
ELEMENTS = {'H', 'C', 'N', 'O', 'S', 'Cl', 'P', 'F', 'Zn', 'Si', 'Na', 'Mg', 'Cs', 'Br', 'I'}
COVALENT = {'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'S': 1.05, 'Cl': 1.02, 'P': 1.07,
            'F': 0.57, 'Zn': 1.22, 'Si': 1.11, 'Br': 1.20, 'I': 1.39}


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode('utf-8')).hexdigest()


def parse_xyz(text, max_atoms=5000):
    """Strict XYZ: count line, comment line, exactly count rows of element x y z."""
    lines = text.splitlines()
    if len(lines) < 3:
        raise ValueError('XYZ requires count, comment and atom rows')
    try:
        n = int(lines[0].strip())
    except ValueError:
        raise ValueError('Invalid XYZ count')
    rows = [line.split() for line in lines[2:] if line.strip()]
    if n < 1 or n > max_atoms or len(rows) != n:
        raise ValueError('Atom count does not match rows')
    elements, points = [], []
    for row in rows:
        symbol = row[0].capitalize() if len(row) == 4 else ''   # e.g. PDB-style 'CL' -> 'Cl'
        if symbol not in ELEMENTS:
            raise ValueError('Expected known element and three coordinates')
        point = tuple(float(v) for v in row[1:])
        if not all(math.isfinite(v) for v in point):
            raise ValueError('Nonfinite coordinate')
        elements.append(symbol)
        points.append(point)
    return elements, points


def xyz_text(elements, points, comment):
    rows = ['%s %.8f %.8f %.8f' % (e, *p) for e, p in zip(elements, points)]
    return '\n'.join([str(len(rows)), comment] + rows) + '\n'


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def dot(a, b):
    return math.fsum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def norm(a):
    return math.sqrt(dot(a, a))


def angle_acos(a, vertex, b):
    u, v = sub(a, vertex), sub(b, vertex)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot(u, v) / (norm(u) * norm(v))))))


def angle_atan2(a, vertex, b):
    """Second implementation (atan2 of |u x v| and u.v), used as a cross-check."""
    u, v = sub(a, vertex), sub(b, vertex)
    return math.degrees(math.atan2(norm(cross(u, v)), dot(u, v)))


def dihedral_normals(p0, p1, p2, p3):
    """IUPAC signed torsion via plane normals, range (-180, 180]."""
    b1, b2, b3 = sub(p1, p0), sub(p2, p1), sub(p3, p2)
    n1, n2 = cross(b1, b2), cross(b2, b3)
    return math.degrees(math.atan2(norm(b2) * dot(b1, n2), dot(n1, n2)))


def dihedral_projection(p0, p1, p2, p3):
    """Second implementation: project outer bonds onto the plane normal to the axis."""
    b0, b1, b2 = sub(p0, p1), sub(p2, p1), sub(p3, p2)
    axis = [x / norm(b1) for x in b1]
    v = [x - dot(b0, axis) * y for x, y in zip(b0, axis)]
    w = [x - dot(b2, axis) * y for x, y in zip(b2, axis)]
    return math.degrees(math.atan2(dot(cross(axis, v), w), dot(v, w)))


def bond_graph(elements, points, scale=1.2):
    """Covalent-radius connectivity; an operational rule, stated in audits."""
    edges = set()
    for i, j in itertools.combinations(range(len(points)), 2):
        limit = scale * (COVALENT[elements[i]] + COVALENT[elements[j]])
        if math.dist(points[i], points[j]) <= limit:
            edges.add((i, j))
    return edges


def neighbors(edges, i):
    return sorted({b if a == i else a for a, b in edges if i in (a, b)})


def dmax(points):
    return max((math.dist(a, b) for a, b in itertools.combinations(points, 2)), default=0.0)


def display(value, decimals):
    quantum = Decimal(1).scaleb(-decimals)
    return str(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def digest(*parts):
    return hashlib.sha256('|'.join(map(str, parts)).encode('utf-8')).digest()


def ordered(items, seed, context, key=lambda x: x[0]):
    """Version-independent deterministic permutation keyed by seed and context."""
    return sorted(items, key=lambda x: digest(seed, context, key(x)))


def target_rank(seed, context):
    return 1 + digest(seed, context, 'rank')[0] % 4


def gap(a, b, period=None):
    """Absolute difference; for periodic quantities (torsions) the circular distance."""
    d = abs(a - b)
    if period is not None:
        period = Decimal(str(period))
        d = min(d % period, period - d % period)
    return d


def choose_numeric(correct, candidates, *, decimals, tolerance, min_separation, seed, context,
                   lower=None, upper=None, period=None, target=None, distractor_separation=None):
    """Pick three misconception distractors.

    candidates: dicts with rule, value, reason and plausibility (1 low .. 3 high).
    Among all valid triples (pairwise separated by more than min_separation and
    from the correct value) prefer the one whose correct-answer numeric rank equals
    a target rank (assigned per batch by the engine, else seeded), so that "always
    pick largest/smallest" does not work, then the most plausible mechanisms.
    min_separation applies to the correct value; distractor_separation (default the
    same) only keeps wrong options visibly distinct from each other.
    Returns (chosen, rejected, target, achieved rank).
    """
    tolerance, min_separation = Decimal(str(tolerance)), Decimal(str(min_separation))
    between = Decimal(str(distractor_separation)) if distractor_separation is not None else min_separation
    if between <= 2 * tolerance:
        raise ValueError('Distractors must not share tolerance intervals')
    if min_separation < 2 * tolerance:
        raise ValueError('Separation must exceed both tolerance intervals')
    right = Decimal(display(correct, decimals))
    valid, rejected = [], []
    for c in candidates:
        value = c['value']
        if value is None or not math.isfinite(float(value)):
            rejected.append(dict(rule=c['rule'], value=None, reason='not defined for this input'))
            continue
        shown = Decimal(display(value, decimals))
        if (lower is not None and shown < Decimal(str(lower))) or (upper is not None and shown > Decimal(str(upper))):
            rejected.append(dict(rule=c['rule'], value=str(shown), reason='outside the defined value range'))
        elif gap(shown, right, period) <= min_separation:
            rejected.append(dict(rule=c['rule'], value=str(shown), reason='too close to the correct value'))
        else:
            valid.append(dict(c, shown=shown))
    best = None
    goal = target if target is not None else target_rank(seed, context)
    for combo in itertools.combinations(valid, 3):
        values = [x['shown'] for x in combo]
        if any(gap(a, b, period) <= between for a, b in itertools.combinations(values, 2)):
            continue
        rank = 1 + sum(v < right for v in values)
        weak = sum(x.get('plausibility', 1) <= 1 for x in combo)   # easily dismissed option: worse than any rank miss
        mirror = right != 0 and any(x['shown'] == -right for x in combo)   # a '+/-' pair cue
        score = (abs(rank - goal) + 4 * weak + int(mirror), -sum(x.get('plausibility', 1) for x in combo),
                 digest(seed, context, *sorted(x['rule'] for x in combo)))
        if best is None or score < best[0]:
            best = (score, combo, rank)
    if best is None:
        raise ValueError('Fewer than three separated misconception distractors')
    chosen = list(best[1])
    names = {x['rule'] for x in chosen}
    for x in valid:
        if x['rule'] not in names:
            rejected.append(dict(rule=x['rule'], value=str(x['shown']), reason='valid but not selected (rank balance / plausibility)'))
    return chosen, rejected, goal, best[2]


def label_numeric(correct, chosen, *, decimals, unit, seed, context, correct_reason):
    """Options in ascending numeric order, so label position equals numeric rank;
    the balanced target rank therefore also balances answer positions."""
    entries = [('correct', display(correct, decimals), correct_reason)] +               [(x['rule'], str(x['shown']), x['reason']) for x in chosen]
    permutation = sorted(entries, key=lambda e: Decimal(e[1]))
    options = [{'label': l, 'value': v, 'unit': unit} for l, (_, v, _) in zip(LABELS, permutation)]
    audit = [{'label': l, 'rule': r, 'value': v, 'reason': why, 'is_correct': r == 'correct',
              'absolute_error': str(abs(Decimal(v) - Decimal(str(correct))))}
             for l, (r, v, why) in zip(LABELS, permutation)]
    return options, audit


def place(correct, others, target, seed, context, key):
    """Categorical options: others in seeded order, correct inserted at the target index."""
    rest = ordered(list(others), seed, context + '/labels', key=key)
    index = (target - 1) if target is not None else target_rank(seed, context) - 1
    return rest[:index] + [correct] + rest[index:]


def validate_numeric(options, expected, *, decimals, tolerance, min_separation, unit, period=None,
                     distractor_separation=None):
    if len(options) != 4 or [o['label'] for o in options] != list(LABELS):
        raise ValueError('Exactly A/B/C/D required')
    values = [Decimal(o['value']) for o in options]
    if any(o['unit'] != unit or not v.is_finite() or o['value'] != display(v, decimals) for o, v in zip(options, values)):
        raise ValueError('Invalid unit, value or precision')
    between = Decimal(str(distractor_separation if distractor_separation is not None else min_separation))
    if any(gap(a, b, period) <= between for a, b in itertools.combinations(values, 2)):
        raise ValueError('Options not separated')
    hits = [o['label'] for o, v in zip(options, values) if gap(v, Decimal(str(expected)), period) <= Decimal(str(tolerance))]
    if len(hits) != 1:
        raise ValueError('Not exactly one correct option')
    right = values[[o['label'] for o in options].index(hits[0])]
    if any(gap(v, right, period) <= Decimal(str(min_separation)) for v in values if v is not right):
        raise ValueError('A distractor is too close to the correct value')
    return hits[0]


def validate_verdicts(options, verdicts, key=lambda o: o['value']):
    """Categorical options: all four verified by the family checker, exactly one true."""
    if len(options) != 4 or [o['label'] for o in options] != list(LABELS):
        raise ValueError('Exactly A/B/C/D required')
    if len({repr(key(o)) for o in options}) != 4:
        raise ValueError('Duplicate options')
    if len(verdicts) != 4 or any(v not in (True, False) for v in verdicts):
        raise ValueError('Every option needs a verified verdict')
    hits = [o['label'] for o, v in zip(options, verdicts) if v]
    if len(hits) != 1:
        raise ValueError('Not exactly one correct option')
    return hits[0]


def score_choice(response, correct):
    if correct not in LABELS or len(correct) != 1:
        raise ValueError('Invalid answer key')
    return isinstance(response, str) and response.strip().upper() == correct


def score_numeric(response, expected, tolerance, unit):
    if not isinstance(response, dict) or set(response) != {'value', 'unit'}:
        return False
    value = response['value']
    if type(value) not in (int, float) or response['unit'] != unit or not math.isfinite(value):
        return False
    return abs(Decimal(str(value)) - Decimal(str(expected))) <= Decimal(str(tolerance))


def mirror_pair_cue(option_values, correct_label):
    """True when the correct value's negation is also an option (a test-wise cue)."""
    values = dict(option_values)
    right = Decimal(values[correct_label])
    return right != 0 and any(Decimal(v) == -right for l, v in option_values if l != correct_label)


def rank_shortcuts(option_values, correct_label):
    """Option-only baselines: which label would 'largest', 'smallest', 'second' pick."""
    order = sorted(option_values, key=lambda x: Decimal(x[1]))
    picks = {'always_smallest': order[0][0], 'always_second': order[1][0],
             'always_third': order[2][0], 'always_largest': order[3][0]}
    return {k: v == correct_label for k, v in picks.items()}
