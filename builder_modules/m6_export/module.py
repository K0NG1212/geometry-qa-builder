from pathlib import Path
from builder_modules.m5_quality import module as quality

def export(b, run, bundle, previous, pipeline_status):
    result = quality.report(b, run)
    # Candidate input export is distinct from private answer/evidence artifacts.
    inputs = [{'qa_id': q['qa_id'], 'question': q['question'], 'model_input': q['model_input'],
        'assets': [{'asset_id': sid, 'kind': s['kind'], 'text': s['text']}
                   for sid in q['input_asset_ids'] for s in bundle['sources'] if s['source_id'] == sid]}
        for q in previous['qa']['items']]
    # XYZ comment lines can contain energies/answers. Preserve only symbols/coordinates.
    for q in inputs:
        for asset in q['assets']:
            lines = asset['text'].strip().splitlines()
            lines[1] = 'Coordinates in angstrom; atoms numbered from 1.'
            asset['text'] = '\n'.join(lines)+'\n'
    public_input = {'synthetic': bundle['synthetic'], 'candidates_only': True, 'items': inputs}
    b.validate(public_input, b.read(Path(__file__).with_name('schema.json')))
    b.write(run/'model-inputs.json', public_input)
    b.write(run/'private-answers.json', {'items': previous['qa']['items']})
    b.write(run/'quality-report.json', {'pipeline': pipeline_status,
        'automated_screening': result, 'review_independent': False,
        'unit_confirmation': b.read(run/'asset-units.json'),
        'limits': ['Quote matching does not establish entailment.',
                   'Numeric generation and recomputation share the same calculator.',
                   'Question/atom-index agreement and semantic answer leakage require audit.',
                   'No expert certification, difficulty validation or benchmark split here.']})
    return pipeline_status
