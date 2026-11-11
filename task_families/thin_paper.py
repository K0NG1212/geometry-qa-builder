"""Build pilot questions from CC BY numeric source cards; paired with independent checkers/thin_paper.py."""
import json
import math
from . import kit

VERSION = '0.1.0'
H, C, E = 6.62607015e-34, 299792458, 1.602176634e-19
DECIMALS = {'opal_fcc_111_spacing': 3, 'moire_triangular_cell_area': 2,
            'cholesteric_band_center': 1, 'vortex_gl_parameter': 4,
            'qdot_exciton_photon_energy': 4}
UNITS = {'opal_fcc_111_spacing': 'nm', 'moire_triangular_cell_area': 'nm²',
         'cholesteric_band_center': 'nm', 'vortex_gl_parameter': '',
         'qdot_exciton_photon_energy': 'eV'}


def compute(family, row):
    if family == 'opal_fcc_111_spacing':
        d = row['diameter_nm']
        truth = math.sqrt(2 / 3) * d
        wrong = {'diameter_as_spacing': d, 'lattice_constant_as_spacing': math.sqrt(2) * d,
                 'body_diagonal_as_spacing': math.sqrt(6) * d,
                 'simple_diagonal_half': d / math.sqrt(2), 'diameter_over_sqrt3': d / math.sqrt(3),
                 'radius_as_diameter': truth / 2}
        question = 'Sample %s: the attached card gives a measured SEM microsphere diameter. Under an ideal close-packed FCC model, calculate the (111) plane spacing d111 = sqrt(2/3) times that diameter, in nm. This is a model calculation, not a measured optical peak.' % row['id']
        scale = d
    elif family == 'moire_triangular_cell_area':
        p = row['period_nm']
        x = p * p
        truth = math.sqrt(3) * x / 2
        wrong = {'square_cell': x, 'parallelogram_without_half': math.sqrt(3) * x,
                 'two_square_cells': 2 * x, 'half_rectangle': x / 2,
                 'triangle_half_cell': math.sqrt(3) * x / 4, 'reciprocal_sqrt3': x / math.sqrt(3)}
        question = 'Sample %s: the attached card gives an approximate measured moiré period. Treat it as the basis-vector length of an ideal triangular lattice. Calculate its primitive-cell area A = sqrt(3) p² / 2, in nm²; do not treat the area as directly measured.' % row['id']
        scale = p
    elif family == 'cholesteric_band_center':
        lo, hi = row['lower_nm'], row['upper_nm']
        width = hi - lo
        if not 0 < width < lo:
            raise ValueError('Invalid measured reflection band')
        truth = (lo + hi) / 2
        wrong = {'upper_edge_as_center': hi, 'sum_edges_without_half': lo + hi,
                 'extend_upper_half_band': hi + width / 2, 'lower_edge_as_center': lo,
                 'bandwidth_as_center': width, 'extend_lower_half_band': lo - width / 2}
        question = 'Sample %s: the attached card gives measured lower and upper reflection-band edges. Define the band-center wavelength as their arithmetic midpoint and report it in nm.' % row['id']
        scale = truth
    elif family == 'vortex_gl_parameter':
        lam, xi = row['lambda_nm'], row['xi_nm']
        dl, dx = row['lambda_sigma_nm'], row['xi_sigma_nm']
        if not lam > dl > 0 or not xi > dx > 0:
            raise ValueError('Invalid fitted length and uncertainty')
        truth = lam / xi
        wrong = {'half_core_length': 2 * lam / xi, 'add_core_to_penetration': (lam + xi) / xi,
                 'upper_error_extremes': (lam + dl) / (xi - dx), 'double_core_length': lam / (2 * xi),
                 'subtract_core_from_penetration': (lam - xi) / xi,
                 'lower_error_extremes': (lam - dl) / (xi + dx)}
        question = 'Sample %s: the attached card gives author-fitted magnetic penetration length λ and coherence length ξ from SANS measurements. Using their central fitted values, calculate the dimensionless Ginzburg–Landau parameter κ = λ/ξ.' % row['id']
        scale = xi
    elif family == 'qdot_exciton_photon_energy':
        peak = row['peak_nm']
        truth = H * C / (peak * 1e-9 * E)
        wrong = {'half_wavelength': 2 * truth, 'h_omega_instead_hbar_omega': 2 * math.pi * truth,
                 'micrometre_as_nm': 1000 * truth, 'double_wavelength': truth / 2,
                 'hbar_nu_instead_h_nu': truth / (2 * math.pi), 'nm_as_micrometre': truth / 1000}
        question = 'Sample %s: the attached card gives the measured first excitonic absorption-peak wavelength λ in nm. Calculate the corresponding single-photon energy E = hc/λ in eV using h = 6.62607015×10⁻³⁴ J s, c = 299792458 m/s, and 1 eV = 1.602176634×10⁻¹⁹ J.' % row['id']
        scale = peak
    else:
        raise ValueError('Unknown thin-paper family')
    return truth, wrong, question, scale


def build(spec, root, seed):
    family = spec['family']
    raw = (root / 'docs' / spec['asset']).read_bytes()
    card = json.loads(raw)
    if card['kind'] != 'thin_paper_numeric_card' or card['family'] != family:
        raise ValueError('Wrong numeric source card')
    if spec['license'] != card['license'] or spec['source'] != card['source']:
        raise ValueError('Source or license mismatch')
    if spec['source_fact']['doi'] != card['doi']:
        raise ValueError('DOI mismatch')
    sample = spec.get('sample') or spec.get('material')
    if sample is None and family == 'moire_triangular_cell_area':
        sample = next((r['id'] for r in card['rows'] if r['period_nm'] == spec['period_nm']), None)
    if sample is None and family == 'vortex_gl_parameter':
        sample = card['rows'][0]['id']
    rows = [r for r in card['rows'] if r['id'] == sample]
    if len(rows) != 1 or not rows[0].get('location') or not rows[0].get('kind'):
        raise ValueError('Source sample or original locator missing')
    row = rows[0]
    for field in ('diameter_nm', 'period_nm', 'lower_nm', 'upper_nm', 'lambda_nm',
                  'lambda_sigma_nm', 'xi_nm', 'xi_sigma_nm', 'peak_nm'):
        if field in spec and spec[field] != row[field]:
            raise ValueError('Spec numeric value differs from source card: ' + field)
    truth, wrong, question, scale = compute(family, row)
    if sum(x > truth for x in wrong.values()) != 3 or sum(x < truth for x in wrong.values()) != 3:
        raise ValueError('Three high and three low misconceptions required')
    target = spec['target_position']
    low = [(k, v) for k, v in wrong.items() if v < truth]
    high = [(k, v) for k, v in wrong.items() if v > truth]
    selected = low[:target - 1] + high[:4 - target]
    decimals, unit = DECIMALS[family], UNITS[family]
    candidates = [dict(rule=k, shown=kit.display(v, decimals), reason=k) for k, v in selected]
    options, audit = kit.label_numeric(truth, candidates, decimals=decimals, unit=unit,
                                       seed=seed, context=spec['id'], correct_reason='Formula applied to the source row')
    step = 10 ** -decimals
    tol, sep = str(step / 2), str(step)
    label = kit.validate_numeric(options, truth, decimals=decimals, tolerance=tol,
                                 min_separation=sep, unit=unit)
    if label != 'ABCD'[target - 1]:
        raise ValueError('Chosen options do not meet target answer position')
    return dict(question=question, scope=spec['scope'],
                inputs=[dict(name=spec['asset'].rsplit('/', 1)[1], format='json', unit=unit,
                             text=raw.decode('utf-8'))],
                numeric=dict(value=kit.display(truth, decimals), unit=unit,
                             decimals=decimals, tolerance=tol),
                options=options, correct_label=label, option_audit=audit,
                excluded_candidates=[dict(rule=k, value=v, reason='unused signed misconception')
                                     for k, v in wrong.items() if k not in dict(selected)],
                rank=dict(target=target, achieved=target),
                checks=dict(source_card_matches=True, original_locator=row['location'],
                            source_value_kind=row['kind'], high_rules=3, low_rules=3),
                scales=dict(input_nm=scale, reasoning_nm=scale,
                            reasoning_definition='Characteristic measured length or optical wavelength used in the formula'),
                input_hashes={spec['asset']: kit.sha256(raw)})
