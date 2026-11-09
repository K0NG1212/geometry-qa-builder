"""Each question's folder must be enough for someone else to make that question again.

The shape is the advisor's whiteboard (2026-11-05): source/ holds the paper or data plus an instruction
saying how to get from them to the question; QA.json is the question and its answer; info.json says what
every file in the folder is. The folder is the *quality-checking* copy -- it is explicitly not what a model
under test is given, which is why the answer sits in it openly and why there is no student/ any more.

So what these tests pin is no longer "the answer must not leak into this file" but "a reader has everything
and is told what it is": every file on disk is listed in info.json and nothing listed is missing; the
instruction names each file and says how to recompute; the attachment in source/data/ is byte-for-byte the
published asset; a computed question ships a runnable recompute.py and the toolkit it needs; and a second
run writes nothing.

The folders live outside the repository (D:/GeoBench-data/qa), so these build them into a temp directory.
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


class QaFolderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix='qa-folders-'))
        # A stale folder from the old layout, to pin that exporting clears it rather than leaving a
        # half-old folder in which student/ still holds a packet nobody maintains.
        stale = cls.dir / ADMITTED[0]['id'] / 'student'
        stale.mkdir(parents=True)
        (stale / 'question.txt').write_text('old layout', encoding='utf-8')
        cls.export = export_qa_folders.Export(cls.dir, papers=False, recompute=False)
        cls.export.run_all()
        cls.teacher = {t['id']: t for t in WORKBENCH['teacher_answers']}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_every_admitted_question_has_the_four_things_the_whiteboard_names(self):
        for question in ADMITTED:
            folder = self.dir / question['id']
            for name in ('info.json', 'QA.json', 'source/SOURCE.txt', 'source/instruction.md'):
                self.assertTrue((folder / name).exists(), '%s/%s' % (question['id'], name))

    def test_the_old_layout_is_gone(self):
        """student/ is the package a model under test is given and has no place in the quality copy;
        reviewer/ was four files that instruction.md and QA.json now carry between them."""
        self.assertFalse((self.dir / ADMITTED[0]['id'] / 'student').exists())
        for question in ADMITTED[:50]:
            folder = self.dir / question['id']
            self.assertFalse((folder / 'student').exists(), question['id'])
            self.assertFalse((folder / 'reviewer').exists(), question['id'])

    def test_info_json_lists_every_file_in_the_folder_and_only_files_that_are_there(self):
        """The advisor's words: "要把所有的 folder、它的功能介绍清楚"。A manifest that is missing a file,
        or names one that is not there, is worse than none -- a checker would trust it."""
        for question in ADMITTED:
            folder = self.dir / question['id']
            info = json.loads((folder / 'info.json').read_text(encoding='utf-8'))
            listed = {f['path'] for f in info['files']}
            on_disk = {str(p.relative_to(folder)).replace('\\', '/')
                       for p in folder.rglob('*') if p.is_file()}
            self.assertEqual(listed, on_disk, question['id'])
            for entry in info['files']:
                self.assertTrue(entry['role'].strip(), '%s: %s 没写作用' % (question['id'], entry['path']))

    def test_qa_json_is_the_question_and_the_answer(self):
        for question in ADMITTED:
            qa = json.loads((self.dir / question['id'] / 'QA.json').read_text(encoding='utf-8'))
            teacher = self.teacher[question['familyInstance']]
            self.assertTrue(qa['question']['text'], question['id'])
            self.assertEqual(len(qa['question']['options']), 4, question['id'])
            self.assertEqual(qa['answer']['label'], teacher['correct_label'], question['id'])
            self.assertEqual(qa['family_instance'], question['familyInstance'])
            # Everything recompute.py needs to rebuild the checker's packet and key.
            self.assertTrue(qa['input_hashes'], question['id'])
            for item in qa['question']['attachments']:
                self.assertTrue(item['file'].startswith('data/'), question['id'])
                self.assertTrue(item['format'], '%s: %s 没记格式' % (question['id'], item['file']))

    def test_the_attachment_in_the_folder_is_the_published_asset_byte_for_byte(self):
        for question in ADMITTED:
            folder = self.dir / question['id']
            for attachment in question.get('attachments') or []:
                local = folder / 'source' / 'data' / Path(attachment['url']).name
                self.assertTrue(local.exists(), '%s/%s' % (question['id'], local.name))
                self.assertEqual(local.read_bytes(), (ROOT / 'docs' / attachment['url']).read_bytes(),
                                 question['id'])

    def test_the_instruction_tells_a_reader_what_to_open_and_what_to_run(self):
        for question in ADMITTED:
            folder = self.dir / question['id']
            text = (folder / 'source' / 'instruction.md').read_text(encoding='utf-8')
            info = json.loads((folder / 'info.json').read_text(encoding='utf-8'))
            for heading in ('## 0 这个文件夹里有什么', '## 1 这道题问什么', '## 2 数据从哪来',
                            '## 3 怎么算出答案', '## 4 答案应该是', '## 7 这题保证不了什么'):
                self.assertIn(heading, text, question['id'])
            for entry in info['files']:                     # every file is named in the instruction too
                name = entry['path'].split('/')[-1]
                if name not in ('instruction.md',):
                    self.assertIn(name, text, '%s: instruction 没提 %s' % (question['id'], name))
            self.assertIn('本题未经任何人工审核', text, question['id'])
            for noise in ('21.535119868514066', '0.00000000000'):   # floats cut to what a person reads
                self.assertNotIn(noise, text, question['id'])

    def test_a_computed_question_ships_a_runnable_recompute_and_the_toolkit_it_needs(self):
        import checkers
        with_py = [q for q in ADMITTED
                   if (self.dir / q['id'] / 'source' / 'recompute.py').exists()]
        self.assertGreater(len(with_py), len(ADMITTED) // 2, '多数题应当能重算')
        for question in with_py:
            script = (self.dir / question['id'] / 'source' / 'recompute.py').read_text(encoding='utf-8')
            self.assertIn('../QA.json', script, question['id'])
            self.assertIn('_toolkit', script, question['id'])
            self.assertIn(question['family'], script, question['id'])
        toolkit = self.dir / '_toolkit'
        for module in (ROOT / 'checkers').glob('*.py'):
            self.assertTrue((toolkit / 'checkers' / module.name).exists(), module.name)
        for question in with_py:                        # and the assets the checker hashes
            qa = json.loads((self.dir / question['id'] / 'QA.json').read_text(encoding='utf-8'))
            for rel in qa['input_hashes']:
                self.assertTrue((toolkit / 'docs' / rel).exists(), '%s 缺 %s' % (question['id'], rel))
        self.assertTrue(checkers.VERSION in (toolkit / 'README.md').read_text(encoding='utf-8'))

    def test_data_we_built_ourselves_says_so_and_gives_the_rule(self):
        """Some attachments are models this project constructed from numbers a paper reports -- an
        ideal triangular vortex lattice at the paper's field, a sphere cut from ideal zinc blende.
        Mistaking one for measured data would be our fault, not the reader's, so the folder has to say
        it in the file the reader opens, and say how it was built."""
        built = []
        for question in ADMITTED:
            folder = self.dir / question['id']
            info = json.loads((folder / 'info.json').read_text(encoding='utf-8'))
            text = (folder / 'source' / 'instruction.md').read_text(encoding='utf-8')
            origin = info['data_origin']
            self.assertTrue(origin['what_it_is'].strip(), question['id'])
            if origin['constructed_by_this_project']:
                built.append(question['id'])
                self.assertTrue(origin['construction_rule'], '%s 标了构造却没有规则' % question['id'])
                self.assertIn('本项目构造的', text, question['id'])
                self.assertIn('### 怎么构造的', text, question['id'])
                self.assertIn(origin['construction_rule'][:40], text, question['id'])
            else:
                self.assertNotIn('本项目构造的', text, '%s 不是构造的却挂了警告' % question['id'])
        self.assertGreater(len(built), 0, '没有一道题标为构造，说明判定失效了')

    def test_the_folder_says_plainly_that_nothing_is_human_reviewed(self):
        for question in ADMITTED:
            info = json.loads((self.dir / question['id'] / 'info.json').read_text(encoding='utf-8'))
            self.assertIn('未经', info['review']['note'])
            self.assertEqual([info['review'][level] for level in ('L1', 'L2', 'L3', 'L4')], ['pending'] * 4)
            self.assertEqual(info['how_to_extract']['model_calls'], 0)
            self.assertTrue(info['how_to_extract']['generator_code'], question['id'])
            self.assertTrue(info['originality']['statement'], question['id'])
            self.assertNotEqual(info['originality']['coordinates'], 'see_statement', question['id'])

    def test_the_folder_is_not_what_a_model_under_test_is_given(self):
        """The whole layout rests on this split, so it is worth a test rather than a comment: the exam
        side builds its prompts from the published workbench, never from these folders."""
        exam = (ROOT / 'evaluation' / 'exam.py').read_text(encoding='utf-8')
        self.assertIn('family-workbench.json', exam)
        for marker in ('GeoBench-data', 'qa/', 'QA.json'):
            self.assertNotIn(marker, exam.split('"""', 2)[2])     # docstring may mention it; code may not

    def test_a_second_run_writes_nothing(self):
        again = export_qa_folders.Export(self.dir, papers=False, recompute=False)
        again.run_all()
        self.assertEqual(again.written, 0)
        self.assertEqual(again.missing, [])
        self.assertEqual(again.removed, 0)


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

    # Keep all 24 historical regressions while checking every newly registered anode too.
    FORMERLY_LEAKING_ANODE = {
        'EN-COD1000028-XD-ANODE-Mo',
        'EN-COD1100043-XD-ANODE-Co',
        'EN-COD1516287-XD-ANODE-Cr',
        'EN-COD1516287-XD-ANODE-Cu',
        'EN-COD1516287-XD-ANODE-Mo',
        'EN-COD1536825-XD-ANODE-Co',
        'EN-COD1536825-XD-ANODE-Cu',
        'EN-COD1538281-XD-ANODE-Co',
        'EN-COD1538281-XD-ANODE-Mo',
        'EN-COD1574067-XD-ANODE-Cr',
        'EN-COD4118591-XD-ANODE-Mo',
        'EN-COD4118891-XD-ANODE-Co',
        'EN-COD4118891-XD-ANODE-Cu',
        'EN-COD4118891-XD-ANODE-Mo',
        'EN-COD4320505-XD-ANODE-Co',
        'EN-COD4320505-XD-ANODE-Cr',
        'EN-COD5000216-XD-ANODE-Co',
        'EN-COD5000216-XD-ANODE-Cu',
        'EN-COD9006483-XD-ANODE-Co',
        'EN-COD9008565-XD-ANODE-Co',
        'EN-COD9008789-XD-ANODE-Cr',
        'EN-COD9008789-XD-ANODE-Cu',
        'EN-COD9008802-XD-ANODE-Mo',
        'EN-COD9011073-XD-ANODE-Mo',
    }

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
        """Every anode table is named COD<number>; the original 24 cases must stay covered."""
        anode = [x for x in MANIFEST['items'] if x['family'] == 'diffraction_design' and x['mode'] == 'anode' and x.get('cod')]
        self.assertTrue(self.FORMERLY_LEAKING_ANODE <= {x['id'] for x in anode})
        for spec in anode:
            packet = diffraction_design.build(dict(spec, target_position=1), ROOT, 'geobench-family-v1')
            names = [i['name'] for i in packet['inputs']]
            self.assertEqual(names, ['COD%s-cell.txt' % spec['cod']], spec['id'])
            self.assertEqual(telltale(names, packet['option_audit']), set(), spec['id'])


if __name__ == '__main__':
    unittest.main()
