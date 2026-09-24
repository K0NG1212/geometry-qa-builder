"""Derive docs/data/task-coverage.json from the single source of truth.

Definitions come only from templates/registry.json. Instance counts come from the
published development records (family-workbench.json, choice-workbench.json) and the
focused screening; nothing here edits definitions.

python tools/export_coverage.py
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cell(nm):
    for lo, hi, name in ((0.1, 1, '0.1-1'), (1, 10, '1-10'), (10, 100, '10-100'), (100, 1000, '100-1000')):
        if lo <= nm < hi:
            return name
    return 'below-0.1' if nm < 0.1 else 'above-1000'


def build():
    read = lambda p: json.loads((ROOT / p).read_text(encoding='utf-8'))
    registry = read('templates/registry.json')
    screening = read('docs/data/focused-screening.json')
    families = read('docs/data/family-workbench.json')
    legacy_choice = read('docs/data/choice-workbench.json')
    decisions = {x['id']: x['decision'] for x in screening['items']}
    by_engine = {}
    for t in families['teacher_answers']:
        by_engine.setdefault(t['family'], []).append(t)
    failures = Counter(f['family'] for f in families['report']['failures'])
    owners = Counter(f for t in registry['templates'] for f in t['engine_families'])
    rows = []
    for t in registry['templates']:
        # A family engine shared by several rows (extent_choice_v2) is split by the legacy QA it derives from.
        instances = [x for f in t['engine_families'] for x in by_engine.get(f, [])
                     if owners[f] == 1 or x['legacy_qa'] in t['legacy_qa']]
        cells = sorted({cell(x['scales']['reasoning_nm']) for x in instances})
        legacy = Counter(decisions[q] for q in t['legacy_qa'])
        rows.append(dict(
            {k: t[k] for k in ('id', 'name', 'ability', 'status', 'priority', 'concept', 'domains', 'input_scale',
                               'reasoning_scale', 'scale_cells', 'scale_limits', 'inputs', 'physical_conditions',
                               'output_forms', 'source_basis', 'answer_method', 'distractor_mechanisms',
                               'four_choice_validation', 'legacy_families', 'legacy_qa', 'code', 'tests',
                               'builder_modules', 'gap', 'engine_families')},
            instance_ids=[x['id'] for x in instances],
            instance_count=len(instances),
            instance_failures=sum(failures[f] for f in t['engine_families']),
            instance_reasoning_cells=cells,
            legacy_decisions=dict(legacy),
            legacy_choice_v01=sum(1 for x in legacy_choice['teacher_answers'] if x['template'] == t['id'])))
    status = Counter(r['status'] for r in rows)
    ability = {a: dict(Counter(r['status'] for r in rows if r['ability'] == a)) for a in registry['axes']['ability']}
    summary = dict(types_defined=len(rows), types_with_running_code=sum(r['status'] in ('implemented', 'pilot') for r in rows),
                   status=dict(status), by_ability=ability,
                   development_instances=families['report']['passed'], instance_failures=len(families['report']['failures']),
                   legacy_candidates=len(decisions), legacy_decisions=dict(Counter(decisions.values())),
                   note='“支持的题型”与“已生成实例”分开计数；全部实例待人工审核，未计入题库配额。')
    return dict(version=registry['version'], updated=registry['updated'], axes=registry['axes'], summary=summary,
                family_run=families['run'], rows=rows)


if __name__ == '__main__':
    data = build()
    path = ROOT / 'docs/data/task-coverage.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(path, json.dumps(data['summary'], ensure_ascii=False))
