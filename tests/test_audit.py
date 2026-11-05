"""Tests for the bank audit (review_system/audit.py).

Two things these are mostly about. First, the audit must not be able to cheat: a shortcut rule is only
evidence of a leak if it never saw the answer, so the object the rules are handed carries no teacher side
at all. Second, a check that flags something legitimate is worse than no check -- a family is a template, so
every question in it reads alike, and an early version of the duplicate test reported 95 pairs that were
simply the same template over different structures. Both of those shapes are pinned here.
"""
import ast
import json
import unittest
from pathlib import Path

from review_system import audit

ROOT = Path(__file__).resolve().parents[1]


def question(id='Q1', options=(('A', '1'), ('B', '2'), ('C', '3'), ('D', '4')), answer='B',
             text='Compute the angle.', scope='scope', family='fam', instance='FA-X',
             teacher=None, inputs=()):
    key = dict(correct_label=answer)
    key.update(teacher or {})
    return audit.Question(
        id=id, instance=instance, family=family, ability='perception', domain='chemistry',
        question=text, scope=scope,
        options=[dict(label=label, value=value, unit=None) for label, value in options],
        inputs=[dict(name=n, format='xyz', unit='angstrom') for n in inputs],
        teacher=key)


class IndependenceTests(unittest.TestCase):
    forbidden = ('task_families', 'family_engine', 'template_engine', 'choice_engine', 'checkers',
                 'builder', 'builder_modules')

    def test_the_audit_shares_no_code_with_the_question_generators(self):
        """Same rule as checkers/ and as the eval harness: an auditor that imports the thing it audits
        agrees with it by construction."""
        tree = ast.parse((ROOT / 'review_system' / 'audit.py').read_text(encoding='utf-8'))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split('.')[0])
        self.assertEqual(imported & set(self.forbidden), set())

    def test_what_a_shortcut_rule_is_handed_carries_no_answer(self):
        seen = question().seen
        self.assertEqual(set(seen), {'question', 'scope', 'options'})
        self.assertNotIn('correct_label', json.dumps(seen))
        for option in seen['options']:
            self.assertEqual(set(option), {'label', 'value', 'unit'})

    def test_the_seeded_guess_matches_the_one_the_harness_uses(self):
        """The whole-exam floor pairs each shortcut with the seeded guess, so the audit's copy of that rule
        has to be the harness's rule and not merely look like it."""
        from evaluation import providers
        questions = audit.bank()
        self.assertTrue(questions)
        for q in questions:
            self.assertEqual(audit.guess(q.id), providers.seeded_label(q))


class ShortcutTests(unittest.TestCase):
    def test_the_second_smallest_rule_picks_by_value_not_by_position(self):
        seen = question(options=(('A', '9'), ('B', '1'), ('C', '7'), ('D', '3'))).seen
        self.assertEqual(audit.by_number(seen, 0), 'B')
        self.assertEqual(audit.by_number(seen, 1), 'D')
        self.assertEqual(audit.by_number(seen, 3), 'A')

    def test_a_rule_abstains_rather_than_guessing_when_two_options_tie(self):
        seen = question(options=(('A', '1'), ('B', '1'), ('C', '7'), ('D', '3'))).seen
        self.assertIsNone(audit.by_number(seen, 1))

    def test_a_rule_abstains_when_an_option_carries_no_number(self):
        seen = question(options=(('A', 'left-handed'), ('B', '1'), ('C', '7'), ('D', '3'))).seen
        self.assertIsNone(audit.by_number(seen, 1))

    def test_numbers_are_read_out_of_mixed_text(self):
        seen = question(options=(('A', '8 at 3.65 A'), ('B', '3 at 2.10 A'),
                                 ('C', '12 at 4.01 A'), ('D', '6 at 2.90 A'))).seen
        self.assertEqual(audit.by_number(seen, 0), 'B')

    def test_the_longest_option_rule_abstains_on_a_tie(self):
        self.assertEqual(audit.by_length(question(options=(
            ('A', 'xx'), ('B', 'xxxx'), ('C', 'x'), ('D', 'xxx'))).seen, True), 'B')
        self.assertIsNone(audit.by_length(question(options=(
            ('A', 'xx'), ('B', 'xxxx'), ('C', 'xxxx'), ('D', 'x'))).seen, True))

    def test_the_odd_magnitude_rule_finds_the_one_different_exponent(self):
        seen = question(options=(('A', '1.1'), ('B', '2.3'), ('C', '305'), ('D', '4.0'))).seen
        self.assertEqual(audit.by_odd_magnitude(seen), 'C')

    def test_the_stem_overlap_rule_needs_a_unique_winner(self):
        seen = question(text='which helix is right handed and long',
                        options=(('A', 'right handed helix'), ('B', 'flat'), ('C', 'bent'),
                                 ('D', 'coil'))).seen
        self.assertEqual(audit.by_stem_overlap(seen), 'A')
        tie = question(text='helix helix',
                       options=(('A', 'helix one'), ('B', 'helix two'), ('C', 'flat'),
                                ('D', 'bent'))).seen
        self.assertIsNone(audit.by_stem_overlap(tie))

    def test_a_rule_that_abstains_everywhere_scores_nothing_and_is_not_counted_right(self):
        rows = {row['shortcut']: row for row in audit.shortcut_scores(
            [question(options=(('A', 'x'), ('B', 'x'), ('C', 'x'), ('D', 'x')))])}
        self.assertEqual(rows['选数值第二小的']['decided'], 0)
        self.assertIsNone(rows['选数值第二小的']['score'])

    def test_the_whole_exam_floor_counts_a_guess_where_the_rule_abstains(self):
        """A cheat that applies to a fifth of the bank must not print as a low score; the floor worth
        reporting is the one a whole exam yields."""
        qs = [question(id='Q%d' % i, options=(('A', 'x'), ('B', 'x'), ('C', 'x'), ('D', 'x')),
                       answer=audit.guess('Q%d' % i)) for i in range(20)]
        rows = {row['shortcut']: row for row in audit.shortcut_scores(qs)}
        self.assertEqual(rows['选最长的选项']['decided'], 0)
        self.assertEqual(rows['选最长的选项']['whole_exam'], 1.0)

    def test_an_even_split_of_labels_is_zero_chi_square(self):
        self.assertEqual(audit.chi_square(dict(A=5, B=5, C=5, D=5)), 0.0)
        self.assertGreater(audit.chi_square(dict(A=20, B=0, C=0, D=0)), audit.CHI2_95)


class OptionStructureTests(unittest.TestCase):
    def codes(self, findings):
        return sorted(f['code'] for f in findings)

    def test_two_options_with_the_same_value_are_flagged(self):
        q = question(options=(('A', '1'), ('B', '1'), ('C', '3'), ('D', '4')),
                     teacher=dict(option_audit=[dict(label='B', is_correct=True, value='1', rule='r')]))
        self.assertIn('O2', self.codes(audit.check_option_structure([q])))

    def test_a_question_with_two_correct_options_is_flagged(self):
        q = question(teacher=dict(option_audit=[dict(label='B', is_correct=True, value='2'),
                                                dict(label='C', is_correct=True, value='3')]))
        self.assertIn('O3', self.codes(audit.check_option_structure([q])))

    def test_the_correct_option_has_to_be_the_numeric_answer(self):
        q = question(teacher=dict(option_audit=[dict(label='B', is_correct=True, value='2', rule='r')],
                                  numeric_answer=dict(value='9', tolerance='0.1')))
        self.assertIn('O5', self.codes(audit.check_option_structure([q])))

    def test_a_distractor_inside_the_tolerance_means_two_right_answers(self):
        q = question(teacher=dict(numeric_answer=dict(value='2', tolerance='0.5'),
                                  option_audit=[dict(label='B', is_correct=True, value='2', rule='ok'),
                                                dict(label='A', is_correct=False, value='2.2',
                                                     rule='near')]))
        self.assertIn('D4', self.codes(audit.check_distractor_quality([q])))

    def test_two_distractors_built_the_same_way_are_flagged(self):
        q = question(teacher=dict(option_audit=[
            dict(label='B', is_correct=True, value='2', rule='correct'),
            dict(label='A', is_correct=False, value='1', rule='wrong_rule:I'),
            dict(label='C', is_correct=False, value='3', rule='wrong_rule:I'),
            dict(label='D', is_correct=False, value='4', rule='other')]))
        self.assertIn('D3', self.codes(audit.check_distractor_quality([q])))


class LeakageTests(unittest.TestCase):
    def codes(self, findings):
        return sorted(f['code'] for f in findings)

    def test_an_instance_id_in_the_question_is_a_leak(self):
        q = question(instance='FA-SREL-7029-SAME', text='In FA-SREL-7029-SAME, compute the angle.')
        self.assertIn('L1', self.codes(audit.check_leakage([q])))

    def test_an_attachment_named_after_its_instance_is_flagged(self):
        q = question(instance='FA-PEAK-B5H9', inputs=('FA-PEAK-B5H9-cell.txt',))
        self.assertIn('L2', self.codes(audit.check_leakage([q])))

    def test_the_answer_alone_in_the_stem_is_a_leak(self):
        q = question(text='The helical twisting power (107.5) is reported. What is the HTP?',
                     options=(('A', '1.1'), ('B', '53.8'), ('C', '107.5'), ('D', '215.0')),
                     answer='C')
        self.assertIn('L4', self.codes(audit.check_leakage([q])))

    def test_a_question_that_lists_its_whole_taxonomy_is_not_a_leak(self):
        """The stem naming every option gives nothing away. An earlier version of this check reported 38
        such questions, all of them fine."""
        q = question(text='Classify as right-handed alpha-helix, left-handed alpha-helix or beta-strand.',
                     options=(('A', 'right-handed alpha-helix'), ('B', 'beta-strand'),
                              ('C', 'left-handed alpha-helix'), ('D', 'polyproline')),
                     answer='B')
        self.assertNotIn('L4', self.codes(audit.check_leakage([q])))


class DuplicateTests(unittest.TestCase):
    def pair(self, files_left, files_right, options_right=(('A', '1'), ('B', '2'), ('C', '3'),
                                                           ('D', '4'))):
        text = 'The file gives a host and four candidate guests as 3D structures in angstrom units.'
        left = question(id='Q1', text=text, teacher=dict(correct_label='B', input_hashes=files_left))
        right = question(id='Q2', text=text, options=options_right,
                         teacher=dict(correct_label='B', input_hashes=files_right))
        return audit.check_duplicates([left, right])

    def test_the_same_wording_over_different_attachments_is_not_a_duplicate(self):
        self.assertEqual(self.pair({'a.xyz': 'aa'}, {'b.xyz': 'bb'}), [])

    def test_the_same_wording_the_same_files_and_the_same_options_is_a_duplicate(self):
        found = self.pair({'a.xyz': 'aa'}, {'a.xyz': 'aa'})
        self.assertEqual([f['code'] for f in found], ['U1'])

    def test_the_same_wording_and_files_but_different_options_is_not_a_duplicate(self):
        self.assertEqual(self.pair({'a.xyz': 'aa'}, {'a.xyz': 'aa'},
                                   options_right=(('A', '7'), ('B', '8'), ('C', '9'), ('D', '0'))), [])


class LedgerTests(unittest.TestCase):
    def test_a_question_whose_content_changed_is_reported_as_needing_another_look(self):
        before = question(id='Q1')
        row = dict(id='Q1', content=before.fingerprint(), audit=audit.VERSION)
        after = question(id='Q1', text='Compute something else.')
        status = audit.ledger_status([after], {'Q1': row})
        self.assertEqual(status['content_changed'], ['Q1'])
        self.assertEqual(status['already_audited'], [])

    def test_an_unchanged_question_is_not_audited_twice(self):
        q = question(id='Q1')
        row = dict(id='Q1', content=q.fingerprint(), audit=audit.VERSION)
        self.assertEqual(audit.ledger_status([q], {'Q1': row})['already_audited'], ['Q1'])

    def test_a_new_check_does_not_claim_to_have_run_on_old_questions(self):
        q = question(id='Q1')
        row = dict(id='Q1', content=q.fingerprint(), audit='0.0.1')
        self.assertEqual(audit.ledger_status([q], {'Q1': row})['content_changed'], ['Q1'])

    def test_a_question_never_seen_before_is_reported_as_new(self):
        self.assertEqual(audit.ledger_status([question(id='Q9')], {})['never_audited'], ['Q9'])

    def test_the_fingerprint_moves_when_the_answer_moves(self):
        self.assertNotEqual(question(answer='B').fingerprint(), question(answer='C').fingerprint())

    def test_a_second_run_does_not_stamp_a_question_again(self):
        """The date on a row has to mean "this is when this question was last checked", not "this is when
        the command last ran"."""
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ledger.jsonl'
            qs = [question(id='Q1'), question(id='Q2')]
            self.assertEqual(audit.write_ledger(qs, [], path=path, today='2026-11-04'), 2)
            self.assertEqual(audit.write_ledger(qs, [], path=path, today='2026-11-05'), 0)
            self.assertEqual(audit.read_ledger(path)['Q1']['audited_on'], '2026-11-04')
            moved = [question(id='Q1', text='changed'), question(id='Q2')]
            self.assertEqual(audit.write_ledger(moved, [], path=path, today='2026-11-05'), 1)
            self.assertEqual(audit.read_ledger(path)['Q1']['audited_on'], '2026-11-05')
            self.assertEqual(audit.read_ledger(path)['Q2']['audited_on'], '2026-11-04')

    def test_the_ledger_round_trips(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ledger.jsonl'
            qs = [question(id='Q1'), question(id='Q2')]
            audit.write_ledger(qs, [dict(id='Q1', code='D3')], path=path, today='2026-11-04')
            rows = audit.read_ledger(path)
            self.assertEqual(sorted(rows), ['Q1', 'Q2'])
            self.assertEqual(rows['Q1']['findings'], ['D3'])
            self.assertEqual(rows['Q2']['findings'], [])
            self.assertEqual(rows['Q1']['audited_on'], '2026-11-04')
            self.assertEqual(audit.ledger_status(qs, rows)['already_audited'], ['Q1', 'Q2'])


class DocumentTests(unittest.TestCase):
    def test_a_rerun_keeps_what_a_human_wrote_under_the_marker(self):
        """The decisions table is the one part of the issues document that cannot be regenerated."""
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'REVIEW_ISSUES.md'
            audit.rewrite(path, 'head\n%s\nold body\n%s\n## 决定\n| D3 | 不改：... |\n'
                          % (audit.MARK_BEGIN, audit.MARK_END))
            audit.rewrite(path, 'head\n%s\nNEW body\n%s\n## 决定\n| | |\n'
                          % (audit.MARK_BEGIN, audit.MARK_END))
            text = path.read_text(encoding='utf-8')
            self.assertIn('NEW body', text)
            self.assertNotIn('old body', text)
            self.assertIn('| D3 | 不改：... |', text)

    def test_an_issue_number_does_not_shift_when_another_issue_appears(self):
        """A decision recorded against ISSUE-D3 has to still mean the same thing next week."""
        report = dict(shortcut_leaks=[], family_leaks=[], orderings={},
                      counts={'D3': 4, 'L2': 2},
                      findings=[dict(code='D3', id='Q1', family='f', domain='d', detail='x'),
                                dict(code='L2', id='Q2', family='g', domain='d', detail='y')])
        names = [i['issue'] for i in audit.issues(report)]
        self.assertEqual(names, ['ISSUE-D3', 'ISSUE-L2'])

    def test_an_ordering_scheme_gets_a_readable_issue_number(self):
        self.assertEqual(audit.slug('numeric ascending (label = rank)'), 'numeric-ascending-label')
        self.assertEqual(audit.slug('候选按 id 排序写入附件'), 'id')


class WholeBankTests(unittest.TestCase):
    """The audit against the real published bank. These are the numbers the morning report quotes."""

    @classmethod
    def setUpClass(cls):
        cls.report = audit.audit()

    def test_every_admitted_question_is_audited(self):
        catalog = json.loads((ROOT / 'docs/data/catalog.json').read_text(encoding='utf-8'))
        active = sum(1 for q in catalog['questions']
                     if q.get('lifecycle') == 'active' and q.get('familyInstance'))
        self.assertEqual(self.report['questions'], active)

    def test_the_bank_has_no_structural_defect_in_its_options(self):
        """O1-O5 and D1/D4 are the red checks that must stay at zero: a question with two right answers or
        an option set that disagrees with its key is not answerable at all."""
        for code in ('O1', 'O2', 'O3', 'O4', 'O5', 'D1', 'D4'):
            self.assertEqual(self.report['counts'][code], 0, code)

    def test_no_question_leaks_its_instance_id_or_the_teacher_vocabulary(self):
        for code in ('L1', 'L3'):
            self.assertEqual(self.report['counts'][code], 0, code)

    def test_every_attachment_still_hashes_to_what_was_recorded(self):
        self.assertGreater(self.report['attachments'], 900)
        for code in ('P1', 'P2', 'P3', 'P4'):
            self.assertEqual(self.report['counts'][code], 0, code)

    def test_sharing_a_rule_never_costs_a_question_its_fourth_option(self):
        """REVIEW_ISSUES.md states that D3 is about distractor variety and not about answerability. That
        claim rests on two facts, so they are checked rather than asserted: the two distractors built the
        same way always differ in value, and the right answer is never one of them."""
        for q in audit.bank():
            groups = {}
            for option in (q.teacher.get('option_audit') or []):
                if option.get('rule'):
                    groups.setdefault(option['rule'], []).append(option)
            for rule, group in groups.items():
                if len(group) < 2:
                    continue
                self.assertEqual(len({str(o.get('value')) for o in group}), len(group),
                                 '%s %s' % (q.id, rule))
                self.assertFalse(any(o.get('is_correct') for o in group), '%s %s' % (q.id, rule))

    def test_no_two_questions_are_the_same_question(self):
        self.assertEqual(self.report['counts']['U1'], 0)

    def test_the_known_shortcut_leak_is_reported_rather_than_silently_passing(self):
        """The bank does have leaks; the audit's job is to name them. If this ever goes quiet, check that
        it is because the questions were fixed and not because a rule stopped working."""
        self.assertTrue(self.report['shortcut_leaks'])
        best = max(self.report['shortcuts'], key=lambda r: r['whole_exam'])
        self.assertGreater(best['whole_exam'], 0.25)

    def test_the_issues_document_names_the_real_floor(self):
        text = audit.markdown(self.report)
        floor = max(self.report['shortcuts'], key=lambda r: r['whole_exam'])['whole_exam']
        self.assertIn('%.3f' % floor, text)
        self.assertIn(audit.MARK_BEGIN, text)
        self.assertIn(audit.MARK_END, text)

    def test_the_shortcut_baselines_are_wired_into_the_harness(self):
        from evaluation import providers
        for name in ('shortcut-2nd-smallest', 'shortcut-longest', 'shortcut-stem-overlap', 'always-b'):
            self.assertIn(name, providers.BASELINES)
            answerer = providers.get(name)
            self.assertFalse(answerer.is_model)
            self.assertEqual(answerer.model_calls, 0)

    def test_the_renderable_count_quoted_by_the_exam_is_the_count_in_the_bank(self):
        """`renders` refuses with a number, and that number was wrong once: it was quoted from memory as
        507 when the bank holds 497. A figure that goes into a report has to be counted, not remembered."""
        from evaluation import exam
        workbench = json.loads((ROOT / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
        active = {q.instance for q in audit.bank()}
        cartesian = sum(1 for p in workbench['student_packets'] if p['id'] in active
                        and any(i.get('format') in ('xyz', 'pdb-excerpt') for i in (p['inputs'] or [])))
        self.assertIn('%d/%d' % (cartesian, len(active)),
                      exam.SETTINGS['renders']['unavailable_because'])

    def test_the_numeric_share_quoted_by_the_exam_is_the_count_in_the_bank(self):
        """evaluation/exam.py's own docstring tells a reader how much of the bank the numeric form covers.
        It sat at `464 of the 871` for a whole expansion because prose is not recounted. Same lesson as the
        renderable count above: a figure that a reader will take as fact gets counted here."""
        from evaluation import exam
        active = {q.instance for q in audit.bank()}
        numeric = len(exam.load(form='numeric'))
        self.assertIn('%d of the %d' % (numeric, len(active)), exam.__doc__)

    def test_a_shortcut_baseline_answers_with_a_label_on_every_question(self):
        from evaluation import exam, providers
        answerer = providers.get('shortcut-2nd-smallest')
        for q in exam.load()[:40]:
            self.assertIn(answerer.answer(q, q.prompt('coords')), ('A', 'B', 'C', 'D'))


if __name__ == '__main__':
    unittest.main()
