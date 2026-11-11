"""Independent Decimal checks for five CC BY paper-value draft families.

No question-generation code is imported. Values come from the hashed student
attachment; formulas here are separate implementations of the published drafts.
"""
import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_UP, localcontext
from .common import need, verify_hashes

PI = Decimal('3.1415926535897932384626433832795028841971693993751')
H = Decimal('6.62607015e-34')
C = Decimal('299792458')
E = Decimal('1.602176634e-19')
UNITS = {'opal_fcc_111_spacing': 'nm', 'moire_triangular_cell_area': 'nm²',
         'cholesteric_band_center': 'nm', 'vortex_gl_parameter': '',
         'qdot_exciton_photon_energy': 'eV'}


def quantities(family, row):
    """Return truth and six signed misconception values using Decimal arithmetic."""
    d = lambda key: Decimal(str(row[key]))
    with localcontext() as ctx:
        ctx.prec = 45
        if family == 'opal_fcc_111_spacing':
            x = d('diameter_nm')
            truth = (Decimal(2) / 3).sqrt() * x
            wrong = [x, Decimal(2).sqrt() * x, Decimal(6).sqrt() * x,
                     x / Decimal(2).sqrt(), x / Decimal(3).sqrt(), truth / 2]
        elif family == 'moire_triangular_cell_area':
            square = d('period_nm') ** 2
            truth = Decimal(3).sqrt() * square / 2
            wrong = [square, Decimal(3).sqrt() * square, 2 * square,
                     square / 2, Decimal(3).sqrt() * square / 4, square / Decimal(3).sqrt()]
        elif family == 'cholesteric_band_center':
            low, high = d('lower_nm'), d('upper_nm')
            width = high - low
            need(0 < width < low, 'Reflection band outside validated data domain')
            truth = (low + high) / 2
            wrong = [high, low + high, high + width / 2,
                     low, width, low - width / 2]
        elif family == 'vortex_gl_parameter':
            lam, xi = d('lambda_nm'), d('xi_nm')
            dl, dx = d('lambda_sigma_nm'), d('xi_sigma_nm')
            need(lam > dl > 0 and xi > dx > 0, 'Fit uncertainties outside validated data domain')
            truth = lam / xi
            wrong = [2 * lam / xi, (lam + xi) / xi, (lam + dl) / (xi - dx),
                     lam / (2 * xi), (lam - xi) / xi, (lam - dl) / (xi + dx)]
        elif family == 'qdot_exciton_photon_energy':
            truth = H * C / (d('peak_nm') * Decimal('1e-9') * E)
            wrong = [2 * truth, 2 * PI * truth, 1000 * truth,
                     truth / 2, truth / (2 * PI), truth / 1000]
        else:
            need(False, 'Unknown thin-paper family: ' + family)
        need(sum(x > truth for x in wrong) == 3 and sum(x < truth for x in wrong) == 3,
             'The source row does not support three high and three low rules')
        return truth, wrong


def check(packet, key, family):
    paths = verify_hashes(key)
    relevant = [rel for rel in paths if rel == 'assets/families/thin-paper/' + family + '.json']
    need(len(relevant) == 1, 'Exactly one matching paper-value asset is required')
    rel = relevant[0]
    attached = [i for i in packet['inputs'] if i.get('name') == rel.rsplit('/', 1)[1]]
    need(len(attached) == 1, 'The hashed numeric source card must be attached')
    text = attached[0]['text']
    need(hashlib.sha256(text.encode('utf-8')).hexdigest() == key['input_hashes'][rel],
         'Attached numeric source card differs from hashed asset')
    card = json.loads(text)
    need(card['kind'] == 'thin_paper_numeric_card' and card['family'] == family,
         'Attached source card has wrong family')
    need(key['license'] == card['license'] and card['source'] in key['source'],
         'Source URL or license differs from attached card')
    match = re.search(r'\bSample ([A-Za-z0-9_-]+)\b', packet['question'])
    need(match is not None, 'Question must identify its source sample')
    rows = [r for r in card['rows'] if r['id'] == match.group(1)]
    need(len(rows) == 1 and rows[0].get('location') and rows[0].get('kind'),
         'Sample or original source locator missing')
    truth, wrong = quantities(family, rows[0])
    dec = key['numeric_answer']['decimals']
    quant = Decimal(1).scaleb(-dec)
    shown = lambda x: x.quantize(quant, rounding=ROUND_HALF_UP)
    options = packet['options']
    need([o['label'] for o in options] == list('ABCD'), 'Options must be A through D')
    need(all(o.get('unit') == UNITS[family] for o in options), 'Option unit differs from family unit')
    values = [Decimal(o['value']) for o in options]
    need(len(set(values)) == 4 and values == sorted(values), 'Options must be distinct and ascending')
    correct = shown(truth)
    hits = [o['label'] for o, v in zip(options, values) if v == correct]
    need(len(hits) == 1 and hits[0] == key['correct_label'], 'Recomputed answer disagrees with key')
    remaining = [shown(v) for v in wrong]
    need(all(v == correct or v in remaining for v in values), 'An option is not a registered misconception value')
    need(all(v > 0 for v in values), 'All displayed quantities must be positive')
    return dict(label=hits[0], recomputed=str(correct), source_location=rows[0]['location'],
                method='Independent Decimal arithmetic from attached source row')


def opal_fcc_111_spacing(packet, key):
    return check(packet, key, 'opal_fcc_111_spacing')


def moire_triangular_cell_area(packet, key):
    return check(packet, key, 'moire_triangular_cell_area')


def cholesteric_band_center(packet, key):
    return check(packet, key, 'cholesteric_band_center')


def vortex_gl_parameter(packet, key):
    return check(packet, key, 'vortex_gl_parameter')


def qdot_exciton_photon_energy(packet, key):
    return check(packet, key, 'qdot_exciton_photon_energy')


CHECKERS = {name: globals()[name] for name in UNITS}
