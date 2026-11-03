"""What a model could get right on this bank without understanding a single question.

Every question is four-way choice, so a quarter of the score is free. The question that matters for a
benchmark is whether *more* than a quarter is free: whether some rule over the four option strings alone --
pick the second smallest, pick the longest, pick B -- beats chance. Such a rule is a leak. A model that
exploits it scores above the floor while demonstrating nothing, and a reviewer who finds the leak before we
report it has found it in our place.

Nothing here calls a model. Every check is a rule over the published bank, so a full pass is free, takes
seconds, and can run on every batch -- which is the point: the failure the advisor named is finding one
problem in the last month and discovering every question has it. Three things this is deliberately not:

  It does not re-derive answers. checkers/ already does that with an independent implementation and all 871
  pass; a third copy of the same arithmetic would prove nothing new.

  It does not judge whether a question faithfully restates its source. That is the half of the review that
  has to read the paper, and it needs a model (HANDOFF T1, cross-validation).

  It does not decide anything. A finding is a numbered entry with its count and its cause; what to do about
  it is the user's call, and REVIEW_ISSUES.md keeps a hand-written decision beside each one.

Independence: this module reads the published docs/data/*.json and nothing else. It must not import the
question generators, for the same reason checkers/ must not -- a checker sharing code with the thing it
checks agrees with it by construction. tests/test_audit.py enforces that.
"""
import datetime
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'reviews' / 'audit-ledger.jsonl'
LABELS = ('A', 'B', 'C', 'D')
BREAK = chr(10) * 2      # a blank line inside a generated paragraph; spelled this way so a heredoc cannot eat it

# Bumped whenever a check is added or its verdict changes. A ledger row written by an older version is not
# evidence that the current checks ever ran on that question, so the row is reported as needing another pass.
VERSION = '0.1.0'

# A shortcut is called out when it beats chance by this much. 0.25 is the floor for four-way choice; at 871
# questions the standard error of a proportion is about 0.015, so 0.30 is roughly three of those above it.
RED_OVERALL = 0.30
# Within one family the counts are small, so the bar is higher and a minimum size applies.
RED_FAMILY = 0.50
FAMILY_MIN = 8
# chi-square, 3 degrees of freedom: 7.81 at 95%, 11.34 at 99%.
CHI2_95 = 7.815

NUMBER = re.compile(r'-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?')
WORD = re.compile(r'[a-z]{4,}')


class Question:
    """One admitted question, as the audit sees it: the student side, plus the teacher side kept apart.

    `seen` is everything a model is shown. Every shortcut rule takes `seen` and nothing else, so a rule
    cannot accidentally consult the answer -- the answer is not in the object it is handed.
    """

    def __init__(self, id, instance, family, ability, domain, question, scope, options, inputs, teacher):
        self.id = id
        self.instance = instance
        self.family = family
        self.ability = ability
        self.domain = domain
        self.question = question
        self.scope = scope
        self.options = options            # [{'label','value','unit'}]
        self.inputs = inputs              # [{'name','format','unit'}] -- names only, not the payload
        self.teacher = teacher

    @property
    def seen(self):
        return dict(question=self.question, scope=self.scope, options=self.options)

    @property
    def answer(self):
        return self.teacher['correct_label']

    def fingerprint(self):
        """What this question is, for the ledger. Covers both sides: a change to the question text, an
        option value, an attachment hash or the key all make the recorded audit stale."""
        body = json.dumps(dict(
            id=self.id, instance=self.instance, family=self.family,
            question=self.question, scope=self.scope,
            options=[[o.get('label'), str(o.get('value')), o.get('unit')] for o in self.options],
            inputs=sorted((i.get('name'), i.get('format')) for i in self.inputs),
            answer=self.answer,
            numeric=self.teacher.get('numeric_answer'),
            audit=[[o.get('label'), o.get('rule'), str(o.get('value'))]
                   for o in (self.teacher.get('option_audit') or [])],
            hashes=self.teacher.get('input_hashes') or {},
        ), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]


def bank(root=ROOT):
    """Every active question of the published run. Same source the website and the exam read."""
    workbench = json.loads((root / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
    catalog = json.loads((root / 'docs/data/catalog.json').read_text(encoding='utf-8'))
    packets = {p['id']: p for p in workbench['student_packets']}
    teachers = {t['id']: t for t in workbench['teacher_answers']}
    out = []
    for entry in sorted(catalog['questions'], key=lambda q: q['id']):
        instance = entry.get('familyInstance')
        if entry.get('lifecycle') != 'active' or not instance:
            continue
        packet, teacher = packets.get(instance), teachers.get(instance)
        if packet is None or teacher is None:
            continue
        out.append(Question(
            id=entry['id'], instance=instance, family=packet['family'], ability=packet['ability'],
            domain=entry['domain'], question=packet['question'], scope=packet['scope'],
            options=packet['options'] or [],
            inputs=[dict(name=i.get('name'), format=i.get('format'), unit=i.get('unit'))
                    for i in (packet['inputs'] or [])],
            teacher=teacher))
    return out


# ---------------------------------------------------------------- shortcuts

def first_number(value):
    found = NUMBER.search(str(value))
    return float(found.group()) if found else None


def by_number(seen, which):
    """The option whose leading number is the `which`-th smallest (0-based). None when the four options do
    not all carry a number, or when two of them tie -- an undecided rule is not a lucky guess."""
    pairs = [(first_number(o['value']), o['label']) for o in seen['options']]
    if len(pairs) != 4 or any(n is None for n, _ in pairs):
        return None
    if len({n for n, _ in pairs}) != 4:
        return None
    return sorted(pairs)[which][1]


def by_length(seen, longest=True):
    lengths = [(len(str(o['value'])), o['label']) for o in seen['options']]
    if len(lengths) != 4:
        return None
    pick = max(lengths) if longest else min(lengths)
    if sum(1 for n, _ in lengths if n == pick[0]) > 1:
        return None
    return pick[1]


def by_odd_magnitude(seen):
    """The one option whose order of magnitude differs from the other three. A classic giveaway: three
    distractors built by the same wrong method share an exponent, the answer does not."""
    pairs = [(first_number(o['value']), o['label']) for o in seen['options']]
    if len(pairs) != 4 or any(n in (None, 0) for n, _ in pairs):
        return None
    exponents = [math.floor(math.log10(abs(n))) for n, _ in pairs]
    odd = [label for (n, label), e in zip(pairs, exponents) if exponents.count(e) == 1]
    return odd[0] if len(odd) == 1 else None


def by_stem_overlap(seen):
    """The option sharing the most words with the question. The oldest multiple-choice tell there is."""
    stem = set(WORD.findall(seen['question'].lower()))
    scores = [(len(stem & set(WORD.findall(str(o['value']).lower()))), o['label']) for o in seen['options']]
    if len(scores) != 4:
        return None
    best = max(scores)
    if best[0] == 0 or sum(1 for n, _ in scores if n == best[0]) > 1:
        return None
    return best[1]


def constant(label):
    return lambda seen: label


SHORTCUTS = {
    '永远选 A': constant('A'),
    '永远选 B': constant('B'),
    '永远选 C': constant('C'),
    '永远选 D': constant('D'),
    '选数值最小的': lambda seen: by_number(seen, 0),
    '选数值第二小的': lambda seen: by_number(seen, 1),
    '选数值第三小的': lambda seen: by_number(seen, 2),
    '选数值最大的': lambda seen: by_number(seen, 3),
    '选量级与众不同的': by_odd_magnitude,
    '选最长的选项': lambda seen: by_length(seen, True),
    '选最短的选项': lambda seen: by_length(seen, False),
    '选与题干用词重合最多的': by_stem_overlap,
}


def guess(question_id):
    """The label the seeded baseline picks for a question: fixed per id, so the floor is reproducible.

    The same rule as evaluation.providers.seeded_label, which is where it belongs; it is repeated here so
    the audit stays readable without the eval harness, and tests/test_audit.py asserts the two agree on
    every question in the bank rather than trusting that they do.
    """
    return LABELS[hashlib.sha256(question_id.encode('utf-8')).digest()[0] % 4]


def shortcut_scores(questions, group=None):
    """每条捷径的命中率。分母是它敢作答的题（`decided`），因为一条规则在一半的题上弃权、
    在另一半上全对，仍然是泄漏。"""
    rows = []
    for name, rule in SHORTCUTS.items():
        decided = hits = whole = 0
        buckets = {}
        for q in questions:
            pick = rule(q.seen)
            # Where the rule abstains, a model exploiting it would still have to answer, so the whole-exam
            # floor pairs the rule with the seeded guess. That is the number a score has to beat.
            whole += (pick or guess(q.id)) == q.answer
            if pick is None:
                continue
            decided += 1
            hit = pick == q.answer
            hits += hit
            if group:
                key = getattr(q, group)
                bucket = buckets.setdefault(key, dict(decided=0, hits=0))
                bucket['decided'] += 1
                bucket['hits'] += hit
        row = dict(shortcut=name, n=len(questions), decided=decided, hits=hits,
                   score=round(hits / decided, 4) if decided else None,
                   whole_exam=round(whole / len(questions), 4) if questions else None)
        if group:
            row['groups'] = {k: dict(v, score=round(v['hits'] / v['decided'], 4))
                             for k, v in sorted(buckets.items()) if v['decided']}
        rows.append(row)
    return sorted(rows, key=lambda r: -(r['score'] or 0))


def chi_square(counts):
    """How far a four-way split is from even. Reported as the statistic, not a verdict: 7.81 is the 95%
    point for three degrees of freedom."""
    total = sum(counts.values())
    if not total:
        return 0.0
    expected = total / 4
    return round(sum((counts.get(label, 0) - expected) ** 2 / expected for label in LABELS), 3)


# ---------------------------------------------------------------- structural checks

def check_option_structure(questions):
    """Four distinct options, exactly one of them correct, and the correct one is the key's own value."""
    out = []
    for q in questions:
        labels = [o.get('label') for o in q.options]
        if sorted(labels) != list(LABELS):
            out.append(finding('O1', q, '选项标签不是 A/B/C/D 各一个：%s' % labels))
        values = [str(o.get('value')) for o in q.options]
        if len(set(values)) != len(values):
            out.append(finding('O2', q, '有两个选项的值字面相同：%s' % values))
        audit = q.teacher.get('option_audit') or []
        correct = [o for o in audit if o.get('is_correct')]
        if len(correct) != 1:
            out.append(finding('O3', q, '标为正确的选项有 %d 个（应为 1 个）' % len(correct)))
            continue
        if correct[0].get('label') != q.answer:
            out.append(finding('O4', q, 'correct_label 是 %s，但审计里标正确的是 %s'
                               % (q.answer, correct[0].get('label'))))
        numeric = q.teacher.get('numeric_answer') or {}
        if numeric.get('value') is not None and str(correct[0].get('value')) != str(numeric['value']):
            out.append(finding('O5', q, '正确选项的值 %s 与数值答案 %s 不一致'
                               % (correct[0].get('value'), numeric['value'])))
    return out


def check_distractor_quality(questions):
    """A distractor has to be wrong, and has to be wrong in its own way.

    Two distractors produced by the same named wrong method may still be two different numbers, so this is
    a flag rather than a defect -- but it is the shape a question takes when it really only offers three
    choices, and it needs a per-family look.
    """
    out = []
    for q in questions:
        audit = q.teacher.get('option_audit') or []
        if not audit:
            out.append(finding('D1', q, '没有 option_audit：四个选项为什么对或错无从检查'))
            continue
        rules = [o.get('rule') for o in audit]
        if all(r is None for r in rules):
            out.append(finding('D2', q, '四个选项都没有 rule 字段'))
            continue
        named = [r for r in rules if r]
        if len(set(named)) < len(named):
            repeated = sorted({r for r in named if named.count(r) > 1})
            shared = ['%s（%s）' % (rule, '、'.join(str(o.get('value')) for o in audit
                                                  if o.get('rule') == rule))
                      for rule in repeated]
            correct_shares = any(o.get('is_correct') and o.get('rule') in repeated for o in audit)
            out.append(finding('D3', q, '两个干扰项标的是同一个错误方法：%s%s'
                               % ('；'.join(shared),
                                  '，而且正确答案也在其中' if correct_shares else '')))
        numeric = q.teacher.get('numeric_answer') or {}
        tolerance = numeric.get('tolerance')
        if tolerance is None:
            continue
        correct = next((o for o in audit if o.get('is_correct')), None)
        if correct is None:
            continue
        try:
            want, tol = float(correct['value']), float(tolerance)
        except (TypeError, ValueError):
            continue
        for option in audit:
            if option.get('is_correct'):
                continue
            try:
                value = float(option['value'])
            except (TypeError, ValueError):
                continue
            if abs(value - want) <= tol:
                out.append(finding('D4', q, '干扰项 %s 的值 %s 落在正确答案的容差内，这题有两个正确答案'
                                   % (option.get('label'), option.get('value'))))
    return out


def check_leakage(questions):
    """Things in the student packet that should not be there: the instance id (some spell their own answer),
    the teacher's vocabulary, or the answer written out in the question."""
    forbidden = ('correct_label', 'is_correct', 'option_audit', 'numeric_answer', 'excluded_candidates')
    out = []
    for q in questions:
        text = q.question + ' ' + q.scope
        if q.instance in text:
            out.append(finding('L1', q, '题面里出现了实例 id %s（有些 id 自己把答案说出来）' % q.instance))
        for name in (i.get('name') or '' for i in q.inputs):
            if q.instance and q.instance in name:
                out.append(finding('L2', q, '附件名 %s 带着实例 id（exam.py 送题前会剥掉，但源数据该干净）' % name))
        for word in forbidden:
            if word in text:
                out.append(finding('L3', q, '题面里出现教师侧字段名 %s' % word))
        # The answer appearing in the stem is only a leak when the distractors do not. A question that
        # names its whole taxonomy ("classify as right-handed alpha-helix, beta-strand, ...") contains the
        # answer by construction and gives nothing away; one that names the answer alone hands it over.
        correct = next((o for o in q.options if o.get('label') == q.answer), None)
        if correct is not None:
            value = str(correct.get('value') or '')
            others = [str(o.get('value') or '') for o in q.options if o.get('label') != q.answer]
            if len(value) >= 3 and value in text and not any(v and v in text for v in others):
                out.append(finding('L4', q, '题面里只出现了正确答案 %s，没出现任何干扰项' % value))
    return out


def check_provenance(questions, root=ROOT):
    """Every question says where its structure came from, and every attachment still hashes to what was
    recorded. A benchmark whose provenance cannot be re-checked is not one a reviewer can accept."""
    out = []
    for q in questions:
        if not q.teacher.get('source'):
            out.append(finding('P1', q, '没有 source 字段'))
        if not q.teacher.get('license'):
            out.append(finding('P2', q, '没有 license 字段'))
        for relative, digest in (q.teacher.get('input_hashes') or {}).items():
            path = root / 'docs' / relative
            if not path.exists():
                out.append(finding('P3', q, '附件文件不存在：%s' % relative))
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                out.append(finding('P4', q, '附件哈希对不上：%s' % relative))
    return out


def shingles(text, size=6):
    words = re.findall(r'\w+', text.lower())
    return {tuple(words[i:i + size]) for i in range(max(0, len(words) - size + 1))}


def check_duplicates(questions, threshold=0.9):
    """Two questions that ask the same thing of the same structure are one question counted twice.

    Same wording is not enough to say that. A family is a template, so every question in it reads alike;
    whole families differ only by which attachment they carry, and three questions whose stems are
    character-identical are three different structures asked the same way. A duplicate therefore needs all
    three to coincide: the wording, the attachments and the options. Compared within a family only --
    across families the wording differs by construction.
    """
    out = []
    by_family = {}
    for q in questions:
        by_family.setdefault(q.family, []).append(q)
    for family, group in sorted(by_family.items()):
        prints = []
        for q in group:
            attachments = tuple(sorted((q.teacher.get('input_hashes') or {}).items()))
            options = tuple(sorted(str(o.get('value')) for o in q.options))
            prints.append((q, shingles(q.question + ' ' + q.scope), attachments, options))
        for index, (left, left_set, left_files, left_options) in enumerate(prints):
            for right, right_set, right_files, right_options in prints[index + 1:]:
                if left_files != right_files or left_options != right_options:
                    continue
                union = left_set | right_set
                if not union:
                    continue
                overlap = len(left_set & right_set) / len(union)
                if overlap >= threshold:
                    out.append(finding('U1', left, '与 %s 同族 %s：题面重合 %.0f%%，附件与四个选项也完全相同'
                                       % (right.id, family, 100 * overlap)))
    return out


def finding(code, question, detail):
    return dict(code=code, id=question.id, instance=question.instance, family=question.family,
                domain=question.domain, detail=detail)


CHECKS = (check_option_structure, check_distractor_quality, check_leakage, check_provenance,
          check_duplicates)

# What each code means, for the issues document. Severity is the audit's own reading, not a decision.
CODES = {
    'O1': ('red', '选项标签不完整'),
    'O2': ('red', '两个选项的值相同'),
    'O3': ('red', '正确选项不止一个或没有'),
    'O4': ('red', 'correct_label 与选项审计不一致'),
    'O5': ('red', '正确选项的值与数值答案不一致'),
    'D1': ('red', '缺 option_audit'),
    'D2': ('amber', '选项没有 rule 字段'),
    'D3': ('amber', '两个干扰项标的是同一个错误方法（干扰项多样性，不影响可答性）'),
    'D4': ('red', '干扰项落在正确答案的容差内'),
    'L1': ('red', '题面泄漏实例 id'),
    'L2': ('amber', '附件名带实例 id'),
    'L3': ('red', '题面出现教师侧字段名'),
    'L4': ('red', '正确答案在题面里原样出现'),
    'P1': ('red', '缺 source'),
    'P2': ('red', '缺 license'),
    'P3': ('red', '附件文件缺失'),
    'P4': ('red', '附件哈希对不上'),
    'U1': ('amber', '同族题面近重复'),
    'S1': ('red', '存在超过四选一下限的捷径'),
    'S2': ('amber', '正确答案的位置分布不均'),
}


# ---------------------------------------------------------------- ledger

def read_ledger(path=LEDGER):
    """已经审过什么。append-only：旧行留着，同一道题的后一行覆盖前一行。"""
    if not Path(path).exists():
        return {}
    out = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        out[row['id']] = row
    return out


def ledger_status(questions, previous):
    """Which questions this pass is the first to look at.

    The point of the ledger is that the next pass -- next week, or after the bank grows to 1230 -- does not
    re-read what has not changed. A question counts as already audited only when the recorded fingerprint
    and the recorded audit version both still match; a new check would otherwise be reported as having run
    on questions it never saw.
    """
    fresh, changed, new = [], [], []
    for q in questions:
        row = previous.get(q.id)
        if row is None:
            new.append(q.id)
        elif row.get('content') != q.fingerprint():
            changed.append(q.id)
        elif row.get('audit') != VERSION:
            changed.append(q.id)
        else:
            fresh.append(q.id)
    return dict(already_audited=fresh, content_changed=changed, never_audited=new)


def write_ledger(questions, findings, path=LEDGER, today=None):
    """One row per question: what it was, which audit version looked at it, what that found.

    A question whose row is already there, with the same fingerprint and the same audit version, is left
    alone. That is the whole point of the file -- re-stamping it every run would turn a record of what has
    been looked at into a record of how often the command was run, and the date on each row would stop
    meaning "this is when this question was last checked".
    """
    by_id = {}
    for item in findings:
        by_id.setdefault(item['id'], []).append(item['code'])
    stamp = today or datetime.date.today().isoformat()
    path = Path(path)
    previous = read_ledger(path)
    written = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as handle:
        for q in questions:
            row = previous.get(q.id)
            if row and row.get('content') == q.fingerprint() and row.get('audit') == VERSION:
                continue
            handle.write(json.dumps(dict(
                id=q.id, instance=q.instance, family=q.family, content=q.fingerprint(),
                audit=VERSION, audited_on=stamp,
                findings=sorted(set(by_id.get(q.id, [])))), ensure_ascii=False) + '\n')
            written += 1
    return written


# ---------------------------------------------------------------- the pass

def audit(root=ROOT, ledger=LEDGER):
    questions = bank(root)
    findings = []
    for check in CHECKS:
        findings += check(questions, root) if check is check_provenance else check(questions)

    labels = {label: sum(1 for q in questions if q.answer == label) for label in LABELS}
    shortcuts = shortcut_scores(questions, group='domain')
    families = shortcut_scores(questions, group='family')

    leaks = [row for row in shortcuts if (row['score'] or 0) >= RED_OVERALL]
    family_leaks = []
    for row in families:
        for name, bucket in row.get('groups', {}).items():
            if bucket['decided'] >= FAMILY_MIN and bucket['score'] >= RED_FAMILY:
                family_leaks.append(dict(shortcut=row['shortcut'], family=name, **bucket))

    previous = read_ledger(ledger)
    return dict(
        kind='geobench_bank_audit',
        audit_version=VERSION,
        date=datetime.date.today().isoformat(),
        bank_run=json.loads((root / 'docs/data/family-workbench.json')
                            .read_text(encoding='utf-8'))['run'],
        questions=len(questions),
        attachments=sum(len(q.teacher.get('input_hashes') or {}) for q in questions),
        findings=sorted(findings, key=lambda f: (f['code'], f['id'])),
        counts={code: sum(1 for f in findings if f['code'] == code) for code, _ in sorted(CODES.items())},
        label_counts=labels,
        label_chi_square=chi_square(labels),
        shortcuts=shortcuts,
        shortcut_leaks=leaks,
        family_leaks=sorted(family_leaks, key=lambda r: -r['score']),
        orderings=orderings(questions),
        ledger=ledger_status(questions, previous))


# What to do about each kind of finding. Written here rather than in the issues document because the
# document is regenerated; the decision taken against the advice is what stays hand-written.
ADVICE = {
    '选最长的选项': '让四个选项的长度相当。现在正确答案往往是最长的那个，因为它写得完整而干扰项写得潦草；'
                    '给干扰项补齐同样的措辞即可，不必改答案。',
    '选最短的选项': '同上，反方向：正确答案偏短说明干扰项被写得冗长。',
    '选数值第二小的': '数值题的选项按数值升序排、标签就是排位，而干扰项通常落在真值两侧，于是真值偏中间。'
                      '两条路：① 打乱选项顺序（标签不再等于排位）；② 保留升序，但出题时控制真值的排位在'
                      '四个位置上均匀分布。',
    '选数值第三小的': '同「选数值第二小的」。',
    '选与题干用词重合最多的': '干扰项也要用题干里的词。现在正确答案复用了题干措辞而干扰项另起说法。',
    '选量级与众不同的': '干扰项的量级要和正确答案同级，否则一眼就能排除三个。',
    '永远选 A': '正确答案的位置要在四个标签上均匀分布。',
    'D2': '补上 option_audit 的 rule 字段，否则「这个干扰项为什么错」无从检查。',
    'D3': '这一条是**干扰项多样性**的观察，不是可答性的缺陷——这 184 道题里，同方法的两个干扰项'
          '取值都不同，而且正确答案从不落在共享组里（有测试钉着），所以每道题仍然是四个互不相同的选项、'
          '一个唯一答案。真正的影响是：一道题里「错法」的种类少了一种，考察面窄一点。'
          '如果要改，给其中一个换一种错误方法；判断值不值得改要看每个族的生成器，那是出题侧的事。',
    'L2': '附件名里的实例 id 要去掉。exam.py 送题前会剥掉，所以不泄漏给模型，但源数据和网站上的名字'
          '仍然带着它，审稿人下载下来就看得到。',
    'L4': '题面已经把答案说出来了（例如条件里写明 HTP = 107.5，然后问 HTP）。要么改问别的量，'
          '要么把这个条件从题面删掉。',
    'U1': '两道题完全相同，留一道。',
}


def advice_for(key):
    return ADVICE.get(key, '')


def with_advice(body, key):
    """A finding, then what to do about it. Kept out of the format string: `%` binds tighter
    than `+`, so building this inline formatted the advice fragment alone."""
    hint = advice_for(key)
    return body + BREAK + '**怎么改**：' + hint if hint else body


def slug(text, words=3):
    """A short stable name for an option-ordering scheme, for the issue number. Truncating the scheme's own
    sentence gives ids like `numeric ascending (label = r`, which read as a bug."""
    found = re.findall(r'[a-z0-9]+', text.lower())
    return '-'.join(found[:words]) if found else 'scheme'


def issues(report):
    """One numbered entry per problem, worst first.

    The number is derived from the check and its scope, not counted off, so an entry keeps its name when
    the bank grows and a decision recorded against ISSUE-D3 still refers to the same thing next week.
    """
    out = []
    for leak in report['shortcut_leaks']:
        out.append(dict(
            issue='ISSUE-S1-%s' % leak['shortcut'], severity='red', code='S1',
            title='捷径「%s」能拿 %.3f，高于四选一的 0.25' % (leak['shortcut'], leak['score']),
            affected=leak['decided'],
            detail=with_advice(
                '在它敢作答的 %d 道题里命中 %d 道。四选一的下限是 0.25，这条规则不看题目内容、'
                '只看四个选项就能超过下限，所以这部分分数不代表模型会做题。'
                % (leak['decided'], leak['hits']), leak['shortcut'])))
    for leak in report['family_leaks']:
        out.append(dict(
            issue='ISSUE-S1-%s-%s' % (leak['family'], leak['shortcut']), severity='red', code='S1',
            title='题型族 %s：捷径「%s」命中 %.0f%%' % (leak['family'], leak['shortcut'],
                                                 100 * leak['score']),
            affected=leak['decided'],
            detail=with_advice(
                '该族 %d 道题里 %d 道能被这条规则答对。族内泄漏比全库泄漏更严重：'
                '它意味着这个族的选项是按同一个模式造出来的，改一次生成器就能修掉整族。'
                % (leak['decided'], leak['hits']), leak['shortcut'])))
    for order, bucket in report['orderings'].items():
        if bucket['chi_square'] >= CHI2_95:
            out.append(dict(
                issue='ISSUE-S2-%s' % slug(order), severity='amber', code='S2',
                title='选项顺序方案「%s」下，正确答案的位置分布不均' % order[:40],
                affected=bucket['n'],
                detail=with_advice(
                    '%d 道题的正确答案落在 A/B/C/D 的次数是 %s，卡方 %.2f（三自由度 95%% 的临界值 7.81）。'
                    '「永远选 %s」在这批题上能拿 %.3f。'
                    % (bucket['n'], bucket['labels'], bucket['chi_square'],
                       bucket['best_constant_label'], bucket['best_constant_score']),
                    '选数值第二小的')))
    for code, count in report['counts'].items():
        if not count:
            continue
        severity, title = CODES[code]
        examples = [f for f in report['findings'] if f['code'] == code][:3]
        families = sorted({f['family'] for f in report['findings'] if f['code'] == code})
        out.append(dict(
            issue='ISSUE-%s' % code, severity=severity, code=code,
            title='%s（%d 道）' % (title, count), affected=count,
            detail=with_advice(
                '涉及 %d 个题型族：%s。例：%s'
                % (len(families), '、'.join(families[:6]) + ('…' if len(families) > 6 else ''),
                   '；'.join('%s %s' % (f['id'], f['detail']) for f in examples)), code)))
    order = {'red': 0, 'amber': 1}
    return sorted(out, key=lambda i: (order.get(i['severity'], 2), -i['affected']))


MARK_BEGIN = '<!-- audit:begin -->'
MARK_END = '<!-- audit:end -->'

HEAD = """# 题库问题清单

机器审计查出来的问题，一条一个编号。**只查「不看题就能答对」和结构性缺陷，不判题目是否忠实于原文**——
那一半要读论文、要调模型，是 T1 的交叉验证部分。

- 重跑：`python -m review_system.audit`
- 标记之间那一段是生成的，**手改会被下次重跑覆盖**；你的决定写在文件末尾那张表里，重跑不动它。
- 已审标注在 `reviews/audit-ledger.jsonl`：每道题一行，记着当时的内容指纹与审计版本。
  下次只有指纹变了的题（或审计版本升级了）才需要重看，**不用把审过的再审一遍**。
"""

TAIL = """
## 决定（手写，重跑不会覆盖这一段）

一条问题可以是「改」、「不改并写明理由」、或「等导师定」。不改也要留一行——
审稿人问起来，「知道并且决定不改」和「没发现」是两件完全不同的事。

| 编号 | 决定 | 谁定的 | 日期 |
|---|---|---|---|
| | | | |
"""


def markdown(report):
    """The issues document, as the user will read it in the morning."""
    found = issues(report)
    reds = sum(1 for i in found if i['severity'] == 'red')
    ledger = report['ledger']
    lines = [HEAD, MARK_BEGIN, '',
             '## 本次审计',
             '',
             '| | |',
             '|---|---|',
             '| 审计版本 | %s |' % report['audit_version'],
             '| 跑的日期 | %s |' % report['date'],
             '| 题库快照 | %s |' % report['bank_run'],
             '| 题数 | %d |' % report['questions'],
             '| 问题条目 | **%d 条**（红 %d 条，黄 %d 条） |' % (len(found), reds, len(found) - reds),
             '| 这次新审的题 | %d 道（内容变过的 %d 道，已审未变的 %d 道） |'
             % (len(ledger['never_audited']), len(ledger['content_changed']),
                len(ledger['already_audited'])),
             '']
    lines += ['## 问题条目', '',
              '| 编号 | 严重度 | 问题 | 影响 |', '|---|---|---|---|']
    for item in found:
        mark = '🔴' if item['severity'] == 'red' else '🟡'
        lines.append('| `%s` | %s | %s | %d 道 |'
                     % (item['issue'], mark, item['title'], item['affected']))
    lines += ['', '### 每条是什么意思', '']
    for item in found:
        lines += ['**`%s`** · %s' % (item['issue'], item['title']), '', item['detail'], '']

    floor = max(report['shortcuts'], key=lambda r: r['whole_exam'] or 0)
    lines += ['## 全部捷径的命中率', '',
              '「敢答」是这条规则能作答的题数——四个选项里凑不出它要的东西（没有数值可排序、两个选项等长）时它弃权。'
              '**命中率的分母是敢答的题**，诊断泄漏看这一列。'
              '**全库**那一列把弃权的题配上种子猜测，是一个利用这条捷径的模型在整张卷子上真能拿到的分数。', '',
              '| 规则 | 敢答 | 命中 | 命中率 | 全库（弃权时按种子猜） |', '|---|---|---|---|---|']
    for row in report['shortcuts']:
        flag = ' **🔴**' if (row['score'] or 0) >= RED_OVERALL else ''
        lines.append('| %s | %d | %d | %.3f%s | %.3f |'
                     % (row['shortcut'], row['decided'], row['hits'], row['score'] or 0, flag,
                        row['whole_exam'] or 0))
    lines += ['',
              '**所以这个题库真实的下限是 %.3f（「%s」），不是四选一的 0.25。**'
              '报分时必须和这个数一起报：一个模型拿到 0.35，高出真实下限的只有 %.1f 个百分点，不是 10 个。'
              % (floor['whole_exam'], floor['shortcut'], 100 * (0.35 - floor['whole_exam']))]

    lines += ['', '## 选项顺序方案与正确答案的位置', '',
              '「数值升序，标签就是排位」这种方案**无法同时平衡正确答案的位置**——位置就是排位。'
              '干扰项通常落在真值两侧，于是真值偏中间。', '',
              '| 顺序方案 | 题数 | A | B | C | D | 卡方 | 最佳常数策略 |', '|---|---|---|---|---|---|---|---|']
    for order, bucket in report['orderings'].items():
        labels = bucket['labels']
        lines.append('| %s | %d | %d | %d | %d | %d | %.2f | %s = %.3f |'
                     % (order, bucket['n'], labels['A'], labels['B'], labels['C'], labels['D'],
                        bucket['chi_square'], bucket['best_constant_label'],
                        bucket['best_constant_score']))

    lines += ['', '## 查过并且没问题的（也要记下来）', '',
              '| 检查 | 结果 |', '|---|---|']
    for code, (severity, title) in sorted(CODES.items()):
        # S1/S2 are the shortcut findings, reported in their own table above; U1 gets a spelled-out row
        # below because "no duplicates" needs the definition of a duplicate beside it to mean anything.
        if code in ('S1', 'S2', 'U1') or report['counts'].get(code):
            continue
        lines.append('| `%s` %s | **0 道** |' % (code, title))
    lines.append('| 附件哈希 | %d 个附件，全部与记录一致 |' % report['attachments'])
    if not report['counts'].get('U1'):
        lines.append('| 同族近重复题 | **0 对**（题面、附件、四个选项三者同时相同才算重复） |')
    lines += ['', MARK_END, TAIL]
    return '\n'.join(lines)


def orderings(questions):
    """How each question's options were ordered, and where the answer landed under that scheme.

    This is the one grouping that explains a position leak rather than just reporting it: a scheme that
    sorts the options by value cannot also balance which label is correct, because the label *is* the rank.
    """
    out = {}
    for q in questions:
        key = q.teacher.get('option_order') or '（未记录）'
        bucket = out.setdefault(key, dict(n=0, labels={label: 0 for label in LABELS}))
        bucket['n'] += 1
        if q.answer in bucket['labels']:
            bucket['labels'][q.answer] += 1
    for bucket in out.values():
        best = max(bucket['labels'].items(), key=lambda kv: kv[1])
        bucket['best_constant_label'] = best[0]
        bucket['best_constant_score'] = round(best[1] / bucket['n'], 4)
        bucket['chi_square'] = chi_square(bucket['labels'])
    return dict(sorted(out.items(), key=lambda kv: -kv[1]['n']))


# ---------------------------------------------------------------- CLI

ISSUES = ROOT / 'REVIEW_ISSUES.md'
LATEST = ROOT / 'reviews' / 'audit-latest.json'


def rewrite(path, body, begin=MARK_BEGIN, end=MARK_END):
    """Replace the generated block, keep whatever a human wrote after it.

    The decisions table at the bottom is the part of this document that cannot be regenerated -- it is the
    record of what we chose to do -- so a re-run must never touch it.
    """
    path = Path(path)
    tail = ''
    if path.exists():
        old = path.read_text(encoding='utf-8')
        if end in old:
            tail = old.split(end, 1)[1]
    if tail.strip():
        body = body.split(end, 1)[0] + end + tail
    path.write_text(body, encoding='utf-8', newline='\n')


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='题库机械审计：查「不看题就能答对」的捷径与结构性缺陷。')
    parser.add_argument('--out', default=str(ISSUES), help='问题清单写到哪（默认 REVIEW_ISSUES.md）')
    parser.add_argument('--json', dest='as_json', default=str(LATEST), help='逐题发现写到哪')
    parser.add_argument('--no-ledger', action='store_true', help='不写已审标注（试跑用）')
    args = parser.parse_args(argv)

    report = audit()
    rewrite(args.out, markdown(report))
    Path(args.as_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.as_json).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8',
                               newline='\n')
    found = issues(report)
    reds = sum(1 for i in found if i['severity'] == 'red')
    print('%d 道题 · %s · %d 条问题（红 %d）' % (report['questions'], report['bank_run'], len(found), reds))
    for item in found[:8]:
        print('  %s %s' % ('🔴' if item['severity'] == 'red' else '🟡', item['title']))
    if len(found) > 8:
        print('  …另外 %d 条见 %s' % (len(found) - 8, args.out))
    if args.no_ledger:
        print('未写已审标注（--no-ledger）')
    else:
        written = write_ledger(bank(), report['findings'])
        print('已审标注：%d 道写入 %s' % (written, LEDGER.relative_to(ROOT)))
    print('清单：%s' % args.out)
    print('逐题：%s' % args.as_json)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
