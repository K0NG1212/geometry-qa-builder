from pathlib import Path

def validate(b, data, bundle, previous, config):
    b.validate(data, b.read(Path(__file__).with_name("schema.json")))
    sources = b.bundle_check(bundle)
    evidence = b.unique(previous['evidence']['records'],'evidence_id')
    for t in b.unique(data['tasks'],'task_id').values():
        audit = t.get('geometry_audit')
        if not bundle['synthetic'] and audit is None:
            raise ValueError('real task requires geometry_audit')
        if audit is not None:
            if any(not audit[k].strip() for k in ('geometry_inputs','without_geometry','dependent_score_items','scale_basis','claim_limits','template_family')):
                raise ValueError('geometry_audit requires concrete reasons')
            if t['eligible'] and (audit['geometry_dependency'] in ('none','uncertain') or not audit['scale_consistent'] or not audit['claims_supported']):
                raise ValueError('eligible task contradicts geometry_audit')
        if not t['evidence_ids'] or any(e not in evidence for e in t['evidence_ids']):
            raise ValueError('task evidence unavailable')
        if t['eligible'] and any(not t[k].strip() for k in ('learning_objective','selection_rationale')):
            raise ValueError('eligible task requires learning objective and selection rationale')
        if t['eligible'] and (t['ability']=='design' or t['unmet_requirements']):
            raise ValueError('ineligible task marked eligible')
        if t['eligible'] and t['validation_route'].startswith('xyz_'):
            if not any(evidence[e]['asset_ids'] for e in t['evidence_ids']):
                raise ValueError('XYZ task without asset')
