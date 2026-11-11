"""Cross-check draft float answers against independent Decimal checkers and card provenance."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from checkers import thin_paper

NIGHT = Path(r'D:\GeoBench-codex\night-2026-11-07')
FILES = (
    ('opal_enumerator.py', 'enumerate_opal', 'sample', 3),
    ('moire_enumerator.py', 'enumerate_moire', 'period_nm', 2),
    ('cholesteric_enumerator.py', 'enumerate_cholesteric', 'material', 1),
    ('vortex_enumerator.py', 'enumerate_vortex', 'lambda_nm', 4),
    ('qdot_enumerator.py', 'enumerate_qdot', 'sample', 4),
)


def main():
    checked = 0
    for filename, function, sample_key, decimals in FILES:
        path = NIGHT / filename
        module_name = path.stem
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for draft in getattr(module, function)():
            family = draft['family']
            rel = draft['asset']
            raw = (ROOT / 'docs' / rel).read_bytes()
            card = json.loads(raw)
            sample = ('CsVTaSb' if family == 'vortex_gl_parameter' else
                      next(r['id'] for r in card['rows'] if r.get(sample_key) == draft[sample_key])
                      if sample_key.endswith('_nm') else draft[sample_key])
            if family == 'opal_fcc_111_spacing':
                truth, wrong = module.answer(draft['diameter_nm']), module.distractors(draft['diameter_nm'])
            elif family == 'moire_triangular_cell_area':
                truth, wrong = module.answer(draft['period_nm']), module.distractors(draft['period_nm'])
            elif family == 'cholesteric_band_center':
                truth, wrong = module.answer(draft['lower_nm'], draft['upper_nm']), module.distractors(draft['lower_nm'], draft['upper_nm'])
            elif family == 'vortex_gl_parameter':
                truth, wrong = module.LAMBDA_NM / module.XI_NM, module.distractors()
            else:
                truth, wrong = module.answer(draft['peak_nm']), module.distractors(draft['peak_nm'])
            nums = sorted([truth] + [wrong[k] for k in draft['distractor_rules']])
            options = [dict(label=label, value=f'{v:.{decimals}f}', unit=thin_paper.UNITS[family])
                       for label, v in zip('ABCD', nums)]
            correct = 'ABCD'[nums.index(truth)]
            packet = dict(family=family, question='Sample ' + sample + ': compute the stated quantity.',
                          inputs=[dict(name=rel.rsplit('/', 1)[1], text=raw.decode('utf-8'))], options=options)
            key = dict(correct_label=correct, numeric_answer=dict(decimals=decimals),
                       source=draft['source'], license=draft['license'],
                       input_hashes={rel: hashlib.sha256(raw).hexdigest()})
            result = thin_paper.CHECKERS[family](packet, key)
            assert result['label'] == correct
            checked += 1
    print('Independent checker comparisons:', checked)


if __name__ == '__main__':
    main()
