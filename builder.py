"""Geometry QA Builder. Standard-library core; optional pypdf import for text PDFs."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
STAGES = ('evidence', 'tasks', 'qa', 'review')

def obj(**properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def arr(item):
    return {'type': 'array', 'items': item}

S = {'type': 'string'}
B = {'type': 'boolean'}
N = {'type': 'number'}
I = {'type': 'integer'}
SS = arr(S)
def enum(*values):
    return {'type': 'string', 'enum': list(values)}
def nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}

REF = obj(source_id=S, quote=S)
ABILITY = enum('perception', 'inference', 'design')
CHECKS = obj(sufficient_input=B, evidence_support=B, geometry_required=B,
             no_answer_leakage=B, conditions_preserved=B, rubric_scorable=B,
             disciplinary_meaning=B, entity_identity_clear=B, attachments_complete=B, single_scale_focus=B)
SCHEMAS = {
 'bundle': obj(paper_id=S, title=S, url=S, synthetic=B,
     sources=arr(obj(source_id=S, location=S, origin=S, kind=enum('text','xyz'), text=S)), warnings=SS),
 'evidence': obj(records=arr(obj(evidence_id=S, objects=S, geometric_relation=S,
     scientific_result=S, conditions=SS, limitations=SS, source_refs=arr(REF), asset_ids=SS)), exclusions=SS),
 'tasks': obj(tasks=arr(obj(task_id=S, evidence_ids=SS, domain=S, object_type=S,
     input_scale=S, reasoning_scale=S, ability=ABILITY, geometry_necessity=S,
     learning_objective=S, selection_rationale=S,
     input_plan=S, validation_route=enum('xyz_distance','xyz_angle','evidence_review'),
     eligible=B, unmet_requirements=SS)), exclusions=SS),
 'qa': obj(items=arr(obj(qa_id=S, task_id=S, evidence_ids=SS, ability=ABILITY,
     question=S, model_input=S, input_asset_ids=SS, reference_answer=S,
     answer_numeric=nullable(N), units=S, answer_refs=arr(REF), rubric=S,
     limitations=SS, verifier=nullable(obj(kind=enum('xyz_distance','xyz_angle'),
         source_id=S, atom_indices=arr(I), tolerance=N)))), exclusions=SS),
 'review': obj(reviews=arr(obj(qa_id=S, checks=CHECKS, issues=SS, notes=S)))
}

def validate(value, schema, at='$'):
    """Validate the deliberately small schema vocabulary used here (not general JSON Schema)."""
    if 'anyOf' in schema:
        for branch in schema['anyOf']:
            try:
                validate(value, branch, at)
                return
            except ValueError:
                pass
        raise ValueError(at + ': no allowed type matched')
    t = schema['type']
    matches = {'object': isinstance(value, dict), 'array': isinstance(value, list),
        'string': isinstance(value, str), 'boolean': type(value) is bool,
        'integer': type(value) is int, 'number': type(value) in (int, float), 'null': value is None}
    if not matches[t]:
        raise ValueError(at + ': expected ' + t)
    if t == 'number' and not math.isfinite(value):
        raise ValueError(at + ': nonfinite number')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(at + ': invalid enum')
    if t == 'object':
        if set(value) != set(schema['properties']):
            raise ValueError(at + ': missing or unexpected keys')
        for k,v in value.items(): validate(v, schema['properties'][k], at+'.'+k)
    if t == 'array':
        for i,v in enumerate(value): validate(v, schema['items'], at+f'[{i}]')

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temp.replace(path)

def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def now(): return datetime.now(timezone.utc).isoformat()

def unique(rows, key):
    ids = [row[key] for row in rows]
    if any(not x.strip() for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('empty or duplicate '+key)
    return {r[key]:r for r in rows}

def parse_xyz(text):
    lines = text.strip().splitlines()
    n = int(lines[0])
    if n <= 0 or len(lines) != n+2: raise ValueError('XYZ atom count mismatch')
    points = []
    for line in lines[2:]:
        parts = line.split()
        if len(parts) != 4: raise ValueError('XYZ requires symbol and x y z')
        p = tuple(float(x) for x in parts[1:])
        if not all(math.isfinite(x) for x in p): raise ValueError('nonfinite XYZ')
        points.append(p)
    return points

def bundle_check(bundle):
    validate(bundle, SCHEMAS['bundle'])
    if not bundle['paper_id'].strip() or not bundle['sources']: raise ValueError('empty paper or sources')
    sources = unique(bundle['sources'], 'source_id')
    for s in sources.values():
        if not s['text'].strip() or not s['location'].strip(): raise ValueError('empty source')
        if s['kind']=='xyz': parse_xyz(s['text'])
    return sources

def check_refs(refs, sources, allowed=None):
    if not refs: raise ValueError('missing evidence references')
    for ref in refs:
        sid, quote = ref['source_id'], ref['quote']
        if sid not in sources or (allowed is not None and sid not in allowed):
            raise ValueError('unknown or unrelated source: '+sid)
        if not quote.strip() or quote not in sources[sid]['text']:
            raise ValueError('quotation not found verbatim in '+sid)

def semantic(stage, data, bundle, previous, config):
    validate(data, SCHEMAS[stage])
    sources = bundle_check(bundle)
    if stage == 'evidence':
        for r in unique(data['records'], 'evidence_id').values():
            check_refs(r['source_refs'], sources)
            if any(a not in sources or sources[a]['kind']!='xyz' for a in r['asset_ids']):
                raise ValueError('unavailable evidence asset')
    elif stage == 'tasks':
        evidence = unique(previous['evidence']['records'],'evidence_id')
        for t in unique(data['tasks'],'task_id').values():
            if not t['evidence_ids'] or any(e not in evidence for e in t['evidence_ids']):
                raise ValueError('task evidence unavailable')
            if t['eligible'] and (t['ability']=='design' or t['unmet_requirements']):
                raise ValueError('ineligible task marked eligible')
            if t['eligible'] and t['validation_route'].startswith('xyz_'):
                if not any(evidence[e]['asset_ids'] for e in t['evidence_ids']):
                    raise ValueError('XYZ task without asset')
    elif stage == 'qa':
        if len(data['items'])>config['max_questions']: raise ValueError('question cap exceeded')
        tasks = unique(previous['tasks']['tasks'],'task_id')
        evidence = unique(previous['evidence']['records'],'evidence_id')
        for q in unique(data['items'],'qa_id').values():
            t = tasks.get(q['task_id'])
            if not t or not t['eligible'] or q['ability']!=t['ability']: raise ValueError('invalid QA task')
            if not q['evidence_ids'] or not set(q['evidence_ids'])<=set(t['evidence_ids']):
                raise ValueError('QA evidence does not match task')
            allowed = {r['source_id'] for e in q['evidence_ids'] for r in evidence[e]['source_refs']}
            allowed |= {a for e in q['evidence_ids'] for a in evidence[e]['asset_ids']}
            check_refs(q['answer_refs'], sources, allowed)
            if any(a not in allowed or sources[a]['kind']!='xyz' for a in q['input_asset_ids']):
                raise ValueError('unrelated or unavailable input asset')
            if not all(q[k].strip() for k in ('question','model_input','reference_answer','rubric')):
                raise ValueError('empty QA text')
            v = q['verifier']
            if t['validation_route']=='evidence_review':
                if v is not None or q['answer_numeric'] is not None or q['units']!='':
                    raise ValueError('unexpected numeric verifier')
            else:
                if not v or v['kind']!=t['validation_route'] or v['source_id'] not in q['input_asset_ids']:
                    raise ValueError('missing or mismatched verifier')
                if q['answer_numeric'] is None: raise ValueError('missing numeric answer')
                geometry(q,sources)  # validate indices/units/tolerance; disagreement is reportable
    else:
        reviews = unique(data['reviews'],'qa_id')
        if set(reviews)!=set(q['qa_id'] for q in previous['qa']['items']):
            raise ValueError('review coverage incomplete or invented')

def geometry(q, sources):
    v = q['verifier']
    pts = parse_xyz(sources[v['source_id']]['text'])
    idx = v['atom_indices']
    count = 2 if v['kind']=='xyz_distance' else 3
    tol = v['tolerance']
    max_tol = .001 if count==2 else .1
    if len(idx)!=count or len(set(idx))!=count or any(i<1 or i>len(pts) for i in idx):
        raise ValueError('invalid atom indices')
    if not 0<tol<=max_tol: raise ValueError('invalid tolerance')
    if q['units']!=('angstrom' if count==2 else 'degree'): raise ValueError('invalid units')
    p = [pts[i-1] for i in idx]
    if count==2: actual = math.dist(*p)
    else:
        u = [a-b for a,b in zip(p[0],p[1])]
        v2 = [a-b for a,b in zip(p[2],p[1])]
        den = math.sqrt(sum(x*x for x in u)*sum(x*x for x in v2))
        if den == 0: raise ValueError('undefined angle')
        actual = math.degrees(math.acos(max(-1,min(1,sum(a*b for a,b in zip(u,v2))/den))))
    return {'kind': v['kind'], 'computed': actual, 'claimed': q['answer_numeric'],
            'passed': abs(actual-q['answer_numeric'])<=tol}

def snapshot(run):
    return {'builder': hashlib.sha256((run/'builder_snapshot.py').read_bytes()).hexdigest(),
            'bundle':digest(read(run/'bundle.json')), 'config':digest(read(run/'config.json')),
            'prompts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((run/'prompts').glob('*.md'))},
            'schemas':digest(read(run/'schemas.json'))}

def state(run):
    run = Path(run)
    manifest = read(run/'manifest.json')
    if manifest['hashes'] != snapshot(run): raise ValueError('run snapshot changed; create a new run')
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=manifest['hashes']['builder']:
        raise ValueError('builder changed; use this run/builder_snapshot.py or create a new run')
    b,c = read(run/'bundle.json'), read(run/'config.json')
    previous = {}
    for stage in STAGES:
        path = run/(stage+'.json')
        if not path.exists(): break
        envelope = read(path)
        if envelope['data_hash'] != digest(envelope['data']):
            raise ValueError('stage data changed')
        if envelope['context_hash'] != digest({'snapshot':manifest['hashes'],'previous':previous}):
            raise ValueError('stage lineage mismatch')
        semantic(stage,envelope['data'],b,previous,c)
        previous[stage] = envelope['data']
    return run,b,c,previous,manifest

def packet(run):
    run,b,c,previous,m = state(run)
    if len(previous)==len(STAGES): return None
    stage = STAGES[len(previous)]
    instructions = (run/'prompts/common.md').read_text(encoding='utf-8')+'\n'+(run/f'prompts/{stage}.md').read_text(encoding='utf-8')
    payload = {'config':c,'bundle':b,'previous':previous}
    request = {'model':c['model'], 'reasoning':{'effort':c['reasoning_effort']},
        'max_output_tokens':c['max_output_tokens'],'store':False,
        'instructions':instructions,'input':json.dumps(payload,ensure_ascii=False),
        'text':{'format':{'type':'json_schema','name':stage,'strict':True,'schema':SCHEMAS[stage]}}}
    write(run/f'{stage}.request.json',request)
    return stage,request

def accept(run, data, model, mode, usage=None, response_id=None):
    run,b,c,previous,m = state(run)
    if len(previous)==4: raise ValueError('all stages complete; create a new run to revise')
    stage = STAGES[len(previous)]
    semantic(stage,data,b,previous,c)
    envelope = {'stage':stage,'mode':mode,'reported_model':model,'time':now(),
        'usage':usage,'response_id':response_id,
        'context_hash':digest({'snapshot':m['hashes'],'previous':previous}),
        'data_hash':digest(data),'data':data}
    write(run/f'{stage}.json',envelope)
    return stage

def init(bundle_path, run):
    bundle=read(bundle_path); bundle_check(bundle)
    c=read(ROOT/'config.json')
    if len(json.dumps(bundle,ensure_ascii=False))>c['max_bundle_chars']: raise ValueError('bundle too large; narrow material explicitly, no silent truncation')
    run=Path(run)
    if run.exists(): raise ValueError('run path already exists; use a new path')
    run.mkdir(parents=True)
    write(run/'bundle.json',bundle); write(run/'config.json',c)
    write(run/'schemas.json',SCHEMAS)
    shutil.copytree(ROOT/'prompts',run/'prompts')
    shutil.copyfile(Path(__file__),run/'builder_snapshot.py')
    write(run/'manifest.json',{'created':now(),'version':c['version'],'hashes':snapshot(run)})

def parse_response(response):
    if response.get('status')!='completed': raise ValueError('API response incomplete; inspect saved raw response')
    texts=[]
    for out in response.get('output',[]):
        for content in out.get('content',[]):
            if content.get('type')=='refusal': raise ValueError('model refused; no result accepted')
            if content.get('type')=='output_text': texts.append(content['text'])
    if not texts: raise ValueError('no model output text')
    return json.loads(''.join(texts))

def api_run(run, max_calls):
    key=os.getenv('OPENAI_API_KEY')
    if not key: raise ValueError('OPENAI_API_KEY is not configured; use next/accept or configure locally')
    for _ in range(max_calls):
        next_item=packet(run)
        if next_item is None: break
        stage,request=next_item
        req=urllib.request.Request('https://api.openai.com/v1/responses',
            data=json.dumps(request).encode(), headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=300) as r: response=json.load(r)
        except urllib.error.HTTPError as e:
            raise ValueError(f'API HTTP {e.code}; stopped without retry') from None
        except (urllib.error.URLError, TimeoutError):
            raise ValueError('API network failure/timeout; no automatic retry; request outcome may be uncertain') from None
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        write(Path(run)/'attempts'/f'{stage}-{stamp}.json',response)
        data=parse_response(response)
        accept(run,data,response.get('model',request['model']),'api',response.get('usage'),response.get('id'))
        print('Completed stage:',stage,flush=True)
    report(run)

def report(run):
    run,b,c,p,m=state(run)
    if len(p)!=4: raise ValueError('four complete stages required for report')
    sources=bundle_check(b)
    reviews=unique(p['review']['reviews'],'qa_id')
    tasks=unique(p['tasks']['tasks'],'task_id')
    rows=[]; seen=set()
    for q in p['qa']['items']:
        r=reviews[q['qa_id']]; issues=list(r['issues'])
        checks=[{'kind':k,'passed':v} for k,v in r['checks'].items()]
        if q['verifier']: checks.append(geometry(q,sources))
        identity=digest({'q':' '.join(q['question'].lower().split()),'input':q['model_input'],'assets':q['input_asset_ids']})
        if identity in seen: issues.append('exact_duplicate_within_run')
        seen.add(identity)
        okay=all(x['passed'] for x in checks) and not issues
        t=tasks[q['task_id']]
        rows.append({'qa_id':q['qa_id'],'task_id':q['task_id'],'ability':q['ability'],
            'domain':t['domain'],'input_scale':t['input_scale'],'reasoning_scale':t['reasoning_scale'],
            'question':q['question'],'model_input':q['model_input'],'input_asset_ids':q['input_asset_ids'],
            'reference_answer':q['reference_answer'],'evidence_ids':q['evidence_ids'],
            'status':'pending_human_audit' if okay else 'needs_revision',
            'benchmark_ready':False,'checks':checks,'issues':issues,'limitations':q['limitations'],'review_notes':r['notes']})
    result={'paper_id':b['paper_id'],'synthetic':b['synthetic'],'benchmark_ready':False,
        'count':len(rows),'pending_human_audit':sum(r['status']=='pending_human_audit' for r in rows),
        'exclusions':{s:p[s].get('exclusions',[]) for s in STAGES},'items':rows}
    write(run/'report.json',result)
    fields=['qa_id','ability','domain','input_scale','reasoning_scale','question','model_input','input_asset_ids','reference_answer','status','benchmark_ready','issues']
    with (run/'candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for row in rows:
            out={k:json.dumps(row[k],ensure_ascii=False) if isinstance(row[k],list) else row[k] for k in fields}
            for k,v in out.items():
                if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')): out[k]="'"+v
            writer.writerow(out)
    lines=['# Candidate QA report',f"Paper: {b['paper_id']}",f"Synthetic software fixture: {b['synthetic']}",f"Candidates: {len(rows)}; pending audit: {result['pending_human_audit']}",
        'No item is scientifically certified or benchmark-ready. See report.json for full checks.']
    for r in rows: lines += ['',f"## {r['qa_id']} — {r['status']}",r['question'], 'Issues: '+('; '.join(r['issues']) or 'none reported by screening')]
    (run/'report.md').write_text('\n\n'.join(lines),encoding='utf-8')
    return result

def prepare(args):
    sources=[]; warnings=[]
    for filename in args.source:
        path=Path(filename)
        if path.suffix.lower()=='.pdf':
            try: from pypdf import PdfReader
            except ImportError: raise ValueError('PDF requires pypdf; alternatively supply extracted UTF-8 text')
            warnings.append(path.name+': text-only PDF extraction; images and table layout NOT validated')
            chunks=[(f'page {i+1}',page.extract_text() or '') for i,page in enumerate(PdfReader(path).pages)]
        else:
            lines=path.read_text(encoding='utf-8-sig').splitlines()
            chunks=[(f'lines {i+1}-{min(i+60,len(lines))}','\n'.join(lines[i:i+60])) for i in range(0,len(lines),60)]
        for loc,text in chunks:
            if not text.strip(): warnings.append(path.name+' '+loc+': empty'); continue
            sources.append({'source_id':f'S{len(sources)+1:04}','location':path.name+' '+loc,'origin':str(path.resolve()),'kind':'text','text':text})
    for filename in args.xyz:
        path=Path(filename); text=path.read_text(encoding='utf-8-sig'); parse_xyz(text)
        sources.append({'source_id':f'S{len(sources)+1:04}','location':path.name+' XYZ angstrom','origin':str(path.resolve()),'kind':'xyz','text':text})
    b={'paper_id':args.paper_id,'title':args.title,'url':args.url,'synthetic':args.synthetic,'sources':sources,'warnings':warnings}
    bundle_check(b)
    if Path(args.out).exists(): raise ValueError('output already exists; choose a new file')
    write(args.out,b)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('schemas')
    p=sub.add_parser('prepare'); p.add_argument('--paper-id',required=True); p.add_argument('--title',required=True); p.add_argument('--url',required=True)
    p.add_argument('--source',action='append',default=[]); p.add_argument('--xyz',action='append',default=[]); p.add_argument('--out',required=True); p.add_argument('--synthetic',action='store_true')
    p=sub.add_parser('init'); p.add_argument('--bundle',required=True); p.add_argument('--run',required=True)
    for command in ('next','accept','run','report'):
        p=sub.add_parser(command); p.add_argument('--run',required=True)
        if command=='accept': p.add_argument('--result',required=True); p.add_argument('--model',required=True)
        if command=='run': p.add_argument('--max-calls',type=int,default=4,choices=range(1,5))
    args=parser.parse_args()
    try:
        if args.command=='schemas':
            for k,v in SCHEMAS.items(): write(ROOT/'schemas'/f'{k}.json',v)
        elif args.command=='prepare': prepare(args)
        elif args.command=='init': init(args.bundle,args.run)
        elif args.command=='next':
            result=packet(args.run)
            print(str(Path(args.run)/(result[0]+'.request.json')) if result else 'All stages complete')
        elif args.command=='accept':
            data=read(args.result)
            try: print(accept(args.run,data,args.model,'manual_import'))
            except ValueError as error:
                stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
                write(Path(args.run)/'attempts'/f'manual-rejected-{stamp}.json',{'error':str(error),'data':data})
                raise
        elif args.command=='run': api_run(args.run,args.max_calls)
        else: report(args.run)
    except (ValueError,OSError,KeyError) as e:
        print('Stopped:',str(e),file=sys.stderr); return 1
    return 0

if __name__=='__main__': sys.exit(main())
