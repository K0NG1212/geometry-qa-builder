"""W1: the per-question folders (tools/export_qa_folders.py) must be traceable and must not leak the answer.

The folders themselves live outside the repository (D:/GeoBench-data/qa by default), so these tests build them
into a temporary directory instead. What they pin: every admitted question gets a folder with the four fields the
advisor asked for (how to extract, originality, locator, evidence); the answer and the measured values stay in
reviewer/ and never appear in info.json or student/, because a folder handed to a model is read from the top; and
a second run writes nothing, so a re-run shows only what really changed.
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import export_qa_folders  # noqa: E402
from task_families import diffraction_design, protein_design  # noqa: E402

CATALOG = json.loads((ROOT / 'docs/data/catalog.json').read_text(encoding='utf-8'))
MANIFEST = json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))
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

    def test_every_folder_has_one_readable_evidence_sheet(self):
        """What a reviewer opens. The pieces were always in the folder, but spread over four JSON files; this
        sheet is the one file that can be read start to finish, by a person or by another model."""
        for question in ADMITTED:
            sheet = (self.dir / question['id'] / 'reviewer/EVIDENCE.txt').read_text(encoding='utf-8')
            teacher = self.teacher[question['familyInstance']]
            self.assertIn(question['id'], sheet)
            self.assertIn('答案：', sheet)
            self.assertIn(str(next(o for o in teacher['option_audit'] if o['is_correct'])['value']), sheet)
            self.assertIn('二、证据：附件原样引用', sheet)
            self.assertIn('五、独立检查器', sheet)
            self.assertIn('本题未经任何人工审核', sheet)
            for marker in ('21.535119868514066', '0.00000000000'):      # floats are cut to what a person reads
                self.assertNotIn(marker, sheet, question['id'])
            info = (self.dir / question['id'] / 'info.json').read_text(encoding='utf-8')
            student = (self.dir / question['id'] / 'student/question.txt').read_text(encoding='utf-8')
            self.assertIn('reviewer/EVIDENCE.txt', info)                # info.json says where it is
            self.assertNotIn('二、证据', student)                        # but the sheet itself stays reviewer-side

    def test_a_second_run_writes_nothing(self):
        again = export_qa_folders.Export(self.dir, papers=False)
        again.run_all()
        self.assertEqual(again.written, 0)
        self.assertEqual(again.missing, [])


FORMAT_WORDS = {'xyz', 'txt', 'pdb', 'cif', 'json', 'design', 'excerpt', 'cell'}


def fields(name):
    """A file name as the dash-separated fields it was built from. 1A6M stays whole: it is a structure id,
    not the number 6."""
    return {s.lower() for s in re.split(r'[^0-9A-Za-z]+', name) if s} - FORMAT_WORDS


def words(value):
    """An option value down to its letters and numbers, so that Glu6 is the residue Glu and the number 6."""
    spaced = re.sub(r'(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])', ' ', str(value))
    return {s.lower() for s in re.split(r'[^0-9A-Za-z]+', spaced) if s} - FORMAT_WORDS


def telltale(names, options):
    """What the file names give away: anything that belongs to the right option and to no other one.

    Nothing is given away when every option names a file of its own -- then picking a file is the question,
    and the candidate numbers belong in the names.
    """
    in_names = set().union(*(fields(n) for n in names))
    if all(words(o['value']) & in_names for o in options):
        return set()
    right = next(o for o in options if o['is_correct'])
    others = set().union(*(words(o['value']) for o in options if not o['is_correct']))
    return (words(right['value']) - others) & in_names


class AttachmentNameTests(unittest.TestCase):
    """A file name is part of the student packet: the question prints it on its 附件 line and the folder
    lists it. A name that singles out the right option answers the question without the geometry.

    This is not hypothetical, and it has happened twice. protein_design named its excerpt after the tail of the
    instance id, and an enumerated id ends in the residue numbers of the correct pair (EN-1A6M-DS-2-6 -> the pair
    2-6), so eight questions shipped with the answer in the file name. diffraction_design did the same with its
    cell table: an enumerated id ends in the line whose angle set the target (EN-COD9008789-XD-ANODE-Cu), which in
    anode mode is the answer, so all 24 enumerated anode questions named it. Both generators now name the file
    after the structure instead.
    """

    # Those eight. The generator was fixed on 2026-11-01 and the re-run of 2026-11-03 (family-pilot-v44)
    # replaced the published names, so none of them leaks any more and the pending list is empty. They are
    # kept here as the cases the last test rebuilds: a regression would show up on exactly these eight.
    PENDING_RERUN = set()
    FORMERLY_LEAKING = {'EN-1A6M-DS-2-6', 'EN-1A6M-FD-25-1-18', 'EN-1FHA-DS-6-9', 'EN-1FHA-FD-25-5-42',
                        'EN-12E8-DS-7-21', 'EN-12E8-FD-25-1-11', 'EN-1HHK-DS-5-168', 'EN-1HHK-FD-25-1-16'}

    def leaking(self):
        teachers = {t['id']: t for t in WORKBENCH['teacher_answers']}
        out = {}
        for question in CATALOG['questions']:
            teacher = teachers.get(question.get('familyInstance'))
            names = [Path(a['url']).name for a in (question.get('attachments') or [])]
            if teacher and names:
                give = telltale(names, teacher['option_audit'])
                if give:
                    out[question['familyInstance']] = (question['id'], names, sorted(give))
        return out

    def test_no_published_attachment_name_gives_the_answer_away(self):
        self.assertEqual({i: v for i, v in self.leaking().items() if i not in self.PENDING_RERUN}, {})

    def test_the_pending_list_holds_nothing_the_latest_run_has_already_fixed(self):
        fixed = sorted(self.PENDING_RERUN - set(self.leaking()))
        self.assertEqual(fixed, [], 'delete these from PENDING_RERUN: %s' % fixed)

    def test_the_fixed_generator_names_the_excerpt_after_the_chain(self):
        specs = {x['id']: x for x in MANIFEST['items']}
        build = {'disulfide_design': protein_design.build_disulfide, 'fret_design': protein_design.build_fret}
        for instance in sorted(self.FORMERLY_LEAKING):
            spec = specs[instance]
            packet = build[spec['family']](spec, ROOT, 'geobench-family-v1')
            names = [i['name'] for i in packet['inputs']]
            self.assertEqual(names, ['%s-%s-design-excerpt.pdb' % (spec['pdb'], spec['chain'])], instance)
            self.assertEqual(telltale(names, packet['option_audit']), set(), instance)

    def test_the_fixed_generator_names_the_cell_table_after_the_crystal(self):
        """The 24 anode questions: the table is named COD<number>, so no name carries the chosen line."""
        anode = [x for x in MANIFEST['items'] if x['family'] == 'diffraction_design' and x['mode'] == 'anode' and x.get('cod')]
        self.assertEqual(len(anode), 24)
        for spec in anode:
            packet = diffraction_design.build(dict(spec, target_position=1), ROOT, 'geobench-family-v1')
            names = [i['name'] for i in packet['inputs']]
            self.assertEqual(names, ['COD%s-cell.txt' % spec['cod']], spec['id'])
            self.assertEqual(telltale(names, packet['option_audit']), set(), spec['id'])


if __name__ == '__main__':
    unittest.main()
