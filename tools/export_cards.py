"""Flash-card data for docs/cards.html (Quizlet-style page asked for at the sixth advisor meeting).

  python tools/export_cards.py      # -> docs/data/cards.json

One card per active catalog question:
- task-family instances: the published student packet (question, options) plus the reviewer-side option audit (correct
  label and why each wrong option is wrong) from docs/data/family-workbench.json;
- legacy questions with a checked four-choice version (familyVersions): that version's packet;
- other legacy questions: the catalog text and reference answer, marked as not four-choice (the meeting asked for a
  list of such format problems).
Attachments point to the published asset files; small inputs that exist only inside the run packet are inlined.
Nothing here is new content: every field is copied from data the site already publishes.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import subdomain_map  # noqa: E402

OUT = 'docs/data/cards.json'
INLINE_LIMIT = 40000          # characters; larger run-only inputs are linked through the workbench instead


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def packet_card(sp, t, attachments):
    by_name = {a['name']: a for a in attachments}
    files = []
    for item in sp['inputs']:
        a = by_name.get(item['name'])
        if a:
            files.append(dict(name=item['name'], url=a['url'], note=a.get('description', '')))
        elif len(item['text']) <= INLINE_LIMIT:
            files.append(dict(name=item['name'], text=item['text'], note='%s；%s' % (item['format'], item['unit'])))
        else:
            files.append(dict(name=item['name'], note='文件较大，请在题型工作台查看'))
    reasons = {a['label']: dict(reason=a.get('reason', ''), rule=a.get('rule', ''), correct=a['is_correct']) for a in t['option_audit']}
    return dict(format='choice', question=sp['question'], options=sp['options'], correct=t['correct_label'],
                numeric=t.get('numeric_answer'), reasons=reasons, files=files)


def build():
    catalog = [q for q in read('docs/data/catalog.json')['questions'] if q['lifecycle'] == 'active']
    wb = read('docs/data/family-workbench.json')
    packets = {p['id']: p for p in wb['student_packets']}
    keys = {t['id']: t for t in wb['teacher_answers']}
    tax = read(subdomain_map.TAXONOMY)
    tree = subdomain_map.Tree(tax)
    names = {}                                     # level-1 ids, then their leaves, in tree order
    for d in tax['domains']:
        for one in d['l1']:
            names[one['id']] = one['name']
            names.update({leaf['id']: '%s · %s' % (one['name'], leaf['name']) for leaf in one['leaves']})
    cards = []
    for q in catalog:
        inst = q.get('familyInstance') or next((v['instance'] for v in q.get('familyVersions', []) if v['instance'] in packets), None)
        base = dict(id=q['id'], title=q['title'], ability=q['ability'], domain=q['domain'],
                    scale=subdomain_map.scale_of(q['reasoningSizeNm']), subdomain=tree.question(q),
                    family=q.get('family', ''), source=q.get('source', ''), attribution=q.get('attribution', ''),
                    objective=q.get('learningObjective', ''), size=q.get('sizeDefinition', ''),
                    trace=q.get('traceUrl', ''), legacy=not q.get('familyInstance'))
        if inst:
            card = packet_card(packets[inst], keys[inst], q.get('attachments', []))
            card['version'] = inst if q.get('familyInstance') else '旧题的四选一版本 ' + inst
        else:
            card = dict(format='open', question=q['question'], options=[], correct=None, numeric=None, reasons={},
                        answer=q.get('answer', ''), rubric=q.get('rubric', ''),
                        files=[dict(name=a['name'], url=a['url'], note=a.get('description', '')) for a in q.get('attachments', [])],
                        version='旧模板题（尚无四选一版本）')
        base['l1'] = tree.leaf[base['subdomain']]['l1']
        cards.append(dict(base, **card))
    order = {'quantum': 0, 'chemistry': 1, 'materials': 2, 'biology': 3}
    cards.sort(key=lambda c: (order[c['domain']], subdomain_map.SCALES.index(c['scale']), c['id']))
    return dict(kind='flash_cards', count=len(cards), choice=sum(c['format'] == 'choice' for c in cards),
                open=sum(c['format'] == 'open' for c in cards), subdomains=names, taxonomy_status=tax['status'],
                note='Copied from the catalogue and the published family workbench; all questions pending human review.',
                cards=cards)


if __name__ == '__main__':
    data = build()
    (ROOT / OUT).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    print(data['count'], 'cards;', data['choice'], 'four-choice;', data['open'], 'not four-choice;',
          (ROOT / OUT).stat().st_size // 1024, 'KB')
