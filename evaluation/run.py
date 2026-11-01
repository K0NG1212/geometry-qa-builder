"""One evaluation run: hand each question to one answerer under one setting, then score it.

The record a run leaves is meant to be read months later, so it states what was asked (which run of the
bank, which form, which setting, a fingerprint of the prompts) and who answered (the answerer's own name and
how many model calls it made). A run by a baseline says baseline in both places.
"""
import datetime
import json
from pathlib import Path

from . import exam, providers, scoring

ROOT = Path(__file__).resolve().parents[1]


def run(provider='seeded', form='choice', setting='coords', ids=None, root=ROOT, keep_replies=False):
    answerer = providers.get(provider)
    questions = exam.load(form=form, ids=ids, root=root)
    if not questions:
        raise ValueError('没有题可跑：form=%s 下没有匹配的题' % form)
    key = scoring.answer_key(root)
    results, replies = [], {}
    for question in questions:
        reply = answerer.answer(question, question.prompt(setting))
        results.append(scoring.grade(question, key[question.id], reply))
        if keep_replies:
            replies[question.id] = reply
    bank = json.loads((root / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
    catalog = json.loads((root / 'docs/data/catalog.json').read_text(encoding='utf-8'))
    record = dict(
        kind='geobench_eval_run',
        date=datetime.date.today().isoformat(),
        bank_run=bank['run'],
        form=form,
        setting=setting,
        setting_label=exam.SETTINGS[setting]['label'],
        questions=len(questions),
        questions_in_bank=sum(q.get('lifecycle') == 'active' and bool(q.get('familyInstance'))
                              for q in catalog['questions']),
        exam_fingerprint=exam.fingerprint(questions),
        answerer=answerer.name,
        answerer_is_a_model=answerer.is_model,
        model_calls=answerer.model_calls,
        summary=scoring.tally(results, questions, root),
        results=results)
    if keep_replies:
        record['replies'] = replies
    return record


def save(record, out):
    """Runs land outside the repository by default: runs/ is gitignored and already a junction to D:."""
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding='utf-8')
    return path
