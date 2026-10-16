"""Format check of every active question (sixth advisor meeting: "list every format problem, then check them one by one").

  python tools/format_check.py      # -> docs/data/format-check.json

Automatic rules run on the card data (docs/data/cards.json) and the catalogue; REVIEWED holds findings that a rule
cannot see (checked by hand on 2026-10-13, e.g. a duplicate confirmed by comparing coordinates). Read-only: nothing in
the catalogue changes. Severity: high = fix before formal use; medium = format the benchmark should not keep;
low = acceptable, but the reviewer should know.
"""
import json
import re
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = 'docs/data/format-check.json'
RULES = {
    'not_four_choice': ('high', '不是四选一', '原为数值或文字作答，没有经独立检查的四选一版本。'),
    'formula_given': ('high', '题干直接给出公式和参数，不需要几何', '只需代入计算，附件结构不起作用，不满足“必须用到几何信息”。'),
    'duplicate': ('high', '与另一道题重复', '问的是同一个几何量、答案相同。'),
    'multi_part': ('medium', '一题多问', '一道题要求多个数值或多项结论，评分按多个得分点。'),
    'needs_explanation': ('medium', '要求文字解释', '含“解释 / 是否能说明”一类开放问题，不能自动判分。'),
    'binary_inside': ('medium', '内含二选一', '题中有“哪一个 / 两者中谁 / 反对还是增强”这类只有两个答案的判断。'),
    'main_record_old_format': ('low', '主记录仍是旧题干', '已有经独立检查的四选一版本，但题库主记录、问题池详情仍显示旧的数值 / 文字题干。'),
    'two_binaries_combined': ('low', '两个二选一拼成四选一', '四个选项是两个二元判断的组合；猜对率仍是 1/4，但审核时要知道。'),
    'mirror_pair': ('low', '选项中正负成对', '正确值与其相反数同时出现，提示答案在两者之一。'),
    'precision_collapse': ('low', '报告精度下数值相同', '要求的小数位数下，不同的量四舍五入后相同，区分度低。'),
}
# Findings confirmed by hand (2026-10-13). Each entry: rule, note.
REVIEWED = {
    'CNP005': [('duplicate', '与 CNP001 重复：DM-β-CD 附件与 β-CD 附件有 133 个原子坐标逐位相同，所问 C4–O3–C37 键角两题都是 116.0251189°。')],
    'MNP008': [('formula_given', '题干给出 a = 16.8303 Å 与 d = a/√(h²+k²+l²)，答案只需代入；不读附件即可作答。')],
    'MNP009': [('formula_given', '题干给出 a = 25.8247 Å 与 d = a/√(h²+k²+l²)，答案只需代入；不读附件即可作答。')],
    'CNP006': [('precision_collapse', '两个 C–O 键长 1.4275 Å 与 1.4309 Å 在要求的两位小数下都是 1.43 Å。')],
}
# Suggested treatment for questions without a four-choice version (by hand, using families that already exist).
SUGGEST = {
    'CNP003': '改用命名键长族（named_bond_distance）出四选一，取代旧题。',
    'CNP005': '与 CNP001 重复，建议归档；DM-β-CD 另选甲基醚处的几何出题（已有 CNP006 的四选一版本）。',
    'HBP001': '需要新的“氢键几何”题型族（给体–受体距离、H···O 距离与角度判据），再出四选一。',
    'HBP002': '拆分：H···O 距离与角度用新的氢键几何族出四选一；“是否满足判据”可做分类四选一。',
    'HBI001': '依赖论文中的光谱趋势，属于论文证据题；按会议意见改为“证据 → 结论”形式重做。',
    'HBI002': '依赖论文中的局部力常数查表，属于论文证据题；按“证据 → 结论”形式重做。',
    'QNI003': '拆成两道受力路径四选一（已有 force_path 族），比较部分可做分类四选一。',
    'BNP001': '拆分：端距可用命名距离、最大间距用整体尺寸族（extent_choice_v2）出四选一。',
    'BNP002': '拆分：每个蛋白的回转半径用整体尺寸族出四选一；去掉“哪个更大”的二选一。',
    'BNP003': '路径长度与端距之比没有现成族；若保留需新族，否则归档。',
    'BNI001': '拆分：Guinier 强度用已有 guinier_intensity 族出四选一；“规则是否允许”可做分类四选一。',
    'BNI002': '用已有 fret_efficiency 族出四选一（直线距离 vs 路径长度已是该族登记的错误机制）。',
    'MNP001': '用已有配位壳层族（coordination_shell）出四选一，已有硅的同类实例可参考。',
    'MNP002': '用配位壳层族分别出 Na–Cl、Na–Na 两道四选一。',
    'MNP003': '晶面间距与面法线夹角：可并入首个衍射峰族或新增“晶面几何”族；拆成单值四选一。',
    'MNI001': '用首个衍射峰族（first_diffraction_peak）出四选一；去掉“哪个更高”的二选一。',
    'MNI002': '用消光判别族（kinematic_extinction）出四选一，硅已有同类实例。',
    'MNI003': '散射衬度比较没有现成族；可新增或归档。',
    'MNP008': '归档或改写：去掉题干中的公式与晶胞参数，改由附件晶胞计算（可并入衍射 / 晶面几何族）。',
    'MNP009': '同 MNP008。',
    'BNP008': '用命名键长族（PDB 二硫键，已有 BNP016 先例）出四选一，取代旧题。',
    'BNP010': '同 BNP008。',
    'BNP011': '用命名距离族（Cα i→i+4）出四选一。',
    'CNP010': '链间最近接触没有现成族；可新增“非键接触”族或归档。',
}
BINARY = re.compile(r'oppose or reinforce|which (conformer|structure|protein|has the (higher|lower|larger))|which of the two|'
                    r'stiffer|for which protein|which has the larger', re.I)
EXPLAIN = re.compile(r'\b(explain|does (this|that) (ranking alone )?establish|can these coordinates|would a terminal|'
                     r'is this marker path|are identical|does cancellation mean|what .* demonstrates)', re.I)


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def scored_items(rubric):
    """Number of separately scored items listed in a rubric, e.g. 'distance (1); rows (1); elements (1)' -> 3."""
    return len(re.findall(r'\(\d+[;)]|(?<![\w.])1 for |\(\d+ (?:total|combined)', rubric or ''))


def two_binaries(options):
    parts = [re.split(r',\s*| and ', o['value']) for o in options]
    if any(len(p) != 2 for p in parts):
        return False
    return all(len({p[i] for p in parts}) == 2 for i in range(2)) and len({tuple(p) for p in parts}) == 4


def mirror(options, correct):
    try:
        right = Decimal(next(o['value'] for o in options if o['label'] == correct))
        return right != 0 and any(Decimal(o['value']) == -right for o in options if o['label'] != correct)
    except (InvalidOperation, StopIteration):
        return False


def build():
    cards = read('docs/data/cards.json')['cards']
    catalog = {q['id']: q for q in read('docs/data/catalog.json')['questions']}
    found = defaultdict(list)
    for c in cards:
        q = catalog[c['id']]
        if c['format'] == 'open':
            found[c['id']].append(('not_four_choice', '作答形式：%s' % (q.get('answerKind') or 'text')))
            text = q['question']
            n = scored_items(q.get('rubric'))
            if n >= 2 or re.search(r'\(a\)|\(b\)', text):
                found[c['id']].append(('multi_part', '评分列出 %d 个得分项。' % n if n >= 2 else '题干分 (a)(b) 多问。'))
            if EXPLAIN.search(text):
                found[c['id']].append(('needs_explanation', '题干：“%s”' % EXPLAIN.search(text).group(0)))
            if BINARY.search(text):
                found[c['id']].append(('binary_inside', '题干：“%s”' % BINARY.search(text).group(0)))
        else:
            if c['legacy']:
                found[c['id']].append(('main_record_old_format', '四选一版本：%s' % c['version']))
            if q.get('family') == 'evidence_quantity':       # by design: value (right / mistake) x conclusion (paper / ruled out)
                found[c['id']].append(('two_binaries_combined', '证据计算族的设计：数值（正确 / 登记的错误做法）× 结论（原文 / 原文排除的解释）。'))
            elif two_binaries(c['options']):
                found[c['id']].append(('two_binaries_combined', '选项：' + ' / '.join(o['value'] for o in c['options'])))
            if mirror(c['options'], c['correct']):
                found[c['id']].append(('mirror_pair', '选项：' + ' / '.join(o['value'] for o in c['options'])))
    active = {c['id'] for c in cards}
    for qid, items in REVIEWED.items():
        if qid in active:            # retired questions (e.g. CNP005, MNP008/9 on 2026-10-13) leave the list
            found[qid] += items
    rows = []
    order = {'high': 0, 'medium': 1, 'low': 2}
    for qid, items in found.items():
        q = catalog[qid]
        issues = [dict(rule=r, severity=RULES[r][0], label=RULES[r][1], detail=d) for r, d in items]
        issues.sort(key=lambda i: order[i['severity']])
        rows.append(dict(id=qid, title=q['title'], legacy=not q.get('familyInstance'), worst=issues[0]['severity'],
                         issues=issues, suggestion=SUGGEST.get(qid, '')))
    rows.sort(key=lambda r: (order[r['worst']], r['id']))
    by_rule = {r: sum(1 for x in rows for i in x['issues'] if i['rule'] == r) for r in RULES}
    positions = {}
    for c in cards:
        if c['format'] == 'choice':
            positions[c['correct']] = positions.get(c['correct'], 0) + 1
    return dict(kind='format_check', date='2026-10-13', checked=len(cards), with_issues=len(rows),
                by_severity={s: sum(1 for x in rows if x['worst'] == s) for s in ('high', 'medium', 'low')},
                by_rule=by_rule, rules={k: dict(severity=v[0], label=v[1], meaning=v[2]) for k, v in RULES.items()},
                answer_positions=dict(sorted(positions.items())),
                note='Automatic rules plus findings checked by hand (REVIEWED). Read-only; fixes follow the RUNBOOK '
                     '(whole-family regeneration, supersede or archive), not edits of single questions.', items=rows)


if __name__ == '__main__':
    data = build()
    (ROOT / OUT).write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: data[k] for k in ('checked', 'with_issues', 'by_severity', 'by_rule', 'answer_positions')}, ensure_ascii=False))
    sys.exit(0)
