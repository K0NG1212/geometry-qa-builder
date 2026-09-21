import csv
import json
from pathlib import Path

def validate(b, data, bundle, previous, config):
    b.validate(data, b.read(Path(__file__).with_name("schema.json")))
    sources = b.bundle_check(bundle)
    reviews = b.unique(data['reviews'],'qa_id')
    if set(reviews)!=set(q['qa_id'] for q in previous['qa']['items']):
        raise ValueError('review coverage incomplete or invented')
    for r in reviews.values():
        audit = r.get('geometry_audit')
        if not bundle['synthetic'] and audit is None:
            raise ValueError('real review requires geometry_audit')
        if audit is not None:
            if any(not audit[k].strip() for k in ('geometry_inputs','without_geometry','dependent_score_items','scale_basis','claim_limits','template_family')):
                raise ValueError('geometry_audit requires concrete reasons')
            failed = []
            if audit['geometry_dependency'] in ('none','uncertain'): failed.append('geometry_required')
            if not audit['scale_consistent']: failed.append('single_scale_focus')
            if not audit['claims_supported']: failed.extend(('evidence_support','rubric_scorable'))
            if any(r['checks'][k] for k in failed) or (failed and not r['issues']):
                raise ValueError('review checks contradict geometry_audit; record failure and issues')


def report(b, run):
    run,bundle,c,p,m=b.state(run)
    if len(p)!=4: raise ValueError('four complete stages required for report')
    sources=b.bundle_check(bundle)
    reviews=b.unique(p['review']['reviews'],'qa_id')
    tasks=b.unique(p['tasks']['tasks'],'task_id')
    rows=[]; seen=set()
    for q in p['qa']['items']:
        r=reviews[q['qa_id']]; issues=list(r['issues'])
        checks=[{'kind':k,'passed':v} for k,v in r['checks'].items()]
        if q['verifier']: checks.append(b.geometry(q,sources))
        identity=b.digest({'q':' '.join(q['question'].lower().split()),'input':q['model_input'],'assets':q['input_asset_ids']})
        if identity in seen: issues.append('exact_duplicate_within_run')
        seen.add(identity)
        okay=all(x['passed'] for x in checks) and not issues
        t=tasks[q['task_id']]
        rows.append({'qa_id':q['qa_id'],'task_id':q['task_id'],'ability':q['ability'],
            'domain':t['domain'],'input_scale':t['input_scale'],'reasoning_scale':t['reasoning_scale'],
            'question':q['question'],'model_input':q['model_input'],'input_asset_ids':q['input_asset_ids'],
            'reference_answer':q['reference_answer'],'evidence_ids':q['evidence_ids'],
            'status':'pending_human_audit' if okay else 'needs_revision',
            'benchmark_ready':False,'checks':checks,'issues':issues,'limitations':q['limitations'],'review_notes':r['notes'],'geometry_audit':r.get('geometry_audit')})
    result={'paper_id':bundle['paper_id'],'synthetic':bundle['synthetic'],'benchmark_ready':False,
        'count':len(rows),'pending_human_audit':sum(r['status']=='pending_human_audit' for r in rows),
        'exclusions':{s:p[s].get('exclusions',[]) for s in b.STAGES},'items':rows}
    b.write(run/'report.json',result)
    fields=['qa_id','ability','domain','input_scale','reasoning_scale','question','model_input','input_asset_ids','reference_answer','status','benchmark_ready','issues']
    with (run/'candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for row in rows:
            out={k:json.dumps(row[k],ensure_ascii=False) if isinstance(row[k],list) else row[k] for k in fields}
            for k,v in out.items():
                if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')): out[k]="'"+v
            writer.writerow(out)
    lines=['# Candidate QA report',f"Paper: {bundle['paper_id']}",f"Synthetic software fixture: {bundle['synthetic']}",f"Candidates: {len(rows)}; pending audit: {result['pending_human_audit']}",
        'No item is scientifically certified or benchmark-ready. See report.json for full checks.']
    for r in rows: lines += ['',f"## {r['qa_id']} — {r['status']}",r['question'], 'Issues: '+('; '.join(r['issues']) or 'none reported by screening')]
    (run/'report.md').write_text('\n\n'.join(lines),encoding='utf-8')
    return result
