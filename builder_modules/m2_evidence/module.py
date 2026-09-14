from pathlib import Path

def validate(b, data, bundle, previous, config):
    b.validate(data, b.read(Path(__file__).with_name("schema.json")))
    sources = b.bundle_check(bundle)
    for r in b.unique(data['records'], 'evidence_id').values():
        b.check_refs(r['source_refs'], sources)
        if any(a not in sources or sources[a]['kind']!='xyz' for a in r['asset_ids']):
            raise ValueError('unavailable evidence asset')
