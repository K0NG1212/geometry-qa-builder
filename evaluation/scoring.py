"""Reading a model's reply and deciding whether it is right. No model judges another model here.

A reply is parsed by rule: one of the four labels for the choice form, one number for the numeric form. A
reply that cannot be parsed is recorded as unparsed, not as wrong -- a model that answered in a format we
failed to read is a harness problem, and burying it in the error rate would hide that.
"""
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ('A', 'B', 'C', 'D')


def answer_key(root=ROOT):
    """The teacher side, keyed by catalog id. Loaded only here, never where a prompt is built."""
    workbench = json.loads((root / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
    catalog = json.loads((root / 'docs/data/catalog.json').read_text(encoding='utf-8'))
    teachers = {t['id']: t for t in workbench['teacher_answers']}
    key = {}
    for question in catalog['questions']:
        teacher = teachers.get(question.get('familyInstance'))
        if teacher and question.get('lifecycle') == 'active':
            key[question['id']] = dict(label=teacher['correct_label'], numeric=teacher.get('numeric_answer'))
    return key


def parse_choice(reply):
    """The label a reply settles on, or None.

    Models answer with 'B', 'B.', '答案：B' or a sentence ending in the letter. A reply naming several
    different labels has not settled on one, so it is unparsed rather than a guess on our part.
    """
    found = re.findall(r'(?<![A-Za-z])([ABCD])(?![A-Za-z])', reply.strip())
    return found[-1] if found and len(set(found)) == 1 else None


def parse_numeric(reply):
    numbers = re.findall(r'-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?', reply.replace(',', ''))
    if not numbers:
        return None
    try:
        return Decimal(numbers[-1])
    except InvalidOperation:
        return None


def grade(question, key, reply):
    """One question's outcome: correct, wrong or unparsed."""
    if question.form == 'choice':
        given = parse_choice(reply)
        if given is None:
            return dict(id=question.id, result='unparsed', given=None, expected=key['label'])
        return dict(id=question.id, result='correct' if given == key['label'] else 'wrong',
                    given=given, expected=key['label'])
    given = parse_numeric(reply)
    if given is None:
        return dict(id=question.id, result='unparsed', given=None, expected=key['numeric']['value'])
    want = Decimal(str(key['numeric']['value']))
    tolerance = Decimal(str(key['numeric'].get('tolerance', '0')))
    return dict(id=question.id, result='correct' if abs(given - want) <= tolerance else 'wrong',
                given=str(given), expected=str(want), tolerance=str(tolerance))


def cells(root=ROOT):
    """Which of the 16 domain × size cells each question sits in, taken from the published coverage data
    rather than recomputed, so a report and the coverage page cannot disagree."""
    progress = json.loads((root / 'docs/data/prototype-progress.json').read_text(encoding='utf-8'))
    return {qa: '%s %s-%s nm' % (cell['domain'], cell['range_nm'][0], cell['range_nm'][1])
            for cell in progress['cells'] for qa in cell.get('qa_ids', [])}


def tally(results, questions, root=ROOT):
    """Scores overall and per group. Unparsed replies are counted and kept out of the rate's numerator."""
    by_id = {q.id: q for q in questions}
    cell_of = cells(root)
    groups = dict(ability={}, family={}, domain={}, cell={})
    for row in results:
        question = by_id[row['id']]
        for name, value in (('ability', question.ability), ('family', question.family),
                            ('domain', question.domain), ('cell', cell_of.get(question.id, '未分格'))):
            bucket = groups[name].setdefault(value, dict(n=0, correct=0, unparsed=0))
            bucket['n'] += 1
            bucket['correct'] += row['result'] == 'correct'
            bucket['unparsed'] += row['result'] == 'unparsed'
    for name in groups:
        for bucket in groups[name].values():
            bucket['score'] = round(bucket['correct'] / bucket['n'], 4) if bucket['n'] else None
    total = len(results)
    correct = sum(r['result'] == 'correct' for r in results)
    unparsed = sum(r['result'] == 'unparsed' for r in results)
    return dict(n=total, correct=correct, unparsed=unparsed,
                score=round(correct / total, 4) if total else None, groups=groups)
