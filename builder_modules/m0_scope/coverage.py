"""Prototype coverage counts use measured REASONING scale, never input size."""
import math

def scale_bin(value,bins):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):return None
    for i,(lo,hi) in enumerate(bins):
        if lo<=value<hi or (i==len(bins)-1 and value==hi):return i
    return None

def summarize(catalog,policy):
    bins=policy['scale_bins_nm'];cells=[]
    for domain in policy['domains']:
        for index,span in enumerate(bins):
            located=[q for q in catalog['questions'] if q['domain']==domain and scale_bin(q.get('reasoningSizeNm'),bins)==index]
            screened=[q for q in located if q.get('prototypeScreeningPassed') is True and q.get('status')=='pending_human_audit']
            counts={a:sum(q['ability']==a for q in screened) for a in policy['ability_soft_targets']}
            cells.append({'domain':domain,'range_nm':span,'target':policy['target_per_cell'],'located_candidates':len(located),'screened_count':len(screened),'remaining':max(0,policy['target_per_cell']-len(screened)),'abilities':counts,'ability_shortfalls':{a:max(0,n-counts[a]) for a,n in policy['ability_soft_targets'].items()},'qa_ids':[q['id'] for q in screened],'blocker':'Still missing validated task/material coverage; absence is not proof the task is impossible.' if len(screened)<policy['target_per_cell'] else ''})
    return {'version':policy['version'],'primary_scale':'reasoning','target_total':len(cells)*policy['target_per_cell'],'screened_total':sum(c['screened_count'] for c in cells),'formal_ready':catalog['counts']['ready'],'unlocated_candidates':sum(scale_bin(q.get('reasoningSizeNm'),bins) is None for q in catalog['questions']),'note':'Same-session prototype screening, not expert certification. Historical candidates are not automatically grandfathered in.','cells':cells}
