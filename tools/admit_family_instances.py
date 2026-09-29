"""Admit published family instances into the catalog under the explicit de-dup map.

Reads docs/data/family-workbench.json, docs/data/independent-check.json and
templates/admission-map.json. Only instances that passed the independent checker are
admitted, and only as PROVISIONAL (L0 auto-verified; L1–L3 review pending):
  new        -> new catalog record
  supersede  -> new record; the legacy rework record is archived with supersededBy
  reformat   -> no new record; linked under the active legacy record's familyVersions
Idempotent: re-running with the same inputs yields the same catalog and files.

python tools/admit_family_instances.py --date 2026-09-29
"""
import argparse
import copy
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_all import rehydrate  # noqa: E402
DOCS = ROOT / 'docs'
ASSET_DIR = 'assets/families/instances'
UNITS = {'angstrom': ' Å', 'degree': '°', 'eV': ' eV', 'nm': ' nm', 'nm^-1': ' nm⁻¹'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def option_text(options):
    return '\n'.join('%s. %s%s' % (o['label'], o['value'], UNITS.get(o.get('unit'), '')) for o in options)


def build_record(entry, family, student, teacher, numeric, check, run, date):
    cid, inst = entry['catalog_id'], entry['instance']
    files, attachments = {}, []
    for item in student['inputs']:
        lines = len(item['text'].rstrip('\n').splitlines())
        if item.get('url'):          # large input published once as a shared asset: link it, do not copy
            rel = item['url']
        else:
            rel = '%s/%s/%s' % (ASSET_DIR, cid, item['name'])
            files[rel] = item['text']
        attachments.append(dict(name=item['name'], url=rel,
                                description='%s；%s；%d 行' % (item['format'], item['unit'], lines)))
    names = '、'.join(a['name'] for a in attachments)
    instructions = ('附件：%s（均为本题完整输入）。范围：%s 只回答一个字母 A、B、C 或 D。' % (names, student['scope']))
    complete = '\n\n'.join([student['question'], '选项：\n' + option_text(student['options']), instructions])
    files['%s/%s/input.txt' % (ASSET_DIR, cid)] = complete + ''.join(
        '\n\n===== %s =====\n%s' % (i['name'], '（大文件，见附件 %s）\n' % i['url'] if i.get('url') else i['text'])
        for i in student['inputs'])
    right = next(o for o in teacher['option_audit'] if o['is_correct'])
    answer = '%s · %s' % (teacher['correct_label'], right['value'])
    rubric = '四选一：只接受单个字母 A/B/C/D（忽略大小写与首尾空白），与答案键一致即得分；不从长解释中猜选项。'
    if teacher['numeric_answer']:
        n = teacher['numeric_answer']
        unit = (' ' + n['unit'].replace('nm^-1', 'nm⁻¹')) if n['unit'] else ''       # counts (capsid T, capsomers) have no unit
        answer += '（数值作答：%s%s）' % (n['value'], unit)
        rubric += ' 数值作答形式：%d 位小数，绝对容差 %s%s。' % (n['decimals'], n['tolerance'], unit)
    record = dict(
        id=cid, title=entry['title'], paper=entry.get('paper', family['paper']), ability=teacher['ability'],
        domain=family['domain'], scale=family['scale'], reasoning=family['reasoning'], status='pending_human_audit',
        family=teacher['family'],
        missing=['L1 题型审定、L2 检查器审阅、L3 分层抽查待审核系统建成后统一进行', '尚无独立领域审核与难度测试'],
        validation='独立检查器（%s）重算并核验四个选项、答案键、学生包泄漏与来源哈希；出题端两种实现交叉复算。L0 自动核验，非专家认证。' % check['method'],
        publicDemo=True, question=student['question'], modelInput=instructions, answer=answer,
        source=teacher['source'], inputSizeNm=teacher['scales']['input_nm'], reasoningSizeNm=teacher['scales']['reasoning_nm'],
        sizeDefinition=family['sizeDefinition'], batchId=run, benchmarkReady=False,
        releaseRole='public_development_example', rubric=rubric, attribution=family['attribution'],
        batchReport='templates.html#workbench', traceUrl='templates.html?instance=%s#workbench' % inst,
        inputInstructions=instructions, sourceRoute='raw_structure_or_simulation', prototypeScreeningPassed=True,
        policyReview='暂计：题型族实例经独立检查器自动核验通过（L0）；题型与检查器尚待人工审定，未做逐题专家审核。',
        attachments=attachments, completeInput=complete, inputDownload='%s/%s/input.txt' % (ASSET_DIR, cid),
        learningObjective=family['learningObjective'], lifecycle='active', lifecycleLabel='当前原型',
        lifecycleReason='暂计入 160 原型（用户 2026-09-28 决定）：独立检查器自动核验通过；L1–L3 审核待审核系统建成后统一进行。',
        lifecycleReviewedAt=date, restartFrom='L1 题型审定 → L2 检查器审阅 → L3 分层抽查',
        admission='provisional_auto_verified', familyInstance=inst, familyRun=run, independentCheck=check['status'])
    if entry.get('supersedes'):
        record['derivedFrom'] = entry['supersedes']
    if numeric:
        record['numericVariant'] = numeric['response_format']
    return record, files


def admit(catalog, workbench, independent, amap, date):
    """Pure function: returns (new catalog, {relative asset path: text})."""
    catalog = copy.deepcopy(catalog)
    workbench = copy.deepcopy(workbench)
    rehydrate(workbench['student_packets'])     # restores 'text'; 'url' stays for shared large inputs
    teachers = {t['id']: t for t in workbench['teacher_answers']}
    students = {s['id']: s for s in workbench['student_packets']}
    numerics = {n['inputs_same_as']: n for n in workbench['numeric_student_packets']}
    checks = {r['id']: r for r in independent['results']}
    mapped = Counter(e['instance'] for e in amap['instances'])
    if set(mapped) != set(teachers) or any(v != 1 for v in mapped.values()):
        raise ValueError('Every published instance must be mapped exactly once')
    if len({e['catalog_id'] for e in amap['instances'] if e['action'] != 'reformat'}) != \
            sum(e['action'] != 'reformat' for e in amap['instances']):
        raise ValueError('Duplicate catalog id in admission map')
    records = {q['id']: q for q in catalog['questions']}
    files = {}
    for entry in amap['instances']:
        inst, cid, action = entry['instance'], entry['catalog_id'], entry['action']
        check = checks.get(inst)
        if not check or check['status'] != 'pass':
            raise ValueError('Instance did not pass the independent checker: ' + inst)
        teacher = teachers[inst]
        if action == 'reformat':
            legacy = records.get(cid)
            if not legacy or legacy['lifecycle'] != 'active' or teacher.get('legacy_qa') != cid:
                raise ValueError('Reformat target must be the active legacy record it derives from: ' + cid)
            link = dict(instance=inst, family=teacher['family'], run=workbench['run'], independentCheck=check['status'],
                        url='templates.html?instance=%s#workbench' % inst, counted=False)
            legacy['familyVersions'] = [v for v in legacy.get('familyVersions', []) if v['instance'] != inst] + [link]
            continue
        if action not in ('new', 'supersede'):
            raise ValueError('Unknown action ' + action)
        if cid in records and records[cid].get('familyInstance') != inst:
            raise ValueError('Catalog id already used by another record: ' + cid)
        # Per-instance overrides (e.g. one PDB instance in a mostly-QM7-X family) on top of family defaults.
        family = dict(amap['families'][teacher['family']],
                      **{k: entry[k] for k in ('domain', 'scale', 'reasoning', 'learningObjective', 'sizeDefinition', 'attribution') if k in entry})
        record, extra = build_record(entry, family, students[inst], teacher,
                                     numerics.get(inst), check, workbench['run'], date)
        files.update(extra)
        if action == 'supersede':
            old = records.get(entry['supersedes'])
            if not old or old['lifecycle'] not in ('rework', 'archived') or old.get('supersededBy') not in (None, cid):
                raise ValueError('Superseded record must be a rework record: ' + entry['supersedes'])
            if teacher.get('legacy_qa') != entry['supersedes']:
                raise ValueError('Instance does not derive from the superseded record')
            old.update(lifecycle='archived', lifecycleLabel='历史归档', supersededBy=cid,
                       lifecycleReason='已有新版改写 %s（题型族 %s，暂计），保留原始版本以追溯，不重复计数。' % (cid, teacher['family']),
                       restartFrom='见新版 ' + cid)
        if cid in records:
            catalog['questions'][[q['id'] for q in catalog['questions']].index(cid)] = record
        else:
            catalog['questions'].append(record)
        records[cid] = record
    catalog['lifecycleCounts'] = dict(Counter(q['lifecycle'] for q in catalog['questions']))
    catalog['counts']['candidates'] = len(catalog['questions'])
    catalog['updated'] = date
    return catalog, files


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--date', required=True)
    a = p.parse_args()
    new, files = admit(read(DOCS / 'data/catalog.json'), read(DOCS / 'data/family-workbench.json'),
                       read(DOCS / 'data/independent-check.json'), read(ROOT / 'templates/admission-map.json'), a.date)
    for rel, text in files.items():
        (DOCS / rel).parent.mkdir(parents=True, exist_ok=True)
        (DOCS / rel).write_text(text, encoding='utf-8', newline='\n')
    path = DOCS / 'data/catalog.json'
    eol = '\r\n' if b'\r\n' in path.read_bytes()[:200] else '\n'    # keep the committed line endings
    path.write_text(json.dumps(new, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline=eol)
    print(json.dumps(dict(lifecycleCounts=new['lifecycleCounts'], files=len(files)), ensure_ascii=False))
