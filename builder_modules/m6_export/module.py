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
    packets = run/'student-packets'
    packets.mkdir(exist_ok=True)
    for index,q in enumerate(inputs,1):
        # Numeric filenames avoid interpreting generated IDs as filesystem paths.
        stem = f'item-{index:04d}'
        attached=[]
        for ai,asset in enumerate(q['assets'],1):
            filename=f'{stem}-asset-{ai}.xyz'
            (packets/filename).write_text(asset['text'],encoding='utf-8')
            attached.append({'asset_id':asset['asset_id'],'file':filename})
        text=q['question']+'\n\n'+q['model_input']+'\n\nAttachments:\n'+'\n'.join(x['asset_id']+': '+x['file'] for x in attached)
        (packets/(stem+'.txt')).write_text(text,encoding='utf-8')
    b.write(packets/'index.json',{'items':[{'qa_id':q['qa_id'],'question_file':f'item-{i:04d}.txt'} for i,q in enumerate(inputs,1)]})
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
