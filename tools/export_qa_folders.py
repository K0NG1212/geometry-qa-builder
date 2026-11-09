"""One folder per question, holding everything needed to make that question again from its source.

  python tools/export_qa_folders.py                       # every admitted question -> D:/GeoBench-data/qa
  python tools/export_qa_folders.py --ids CND022,BND024   # just these
  python tools/export_qa_folders.py --no-recompute        # skip running each question's recompute.py
  python tools/export_qa_folders.py --out E:/somewhere --no-papers --dry-run

The shape comes from the advisor's whiteboard (2026-11-05 meeting):

  <id>/info.json            metadata: what every file here is, and how this QA came to be
  <id>/QA.json              the question and its answer
  <id>/source/SOURCE.txt    citation, links, licence, asset hashes
  <id>/source/instruction.md    HOW to get from the files in source/ to QA.json -- the required piece
  <id>/source/data/         the data the question hands out, as a file
  <id>/source/<paper>       the paper or document in full, for questions that come from one
  <id>/source/recompute.py  for questions whose answer is computed: the independent checker, runnable
  <id>/source/recompute.out.txt   what that script actually printed here

and, once for the whole tree, `_toolkit/` -- the checker code and the assets it hashes, so a recompute.py
runs without this repository.

The test is not "is the evidence attached" but "can someone else rebuild the question": read info.json,
follow instruction.md, run recompute.py, and you must land on the same QA.json. That is what lets a
thousand questions be checked by a model instead of by hand.

**The folder is not what a model under test is given.** It is the quality-checking copy, so the answer,
the option audit and the checker's own numbers all sit in it openly. The exam side reads
docs/data/family-workbench.json (see evaluation/exam.py) and never these folders, which is why they no
longer carry a student/ directory.

The folders are local, never in git: they hold copies of paper full texts and of every attachment. The
repository keeps only this generator, so the tree can be rebuilt at any time.

Writing is idempotent: a file is only touched when its content changes, so a re-run shows what moved.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
DEFAULT_OUT = Path('D:/GeoBench-data/qa')
NEWLINE = chr(10)
SITE = 'https://k0ng1212.github.io/geometry-qa-builder/'
TOOLKIT = '_toolkit'
RUNBOOK_STEPS = ['3 题型族', '4 独立检查器', '5 注册表与规格', '6 生成', '7 独立复核', '8 导出', '9 入库', '10 挑选与审核材料']
# Written by earlier runs; the whiteboard replaced both. Removed on export so a folder cannot be half old.
STALE = ('student', 'reviewer')
# What the coordinates in the attachments actually are. Each rule is a phrase the attribution text itself uses,
# so the label is read off the record rather than guessed; anything unmatched stays "see_statement".
COORDINATES = [('照抄', 'database_verbatim'), ('原样', 'database_verbatim'), ('未改动', 'database_verbatim'),
               ('约简', 'database_reduced'), ('刚性旋转平移', 'database_rigid_transform'),
               ('对称操作展开', 'database_symmetry_expanded'), ('对称展开', 'database_symmetry_expanded'),
               ('转为 XYZ', 'database_format_converted'), ('转换为 XYZ', 'database_format_converted'),
               ('Cα 坐标', 'database_format_converted'),
               ('由本项目生成', 'generated_by_this_project'), ('由本项目构建', 'generated_by_this_project')]
# A statement that names a database but no transformation: the coordinates are that database's, and the
# statement itself says how they were handled. Checked only after the rules above, which are more specific.
DATABASES = ['RCSB PDB', 'Crystallography Open Database', 'COD', 'QM7-X', 'SAMPL9', 'Landscape17', 'wwPDB']

CONSTRUCTED_WARNING = ('**本项目自己构造的模型**，不是实测数据，也不是数据库里的条目：'
                       '参数取自论文，结构由本库按下面的规则生成。')
NOT_CONSTRUCTED = {
    'database_verbatim': '数据库条目原样照抄，未改动。',
    'database_format_converted': '数据库条目，只换了文件格式（如 PDB → XYZ），坐标未改动。',
    'database_reduced': '数据库条目的约简表示（如每条链一个质心），坐标来自数据库。',
    'database_symmetry_expanded': '数据库条目按其沉积的对称操作展开，坐标来自数据库。',
    'database_rigid_transform': '数据库条目经刚性旋转平移，内部几何未改动。',
    'database_source': '来自数据库，具体处理方式见 originality.statement。',
    'evidence_from_paper_no_coordinates': '论文里的事实，逐条转述为文字；没有坐标。',
    'measured_values_from_paper_no_coordinates': '论文报告的测量值，转述为候选描述；没有坐标。',
}

RECOMPUTE = '''"""重算 %(id)s 的答案，只用这个文件夹里的东西。

读 ../QA.json 的题面与选项、data/ 里的附件，交给题型族 %(family)s 的独立检查器
（%(checker)s，在 %(toolkit)s，与题库一起发布）重算一遍，再把它算出来的量和
QA.json 里记的答案对一下。

  python recompute.py        本机跑出来的输出见 recompute.out.txt

退出码 0 表示检查器重算通过且与 QA.json 的答案一致；非 0 表示对不上，这道题要人看。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / '%(toolkit_name)s'))

import checkers                                                    # noqa: E402

qa = json.loads((HERE.parent / 'QA.json').read_text(encoding='utf-8'))
question, answer = qa['question'], qa['answer']

packet = dict(id=qa['family_instance'], family=qa['family'], question=question['text'],
              scope=question['scope'], options=question['options'],
              inputs=[dict(name=a['name'], format=a['format'], unit=a['unit'],
                           text=(HERE / a['file']).read_text(encoding='utf-8'))
                      for a in question['attachments']])
key = dict(id=qa['family_instance'], family=qa['family'], correct_label=answer['label'],
           numeric_answer=answer['numeric'], input_hashes=qa['input_hashes'])

report = checkers.check(packet, key)
print(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True))
print()
if report['status'] != 'pass':
    print('独立检查器没通过：%%s' %% report.get('problem'))
    sys.exit(1)
print('独立检查器通过；QA.json 记的答案是 %%s，检查器用自己的算法重算后认同这个答案。'
      %% (answer['label'] or answer['value']))
'''

TOOLKIT_README = '''# _toolkit —— 重算用的代码与附件

每道题的 `source/recompute.py` 都从这里 import。放在题库根目录一份，不是每题一份。

  checkers/          独立检查器：和出题代码分开写的另一套实现，用来重算答案
  docs/assets/...    检查器要核对哈希的附件原件（%(assets)d 个文件）

跑一道题：

  cd <题号>/source && python recompute.py

需要 Python 3.9+ 与 numpy。代码来自 geometry-qa-builder 仓库的 checkers/，
版本 %(version)s，复制于 %(date)s。
'''


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_links(source):
    """The links docs/sources.js shows for a citation, so the folder and the site agree."""
    source = source or ''
    if re.match(r'^https?://', source.strip()):
        return [source.strip()]
    inside = list(dict.fromkeys(re.findall(r'https?://[^\s;,，、）)]+', source)))[:3]
    if inside:
        return inside
    out = []
    doi = re.search(r'\bdoi:?\s*(10\.\S+?)(?:[\s;,，（(。]|$)', source, re.I)
    pmc = re.search(r'\b(PMC\d+)\b', source)
    arxiv = re.search(r'arXiv:\s*(\d{4}\.\d{4,5})', source, re.I)
    if doi:
        out.append('https://doi.org/' + doi.group(1))
    if pmc:
        out.append('https://europepmc.org/article/PMC/' + pmc.group(1))
    if arxiv:
        out.append('https://arxiv.org/abs/' + arxiv.group(1))
    return out


def coordinates_kind(question, card):
    if card and card.get('kind') == 'design_pointer_card':
        return 'measured_values_from_paper_no_coordinates'
    if card:
        return 'evidence_from_paper_no_coordinates'
    statement = question.get('attribution') or ''
    for phrase, label in COORDINATES:
        if phrase in statement:
            return label
    if any(name in statement for name in DATABASES):
        return 'database_source'
    return 'see_statement'


def asset_group(paths):
    """The docs/assets folder the attachments come from; its sources.json records how they were built."""
    for path in paths:
        parts = path.split('/')
        if len(parts) > 2 and parts[1] == 'families':
            return 'docs/assets/families/' + parts[2]
        if len(parts) > 1:
            return 'docs/assets/' + parts[1]
    return None


def show(value, places=6):
    """A number a person reads: 21.535119868514066 is noise, 21.5351 is the angle."""
    if isinstance(value, float):
        return '%.*g' % (places, value)
    if isinstance(value, dict):
        return '{%s}' % ', '.join('%s: %s' % (k, show(v)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return '[%s]' % ', '.join(show(v) for v in value)
    return str(value)


def indent(text, prefix='  '):
    return NEWLINE.join(prefix + line for line in str(text).splitlines()) or prefix + '—'


def quote(text, head=40, tail=5):
    """The attachment as it is; a long one is cut in the middle so the sheet stays readable."""
    lines = str(text or '').splitlines()
    if len(lines) <= head + tail + 1:
        return indent(NEWLINE.join(lines), '      ')
    middle = '      …（共 %d 行，中间省略 %d 行）' % (len(lines), len(lines) - head - tail)
    kept = ['      ' + x for x in lines[:head]] + [middle] + ['      ' + x for x in lines[-tail:]]
    return NEWLINE.join(kept)


class Export:
    def __init__(self, out, papers=True, dry_run=False, recompute=True):
        self.out, self.papers, self.dry_run = Path(out), papers, dry_run
        self.recompute = recompute and not dry_run
        self.catalog = read('docs/data/catalog.json')
        self.cards = {c['id']: c for c in read('docs/data/cards.json')['cards']}
        workbench = read('docs/data/family-workbench.json')
        self.run = workbench['run']
        self.teacher = {t['id']: t for t in workbench['teacher_answers']}
        self.student = {s['id']: s for s in workbench['student_packets']}
        self.stage = {s['id']: s for s in workbench['stage_records']}
        self.checks = {r['id']: r for r in read('docs/data/independent-check.json')['results']}
        self.registry = {}
        for row in read('templates/registry.json')['templates']:
            for family in row.get('engine_families') or []:
                self.registry[family] = row
        self.pointers = {p.stem: json.loads(p.read_text(encoding='utf-8'))
                         for p in (DOCS / 'assets/families/design/pointers').glob('*.json')}
        self.evidence = {p.stem: json.loads(p.read_text(encoding='utf-8'))
                         for p in (DOCS / 'assets/families/evidence').glob('*.json') if p.name != 'sources.json'}
        sys.path.insert(0, str(ROOT))
        import checkers                                            # the families that can be recomputed
        self.checkers = set(checkers.CHECKERS)
        self.checker_version = checkers.VERSION
        self.records = {}
        self.orphans = []
        self.written = self.unchanged = self.removed = 0
        self.missing = []
        self.assets = set()
        self.reproduced, self.failed = [], []

    # ---------- writing ----------
    def put(self, path, text):
        """Write only when the content differs, so a re-run reports real changes."""
        if path.exists() and path.read_text(encoding='utf-8') == text:
            self.unchanged += 1
            return
        self.written += 1
        if self.dry_run:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8', newline='\n')

    def put_json(self, path, obj):
        self.put(path, json.dumps(obj, ensure_ascii=False, indent=1) + '\n')

    def copy(self, src, dst):
        src = Path(src)
        if not src.exists():
            self.missing.append(str(src))
            return False
        if dst.exists() and dst.stat().st_size == src.stat().st_size and sha256(dst) == sha256(src):
            self.unchanged += 1
            return True
        self.written += 1
        if not self.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        return True

    def tidy(self, folder):
        """Drop what earlier runs wrote and the whiteboard removed, so no folder is half old.

        student/ is the package a model under test is given; it does not belong in the quality copy
        (the exam side builds it from docs/data/family-workbench.json). reviewer/ was answer.json +
        locators.json + EVIDENCE.txt + limits.txt, all of which are now QA.json and instruction.md."""
        for name in STALE:
            path = folder / name
            if path.is_dir():
                self.removed += 1
                if not self.dry_run:
                    shutil.rmtree(path)

    # ---------- one question ----------
    def card_of(self, teacher):
        name = (teacher.get('checks') or {}).get('card')
        return self.pointers.get(name) or self.evidence.get(name)

    def how_to_extract(self, question, teacher, row):
        checker = self.checks.get(teacher['id'], {})
        return {
            'summary': '题型族 %s（代码 %s）按实例规格生成，独立检查器 %s 用不同方法从题干与附件重算后核验；出题全程未调用模型。'
                       % (question['family'], ', '.join(row.get('code') or []) or '—',
                          row.get('independent_checker') or '—'),
            'family': question['family'],
            'family_version': teacher.get('family_version'),
            'family_instance': teacher['id'],
            'run': question.get('familyRun') or self.run,
            'generator_code': row.get('code') or [],
            'independent_checker': row.get('independent_checker'),
            'checker_method': checker.get('method'),
            'tests': row.get('tests') or [],
            'runbook_steps': RUNBOOK_STEPS,
            'model_calls': 0,
            'answer_method': row.get('answer_method'),
            'distractor_mechanisms': row.get('distractor_mechanisms') or [],
        }

    def originality(self, question, teacher, card):
        group = asset_group(list((teacher.get('input_hashes') or {}).keys()))
        record = Path(ROOT / group / 'sources.json') if group else None
        return {
            'coordinates': coordinates_kind(question, card),
            'statement': question.get('attribution'),
            'license': teacher.get('license') or question.get('attributionLicenseUrl'),
            'citation': question.get('source'),
            'links': source_links(question.get('source')),
            'asset_record': str(record.relative_to(ROOT)).replace('\\', '/') if record and record.exists() else None,
            'card': (teacher.get('checks') or {}).get('card'),
            'card_prose': '卡片上的题干、候选描述与结论措辞由本项目（AI 助手参与）撰写，未经人工审核；原文位置见 instruction.md。' if card else None,
        }

    def locator(self, teacher, card):
        checks = teacher.get('checks') or {}
        out = {'asset_files': sorted((teacher.get('input_hashes') or {}).keys())}
        if card and card.get('kind') == 'design_pointer_card':
            out['paper'] = card.get('citation')
            out['properties'] = {k: v.get('locator') for k, v in (card.get('properties') or {}).items()}
            out['paper_choice'] = checks.get('paper_choice')
            out['paper_choice_locator'] = card.get('paper_choice_locator')
            out['per_candidate'] = checks.get('locators')
            out['measured'] = checks.get('measured')
        elif card:
            out['paper'] = card.get('citation') or card.get('paper')
            out['facts'] = checks.get('facts')
            out['paper_conclusion_locator'] = checks.get('paper_conclusion_locator')
        else:
            out['scope'] = (self.student.get(teacher['id']) or {}).get('scope')
            # Keep the dicts and lists: 'lines' (2theta per X-ray line) and 'candidates' are the
            # intermediate values a reviewer follows.
            out['recomputed'] = {k: v for k, v in checks.items() if k != 'limits'}
        return out

    # ---------- the three files the whiteboard names ----------
    def attachments(self, question, teacher):
        """What the question hands out, as files under source/data/, joined with how the checker reads them."""
        packet = self.student.get(teacher['id']) or {}
        by_name = {i.get('name'): i for i in packet.get('inputs') or []}
        hashes = teacher.get('input_hashes') or {}
        out = []
        for item in question.get('attachments') or []:
            name = item['name']
            spec = by_name.get(name, {})
            out.append({'file': 'data/' + Path(item['url']).name,
                        'name': name,
                        'format': spec.get('format'),
                        'unit': spec.get('unit'),
                        'description': item.get('description'),
                        'asset': item['url'],
                        'sha256': hashes.get(item['url']) or spec.get('sha256')
                        or (sha256(DOCS / item['url']) if (DOCS / item['url']).exists() else None)})
        return out

    def asset_record(self, group):
        """docs/assets/<group>/sources.json: how every file in that group was built, and from what."""
        if group not in self.records:
            path = ROOT / group / 'sources.json' if group else None
            self.records[group] = json.loads(path.read_text(encoding='utf-8')) if path and path.exists() else {}
        return self.records[group]

    def data_origin(self, question, teacher, card, attachments):
        """Where the files in source/data/ come from -- and in particular whether we built them ourselves.

        Some of this bank's attachments are not measurements and not database entries: they are models
        this project constructed from numbers a paper reports (an ideal FCC lattice at the paper's edge
        length, a model Abrikosov lattice at the paper's field, a sphere cut out of ideal zinc blende).
        That is legitimate and it is what the question needs, but a reader who mistakes one for data is
        being misled by us, so the folder says it outright and gives the construction rule. The rule is
        not written here: it is read off the group's sources.json, which the builder wrote."""
        kind = coordinates_kind(question, card)
        group = asset_group(list((teacher.get('input_hashes') or {}).keys()))
        record = self.asset_record(group)
        files = record.get('files') or {}
        constructed = kind == 'generated_by_this_project' or record.get('route') == 'paper_parameter_model'
        papers = record.get('papers') or ({'paper': record['paper']} if record.get('paper') else {})
        out = {
            'kind': kind,
            'constructed_by_this_project': constructed,
            'what_it_is': CONSTRUCTED_WARNING if constructed else NOT_CONSTRUCTED.get(kind, '见 originality.statement'),
            'route': record.get('route'),
            'construction_rule': record.get('model') or record.get('note'),
            'parameters_from': [{'citation': p.get('citation'), 'url': p.get('url') or p.get('doi'),
                                 'where_in_the_paper': p.get('locators') or p.get('table') or p.get('numbers')}
                                for p in papers.values()],
            'per_file': {a['name']: files.get(a['name']) for a in attachments if files.get(a['name'])},
            'record': (group + '/sources.json') if group and record else None,
        }
        return out

    def extra_source_files(self, source, paper):
        """Files another tool put in source/ -- review_system/stock.py leaves the paper itself there,
        plus its check sheet and the readable copy. They belong in the folder's own file list, so a
        reviewer is told what the PDF next to instruction.md is. A fresh tree has none of them until
        stock.py has run, which is why the RUNBOOK runs this exporter again afterwards."""
        ours = {'SOURCE.txt', 'instruction.md', 'recompute.py', 'recompute.out.txt', paper}
        roles = {'.pdf': '论文全文（本地副本，不得再分发）', '.xml': '论文全文（本地副本，不得再分发）',
                 'SOURCE_CHECK.txt': '逐条事实回原文核对的结果（review_system/sources.py 写）',
                 '论文核对.html': '可读版：事实 + 它在原文第几页 + 高亮原文（review_system/stock.py 写）'}
        out = []
        for path in sorted(source.glob('*')) if source.is_dir() else []:
            if path.is_dir() or path.name in ours:
                continue
            out.append((path.name, roles.get(path.name) or roles.get(path.suffix.lower()) or '另一个工具放进来的文件'))
        return out

    def qa_json(self, question, teacher, attachments):
        """The question and its answer, in one file -- the whiteboard's QA.json, with no QA/ folder."""
        packet = self.student.get(teacher['id']) or {}
        return {
            'id': question['id'],
            'title': question.get('title'),
            'family': question['family'],
            'family_instance': teacher['id'],
            'form': (self.cards.get(question['id']) or {}).get('format') or 'choice',
            'question': {
                'text': packet.get('question') or question.get('question'),
                'scope': packet.get('scope'),
                'instructions': question.get('inputInstructions'),
                'attachments': attachments,
                'options': packet.get('options') or [],
                'response_format': packet.get('response_format'),
            },
            'input_hashes': teacher.get('input_hashes') or {},
            'answer': {
                'label': teacher.get('correct_label'),
                'numeric': teacher.get('numeric_answer'),
                'text': question.get('answer'),
            },
            'note': '这个文件连答案一起放，是因为整个文件夹只用于质量核查，不发给被测模型；'
                    '被测模型拿到的那一份由 evaluation/exam.py 另外生成。',
        }

    def instruction_text(self, question, teacher, card, row, attachments, has_py, extra=(), origin=None):
        """How to get from the files in source/ to QA.json. The required piece of the whiteboard.

        It replaces four files that used to be read side by side (reviewer/EVIDENCE.txt, locators.json,
        limits.txt and the how_to_extract block of info.json): whoever checked a question had to join
        them by hand, which is why nobody could check a thousand. Here it is in doing order -- what is
        in the folder, what the question asks, where the data comes from, how the answer is computed,
        what it should come out as, and what none of it covers."""
        qid, packet = question['id'], (self.student.get(teacher['id']) or {})
        checks = {k: v for k, v in (teacher.get('checks') or {}).items() if k != 'limits'}
        check = self.checks.get(teacher['id'], {})
        where = self.locator(teacher, card)
        paper = None
        if card and card.get('paper_xml'):
            paper = Path(card['paper_xml']['path']).name

        out = ['# %s · 怎么从这些文件重做出这道题' % qid,
               '',
               '%s' % (question.get('title') or ''),
               '',
               '> 这个文件夹**不是**发给被测模型的那一份，它只用来核查这道题的质量，所以答案、选项评注和',
               '> 检查器算出来的量都摊开放在里面。',
               '']
        if (origin or {}).get('constructed_by_this_project'):
            out += ['> ⚠ **`data/` 里的结构是本项目构造的，不是实测数据，也不是数据库里的条目。**',
                    '> 参数取自论文，结构按第 2 节「怎么构造的」那条规则生成。引用时不要当成实验数据。',
                    '']
        out += [
               '## 0 这个文件夹里有什么', '']
        files = [('../info.json', '元数据：文件清单、这道题怎么出的、许可与审核状态'),
                 ('../QA.json', '题目与答案'),
                 ('SOURCE.txt', '引文、链接、许可、附件哈希'),
                 ('instruction.md', '本文件')]
        files += [(a['file'], '附件：%s' % (a.get('description') or a.get('format') or '—')) for a in attachments]
        if paper:
            files.append((paper, '论文全文（本地副本，按许可不得再分发）'))
        files += list(extra)
        if has_py:
            files += [('recompute.py', '用独立检查器重算一遍答案；`python recompute.py`'),
                      ('recompute.out.txt', '上面那条命令在本机跑出来的输出')]
        out += ['| 文件 | 是什么 |', '|---|---|']
        out += ['| `%s` | %s |' % (name, role) for name, role in files]

        out += ['', '## 1 这道题问什么', '', indent(packet.get('question') or question.get('question') or '—', '')]
        if packet.get('options'):
            out += [''] + ['- %s. %s %s' % (o['label'], o['value'], o.get('unit') or '') for o in packet['options']]

        out += ['', '## 2 数据从哪来', '']
        out += ['- **`data/` 里是什么**：%s' % (origin or {}).get('what_it_is', '—'),
                '- 来源：%s' % (question.get('source') or '—'),
                '- 许可：%s' % (teacher.get('license') or question.get('attributionLicenseUrl') or '—')]
        if (origin or {}).get('constructed_by_this_project'):
            out += ['', '### 怎么构造的', '',
                    '- 规则：%s' % (origin.get('construction_rule') or '—')]
            for cite in origin.get('parameters_from') or []:     # not `paper`: that is the file name
                out.append('- 参数取自：%s' % (cite.get('citation') or '—'))
                if cite.get('url'):
                    out.append('    - %s' % cite['url'])
                if cite.get('where_in_the_paper'):
                    out.append('    - 在论文哪一处：%s' % show(cite['where_in_the_paper']))
            for name, spec in (origin.get('per_file') or {}).items():
                out.append('- `%s` 的参数：%s' % (name, show(spec)))
            if origin.get('record'):
                out.append('- 构造记录：`%s`（仓库里）' % origin['record'])
        for key, label in (('paper', '论文'), ('paper_choice_locator', '论文里选型那句的位置'),
                           ('properties', '每个物性在原文的位置'), ('per_candidate', '每个候选在原文的位置'),
                           ('facts', '每条事实在原文的位置'), ('paper_conclusion_locator', '结论在原文的位置'),
                           ('scope', '范围')):
            if where.get(key):
                out.append('- %s：%s' % (label, show(where[key])))
        if paper:
            out.append('- 论文全文就在本目录：`%s`（原文位置的逐条核对见同目录的 `SOURCE_CHECK.txt` 与 `论文核对.html`，由 review_system/stock.py 放入）' % paper)
        for item in packet.get('inputs') or []:
            out += ['', '附件 `%s`（%s；%s）前几行：' % (item.get('name'), item.get('format'), item.get('unit') or '—'),
                    '', '```', quote(item.get('text'), head=12, tail=3).replace('      ', ''), '```']

        out += ['', '## 3 怎么算出答案', '']
        out += ['- 方法：%s' % (row.get('answer_method') or '—'),
                '- 题型族：%s %s（生成代码 %s）' % (question['family'], teacher.get('family_version') or '',
                                             ', '.join(row.get('code') or []) or '—')]
        if has_py:
            out += ['', '**可以直接跑**：', '', '```', 'cd %s/source && python recompute.py' % qid, '```', '',
                    '它读 `../QA.json` 与 `data/`，调用独立检查器 `%s` 重算，退出码 0 表示重算结果与 QA.json 的答案一致。'
                    % (row.get('independent_checker') or '—'),
                    '本机跑出来的输出存在 `recompute.out.txt`。']
        else:
            out += ['', '这道题没有可跑的脚本：它的答案是从论文里读出来的，不是算出来的。',
                    '请照第 2 节的原文位置自己核对。']
        out += ['', '程序算出来的中间量：', '']
        out += ['- `%s` = %s' % (k, show(v)) for k, v in checks.items()] or ['- —']

        answer = question.get('answer') or teacher.get('correct_label') or '—'
        out += ['', '## 4 答案应该是', '', '**%s**' % answer]
        if teacher.get('numeric_answer'):
            out.append('')
            out.append('数值形式：%s' % show(teacher['numeric_answer']))

        out += ['', '## 5 四个选项为什么对或错', '']
        for option in teacher.get('option_audit') or []:
            out.append('- **%s** %s  [%s]%s' % (option['label'], option['value'], option.get('rule') or '—',
                                                ' ← 正确' if option.get('is_correct') else ''))
            if option.get('reason'):
                out.append('    - %s' % option['reason'])
        if not (teacher.get('option_audit') or []):
            out.append('- —')

        out += ['', '## 6 另一套代码复核的结果', '',
                '- 方法：%s' % (check.get('method') or '—'),
                '- 结论：%s%s' % (check.get('status') or '—',
                                '（%s）' % check['problem'] if check.get('problem') else '')]
        if check.get('parameters'):
            out.append('- 它自己算出来的：%s' % show(check['parameters']))

        out += ['', '## 7 这题保证不了什么', '',
                indent(row.get('limits') or (teacher.get('checks') or {}).get('limits') or '—', ''),
                '',
                '本题未经任何人工审核（L1–L4 全部 pending）。程序只核验指定量，不保证科学意义与难度。',
                '',
                '---', '',
                '本文件由 tools/export_qa_folders.py 生成，运行 %s，%s。'
                % (question.get('familyRun') or self.run, date.today().isoformat())]
        return NEWLINE.join(out) + NEWLINE

    def source_text(self, question, teacher, card, copied):
        lines = ['%s 的来源' % question['id'], '',
                 '引文：%s' % (question.get('source') or '—'), '']
        links = source_links(question.get('source'))
        lines += ['链接：'] + ['  ' + u for u in links] if links else ['链接：无（引文中没有可解析的标识符）']
        lines += ['', '许可：%s' % (teacher.get('license') or question.get('attributionLicenseUrl') or '见归属说明'),
                  '归属与原创性：%s' % (question.get('attribution') or '—'), '']
        if card and card.get('paper_xml'):
            lines += ['论文全文：%s（SHA-256 %s）%s'
                      % (Path(card['paper_xml']['path']).name, card['paper_xml']['sha256'],
                         '，已复制到本目录' if copied else '，未复制（本机没有这个文件）')]
        lines += ['', '附件哈希：'] + ['  %s  %s' % (h, p) for p, h in sorted((teacher.get('input_hashes') or {}).items())]
        lines += ['', '本文件由 tools/export_qa_folders.py 生成，运行 %s。' % (question.get('familyRun') or self.run)]
        return NEWLINE.join(lines) + NEWLINE

    def info_json(self, question, teacher, card, row, files, origin):
        qid = question['id']
        return {
            'id': qid,
            'title': question.get('title'),
            'generated': date.today().isoformat(),
            'generated_by': 'tools/export_qa_folders.py',
            'run': question.get('familyRun') or self.run,
            'what_this_folder_is': '这道题的质量核查副本：源文件、怎么从源文件得到这道题（instruction.md）、'
                                   '题目与答案（QA.json）。不是发给被测模型的那一份。',
            'files': files,
            'data_origin': origin,
            'classification': {'ability': question.get('ability'), 'domain': question.get('domain'),
                               'scale': question.get('scale'), 'reasoning': question.get('reasoning'),
                               'subdomain': (self.cards.get(qid) or {}).get('subdomain'),
                               'format': (self.cards.get(qid) or {}).get('format')},
            'how_to_extract': self.how_to_extract(question, teacher, row),
            'originality': self.originality(question, teacher, card),
            'locator': self.locator(teacher, card),
            'evidence': {
                'asset_hashes': teacher.get('input_hashes') or {},
                'independent_check': {k: v for k, v in (self.checks.get(teacher['id']) or {}).items()
                                      if k in ('status', 'method', 'problem')},
                'option_order_rule': teacher.get('option_order'),
                'option_audit': teacher.get('option_audit'),
                'excluded_candidates': teacher.get('excluded_candidates'),
                'rank': teacher.get('rank'),
                'rank_shortcuts': teacher.get('rank_shortcuts'),
            },
            'review': {'human_review': teacher.get('human_review') or 'pending', 'L1': 'pending', 'L2': 'pending',
                       'L3': 'pending', 'L4': 'pending',
                       'note': '本题未经任何人工审核；程序核验与独立检查器只保证指定量，不保证领域正确性与难度。'},
            'site': {'question_pool': SITE + 'index.html?qa=%s#questions' % qid,
                     'workbench': SITE + (question.get('traceUrl') or '')},
        }

    def question(self, question):
        qid = question['id']
        teacher = self.teacher[question['familyInstance']]
        row = self.registry.get(question['family'], {})
        card = self.card_of(teacher)
        folder = self.out / qid
        source = folder / 'source'
        self.tidy(folder)

        attachments = self.attachments(question, teacher)
        for item in question.get('attachments') or []:
            self.copy(DOCS / item['url'], source / 'data' / Path(item['url']).name)
            # The checker hashes the asset at its repository path, so the toolkit needs it under the
            # same name. Copied here rather than at the end: recompute.py runs before that.
            self.copy(DOCS / item['url'], self.out / TOOLKIT / 'docs' / item['url'])
            self.assets.add(item['url'])
        for rel in teacher.get('input_hashes') or {}:          # what the checker hashes, often another file
            if rel not in self.assets:
                self.copy(DOCS / rel, self.out / TOOLKIT / 'docs' / rel)
                self.assets.add(rel)
        paper = None
        copied = False
        if card and card.get('paper_xml'):
            paper = Path(card['paper_xml']['path']).name
            if self.papers:
                copied = self.copy(ROOT / card['paper_xml']['path'], source / paper)

        has_py = question['family'] in self.checkers and bool(attachments)
        extra = self.extra_source_files(source, paper)
        origin = self.data_origin(question, teacher, card, attachments)
        files = [{'path': 'info.json', 'role': '元数据与文件清单（本文件）'},
                 {'path': 'QA.json', 'role': '题目与答案'},
                 {'path': 'source/SOURCE.txt', 'role': '引文、链接、许可、附件哈希'},
                 {'path': 'source/instruction.md', 'role': '怎么从 source/ 里的文件得到 QA.json'}]
        files += [{'path': 'source/' + a['file'], 'role': '附件：' + (a.get('description') or a.get('format') or '')}
                  for a in attachments]
        if paper and copied:
            files.append({'path': 'source/' + paper, 'role': '论文全文（本地副本，不得再分发）'})
        files += [{'path': 'source/' + name, 'role': role} for name, role in extra]
        if has_py:
            files.append({'path': 'source/recompute.py', 'role': '用独立检查器重算答案，可执行'})
            # Listed whenever it is there: a re-export with --no-recompute must not drop a file that
            # an earlier run left in the folder.
            if self.recompute or (source / 'recompute.out.txt').exists():
                files.append({'path': 'source/recompute.out.txt', 'role': 'recompute.py 在本机的输出'})

        self.put_json(folder / 'info.json', self.info_json(question, teacher, card, row, files, origin))
        self.put_json(folder / 'QA.json', self.qa_json(question, teacher, attachments))
        self.put(source / 'SOURCE.txt', self.source_text(question, teacher, card, copied))
        self.put(source / 'instruction.md',
                 self.instruction_text(question, teacher, card, row, attachments, has_py, extra, origin))
        if has_py:
            self.put(source / 'recompute.py', RECOMPUTE % dict(
                id=qid, family=question['family'], toolkit_name=TOOLKIT,
                toolkit='`%s/`（题库根目录）' % TOOLKIT,
                checker=row.get('independent_checker') or '—'))
            if self.recompute:
                self.run_recompute(qid, source)
        return files

    # ---------- the toolkit, written once for the whole tree ----------
    def write_toolkit_code(self):
        """checkers/, so recompute.py runs without this repository. Written before the questions,
        because each question's recompute.py is run as soon as it is written."""
        for path in sorted((ROOT / 'checkers').glob('*.py')):
            self.copy(path, self.out / TOOLKIT / 'checkers' / path.name)

    def write_toolkit_readme(self):
        self.put(self.out / TOOLKIT / 'README.md', TOOLKIT_README % dict(assets=len(self.assets),
                                                                         version=self.checker_version,
                                                                         date=date.today().isoformat()))

    def run_recompute(self, qid, source):
        """Run the script and keep what it printed. A folder claiming to be reproducible is worth
        nothing until someone has actually run it, and that someone should be us, not the reviewer."""
        try:
            done = subprocess.run([sys.executable, 'recompute.py'], cwd=str(source), capture_output=True,
                                  text=True, encoding='utf-8', errors='replace', timeout=300)
            output = (done.stdout or '') + (done.stderr or '')
            ok = done.returncode == 0
        except Exception as error:                      # a hung or unlaunchable script is a failure too
            output, ok = '%s: %s' % (type(error).__name__, error), False
        (self.reproduced if ok else self.failed).append(qid)
        self.put(source / 'recompute.out.txt',
                 '$ python recompute.py        （%s，%s）%s%s'
                 % (date.today().isoformat(), '重算与 QA.json 一致' if ok else '**没对上，要人看**',
                    NEWLINE * 2, output.rstrip() + NEWLINE))

    def find_orphans(self, exported):
        """Folders of questions this export did not write: ids the catalogue no longer has.

        They keep whatever layout the run that made them used, so they quietly become the stale half of
        the tree. Reported rather than deleted: whether a withdrawn question's folder should be kept is
        the user's call, not this script's."""
        out = []
        for folder in sorted(self.out.iterdir()) if self.out.is_dir() else []:
            if folder.is_dir() and folder.name != TOOLKIT and (folder / 'info.json').exists()                     and folder.name not in exported:
                out.append(folder.name)
        return out

    def run_all(self, ids=None):
        questions = [q for q in self.catalog['questions']
                     if q.get('lifecycle') == 'active' and q.get('familyInstance') in self.teacher]
        if ids:
            questions = [q for q in questions if q['id'] in ids]
        self.write_toolkit_code()
        index = []
        for question in questions:
            self.question(question)
            index.append(question)
        self.write_toolkit_readme()
        self.orphans = self.find_orphans({q['id'] for q in index}) if not ids else []
        self.put_json(self.out / 'index.json', {
            'kind': 'qa_folders_index', 'generated': date.today().isoformat(), 'run': self.run,
            'layout': ['info.json', 'QA.json', 'source/SOURCE.txt', 'source/instruction.md',
                       'source/data/', 'source/recompute.py'],
            'toolkit': TOOLKIT,
            'questions': [{'id': q['id'], 'folder': q['id'], 'family': q['family'],
                           'ability': q.get('ability'), 'domain': q.get('domain')} for q in index],
            'recompute': {'ran': len(self.reproduced) + len(self.failed),
                          'reproduced': len(self.reproduced), 'failed': sorted(self.failed)},
            'note': '每题一个文件夹，内容是质量核查用的；被测模型拿到的那一份不在这里。'
                    '全部未经人工审核。由 tools/export_qa_folders.py 生成，可随时重建。'})
        return index


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(DEFAULT_OUT), help='where the folders go (local, never in git)')
    ap.add_argument('--ids', help='comma-separated question ids; default is every admitted question')
    ap.add_argument('--no-papers', dest='papers', action='store_false', help='do not copy paper full texts')
    ap.add_argument('--no-recompute', dest='recompute', action='store_false',
                    help="do not run each question's recompute.py")
    ap.add_argument('--dry-run', action='store_true', help='report what would change, write nothing')
    args = ap.parse_args(argv)
    export = Export(args.out, papers=args.papers, dry_run=args.dry_run, recompute=args.recompute)
    index = export.run_all(set(args.ids.split(',')) if args.ids else None)
    print('questions %d -> %s%s' % (len(index), args.out, ' (dry run)' if args.dry_run else ''))
    print('files written %d, unchanged %d, stale folders removed %d'
          % (export.written, export.unchanged, export.removed))
    if export.reproduced or export.failed:
        print('recompute.py 跑了 %d 道：重算一致 %d，没对上 %d'
              % (len(export.reproduced) + len(export.failed), len(export.reproduced), len(export.failed)))
        for qid in sorted(export.failed)[:20]:
            print('  没对上 ' + qid)
    if export.orphans:
        print('%d 个文件夹不在本次导出里（题目已不在目录中），仍是旧版式，要删要留你定：' % len(export.orphans))
        print('  ' + ', '.join(export.orphans))
    if export.missing:
        print('MISSING %d source files:' % len(export.missing))
        for path in sorted(set(export.missing))[:20]:
            print('  ' + path)
    return 1 if export.missing or export.failed else 0


if __name__ == '__main__':
    sys.exit(main())
