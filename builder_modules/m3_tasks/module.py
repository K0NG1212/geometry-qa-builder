from pathlib import Path

def validate(b, data, bundle, previous, config):
    b.validate(data, b.read(Path(__file__).with_name("schema.json")))
    sources = b.bundle_check(bundle)
    evidence = b.unique(previous['evidence']['records'],'evidence_id')
    for t in b.unique(data['tasks'],'task_id').values():
        if not t['evidence_ids'] or any(e not in evidence for e in t['evidence_ids']):
            raise ValueError('task evidence unavailable')
        if t['eligible'] and any(not t[k].strip() for k in ('learning_objective','selection_rationale')):
            raise ValueError('eligible task requires learning objective and selection rationale')
        if t['eligible'] and (t['ability']=='design' or t['unmet_requirements']):
            raise ValueError('ineligible task marked eligible')
        if t['eligible'] and t['validation_route'].startswith('xyz_'):
            if not any(evidence[e]['asset_ids'] for e in t['evidence_ids']):
                raise ValueError('XYZ task without asset')
