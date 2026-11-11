"""The arithmetic of 3000 questions, recomputed from the data rather than remembered.

The number the advisor asked for (3000 evaluation questions) is not reached by working harder at the current
rules: three separate ceilings bite first, and each one is a number in a file here, not an opinion. This tool
recomputes all three from docs/data/enumeration-capacity.json (run enum-v34), docs/data/batch-plan.json and
the published bank, writes them to docs/data/scale-plan.json, and refreshes the table inside
MEETING_2026-11-04.md between its markers, so the meeting sheet cannot drift from the data.

What the three ceilings are:

  per source   each source structure may give at most max_per_source questions. With 78 structures the whole
               enumeration yields 557 (cap 8) or 978 (cap 15) -- the binding limit is how many structures we
               have, not how many questions the enumerators can propose (27634 estimated admissible).
  per family   max_per_family 60 across 52 families is 3120, which leaves 3000 no slack at all, and only 19
               families have an enumerator, so those 19 cannot carry more than 1140 between them.
  per paper    the paper-driven families yield about 4 questions per paper. "30% from papers" = 900 questions
               = about 223 papers of hand-made cards.

    python tools/export_scale_plan.py
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import enumerators  # noqa: E402
TARGET = 3000
MEETING = ROOT / 'MEETING_2026-11-04.md'
BEGIN, END = '<!-- scale-plan:begin -->', '<!-- scale-plan:end -->'
# Sources whose questions come from a database or a published dataset; the rest are paper-driven, and the
# difference is what sets how many papers "30% from papers" would need.
DATABASES = {'pdb-bio-nm', 'pdb-dna-origami', 'pdb-1aa5-vancomycin', 'cod-materials-cell', 'cod-mof',
             'qm7x', 'oe62', 'sampl9', 'paper-landscape17-azobenzene'}


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def build():
    catalog = read('docs/data/catalog.json')
    workbench = read('docs/data/family-workbench.json')
    capacity = read('docs/data/enumeration-capacity.json')
    plan = read('docs/data/batch-plan.json')
    selection_rule = read('templates/batch-selection-rule.json')
    progress = read('docs/data/prototype-progress.json')
    packets = {p['id']: p for p in workbench['student_packets']}
    questions = [q for q in catalog['questions']
                 if q.get('lifecycle') == 'active' and q.get('familyInstance')]
    families = {packets[q['familyInstance']]['family'] for q in questions}

    per_structure = {}
    for row in capacity['rows']:
        per_structure[row['structure']] = per_structure.get(row['structure'], 0) + row['estimated_admissible']
    caps = []
    # The actual global source cap is eight. Keep fifteen as a clearly hypothetical
    # comparison with the former rule so the meeting table still shows its effect.
    for cap in (selection_rule['global']['max_per_source'], 15):
        total = sum(min(cap, v) for v in per_structure.values())
        yield_each = total / len(per_structure)
        caps.append(dict(max_per_source=cap, questions=total, structures=len(per_structure),
                         per_structure=round(yield_each, 2),
                         structures_for_target=round(TARGET / yield_each),
                         more_structures_needed=round(TARGET / yield_each) - len(per_structure)))

    implemented = set(enumerators.ENUMERATORS)
    productive = {row['family'] for row in capacity['rows'] if row['accepted'] > 0}
    exhausted = set(capacity['families']['exhausted']) & implemented
    unprobed = set(capacity['families']['unprobed']) & implemented
    database_only, paper_only, mixed = set(), set(), set()
    for family in sorted(families):
        kinds = {q['paper'] in DATABASES for q in questions
                 if packets[q['familyInstance']]['family'] == family}
        (database_only if kinds == {True} else paper_only if kinds == {False} else mixed).add(family)
    truly_missing = database_only - implemented
    paper_questions = [q for q in questions if q['paper'] not in DATABASES]
    papers = {q['paper'] for q in paper_questions}
    per_paper = len(paper_questions) / len(papers)
    paper_share = selection_rule['global']['max_paper_parameter_share']

    family_cap = selection_rule['global']['max_per_family']
    return dict(
        kind='scale_plan', date=date.today().isoformat(), target=TARGET,
        bank=dict(run=workbench['run'], questions=len(questions), families=len(families),
                  cells=len(progress['cells']), cell_target=progress['cells'][0]['target']),
        gap=TARGET - len(questions),
        enumeration=dict(run=capacity['run'], proposals=capacity['totals']['proposals'],
                         sampled=capacity['totals']['sampled'], accepted=capacity['totals']['accepted'],
                         estimated_admissible=capacity['totals']['estimated_admissible'],
                         structures=len(per_structure),
                         structures_by_kind={k: len(v) for k, v in capacity['structures'].items()}),
        source_caps=caps,
        family_cap=dict(max_per_family=family_cap, families=len(families),
                        ceiling=family_cap * len(families),
                        per_family_for_target=round(TARGET / len(families), 1),
                        implemented_enumerator_families=len(implemented),
                        implemented_enumerator_ceiling=family_cap * len(implemented),
                        database_enumerator_productive=sorted(database_only & productive),
                        database_enumerator_exhausted=sorted(database_only & exhausted),
                        database_enumerator_unprobed=sorted(database_only & unprobed),
                        database_no_enumerator=sorted(truly_missing),
                        paper_driven=len(paper_only)),
        papers=dict(questions=len(paper_questions), papers=len(papers), per_paper=round(per_paper, 2),
                    share_cap=paper_share,
                    questions_at_share=round(TARGET * 0.30),
                    papers_at_share=round(TARGET * 0.30 / per_paper),
                    papers_at_rule_cap=round(TARGET * paper_share / per_paper)),
        selection_rule=dict(file='docs/data/batch-plan.json', version=plan['rule_version'],
                            status=plan['status'], target=plan['summary']['target'],
                            max_selectable=plan['summary']['max_selectable'],
                            note='选题规则现在的目标是 %d 道，不是 %d 道：R1 要按新目标重写'
                                 % (plan['summary']['target'], TARGET)),
        levers=[
            dict(id='R1', what='改每族 60 道的全局上限',
                 why='不改，上限就是 %d 道，%d 道没有余量（等于每族 %s 道）'
                     % (family_cap * len(families), TARGET, round(TARGET / len(families), 1)),
                 blocked_on='导师对 Q2 的答复'),
            dict(id='A1', what='来源结构从 %d 个扩到 %d 个左右' % (len(per_structure), caps[0]['structures_for_target']),
                 why='PDB / COD 来源可持续补充，但当前 60 道族上限与来源 8 道上限使新增结构的边际产出明显低于历史均值',
                 blocked_on='PDB、COD、Europe PMC 开放获取全文已有长期下载授权；新增站点及受限内容另核许可'),
            dict(id='E1', what='给 %d 个数据库驱动但没有枚举器的族写枚举器' % len(truly_missing),
                 why='写了就能跟结构一起扩，等于提高每个结构的产出，少下载一批结构',
                 blocked_on='不卡'),
            dict(id='Q2', what='确认「论文题 30%」',
                 why='按 30%% 要 %d 道论文题 ≈ %d 篇论文的手工卡，做不到；改成固定 300 道则现有 %d 篇够起步'
                     % (round(TARGET * 0.30), round(TARGET * 0.30 / per_paper), len(papers)),
                 blocked_on='导师'),
        ])


def table(plan):
    """The meeting table, as markdown. Every number in it comes from `plan`."""
    caps = {c['max_per_source']: c for c in plan['source_caps']}
    low, high = sorted(caps)
    rows = [
        ('枚举出的候选 / 抽样验过 / 估计可入库',
         '%d / %d / %d' % (plan['enumeration']['proposals'], plan['enumeration']['accepted'],
                           plan['enumeration']['estimated_admissible']), '原始产能不缺'),
        ('但按暂定规则 `max_per_source = %d` 封顶' % low, '**%d**' % caps[low]['questions'],
         '产能被来源数卡住，不是被枚举卡住'),
        ('假设放宽到 `max_per_source = %d`' % high, '%d' % caps[high]['questions'], '仍不够 %d' % plan['target']),
        ('现有来源结构',
         '%d 个（%s）' % (plan['enumeration']['structures'],
                         ' + '.join('%s %d' % (k, v)
                                    for k, v in plan['enumeration']['structures_by_kind'].items())),
         '每个结构现在出 %.2f 道（按 %d 封顶）；%d 道要 ≈ %d 个结构（按 %d）或 ≈ %d 个（按 %d）'
         % (caps[low]['per_structure'], low, plan['target'], caps[low]['structures_for_target'], low,
            caps[high]['structures_for_target'], high)),
        ('全局 `max_per_family = %d` × %d 族' % (plan['family_cap']['max_per_family'],
                                                plan['family_cap']['families']),
         '**%d**' % plan['family_cap']['ceiling'],
         '%d 道等于每族做满 %s 道，几乎没有余量' % (plan['target'], plan['family_cap']['per_family_for_target'])),
        ('已有枚举器的族',
         '%d 族（× %d = %d）' % (plan['family_cap']['implemented_enumerator_families'],
                                plan['family_cap']['max_per_family'], plan['family_cap']['implemented_enumerator_ceiling']),
         '容量探针有产出 %d 族、exhausted %d 族、未探测 %d 族' %
         (len(plan['family_cap']['database_enumerator_productive']),
          len(plan['family_cap']['database_enumerator_exhausted']),
          len(plan['family_cap']['database_enumerator_unprobed']))),
        ('数据库驱动但确实没有枚举器的族',
         '%d 族' % len(plan['family_cap']['database_no_enumerator']),
         '、'.join(plan['family_cap']['database_no_enumerator'])),
        ('论文驱动的族',
         '**%d 族，每篇论文只出 %.2f 道**' % (plan['family_cap']['paper_driven'], plan['papers']['per_paper']),
         '要 %d 道论文题（导师说的 30%%）≈ %d 篇论文的手工卡，做不到'
         % (plan['papers']['questions_at_share'], plan['papers']['papers_at_share'])),
        ('现在的选题规则（%s，%s）' % (plan['selection_rule']['version'], plan['selection_rule']['status']),
         '目标 %d 道' % plan['selection_rule']['target'], plan['selection_rule']['note']),
        ('已入库 / 还差', '%d / **%d**' % (plan['bank']['questions'], plan['gap']),
         '%d 道分在 %d 格，每格目标 %d 道' % (plan['bank']['questions'], plan['bank']['cells'],
                                           plan['bank']['cell_target'])),
    ]
    out = ['| 事实 | 数字 | 含义 |', '|---|---|---|']
    out += ['| %s | %s | %s |' % row for row in rows]
    out += ['', '**四条能动的杠杆**（按影响排序）：', '']
    out += ['| 代号 | 做什么 | 为什么 | 卡在谁 |', '|---|---|---|---|']
    out += ['| %s | %s | %s | %s |' % (l['id'], l['what'], l['why'], l['blocked_on']) for l in plan['levers']]
    return '\n'.join(out)


def main():
    plan = build()
    out = ROOT / 'docs/data/scale-plan.json'
    out.write_bytes((json.dumps(plan, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    if MEETING.exists():
        text = MEETING.read_text(encoding='utf-8')
        block = '%s\n\n%s\n\n%s' % (BEGIN, table(plan), END)
        text = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END), lambda m: block, text, flags=re.S)
        MEETING.write_bytes(text.replace('\r\n', '\n').encode('utf-8'))
    print('Scale plan: %d admitted, target %d, gap %d; caps %s' %
          (plan['bank']['questions'], plan['target'], plan['gap'],
           '，'.join('%d→%d 道' % (c['max_per_source'], c['questions']) for c in plan['source_caps'])))
    print('Ceilings: 每族 %d × %d 族 = %d；可枚举 %d 族 = %d；论文 %.2f 道/篇' %
          (plan['family_cap']['max_per_family'], plan['family_cap']['families'], plan['family_cap']['ceiling'],
           plan['family_cap']['implemented_enumerator_families'], plan['family_cap']['implemented_enumerator_ceiling'],
           plan['papers']['per_paper']))


if __name__ == '__main__':
    main()
