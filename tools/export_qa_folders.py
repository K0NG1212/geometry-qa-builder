"""W1: one folder per question, so a reviewer can trace a question to its source without reading this repository.

  python tools/export_qa_folders.py                       # all admitted questions -> D:/GeoBench-data/qa
  python tools/export_qa_folders.py --ids CND022,BND024   # just these
  python tools/export_qa_folders.py --out E:/somewhere --no-papers --dry-run

The folders are local, never in git: they hold copies of paper full texts and of every attachment, which is tens
of megabytes and duplicates what runs/ and docs/assets/ already carry. The repository keeps only this generator,
so the folders can be rebuilt at any time. Asked for at the 2026-10-28 meeting: "每一个题目就是你做一个 folder",
with info.json saying how the question was extracted, what is original, where in the source it comes from, and
what the evidence is -- the advisor's point being that a question whose source cannot be traced cannot be reviewed.

  <out>/<id>/info.json          the four fields above, plus what is still unreviewed
  <out>/<id>/source/            SOURCE.txt (citation, links, license, hashes) and the paper full text when we have it
  <out>/<id>/student/           question.txt and the attachments, exactly what a model or a student is given
  <out>/<id>/reviewer/          answer.json, locators.json, limits.txt -- never shown to the model

Writing is idempotent: a file is only touched when its content changes, so a re-run shows what actually moved.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
DEFAULT_OUT = Path('D:/GeoBench-data/qa')
NEWLINE = chr(10)
SITE = 'https://k0ng1212.github.io/geometry-qa-builder/'
RUNBOOK_STEPS = ['3 题型族', '4 独立检查器', '5 注册表与规格', '6 生成', '7 独立复核', '8 导出', '9 入库', '10 挑选与审核材料']
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
    def __init__(self, out, papers=True, dry_run=False):
        self.out, self.papers, self.dry_run = Path(out), papers, dry_run
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
        self.written = self.unchanged = 0
        self.missing = []

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
            'card_prose': '卡片上的题干、候选描述与结论措辞由本项目（AI 助手参与）撰写，未经人工审核；原文位置见 locator。' if card else None,
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
            # intermediate values a reviewer follows, and dropping them left locators.json saying less
            # than reviewer/answer.json already does.
            out['recomputed'] = {k: v for k, v in checks.items() if k != 'limits'}
        return out

    def public_locator(self, teacher, card):
        """The locator as info.json may carry it. The measured values, the recomputed quantities and the answer
        position are the answer, so they stay in reviewer/ -- info.json sits where a folder handed to a model
        would be read."""
        out = {k: v for k, v in self.locator(teacher, card).items() if k not in ('measured', 'recomputed')}
        out['values_in'] = 'reviewer/locators.json'
        return out

    def evidence_block(self, teacher, card):
        check = self.checks.get(teacher['id'], {})
        block = {
            'asset_hashes': teacher.get('input_hashes') or {},
            'independent_check': {'status': check.get('status'), 'method': check.get('method'),
                                  'problem': check.get('problem')},
            'option_order_rule': teacher.get('option_order'),       # the rule, not which option is right
            'answer_in': 'reviewer/answer.json',
            'readable_sheet': 'reviewer/EVIDENCE.txt',              # answer, attachment and derivation in one file
        }
        if card and card.get('paper_xml'):
            block['paper_full_text'] = {'file': Path(card['paper_xml']['path']).name,
                                        'sha256': card['paper_xml']['sha256']}
        return block

    def student_text(self, question, teacher):
        packet = self.student.get(teacher['id']) or {}
        lines = ['%s · %s' % (question['id'], question.get('title') or ''), '',
                 packet.get('question') or question.get('question') or '', '']
        instructions = question.get('inputInstructions') or ''
        if packet.get('scope') and packet['scope'] not in instructions:
            lines += ['范围：' + packet['scope'], '']
        if instructions:
            lines += [instructions, '']
        for option in packet.get('options') or []:
            lines.append(('%s. %s %s' % (option['label'], option['value'], option.get('unit') or '')).rstrip())
        lines += ['', '附件在本文件夹内，与考生看到的一致。答案、选项核验与原文位置在 ../reviewer/，不要给模型。']
        return '\n'.join(lines).rstrip() + '\n'

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
        return '\n'.join(lines) + '\n'

    # ---------- the readable evidence sheet ----------
    def evidence_text(self, question, teacher, card, row):
        """One file an auditor -- a person, or another model -- can read start to finish.

        Every piece of this was already in the folder, but spread over four files: the attachment in student/,
        the derivation in reviewer/answer.json, the source in source/SOURCE.txt, the scope in locators.json.
        Whoever checked a question had to join them by hand, which is why nobody could check a thousand of
        them. Here they are in reading order: the answer, the attachment lines it rests on, the quantities the
        generator computed, why the other three options fail, what the second checker did, and what none of it
        covers.
        """
        qid, packet = question['id'], (self.student.get(teacher['id']) or {})
        checks = {k: v for k, v in (teacher.get('checks') or {}).items() if k != 'limits'}
        check = self.checks.get(teacher['id'], {})
        out = ['%s · %s' % (qid, question.get('title') or ''),
               '答案：%s' % (question.get('answer') or teacher.get('correct_label') or '—'), '',
               '一、题目（考生看到的全部）',
               indent(packet.get('question') or question.get('question') or '—')]
        if packet.get('options'):
            out += ['  选项：'] + ['    %s. %s %s' % (o['label'], o['value'], o.get('unit') or '')
                                 for o in packet['options']]
        out += ['', '二、证据：附件原样引用']
        for item in packet.get('inputs') or []:
            out += ['  %s（%s；%s）' % (item.get('name'), item.get('format'), item.get('unit') or '—'),
                    quote(item.get('text'))]
        for path, digest in sorted((teacher.get('input_hashes') or {}).items()):
            out.append('  上游文件 %s  sha256 %s' % (path, digest))
        out += ['  来源：%s' % (question.get('source') or '—'),
                '  许可：%s' % (teacher.get('license') or question.get('attributionLicenseUrl') or '—')]
        where = self.locator(teacher, card)
        for key in ('paper', 'paper_choice_locator', 'properties', 'per_candidate', 'facts',
                    'paper_conclusion_locator', 'scope'):
            if where.get(key):
                out.append('  原文位置 · %s：%s' % (key, show(where[key])))
        out += ['', '三、推导（程序算出来的量，不是转述）']
        out += ['  %s = %s' % (k, show(v)) for k, v in checks.items()] or ['  —']
        out += ['', '四、四个选项为什么对或错']
        for option in teacher.get('option_audit') or []:
            out.append('  %s %s  [%s]%s' % (option['label'], option['value'], option.get('rule') or '—',
                                            '  ← 正确' if option.get('is_correct') else ''))
            if option.get('reason'):
                out.append('      %s' % option['reason'])
        out += ['', '五、独立检查器（另一套代码重算）',
                '  方法：%s' % (check.get('method') or '—'),
                '  结论：%s%s' % (check.get('status') or '—',
                                '（%s）' % check['problem'] if check.get('problem') else '')]
        if check.get('parameters'):
            out.append('  它自己算出来的：%s' % show(check['parameters']))
        out += ['', '六、这题保证不了什么',
                indent(row.get('limits') or (teacher.get('checks') or {}).get('limits') or '—'),
                '  本题未经任何人工审核（L1–L4 全部 pending）。程序只核验指定量，不保证科学意义与难度。', '',
                '本文件由 tools/export_qa_folders.py 生成，运行 %s，%s。'
                % (question.get('familyRun') or self.run, date.today().isoformat())]
        return NEWLINE.join(out) + NEWLINE

    def question(self, question):
        qid = question['id']
        teacher = self.teacher[question['familyInstance']]
        row = self.registry.get(question['family'], {})
        card = self.card_of(teacher)
        folder = self.out / qid
        info = {
            'id': qid,
            'title': question.get('title'),
            'generated': date.today().isoformat(),
            'generated_by': 'tools/export_qa_folders.py',
            'run': question.get('familyRun') or self.run,
            'classification': {'ability': question.get('ability'), 'domain': question.get('domain'),
                               'scale': question.get('scale'), 'reasoning': question.get('reasoning'),
                               'subdomain': (self.cards.get(qid) or {}).get('subdomain'),
                               'format': (self.cards.get(qid) or {}).get('format')},
            'how_to_extract': self.how_to_extract(question, teacher, row),
            'originality': self.originality(question, teacher, card),
            'locator': self.public_locator(teacher, card),
            'evidence': self.evidence_block(teacher, card),
            'review': {'human_review': teacher.get('human_review') or 'pending', 'L1': 'pending', 'L2': 'pending',
                       'L3': 'pending', 'L4': 'pending',
                       'note': '本题未经任何人工审核；程序核验与独立检查器只保证指定量，不保证领域正确性与难度。'},
            'site': {'question_pool': SITE + 'index.html?qa=%s#questions' % qid,
                     'workbench': SITE + (question.get('traceUrl') or '')},
        }
        copied = False
        if card and card.get('paper_xml') and self.papers:
            copied = self.copy(ROOT / card['paper_xml']['path'], folder / 'source' / Path(card['paper_xml']['path']).name)
        self.put_json(folder / 'info.json', info)
        self.put(folder / 'source' / 'SOURCE.txt', self.source_text(question, teacher, card, copied))
        self.put(folder / 'student' / 'question.txt', self.student_text(question, teacher))
        for attachment in question.get('attachments') or []:
            self.copy(DOCS / attachment['url'], folder / 'student' / Path(attachment['url']).name)
        self.put_json(folder / 'reviewer' / 'answer.json', {
            'id': qid, 'correct_label': teacher.get('correct_label'), 'numeric_answer': teacher.get('numeric_answer'),
            'answer_text': question.get('answer'), 'option_audit': teacher.get('option_audit'),
            'excluded_candidates': teacher.get('excluded_candidates'), 'checks': teacher.get('checks'),
            'rank': teacher.get('rank'), 'rank_shortcuts': teacher.get('rank_shortcuts'),
            'independent_check': self.checks.get(teacher['id'])})
        self.put_json(folder / 'reviewer' / 'locators.json', self.locator(teacher, card))
        self.put(folder / 'reviewer' / 'EVIDENCE.txt', self.evidence_text(question, teacher, card, row))
        self.put(folder / 'reviewer' / 'limits.txt', '\n\n'.join(
            ['%s · 题型族 %s（%s）' % (qid, question['family'], row.get('name') or '—'),
             '考点：%s' % (row.get('concept') or '—'),
             '四选一校验：%s' % (row.get('four_choice_validation') or '—'),
             '限制（程序保证什么、保证不了什么）：%s' % (row.get('limits') or '—'),
             '本题的核验说明：%s' % (question.get('validation') or '—')]) + '\n')
        return info

    def run_all(self, ids=None):
        questions = [q for q in self.catalog['questions']
                     if q.get('lifecycle') == 'active' and q.get('familyInstance') in self.teacher]
        if ids:
            questions = [q for q in questions if q['id'] in ids]
        index = [self.question(q) for q in questions]
        self.put_json(self.out / 'index.json', {
            'kind': 'qa_folders_index', 'generated': date.today().isoformat(), 'run': self.run,
            'questions': [{'id': i['id'], 'folder': i['id'], 'family': i['how_to_extract']['family'],
                           'ability': i['classification']['ability'], 'domain': i['classification']['domain'],
                           'coordinates': i['originality']['coordinates']} for i in index],
            'note': '每题一个文件夹；全部未经人工审核。由 tools/export_qa_folders.py 生成，可随时重建。'})
        return index


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(DEFAULT_OUT), help='where the folders go (local, never in git)')
    ap.add_argument('--ids', help='comma-separated question ids; default is every admitted question')
    ap.add_argument('--no-papers', dest='papers', action='store_false', help='do not copy paper full texts')
    ap.add_argument('--dry-run', action='store_true', help='report what would change, write nothing')
    args = ap.parse_args(argv)
    export = Export(args.out, papers=args.papers, dry_run=args.dry_run)
    index = export.run_all(set(args.ids.split(',')) if args.ids else None)
    print('questions %d -> %s%s' % (len(index), args.out, ' (dry run)' if args.dry_run else ''))
    print('files written %d, unchanged %d' % (export.written, export.unchanged))
    kinds = {}
    for i in index:
        kinds[i['originality']['coordinates']] = kinds.get(i['originality']['coordinates'], 0) + 1
    for kind, n in sorted(kinds.items(), key=lambda x: -x[1]):
        print('  %4d %s' % (n, kind))
    if export.missing:
        print('MISSING %d source files:' % len(export.missing))
        for path in sorted(set(export.missing))[:20]:
            print('  ' + path)
    return 1 if export.missing else 0


if __name__ == '__main__':
    sys.exit(main())
