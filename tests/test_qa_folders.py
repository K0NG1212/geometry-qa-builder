"""W1: the per-question folders (tools/export_qa_folders.py) must be traceable and must not leak the answer.

The folders themselves live outside the repository (D:/GeoBench-data/qa by default), so these tests build them
into a temporary directory instead. What they pin: every admitted question gets a folder with the four fields the
advisor asked for (how to extract, originality, locator, evidence); the answer and the measured values stay in
reviewer/ and never appear in info.json or student/, because a folder handed to a model is read from the top; and
a second run writes nothing, so a re-run shows only what really changed.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import export_qa_folders  # noqa: E402

CATALOG = json.loads((ROOT / 'docs/data/catalog.json').read_text(encoding='utf-8'))
WORKBENCH = json.loads((ROOT / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
ADMITTED = [q for q in CATALOG['questions'] if q.get('lifecycle') == 'active' and q.get('familyInstance')]
# Markers that would say which option is right. "reason" alone is not one of them: "reasoning" is a legitimate
# classification field, and the engine already scans the packets themselves for its own word list.
LEAK_MARKERS = ('is_correct', 'correct_label', 'option_audit', '"measured"', 'excluded_candidates')


def leaves(node):
    """Every text value in a JSON tree, so a copied-in answer can be spotted exactly. Numbers are left out:
    info.json legitimately carries counts such as model_calls 0, and an option whose value is "0" would match
    one of those without anything having leaked."""
    if isinstance(node, dict):
        return set().union(*(leaves(v) for v in node.values())) if node else set()
    if isinstance(node, list):
        return set().union(*(leaves(v) for v in node)) if node else set()
    return {node} if isinstance(node, str) and len(node) >= 3 else set()


class QaFolderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix='qa-folders-'))
        cls.export = export_qa_folders.Export(cls.dir, papers=False)
        cls.index = cls.export.run_all()
        cls.teacher = {t['id']: t for t in WORKBENCH['teacher_answers']}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_every_admitted_question_has_a_folder_with_the_four_fields(self):
        self.assertEqual(len(self.index), len(ADMITTED))
        for question in ADMITTED:
            folder = self.dir / question['id']
            for name in ('info.json', 'source/SOURCE.txt', 'student/question.txt',
                         'reviewer/answer.json', 'reviewer/locators.json', 'reviewer/limits.txt'):
                self.assertTrue((folder / name).exists(), '%s/%s' % (question['id'], name))
            info = json.loads((folder / 'info.json').read_text(encoding='utf-8'))
            self.assertTrue(info['how_to_extract']['generator_code'], question['id'])
            self.assertTrue(info['how_to_extract']['independent_checker'], question['id'])
            self.assertTrue(info['originality']['statement'], question['id'])
            self.assertNotEqual(info['originality']['coordinates'], 'see_statement', question['id'])
            self.assertTrue(info['locator']['asset_files'], question['id'])
            self.assertTrue(info['evidence']['asset_hashes'], question['id'])
            self.assertEqual(info['evidence']['independent_check']['status'], 'pass', question['id'])

    def test_the_folder_says_plainly_that_nothing_is_human_reviewed(self):
        for question in ADMITTED:
            info = json.loads((self.dir / question['id'] / 'info.json').read_text(encoding='utf-8'))
            self.assertIn('未经', info['review']['note'])
            self.assertEqual([info['review'][level] for level in ('L1', 'L2', 'L3', 'L4')], ['pending'] * 4)
            self.assertEqual(info['how_to_extract']['model_calls'], 0)

    def test_info_json_and_student_do_not_carry_the_answer(self):
        for question in ADMITTED:
            folder = self.dir / question['id']
            info = (folder / 'info.json').read_text(encoding='utf-8')
            student = (folder / 'student/question.txt').read_text(encoding='utf-8')
            teacher = self.teacher[question['familyInstance']]
            right = next(o for o in teacher['option_audit'] if o['is_correct'])
            for marker in LEAK_MARKERS:
                self.assertNotIn(marker, info, '%s: info.json carries %s' % (question['id'], marker))
                self.assertNotIn(marker, student, '%s: question.txt carries %s' % (question['id'], marker))
            # Which option is right must be in neither file: not as a label, not as the audit's wording, and
            # not as the value only the right option has.
            self.assertNotIn(str(right.get('reason') or 'nothing to look for'), info, question['id'])
            self.assertNotIn(str(right.get('reason') or 'nothing to look for'), student, question['id'])
            # No field of info.json may be an option's value. Substring matching would cry wolf here: for
            # stereo_relationship the right value is the word "same", which also sits inside a distractor
            # mechanism's name -- and inside the instance id FA-SREL-7029-SAME, which is why a model is given
            # student/ only and never the instance id.
            values = {str(o['value']) for o in teacher['option_audit'] if len(str(o['value'])) >= 3}
            self.assertEqual(values & leaves(json.loads(info)), set(), question['id'])
            self.assertIn('reviewer/answer.json', info, question['id'])
            answer = json.loads((folder / 'reviewer/answer.json').read_text(encoding='utf-8'))
            self.assertEqual(answer['correct_label'], teacher['correct_label'], question['id'])

    def test_the_student_folder_holds_every_attachment_the_question_names(self):
        for question in ADMITTED:
            for attachment in question.get('attachments') or []:
                name = Path(attachment['url']).name
                self.assertTrue((self.dir / question['id'] / 'student' / name).exists(),
                                '%s/%s' % (question['id'], name))

    def test_a_second_run_writes_nothing(self):
        again = export_qa_folders.Export(self.dir, papers=False)
        again.run_all()
        self.assertEqual(again.written, 0)
        self.assertEqual(again.missing, [])


if __name__ == '__main__':
    unittest.main()
