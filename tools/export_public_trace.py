"""Export public excerpts for explicitly published development examples only.
Usage: python tools/export_public_trace.py --run runs/chem-nm001-bcd
Full packets stay local; bundle text is replaced with a source manifest.
"""
import argparse, hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def clean(v):
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k not in ('local_path','run_directory')}
    if isinstance(v,list):return [clean(x) for x in v]
    if isinstance(v,str) and re.search(r'[A-Za-z]:[\\/]|file://',v):return '[local path omitted]'
    return v

def export(run):
    cat=read(ROOT/'docs/data/catalog.json');published={q['id']:q for q in cat['questions'] if q.get('publicDemo') and q.get('releaseRole')=='public_development_example'}
    qa=read(run/'qa.json');ids=[x['qa_id'] for x in qa['data']['items']]
    if not ids or any(q not in published for q in ids):raise ValueError('Run must contain only explicitly published development examples')
    bundle=read(run/'bundle.json')
    manifest=[{k:s[k] for k in ('source_id','location','origin','kind') if k in s} for s in bundle['sources']]
    manifest=clean(manifest)
    units=read(run/'asset-units.json');ev=read(run/'evidence.json');tasks=read(run/'tasks.json');receipt=read(run/'construction-receipt.json');review=read(run/'review.json');report=read(run/'report.json')
    sources=read(run/'sources.json')
    def record(name,value):return {'file':name,'sha256':hashlib.sha256((run/name).read_bytes()).hexdigest(),'excerpt':clean(value)}
    def packet(stage):
        name=stage+'.packet.json';p=read(run/name)
        return record(name,{'module':p['module'],'execution_mode':p['execution_mode'],'requested_model':p['requested_model'],'context_hash':p['context_hash'],'instructions':p['instructions'],'output_schema':p['output_schema'],'input':{'bundle_sources_manifest':manifest,'asset_units':p['input']['asset_units'],'max_questions':p['input']['max_questions'],'previous':p['input']['previous']},'omitted':'Full source text / bundle omitted; source locations retained. Prior stage records shown as saved.'})
    results=[]
    for id in ids:
        item=next(x for x in qa['data']['items'] if x['qa_id']==id)
        task=next(x for x in tasks['data']['tasks'] if x['task_id']==item['task_id'])
        checks=[dict(x,qa_checks=[c for c in x['qa_checks'] if c['qa_id']==id]) for x in read(run/'independent-checks.json') if any(c['qa_id']==id for c in x['qa_checks'])]
        filt=lambda d:{**{k:v for k,v in d.items() if k!='items'},'items':[x for x in d['items'] if x['qa_id']==id]}
        modules=[
          dict(id='M0',name='范围配置',action='将批次目标和运行配置冻结保存。goal.json 是启动时快照，status 字段不会随本次展示改写。',inputs=[record('goal.json',read(run/'goal.json'))],outputs=[record('config.json',read(run/'config.json'))]),
          dict(id='M1',name='检索与材料整理',action='助手检索官方材料；PDB 转 XYZ，核实坐标、顺序与单位。此处是共享材料清单，原文件内容按来源链接追溯。',inputs=[record('sources.json',{k:sources[k] for k in ('search_queries','selection_unit','resources')})],outputs=[record('bundle.json',{'paper_id':bundle['paper_id'],'title':bundle['title'],'sources':manifest,'omitted':'Source text omitted; full XYZ available in M6 output and question detail.'}),record('asset-units.json',units)]),
          dict(id='M2',name='科学证据提取',action='按保存的提示词提取条件、坐标依据与限制。本次两道题共享证据，不是为每道题重新读一篇论文。',inputs=[packet('evidence')],outputs=[record('evidence.json',ev)]),
          dict(id='M3',name='任务模板',action='把证据转成可执行任务。本题对应 '+item['task_id']+'；保留未被采用的推断提案，说明为什么没有构题。',inputs=[packet('tasks')],outputs=[record('tasks.json',{'selected_task':task,'excluded_tasks':[t for t in tasks['data']['tasks'] if not t['eligible']],'exclusions':tasks['data'].get('exclusions',[])})]),
          dict(id='M4',name='构题与答案计算',action='构题计划指定原子与评分器，answer_text 为空；程序根据坐标算出数值答案。输出按当前题号摘取。',inputs=[packet('construction')],outputs=[record('construction-receipt.json',{'plan':{'items':[x for x in receipt['plan']['items'] if x['qa_id']==id]}}),record('qa.json',{'stage':qa['stage'],'time':qa['time'],'data':{'items':[item]}})]),
          dict(id='M5',name='质量筛查',action='同一次会话中的 AI 筛查，加上程序计算与另一种算法复核；没有领域专家审核，题目仍是待审核状态。',inputs=[packet('review')],outputs=[record('review.json',{'reviews':[x for x in review['data']['reviews'] if x['qa_id']==id]}),record('report.json',filt(report)),record('independent-checks.json',checks)]),
          dict(id='M6',name='整理与导出',action='分离模型输入和参考答案。以下仅导出当前这道已公开开发示例；不是可直接公开所有私有运行记录的通用开关。',inputs=[record('report.json',filt(report))],outputs=[record('model-inputs.json',filt(read(run/'model-inputs.json'))),record('private-answers.json',filt(read(run/'private-answers.json')))])]
        results.append(dict(qaId=id,title=published[id]['title'],runName=run.name,taskId=item['task_id'],evidenceIds=item['evidence_ids'],status='pending_human_audit',modules=modules))
    dest=ROOT/'docs/data/traces';dest.mkdir(exist_ok=True)
    for result in results:
        text=json.dumps(result,ensure_ascii=False,indent=2)
        if re.search(r'[A-Za-z]:\\|C:/Users|file://',text):raise ValueError('Local path remains')
        (dest/(result['qaId']+'.json')).write_bytes(text.encode('utf8'))
    print('Exported public excerpts:',', '.join(ids))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);args=parser.parse_args();export(args.run)
