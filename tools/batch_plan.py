"""Gap analysis for batch production under templates/batch-selection-rule.json (provisional rule).

  python tools/batch_plan.py            # -> docs/data/batch-plan.json

For every cell it pools (a) admitted family questions (catalog, family form) and (b) the enumeration capacity
estimate (docs/data/enumeration-capacity.json, per family x structure x cell), keyed by family and source
(structure or paper). The diversity caps act together and are summed, not multiplied: each family x source pair,
each family and each source has its own ceiling. The largest selectable number of questions under all caps is a
maximum flow  target -> family (<= max_per_family) -> source (<= max_per_family_source per pair) -> sink
(<= max_per_source per source). The report lists, per cell, how far the current data are from the rule.
Enumeration figures are estimates (sample acceptance scaled to all proposals); nothing here admits questions.
"""
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import review_system as rs  # noqa: E402
from task_families import FAMILIES  # noqa: E402

ABILITIES = ('perception', 'inference', 'design')


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def route_of(family, routes):
    return routes.get(FAMILIES[family]['module'].split('/')[-1], 'general')


def source_of(spec, paper, route):
    """One key per independent source: the paper for paper-parameter and evidence routes, otherwise the structure."""
    if route in ('paper', 'evidence'):
        return paper or 'unknown-paper'
    if spec.get('pdb'):
        return spec['pdb']
    m = re.search(r'COD (\d+)', spec.get('name', ''))
    if m:
        return 'COD' + m.group(1)
    stem = spec['asset'].rsplit('/', 1)[-1].split('.')[0]
    if spec['asset'].startswith('assets/materials/'):
        return 'COD' + stem
    if spec['asset'].startswith('assets/families/assemblies/'):
        return stem.split('-')[0]
    m = re.search(r'QM7X?-?(\d{4})|-(7\d{3})-', spec['asset'])
    if m:
        return 'QM7X-' + (m.group(1) or m.group(2))
    if 'hostguest' in spec['asset'] or stem in ('BCD', 'WP6', 'DMBCD'):
        return 'SAMPL9-' + stem.replace('WP6-', 'WP6-')
    return stem


def normalise_structure(name):
    """Enumeration rows use PDB / COD / molecule / assembly ids; align them with source_of."""
    name = name[:-2] if name.endswith('-T') else name
    if name.isdigit():
        return 'COD' + name
    if name.startswith('SAMPL9-WP6-'):
        return 'SAMPL9-' + name[len('SAMPL9-'):]
    return name


def pools(rule):
    """{cell: {(family, source): available}} plus ability and route per family."""
    routes = read('templates/system-pipeline.json')['module_routes']
    manifest = {s['id']: s for s in read('templates/family-manifest.json')['items']}
    catalog = read('docs/data/catalog.json')
    out = defaultdict(lambda: defaultdict(float))
    origin = defaultdict(lambda: defaultdict(float))
    for q in catalog['questions']:
        if q.get('lifecycle') != 'active':
            continue
        f = rs.review_form(q)
        if f['form'] == 'legacy' or f['instance'] not in manifest:
            continue
        family = f['unit']
        cell = '%s %s' % (q['domain'], rs.cell(q.get('reasoningSizeNm')))
        src = source_of(manifest[f['instance']], q.get('paper'), route_of(family, routes))
        out[cell][(family, src)] += 1
        origin[cell]['admitted'] += 1
    cap = read('docs/data/enumeration-capacity.json')
    for r in cap['rows']:
        accepted = sum(r.get('cells', {}).values())
        if not accepted:
            continue
        for cell, n in r['cells'].items():
            share = r['estimated_admissible'] * n / accepted
            out[cell][(r['family'], normalise_structure(r['structure']))] += share
            origin[cell]['enumerated'] += share
    return out, origin, routes


def max_flow(pairs, caps, target, families=None):
    """Largest selection under the pair / family / source caps. Returns (total, flow per family, flow per source)."""
    graph = defaultdict(dict)

    def edge(u, v, c):
        graph[u][v] = graph[u].get(v, 0) + c
        graph[v].setdefault(u, 0)

    edge('S0', 'S', target)
    for (fam, src), avail in pairs.items():
        if families is not None and fam not in families:
            continue
        n = int(min(avail, caps['max_per_family_source']))
        if n <= 0:
            continue
        if ('f', fam) not in graph['S']:           # family and source ceilings are set once, not once per pair
            edge('S', ('f', fam), caps['max_per_family'])
        if 'T' not in graph[('s', src)]:
            edge(('s', src), 'T', caps['max_per_source'])
        edge(('f', fam), ('s', src), n)
    total = 0
    while True:                                   # Edmonds-Karp on a graph of a few hundred nodes
        parent = {'S0': None}
        queue = deque(['S0'])
        while queue and 'T' not in parent:
            u = queue.popleft()
            for v, c in graph[u].items():
                if c > 0 and v not in parent:
                    parent[v] = u
                    queue.append(v)
        if 'T' not in parent:
            break
        path, v = [], 'T'
        while parent[v] is not None:
            path.append((parent[v], v))
            v = parent[v]
        push = min(graph[u][v] for u, v in path)
        for u, v in path:
            graph[u][v] -= push
            graph[v][u] += push
        total += push
    fam_flow = {k[1]: graph[k]['S'] for k in graph if isinstance(k, tuple) and k[0] == 'f' and graph[k].get('S')}
    src_flow = {k[1]: graph['T'][k] for k in graph['T'] if isinstance(k, tuple) and graph['T'].get(k)}
    return total, fam_flow, src_flow


def plan(rule=None):
    rule = rule or read('templates/batch-selection-rule.json')
    pool, origin, routes = pools(rule)
    share = rule['ability_share']
    cells, paper_total, grand, grand_balanced = [], 0, 0, 0
    for cell, tier in rule['cells'].items():
        caps = rule['tiers'][tier]
        pairs = {k: v for k, v in pool.get(cell, {}).items() if v >= 1}
        fams = sorted({f for f, _ in pairs})
        srcs = sorted({s for _, s in pairs})
        by_ability = {a: sorted(f for f in fams if FAMILIES[f]['ability'] == a) for a in ABILITIES}
        systems = sorted({FAMILIES[f]['module'].split('/')[-1] for f in fams if route_of(f, routes) == 'paper'})
        total, fam_flow, src_flow = max_flow(pairs, caps, caps['target'])
        need_ability = int(caps['target'] * (share['target'] - share['tolerance']))
        ability_max = {a: max_flow(pairs, caps, caps['target'], set(by_ability[a]))[0] for a in ABILITIES}
        paper = sum(v for f, v in fam_flow.items() if route_of(f, routes) == 'paper')
        paper_total += paper
        grand += total
        # With the ability rule: no ability may exceed (1/3 + tolerance) of the target, so a cell short in one ability
        # cannot be filled up with another.
        ceiling = int(caps['target'] * (share['target'] + share['tolerance']))
        balanced = min(total, sum(min(ability_max[a], ceiling) for a in ABILITIES))
        grand_balanced += balanced
        gaps = []
        if total < caps['target']:
            gaps.append('最多只能选 %d / %d 道' % (total, caps['target']))
        if len(fams) < caps['min_families']:
            gaps.append('题型族 %d 个，需 ≥ %d' % (len(fams), caps['min_families']))
        for a in ABILITIES:
            if len(by_ability[a]) < caps['min_families_per_ability']:
                gaps.append('%s 族 %d 个，需 ≥ %d' % ({'perception': '感知', 'inference': '推断', 'design': '设计'}[a],
                                                    len(by_ability[a]), caps['min_families_per_ability']))
            if ability_max[a] < need_ability:
                gaps.append('%s 最多 %d 道，需 ≥ %d' % ({'perception': '感知', 'inference': '推断', 'design': '设计'}[a],
                                                     ability_max[a], need_ability))
        if len(srcs) < caps['min_sources']:
            gaps.append('来源 %d 个，需 ≥ %d' % (len(srcs), caps['min_sources']))
        if caps.get('min_systems') and len(systems) < caps['min_systems']:
            gaps.append('论文参数体系 %d 个，需 ≥ %d' % (len(systems), caps['min_systems']))
        cells.append(dict(cell=cell, tier=tier, target=caps['target'], max_selectable=total, max_balanced=balanced, families=len(fams),
                          families_by_ability={a: len(v) for a, v in by_ability.items()}, sources=len(srcs), paper_systems=systems,
                          ability_max=ability_max, pool=dict(admitted=round(origin[cell]['admitted']), enumerated=round(origin[cell]['enumerated'])),
                          family_flow={k: v for k, v in sorted(fam_flow.items(), key=lambda kv: -kv[1])},
                          meets_rule=not gaps, gaps=gaps))
    target = sum(c['target'] for c in cells)
    summary = dict(target=target, max_selectable=grand, max_balanced=grand_balanced, cells_meeting_rule=sum(c['meets_rule'] for c in cells),
                   paper_parameter_share_of_selectable=round(paper_total / grand, 3) if grand else None,
                   max_paper_parameter_share=rule['global']['max_paper_parameter_share'])
    return dict(kind='batch_plan', rule_version=rule['version'], status=rule['status'], status_note=rule['status_note'],
                enumeration_run=read('docs/data/enumeration-capacity.json')['run'], summary=summary, cells=cells,
                rule={k: rule[k] for k in ('tiers', 'ability_share', 'global', 'rationale', 'pending_advisor')},
                note='Pools combine admitted family questions and enumeration estimates; the maximum is computed under the '
                     'per-cell caps only (the global per-source and per-family caps are applied at actual selection).')


if __name__ == '__main__':
    out = plan()
    (ROOT / 'docs/data/batch-plan.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(out['summary'], ensure_ascii=False))
    for c in out['cells']:
        print('%-20s %s %3d/%3d (balanced %3d) fam %2d src %3d %s' % (c['cell'], c['tier'], c['max_selectable'], c['target'], c['max_balanced'],
                                                                    c['families'], c['sources'],
                                                     '; '.join(c['gaps']) or 'OK'))
