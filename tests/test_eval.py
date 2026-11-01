"""W3: the evaluation harness must ask fairly and score by rule.

What these pin: a prompt carries the student packet and nothing from the teacher side (the instance id
included -- some ids spell their own answer); every admitted question is on the exam and its files resolve
to their recorded hash; a reply we cannot read is recorded as unparsed instead of wrong; the numeric form
covers part of the bank and the record says so; a setting that cannot be served refuses instead of quietly
degrading; and a record states who answered and how many model calls it took, so a baseline run can never
be read as a model's score.
"""
import ast
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation import exam, providers, run, scoring  # noqa: E402

CATALOG = json.loads((ROOT / 'docs/data/catalog.json').read_text(encoding='utf-8'))
WORKBENCH = json.loads((ROOT / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
ADMITTED = [q for q in CATALOG['questions'] if q.get('lifecycle') == 'active' and q.get('familyInstance')]


class ExamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = exam.load(form='choice')
        cls.teachers = {t['id']: t for t in WORKBENCH['teacher_answers']}

    def test_every_admitted_question_is_on_the_exam_and_its_files_resolve(self):
        # load() verifies each referenced asset against its recorded sha256, so reaching here means they
        # all matched; what is left to check is that every question arrived with its files attached.
        self.assertEqual(len(self.questions), len(ADMITTED))
        for question in self.questions:
            self.assertTrue(question.inputs, question.id)
            for item in question.inputs:
                self.assertTrue(item['text'].strip(), '%s/%s' % (question.id, item['name']))
            self.assertEqual([o['label'] for o in question.options], list(scoring.LABELS), question.id)

    def test_a_prompt_carries_nothing_from_the_teacher_side(self):
        for question in self.questions:
            prompt = question.prompt('coords')
            # The id is teacher side: FA-SREL-7029-SAME ends in its own answer, and ids like
            # EN-1A6M-DS-2-6 name the correct residue pair.
            self.assertNotIn(question.instance, prompt, question.id)
            teacher = self.teachers[question.instance]
            right = next(o for o in teacher['option_audit'] if o['is_correct'])
            self.assertNotIn(str(right.get('reason') or 'nothing to look for'), prompt, question.id)
            for marker in ('is_correct', 'correct_label', 'option_audit', 'reviewer/'):
                self.assertNotIn(marker, prompt, '%s: prompt carries %s' % (question.id, marker))

    def test_a_file_renamed_to_hide_its_instance_id_is_never_named_in_the_question(self):
        # 56 attachments are named after their instance (FA-PEAK-B5H9-cell.txt), so the prompt renames
        # them. That is only safe while no question text points at the published name.
        renamed = [(q, i) for q in self.questions for i in q.inputs if i['name'] != i['published_name']]
        self.assertGreater(len(renamed), 50)
        for question, item in renamed:
            self.assertNotIn(item['published_name'], question.text + question.scope, question.id)
        names = {i['name'] for q in self.questions for i in q.inputs}
        self.assertEqual([n for n in names if n.startswith('FA-') or n.startswith('EN-')], [])

    def test_the_numeric_form_covers_part_of_the_bank_and_the_record_says_so(self):
        numeric = exam.load(form='numeric')
        self.assertEqual(len(numeric), len(WORKBENCH['numeric_student_packets']))
        self.assertLess(len(numeric), len(ADMITTED))
        record = run.run(provider='seeded', form='numeric')
        self.assertEqual(record['questions'], len(numeric))
        self.assertEqual(record['questions_in_bank'], len(ADMITTED))

    def test_a_setting_that_cannot_be_served_refuses(self):
        self.assertFalse(exam.SETTINGS['renders']['available'])
        with self.assertRaises(ValueError) as refused:
            self.questions[0].prompt('renders')
        self.assertIn('169', str(refused.exception))      # says which part of the bank it could cover


class ScoringTests(unittest.TestCase):
    def test_a_reply_that_names_one_label_is_read_and_an_ambiguous_one_is_not(self):
        for reply, want in (('B', 'B'), ('B.', 'B'), ('答案：C', 'C'), ('The answer is D.', 'D'),
                            ('A or B', None), ('', None), ('none of these', None)):
            self.assertEqual(scoring.parse_choice(reply), want, reply)

    def test_an_unreadable_reply_is_unparsed_not_wrong(self):
        record = run.run(provider='blank')
        self.assertEqual(record['summary']['unparsed'], record['summary']['n'])
        self.assertEqual(record['summary']['correct'], 0)
        self.assertTrue(all(r['result'] == 'unparsed' for r in record['results']))

    def test_a_perfect_sheet_scores_one_and_the_floor_sits_near_a_quarter(self):
        questions = exam.load(form='choice')
        key = scoring.answer_key()
        perfect = [scoring.grade(q, key[q.id], key[q.id]['label']) for q in questions]
        self.assertEqual(scoring.tally(perfect, questions)['score'], 1.0)
        floor = run.run(provider='seeded')['summary']['score']
        self.assertTrue(0.15 < floor < 0.35, floor)       # four-way choice: a quarter comes free

    def test_numeric_grading_uses_the_recorded_tolerance(self):
        questions = [q for q in exam.load(form='numeric')][:1]
        key = scoring.answer_key()[questions[0].id]
        want, tolerance = Decimal(str(key['numeric']['value'])), Decimal(str(key['numeric']['tolerance']))
        self.assertEqual(scoring.grade(questions[0], key, str(want + tolerance))['result'], 'correct')
        self.assertEqual(scoring.grade(questions[0], key, str(want + tolerance * 2))['result'], 'wrong')

    def test_every_question_lands_in_one_of_the_published_cells(self):
        cells = scoring.cells()
        self.assertEqual([q['id'] for q in ADMITTED if q['id'] not in cells], [])


class RecordTests(unittest.TestCase):
    def test_a_record_states_who_answered_and_that_no_model_was_called(self):
        record = run.run(provider='always-a', ids={q['id'] for q in ADMITTED[:5]})
        self.assertEqual(record['answerer'], 'baseline-always-a')
        self.assertFalse(record['answerer_is_a_model'])
        self.assertEqual(record['model_calls'], 0)
        self.assertEqual(record['bank_run'], WORKBENCH['run'])
        self.assertEqual(record['questions'], 5)

    def test_asking_for_an_answerer_that_is_not_wired_up_says_so(self):
        with self.assertRaises(ValueError) as refused:
            providers.get('claude-opus-5')
        self.assertIn('API', str(refused.exception))

    def test_the_harness_shares_no_code_with_the_question_generators(self):
        # Same rule as the independent checkers: a harness that imported the generators could inherit a
        # mistake from them and agree with it.
        for path in sorted((ROOT / 'evaluation').glob('*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
                for name in names:
                    self.assertFalse(name.split('.')[0] in ('task_families', 'family_engine', 'checkers',
                                                            'builder', 'builder_modules'),
                                     '%s imports %s' % (path.name, name))


if __name__ == '__main__':
    unittest.main()
