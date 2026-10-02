"""Data for the question-generation system page (docs/system.html) -> docs/data/system.json.

  python tools/export_system.py

Hand-written content (principles, steps, routes, reproduce commands) comes from templates/system-pipeline.json;
every number, family row, file hash and source text is read from the repository at export time, so the page
cannot drift from the code. No model calls.
"""
import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checkers  # noqa: E402
import enumerators  # noqa: E402
import review_system as rs  # noqa: E402
from task_families import FAMILIES  # noqa: E402

REPO = 'https://github.com/K0NG1212/geometry-qa-builder/blob/main/'
EMBED_LIMIT = 60000          # characters; larger files are linked, not embedded
REGISTRY_KEYS = ('name', 'concept', 'physical_conditions', 'answer_method', 'distractor_mechanisms', 'validation', 'limits')


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def lines(path):
    return sum(1 for _ in path.read_text(encoding='utf-8').splitlines())


def file_entry(rel, embed=True):
    path = ROOT / rel
    if not path.exists():
        return dict(path=rel, url=REPO + rel, missing=True)
    text = path.read_text(encoding='utf-8')
    entry = dict(path=rel, url=REPO + rel, lines=len(text.splitlines()), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    if embed and rel.endswith('.py') and len(text) <= EMBED_LIMIT:
        entry['source'] = text
    return entry


def count_tests():
    n = 0
    for path in (ROOT / 'tests').glob('test_*.py'):
        n += sum(isinstance(node, ast.FunctionDef) and node.name.startswith('test_') for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))))
    return n


def build():
    content = read('templates/system-pipeline.json')
    registry = read('templates/registry.json')
    manifest = read('templates/family-manifest.json')
    catalog = read('docs/data/catalog.json')
    workbench = read('docs/data/family-workbench.json')
    check = read('docs/data/independent-check.json')
    capacity = read('docs/data/enumeration-capacity.json')
    per_family = {}
    for spec in manifest['items']:
        per_family[spec['family']] = per_family.get(spec['family'], 0) + 1
    cells, active = {}, {}
    for q in catalog['questions']:
        if q.get('lifecycle') != 'active':
            continue
        f = rs.review_form(q)
        if f['form'] != 'legacy':
            cells.setdefault(f['unit'], set()).add('%s %s' % (q['domain'], rs.cell(q.get('reasoningSizeNm'))))
            active[f['unit']] = active.get(f['unit'], 0) + 1
    methods = {r['id']: r.get('method') for r in check['results']}
    first = {}
    for t in workbench['teacher_answers']:
        first.setdefault(t['family'], t['id'])
    families = []
    for name, info in FAMILIES.items():
        row = rs.registry_row(registry, name) or {}
        fn = checkers.CHECKERS.get(name)
        module = info['module'].split('/')[-1]
        example = first.get(name)
        families.append(dict(
            id=name, ability=info['ability'], output=info['output'], version=info['version'], module=info['module'],
            module_url=REPO + info['module'], route=content['module_routes'].get(module, 'general'),
            registry_id=row.get('id'), registry={k: row.get(k) for k in REGISTRY_KEYS if row.get(k) not in (None, '', [])},
            checker=fn and '%s:%s' % (fn.__module__.replace('.', '/') + '.py', fn.__name__),
            checker_url=fn and REPO + fn.__module__.replace('.', '/') + '.py',
            instances=per_family.get(name, 0), active=active.get(name, 0), cells=sorted(cells.get(name, [])),
            enumerator=name in enumerators.ENUMERATORS, example=example, checker_method=methods.get(example)))
    code_files = sorted(ROOT.glob('task_families/*.py')) + sorted(ROOT.glob('checkers/*.py'))
    report = workbench['report']
    summary = dict(
        families=len(FAMILIES), checkers=sum(f in checkers.CHECKERS for f in FAMILIES),
        family_modules=len({f['module'] for f in families}),
        manifest_instances=len(manifest['items']), run=workbench['run'], attempted=report['attempted'], passed=report['passed'],
        failures=report['failures'], independent_checked=check['checked'], independent_passed=check['passed'],
        tests=count_tests(), code_lines=sum(lines(p) for p in code_files),
        generator_lines=sum(lines(p) for p in code_files if p.parent.name == 'task_families'),
        checker_lines=sum(lines(p) for p in code_files if p.parent.name == 'checkers'),
        abilities={a: sum(f['ability'] == a for f in families) for a in ('perception', 'inference', 'design')},
        routes={k: sum(f['route'] == k for f in families) for k in content['routes']},
        enumerated_families=sorted(enumerators.ENUMERATORS), model_calls=0)
    steps = [dict(s, files=[file_entry(rel) for rel in s['files']]) for s in content['steps']]
    return dict(kind='system_page', summary=summary, principles=content['principles'], stages=content['stages'], steps=steps,
                routes=content['routes'], families=families, capacity=capacity, reproduce=content['reproduce'],
                repo=REPO.rsplit('/blob/', 1)[0])


if __name__ == '__main__':
    data = build()
    (ROOT / 'docs/data/system.json').write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(data['summary'], ensure_ascii=False))
