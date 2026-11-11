"""Transcribe the five CC BY paper rows audited in night-2026-11-07 into reviewable numeric assets.

The values and their original locations are transcribed from the dated audit notes. This
script publishes numbers and locators only; it does not download or redistribute papers.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/families/thin-paper'
DATA = {
    'opal_fcc_111_spacing': dict(doi='10.3390/polym13132171', license='CC BY',
        paper='Sánchez et al., Polymers 13, 2171 (2021)',
        notes='SEM diameters are measured; ideal FCC (111) spacing is calculated by this benchmark, not a measured stop-band.',
        rows=[dict(id='PMMA-7', diameter_nm=323.0, diameter_uncertainty_nm=9.0, location='Table 1, Davg', kind='SEM measured'),
              dict(id='PMMA-8', diameter_nm=311.0, diameter_uncertainty_nm=8.1, location='Table 1, Davg', kind='SEM measured'),
              dict(id='PMMA-9', diameter_nm=306.0, diameter_uncertainty_nm=11.0, location='Table 1, Davg', kind='SEM measured')]),
    'moire_triangular_cell_area': dict(doi='10.1038/s41598-021-04030-z', license='CC BY 4.0',
        paper='In-situ twistable bilayer graphene, Scientific Reports (2022)',
        notes='SNOM periods are approximate measured values; ideal triangular-cell area is calculated by this benchmark.',
        rows=[dict(id='Fig4c', period_nm=25.0, approximate=True, location='Results, Small-range fine-tuning; Figure 4c', kind='SNOM measured approximate'),
              dict(id='Fig4d', period_nm=45.0, approximate=True, location='Results, Small-range fine-tuning; Figure 4d', kind='SNOM measured approximate'),
              dict(id='Fig4e', period_nm=170.0, approximate=True, location='Results, Small-range fine-tuning; Figure 4e', kind='SNOM measured approximate'),
              dict(id='Fig4f', period_nm=250.0, approximate=True, location='Results, Small-range fine-tuning; Figure 4f', kind='SNOM measured approximate')]),
    'cholesteric_band_center': dict(doi='10.3390/ma11010005', license='CC BY 4.0',
        paper='Ortega et al., Materials 11, 5 (2018)',
        notes='Reflection band edges are measured; the arithmetic center is calculated by this benchmark. Pitch is not used.',
        rows=[dict(id='DCM', lower_nm=533, upper_nm=605, location='Section 3.1, Table 3', kind='measured reflection band edges'),
              dict(id='PM', lower_nm=519, upper_nm=590, location='Section 3.1, Table 3', kind='measured reflection band edges'),
              dict(id='passive_mirror', lower_nm=564, upper_nm=642, location='Section 3.1, Table 3', kind='measured reflection band edges')]),
    'vortex_gl_parameter': dict(doi='10.1038/s41467-024-50856-2', license='CC BY 4.0',
        paper='Xie et al., Nature Communications (2024)',
        notes='Lambda and xi are author-fit outputs from SANS data, not direct microscopy measurements; kappa is calculated here.',
        rows=[dict(id='CsVTaSb', lambda_nm=113.7, lambda_sigma_nm=4.8, xi_nm=14.5, xi_sigma_nm=0.6,
                   location='Results, Form factor field dependence; Figure 3b and equation (3)', kind='author fit to measured SANS data')]),
    'qdot_exciton_photon_energy': dict(doi='10.1155/2012/952610', license='CC BY',
        paper='Kashyout et al., International Journal of Photoenergy (2012)',
        notes='First-exciton absorption peaks are measured; photon energy is calculated from exact SI constants. S4 is omitted because body text 506 nm conflicts with Table 4 505 nm.',
        rows=[dict(id='S1', peak_nm=577.0, location='Section 3.3, Figure 7 and Table 4', kind='measured absorption peak'),
              dict(id='S2', peak_nm=543.0, location='Section 3.3, Figure 7 and Table 4', kind='measured absorption peak'),
              dict(id='S3', peak_nm=530.0, location='Section 3.3, Figure 7 and Table 4', kind='measured absorption peak')]),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = dict(kind='thin_paper_sources', built_on='2026-11-07',
                 method='Transcribed numeric values and exact original locations from night-2026-11-07 audit notes; L1 checks fidelity to the papers.',
                 files={})
    for family, paper in DATA.items():
        if not paper['doi'] or not paper['license'] or not paper['rows']:
            raise ValueError('Missing source provenance for ' + family)
        if len({row['id'] for row in paper['rows']}) != len(paper['rows']):
            raise ValueError('Duplicate sample identifier for ' + family)
        if any(not row.get('location') or not row.get('kind') for row in paper['rows']):
            raise ValueError('Every numeric row needs a source location and measurement kind: ' + family)
        card = dict(kind='thin_paper_numeric_card', family=family, doi=paper['doi'],
                    source='https://doi.org/' + paper['doi'], license=paper['license'],
                    paper=paper['paper'], notes=paper['notes'], rows=paper['rows'])
        name = family + '.json'
        blob = (json.dumps(card, ensure_ascii=False, indent=1) + '\n').encode('utf-8')
        (OUT / name).write_bytes(blob)
        index['files'][name] = dict(doi=paper['doi'], url=card['source'], license=paper['license'],
                                    sha256=hashlib.sha256(blob).hexdigest(), rows=len(paper['rows']))
    (OUT / 'sources.json').write_text(json.dumps(index, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('Built %d cards, %d numeric source rows' % (len(DATA), sum(len(p['rows']) for p in DATA.values())))


if __name__ == '__main__':
    main()
