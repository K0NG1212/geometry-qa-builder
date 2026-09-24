"""Run reusable task families over a manifest of real inputs: define -> construct -> verify.

No model/API calls. Every instance is built by its family function, all four options
are verified, and student packets (no answers, evidence or mechanisms) are written
separately from reviewer packets. Output directories are never overwritten.
Development pilots only: nothing here admits questions to the catalog.

python family_engine.py --manifest templates/family-manifest.json --out runs/family-new --seed geobench-family-v1
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from task_families import FAMILIES, kit

ROOT = Path(__file__).resolve().parent
VERSION = '0.1.0'
MODULES = {
    'M0': '范围与尺度：spec.scope + scales（输入尺度、推理尺度定义）',
    'M1': '材料：docs/assets 输入、来源、许可与 SHA-256',
    'M2': '证据：计算器复核或数据集性质记录（审核侧）',
    'M3': '题型契约：registry.json 中的族定义与适用条件',
    'M4': '构造：族函数生成题干、正确值与候选错误机制',
    'M5': '质量：四项逐一核验、唯一性、分隔、捷径诊断',
    'M6': '导出：学生包 / 审核包分离与运行快照',
}


def code_files():
    files = sorted((ROOT / 'task_families').glob('*.py')) + [ROOT / 'family_engine.py', ROOT / 'template_engine.py',
                                                              ROOT / 'tools/recompute_materials_batch.py']
    return {str(p.relative_to(ROOT)).replace('\\', '/'): p for p in files}


def build_instance(spec, seed):
    family = FAMILIES[spec['family']]
    if not spec.get('scope', '').strip() or not spec.get('source', '').strip():
        raise ValueError('Missing scope or source')
    asset = (ROOT / 'docs' / spec['asset']).resolve()
    if not asset.is_relative_to((ROOT / 'docs/assets').resolve()):
        raise ValueError('Asset must stay inside docs/assets')
    return family, family['build'](spec, ROOT, seed)


def run(manifest_path, out, seed='geobench-family-v1'):
    manifest_path, out = Path(manifest_path), Path(out)
    if out.exists():
        raise ValueError('Output exists; use a new directory to preserve history')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    ids = [x['id'] for x in manifest['items']]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Empty batch or duplicate ID')
    students, numeric_students, teachers, stages, failures = [], [], [], [], []
    counters = Counter()
    for spec in manifest['items']:
        # Batch-level balance: within each family, correct positions cycle A..D from a seeded offset.
        offset = kit.digest(seed, spec['family'], 'offset')[0] % 4
        spec = dict(spec, target_position=1 + (offset + counters[spec['family']]) % 4)
        counters[spec['family']] += 1
        try:
            family, built = build_instance(spec, seed)
        except (ValueError, KeyError) as error:
            failures.append(dict(id=spec['id'], family=spec['family'], stage='construct/verify', reason=str(error)))
            continue
        students.append(dict(id=spec['id'], family=spec['family'], ability=family['ability'],
                             question=built['question'], scope=built['scope'], inputs=built['inputs'],
                             options=built['options'], response_format='one label: A/B/C/D'))
        if built['numeric']:
            n = built['numeric']
            numeric_students.append(dict(id='N-' + spec['id'], family=spec['family'], ability=family['ability'],
                                         question=built['question'], scope=built['scope'], inputs=built['inputs'],
                                         response_format=dict(value='one number rounded to %d decimals' % n['decimals'],
                                                              unit=n['unit'])))
        shortcuts = None
        if built['rank']:
            pairs = [(o['label'], o['value']) for o in built['options']]
            shortcuts = dict(kit.rank_shortcuts(pairs, built['correct_label']),
                             mirror_pair_cue=kit.mirror_pair_cue(pairs, built['correct_label']))
        teachers.append(dict(id=spec['id'], family=spec['family'], family_version=family['version'],
                             ability=family['ability'], correct_label=built['correct_label'],
                             numeric_answer=built['numeric'], option_audit=built['option_audit'],
                             excluded_candidates=built['excluded_candidates'], rank=built['rank'],
                             rank_shortcuts=shortcuts, checks=built['checks'], scales=built['scales'],
                             source=spec['source'], license=spec.get('license', ''), legacy_qa=spec.get('legacy_qa'),
                             input_hashes=built['input_hashes'], seed=seed, target_position=spec['target_position'],
                             option_order='numeric ascending (label = rank)' if built['rank'] else 'correct at batch-balanced target; others sha256-sorted',
                             human_review='pending', catalog_admitted=False))
        stages.append(dict(id=spec['id'], family=spec['family'],
                           define=dict(family=spec['family'], version=family['version'], ability=family['ability'],
                                       output=family['output'], module=family['module']),
                           construct=dict(inputs=[dict(name=i['name'], format=i['format'], chars=len(i['text']))
                                                  for i in built['inputs']],
                                          candidates_considered=len(built['option_audit']) + len(built['excluded_candidates'])),
                           verify=dict(four_options_verified=True, unique_correct=True, correct_label=built['correct_label'],
                                       checks=sorted(k for k, v in built['checks'].items() if v is True)),
                           modules=MODULES))
    positions = Counter(t['correct_label'] for t in teachers)
    by_family = {}
    for t in teachers:
        f = by_family.setdefault(t['family'], dict(passed=0, shortcut_hits=Counter()))
        f['passed'] += 1
        for k, v in (t['rank_shortcuts'] or {}).items():
            f['shortcut_hits'][k] += int(v)
    for f in failures:
        by_family.setdefault(f['family'], dict(passed=0, shortcut_hits=Counter()))
    for name, f in by_family.items():
        f['attempted'] = sum(1 for s in manifest['items'] if s['family'] == name)
        f['shortcut_hits'] = dict(f['shortcut_hits'])
    code = code_files()
    report = dict(version=VERSION, kind='reusable_family_development_pilot', seed=seed,
                  attempted=len(ids), passed=len(teachers), failures=failures, model_calls=0,
                  catalog_admitted=0, human_review='pending', by_family=by_family,
                  correct_position_counts={l: positions.get(l, 0) for l in kit.LABELS},
                  manifest_sha256=kit.sha256(manifest_path.read_bytes()),
                  registry_sha256=kit.sha256((ROOT / 'templates/registry.json').read_bytes()),
                  code_sha256={k: kit.sha256(p.read_bytes()) for k, p in code.items()},
                  difficulty_note='程序通过只说明四项已核验且唯一正确；难度、迷惑性与科学意义仍需人工审核与模型实验。',
                  limits='开发试跑，不计入题库；模板与来源选择待人工审核。')
    out.mkdir(parents=True)
    for name, data in [('student-packets.json', students), ('numeric-student-packets.json', numeric_students),
                       ('private-answers.json', teachers), ('stage-records.json', stages), ('verification.json', report)]:
        (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    snap = out / 'snapshot'
    for rel, p in code.items():
        (snap / rel).parent.mkdir(parents=True, exist_ok=True)
        (snap / rel).write_bytes(p.read_bytes())
    (snap / 'manifest.json').write_bytes(manifest_path.read_bytes())
    (snap / 'registry.json').write_bytes((ROOT / 'templates/registry.json').read_bytes())
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', default='geobench-family-v1')
    a = p.parse_args()
    r = run(a.manifest, a.out, a.seed)
    print(json.dumps(dict(attempted=r['attempted'], passed=r['passed'], failures=r['failures'],
                          positions=r['correct_position_counts'], model_calls=0), ensure_ascii=False))
