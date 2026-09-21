"""Inventory-only common admission checks. Does not re-run AI or certify science."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def build():
 c=read(DOCS/'data/catalog.json');progress=read(DOCS/'data/prototype-progress.json');rows=[]
 for q in c['questions']:
  assets=q.get('attachments',[])
  files=[DOCS/a['url'] for a in assets]
  tests={'完整公开题干':bool(q.get('publicDemo') and q.get('question') and q.get('completeInput')),'实际附件可用':bool(assets) and all(p.is_file() for p in files),'参考答案与评分标准':bool(q.get('answer') and q.get('rubric')),'来源与学科考点':bool(q.get('source') and q.get('learningObjective')),'两种实测尺度':all(isinstance(q.get(k),(int,float)) and q[k]>0 for k in ['inputSizeNm','reasoningSizeNm']),'新版初筛记录':q.get('prototypeScreeningPassed') is True and q.get('status')=='pending_human_audit','当前原型':q.get('lifecycle')=='active'}
  ready=all(tests.values())
  rows.append({'id':q['id'],'title':q['title'],'lifecycle':q['lifecycle'],'checks':tests,'human_review_queue':ready,'reason':q['lifecycleReason'],'next':q['restartFrom'],'limits':'字段、附件存在性和已记录初筛状态的检查；不等于重跑M2–M5或独立领域审核。'})
 queue=[r['id'] for r in rows if r['human_review_queue']]
 assert len(queue)==progress['screened_total'],'Admission inventory disagrees with coverage; resolve before publishing'
 readiness=read(DOCS/'data/task-readiness-v04.json');directions=[{'id':k,'instance_ids':v['linked_candidates'],'state':v['label'],'next':v['next_action']} for k,v in readiness['reviews'].items()]
 return {'date':c['updated'],'scope':'对全部目录记录采用相同准入清单；2026-09-22 专项审读处置见 screening.html；本统计不代表完整 M0–M6 重跑。','target':progress['target_total'],'screened':progress['screened_total'],'remaining_screened':progress['target_total']-progress['screened_total'],'formal_ready':c['counts']['ready'],'remaining_formal':progress['target_total']-c['counts']['ready'],'human_review_count':len(queue),'human_review_ids':queue,'lifecycle_counts':c['lifecycleCounts'],'records':rows,'directions':directions,'cells':progress['cells']}
if __name__=='__main__':
 result=build();(DOCS/'data/admission-audit.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode());print('Admission inventory:',result['screened'],'candidates;',result['human_review_count'],'human reviews;',result['remaining_screened'],'candidate gap')
