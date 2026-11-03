"""Several answerers over the whole bank in one go, and the model x discipline table that comes out of it.

run.py does one answerer; this does the comparison, which is the thing that gets read. Three facts about
the bank shape it:

  It is paid for per token, so nothing is asked twice. Every answer is appended to a cache and stamped
  with a hash of the exact prompt it answered, so a repeated command calls nothing, a run interrupted at
  question 700 resumes at 700, and a thirty-question trial run is not paid for again by the full pass. The
  stamp is per question rather than per exam: when the bank is rebuilt, only the questions whose prompt
  actually changed are asked again.

  Questions are of wildly different sizes, so a model with a small window cannot be shown all of them. The
  ones that do not fit are recorded as `oversize` before any call is made, with their measured size. They
  are concentrated in biology, so a report that silently counted them as wrong would be reporting the
  window, not the model.

  A baseline belongs in the same table. Four-way choice gives a quarter away; a column of model scores
  without the floor measured on the same questions says very little.
"""
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import budget, exam, providers, remote, scoring

ROOT = Path(__file__).resolve().parents[1]


def cache_path(answerer, setting, form, root=ROOT):
    """One append-only file per (answerer, form, setting). Which bank run an answer belongs to is settled
    per row by `prompt`, not by the file name, so a sample and the full pass share one file."""
    safe = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in answerer)
    return root / 'runs' / 'eval' / 'cache' / ('%s-%s-%s.jsonl' % (safe, form, setting))


def stamp(prompt):
    """What a cached answer was an answer to."""
    return hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]


def read_cache(path, stamps):
    """The usable rows: the ones whose question still asks exactly what it asked when they were written.

    A row for a question whose prompt has changed is left on disk (the file is append-only, and the old
    answer is still a record of what was asked then) but is not read back as an answer to the new one.
    """
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue                                    # a half-written last line after a kill
        if row.get('prompt') == stamps.get(row['id']):
            out[row['id']] = row
        else:
            out.pop(row['id'], None)                    # a later row for a changed prompt supersedes
    return out


class Session:
    """One answerer working through one exam, writing each answer down as it arrives."""

    def __init__(self, answerer, questions, key, setting, path, workers=1):
        self.answerer = answerer
        self.questions = questions
        self.key = key
        self.setting = setting
        self.path = path
        self.workers = workers
        self.lock = threading.Lock()
        self.stamps = {q.id: stamp(q.prompt(setting)) for q in questions}
        self.done = read_cache(path, self.stamps)
        self.resumed = len(self.done)                   # answers that were already on disk

    def record(self, row):
        with self.lock:
            self.done[row['id']] = row
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + '\n')

    def ask(self, question):
        if question.id in self.done:
            return
        try:
            reply = self.answerer.answer(question, question.prompt(self.setting))
        except remote.CallFailed as failure:
            self.record(dict(id=question.id, prompt=self.stamps[question.id], reply=None,
                             error=str(failure)))
            return
        self.record(dict(id=question.id, prompt=self.stamps[question.id], reply=reply, error=None))

    def run(self, oversize=()):
        for row in oversize:
            if row['id'] not in self.done:
                self.record(dict(id=row['id'], prompt=self.stamps[row['id']], reply=None,
                                 oversize=row['tokens']))
        todo = [q for q in self.questions if q.id not in self.done]
        if self.workers > 1 and todo:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                list(pool.map(self.ask, todo))
        else:
            for question in todo:
                self.ask(question)
        return [self.grade(q) for q in self.questions]

    def grade(self, question):
        row = self.done[question.id]
        if row.get('oversize'):
            return scoring.not_asked(question, 'oversize',
                                     '提示词 %d token，超过该模型的上下文窗口，未发送' % row['oversize'])
        if row.get('error'):
            return scoring.not_asked(question, 'error', row['error'])
        return scoring.grade(question, self.key[question.id], row['reply'])


def sample(questions, size):
    """A small, deterministic, spread-out slice of the exam.

    The first paid run should not be the full 10M-token pass: a wrong model id or a misread context window
    costs 871 calls to find out that way. Each discipline contributes a share of `size`, taken at even
    spacing through that discipline's questions in id order -- so the slice is identical every time, covers
    all four disciplines, and is not made only of the cheap short questions.
    """
    if not size or size >= len(questions):
        return questions
    by_domain = {}
    for question in sorted(questions, key=lambda q: q.id):
        by_domain.setdefault(question.domain, []).append(question)
    domains = sorted(by_domain)
    picked = []
    for index, domain in enumerate(domains):
        pool = by_domain[domain]
        share = size // len(domains) + (1 if index < size % len(domains) else 0)
        share = min(share, len(pool))
        step = len(pool) / share if share else 0
        picked += [pool[min(len(pool) - 1, int(k * step))] for k in range(share)]
    return sorted(set(picked), key=lambda q: q.id)


def one(name, questions, key, setting='coords', form='choice', workers=1, root=ROOT, sizes=None,
        models=None, **kwargs):
    """One answerer's pass, resumed from cache, with the questions it cannot be shown set aside first.

    `models` is the model table to look `name` up in; the default is the shipped models.json, and a
    caller passes its own when it is wiring a model the file does not describe. It is not called `table`
    because that name belongs to the function below that builds the report's grid.
    """
    answerer = providers.get(name, models=models, **kwargs)
    spec = (providers.catalogue() if models is None else models).get(name, {})
    _, oversize, room = budget.fit(sizes or [], spec) if spec else ([], [], None)
    path = cache_path(name, setting, form, root)
    session = Session(answerer, questions, key, setting, path, workers)
    results = session.run(oversize)
    summary = scoring.tally(results, questions, root)
    identity = answerer.identity()
    return dict(
        asked_for=name,
        **identity,
        answerer_is_a_model=answerer.is_model,
        context_tokens=spec.get('context_tokens'),
        room_for_prompt=room,
        usd_from_reported_usage=answerer.cost(),
        cache=str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
        answers_from_cache=session.resumed,
        summary=summary,
        results=results)


def run(names, form='choice', setting='coords', ids=None, workers=1, root=ROOT, models=None, size=None,
        **kwargs):
    """The whole comparison: every answerer over the same exam, then the table."""
    questions = exam.load(form=form, ids=ids, root=root)
    if not questions:
        raise ValueError('没有题可跑：form=%s 下没有匹配的题' % form)
    whole_exam = len(questions)
    questions = sample(questions, size)
    key = scoring.answer_key(root)
    fingerprint = exam.fingerprint(questions)
    sizes, exact = budget.measure(questions, setting)
    bank = json.loads((root / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
    runs = [one(name, questions, key, setting=setting, form=form, workers=workers, root=root,
                sizes=sizes, models=models, **kwargs) for name in names]
    return dict(
        kind='geobench_benchmark',
        date=datetime.date.today().isoformat(),
        bank_run=bank['run'],
        form=form,
        setting=setting,
        setting_label=exam.SETTINGS[setting]['label'],
        questions=len(questions),
        is_a_sample=len(questions) < whole_exam,
        whole_exam=whole_exam,
        exam_fingerprint=fingerprint,
        token_counts_are_exact=exact,
        total_prompt_tokens=sum(s['tokens'] for s in sizes),
        runs=runs,
        table=table(runs))


def table(runs, group='domain'):
    """Rows are answerers, columns are the groups. Each cell carries its own denominator, because the
    denominators differ: a model with a small window was not asked the same questions as one without."""
    columns = sorted({name for r in runs for name in r['summary']['groups'][group]})
    rows = []
    for run_record in runs:
        buckets = run_record['summary']['groups'][group]
        rows.append(dict(
            answerer=run_record['answerer'],
            is_a_model=run_record['answerer_is_a_model'],
            overall=run_record['summary']['score'],
            asked=run_record['summary']['asked'],
            oversize=run_record['summary']['oversize'],
            error=run_record['summary']['error'],
            cells={name: dict(score=buckets.get(name, {}).get('score'),
                              asked=buckets.get(name, {}).get('asked', 0),
                              n=buckets.get(name, {}).get('n', 0))
                   for name in columns}))
    return dict(group=group, columns=columns, rows=rows)


def markdown(record, group='domain'):
    """The table as the user will paste it into a slide or a mail."""
    grid = record['table'] if record['table']['group'] == group else table(record['runs'], group)
    # The column headings carry the bank's own count, so a reader can see at a glance that biology is 281
    # of the 871 and a cell marked 236/281 is a third of the exam missing from that row.
    sizes = {name: max(row['cells'][name]['n'] for row in grid['rows']) for name in grid['columns']}
    head = ('| 作答者 | 总分 | ' + ' | '.join('%s<br><sub>%d 道</sub>' % (n, sizes[n]) for n in grid['columns'])
            + ' | 未问（超窗/失败） |')
    out = ['**%s · %s · %d 道 · 指纹 %s**' % (record['bank_run'], record['setting_label'],
                                            record['questions'], record['exam_fingerprint'][:12]), '',
           head, '|' + '---|' * (len(grid['columns']) + 3)]
    for row in grid['rows']:
        cells = []
        for name in grid['columns']:
            cell = row['cells'][name]
            if not cell['asked']:
                cells.append('—')
            else:
                mark = '' if cell['asked'] == cell['n'] else ' <sub>%d/%d</sub>' % (cell['asked'], cell['n'])
                cells.append('%.3f%s' % (cell['score'], mark))
        label = row['answerer'] + ('' if row['is_a_model'] else ' *(基线)*')
        out.append('| %s | **%s** | %s | %d / %d |'
                   % (label, '%.3f' % row['overall'] if row['overall'] is not None else '—',
                      ' | '.join(cells), row['oversize'], row['error']))
    if record.get('is_a_sample'):
        out.insert(1, '**这是 %d / %d 道的样本，不是全库成绩。**' % (record['questions'], record['whole_exam']))
    out += ['', '分母是「实际问到的题」：超过上下文窗口没发出去的（超窗）与调用失败的（失败）不算错，'
                '也不进分母；格子里的 <sub>a/b</sub> 表示该列只问到了 a 道（共 b 道）。'
                '基线是不看题目作答的下限，四选一本身就送四分之一。']
    return '\n'.join(out)

