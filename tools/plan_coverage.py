"""Coverage planner: for each of the 16 cells and each ability, the current count
(from the M0 coverage summary) and the routes that could fill the gap.

Routes come only from templates/registry.json (declared ability, domains, scale cells)
and from rework records already located in the cell. The planner suggests; it never
generates questions or changes counts.

  ready    task family with running code and an independent checker
  migrate  legacy calculator not yet on the family interface (roadmap A5)
  build    family defined but not implemented (e.g. stereo ladder A1, evidence inference A2)
  none     no declared route; needs data-source research (roadmap A4)

python tools/plan_coverage.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from builder_modules.m0_scope.coverage import summarize, scale_bin

KIND = {'implemented': 'ready', 'pilot': 'ready', 'existing_legacy': 'migrate', 'planned': 'build'}
ORDER = {'ready': 0, 'migrate': 1, 'build': 2}


def cell_name(span):
    return '%g-%g' % tuple(span)


def plan(catalog, policy, registry, feasibility=None):
    progress = summarize(catalog, policy)
    notes = {(c['domain'], c['cell']): c for c in (feasibility or {}).get('cells', [])}
    bins = policy['scale_bins_nm']
    rows = []
    for cell in progress['cells']:
        name = cell_name(cell['range_nm'])
        index = bins.index(cell['range_nm'])
        abilities = {}
        for ability, soft in policy['ability_soft_targets'].items():
            routes = []
            for t in registry['templates']:
                kind = KIND.get(t['status'])
                if kind and t['ability'] == ability and cell['domain'] in t['domains'] and name in t['scale_cells']:
                    if kind == 'ready' and not t.get('independent_checker'):
                        kind = 'migrate'
                    routes.append(dict(family=t['id'], name=t['name'], kind=kind, status=t['status']))
            routes.sort(key=lambda r: (ORDER[r['kind']], r['family']))
            rework = [q['id'] for q in catalog['questions'] if q.get('lifecycle') == 'rework' and q['domain'] == cell['domain']
                      and q['ability'] == ability and scale_bin(q.get('reasoningSizeNm'), bins) == index]
            have = cell['abilities'][ability]
            abilities[ability] = dict(current=have, soft_target=soft, shortfall=max(0, soft - have), routes=routes,
                                      rework_in_cell=rework,
                                      best_route=routes[0]['kind'] if routes else 'none')
        note = notes.get((cell['domain'], name))
        rows.append(dict(domain=cell['domain'], cell=name, target=cell['target'], current=cell['screened_count'],
                         provisional=len(cell['provisional_ids']), remaining=cell['remaining'], abilities=abilities,
                         feasibility=dict(level=note['feasibility'], route=note['route'],
                                          sources=[x['id'] for x in note['sources']], needs_download=note['needs_download'],
                                          risks=note['risks']) if note else None))
    gaps = [(r['domain'], r['cell'], a, v) for r in rows for a, v in r['abilities'].items() if v['shortfall']]
    summary = dict(target_total=progress['target_total'], current_total=progress['screened_total'],
                   capped_total=sum(min(r['current'], r['target']) for r in rows),
                   over_target_cells=[r['domain'] + ' ' + r['cell'] for r in rows if r['current'] > r['target']],
                   provisional_total=progress['provisional_total'],
                   ability_gaps=len(gaps), gap_slots=sum(v['shortfall'] for *_, v in gaps),
                   gaps_by_best_route={k: sum(1 for *_, v in gaps if v['best_route'] == k)
                                       for k in ('ready', 'migrate', 'build', 'none')},
                   note='capped_total 为每格最多按目标 10 道计的有效覆盖；超额题有效但不填补其他格。'
                        '能力软目标来自 prototype-policy（每格感知/推断/设计各 3，外加 1 个机动名额）；'
                        '路线只表示注册表声明可覆盖，不保证该格一定有合适数据。')
    return dict(version='0.1.0', basis='prototype-policy + registry', summary=summary, cells=rows)


if __name__ == '__main__':
    read = lambda p: json.loads((ROOT / p).read_text(encoding='utf-8'))
    result = plan(read('docs/data/catalog.json'), read('builder_modules/m0_scope/prototype-policy.json'),
                  read('templates/registry.json'), read('templates/scale-feasibility.json'))
    (ROOT / 'docs/data/coverage-plan.json').write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n',
                                                       encoding='utf-8', newline='\n')
    print(json.dumps(result['summary'], ensure_ascii=False))
