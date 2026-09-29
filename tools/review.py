"""Review tooling L1-L3 (roadmap A6). Builds queues and records; never calls a model and never approves by itself.

  python tools/review.py queue                                   # one-click queue -> docs/data/review-queue.json
  python tools/review.py record-l1 --unit named_bond_angle --reviewer "Name" --decision approved --notes "..."
  python tools/review.py record-l2 --unit named_bond_angle --reviewer "Name" --decision approved --notes "..." \
                                   [--model-review review.txt --model-id <model>]
  python tools/review.py l3-prompts --batch l3-001 [--out runs/review-l3-001]   # prompts for the sampled instances (local)
  python tools/review.py record-l3 --batch l3-001 --model-results model.jsonl [--human human.json] --date YYYY-MM-DD

L1/L2 records need a named human reviewer and are bound to the current code/registry hashes. L3 results must
cover the four fixed questions (templates/review-l3-questions.json) and are stored under reviews/L3/<batch>/.
Records are append-only: an existing file is never overwritten.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import review_system as rs  # noqa: E402

LARGE = 40000


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def context():
    from task_families import FAMILIES
    import checkers
    registry = read('templates/registry.json')
    catalog = read('docs/data/catalog.json')
    workbench = read('docs/data/family-workbench.json')
    units = rs.units(registry, FAMILIES, checkers.CHECKERS, catalog)
    return registry, catalog, workbench, units


def student_text(packet=None, record=None):
    if packet is None:
        return record.get('completeInput') or record.get('question', '')
    parts = [packet['question'], '', 'Options:'] + ['%s. %s %s' % (o['label'], o['value'], o.get('unit') or '') for o in packet['options']]
    parts += ['', 'Scope: ' + packet.get('scope', '')]
    for i in packet['inputs']:
        body = i.get('text')
        if body is None or len(body) > LARGE:
            body = '[large input published at docs/%s, sha256 %s; attach the file itself when prompting]' % (i.get('url'), i.get('sha256'))
        parts += ['', '===== %s (%s, %s) =====' % (i['name'], i['format'], i['unit']), body]
    return '\n'.join(parts)


def card(unit, registry, catalog, workbench):
    """L1 family card: what the template claims plus two samples (student view and reviewer view)."""
    row = next((t for t in registry['templates'] if t['id'] == unit['registry_id']), {}) or {}
    keys = ('name', 'concept', 'inputs', 'physical_conditions', 'reasoning_scale', 'scale_limits', 'source_basis', 'answer_method',
            'distractor_mechanisms', 'four_choice_validation', 'principle', 'validation', 'limits', 'template_review')
    info = {k: row.get(k) for k in keys if row.get(k) is not None}
    samples = []
    if unit['kind'] == 'family':
        teachers = {t['id']: t for t in workbench['teacher_answers'] if t['family'] == unit['unit']}
        students = {s['id']: s for s in workbench['student_packets'] if s['id'] in teachers}
        for iid in sorted(teachers)[:2]:
            s, t = students[iid], teachers[iid]
            samples.append(dict(instance=iid, question=s['question'], options=s['options'], inputs=[i['name'] for i in s['inputs']],
                                correct_label=t['correct_label'],
                                audit=[dict(label=o['label'], rule=o.get('rule') or o.get('source_id'), reason=o.get('reason')) for o in t['option_audit']]))
    else:
        recs = [q for q in catalog['questions'] if q.get('lifecycle') == 'active' and not q.get('familyInstance')
                and 'legacy:' + (q.get('family') or q['id']) == unit['unit']]
        for q in sorted(recs, key=lambda q: q['id'])[:2]:
            samples.append(dict(record=q['id'], question=q.get('question'), answer=q.get('answer'), validation=q.get('validation')))
    return dict(template=info, samples=samples)


def queue(date):
    registry, catalog, workbench, units = context()
    records = rs.load_records()
    questions = rs.load_questions()
    items = rs.instances(catalog)
    counts = {}
    for it in items:
        counts[it['unit']] = counts.get(it['unit'], 0) + 1
    unit_rows, states = [], {}
    for uid, u in sorted(units.items(), key=lambda kv: (kv[1]['kind'], kv[0])):
        b = rs.bindings(u, registry)
        l1, rec1 = rs.unit_state(uid, 'L1', b['L1'], records)
        l2, rec2 = rs.unit_state(uid, 'L2', b['L2'], records)
        states[uid] = (l1, l2)
        unit_rows.append(dict(u, bindings=b, L1=l1, L2=l2, instances=counts.get(uid, 0),
                              L1_record=rec1 and dict(reviewer=rec1['reviewer']['name'], date=rec1['date'], decision=rec1['decision']),
                              L2_record=rec2 and dict(reviewer=rec2['reviewer']['name'], date=rec2['date'], decision=rec2['decision']),
                              card=card(u, registry, catalog, workbench)))
    l3_final = {r['id']: r.get('final') for b in records['L3'] for r in b.get('results', [])}
    stages = {it['id']: rs.instance_stage(it, states, l3_final) for it in items}
    seed = 'l3-batch-%03d' % (len(records['L3']) + 1)
    plan = rs.plan_l3(items, records['L3'], seed)
    summary = dict(units=len(unit_rows), families=sum(u['kind'] == 'family' for u in unit_rows),
                   legacy_units=sum(u['kind'] == 'legacy' for u in unit_rows),
                   L1={s: sum(u['L1'] == s for u in unit_rows) for s in ('pending', 'approved', 'revise', 'stale')},
                   L2={s: sum(u['L2'] == s for u in unit_rows) for s in ('pending', 'approved', 'revise', 'stale')},
                   instances=len(items), stages={s: sum(v == s for v in stages.values()) for s in ('not-verified',) + rs.STAGES},
                   next_l3_batch=seed, l3_sample=sum(p['sample'] for p in plan), l3_strata=len(plan),
                   l3_steady_state_sample=sum(min(p['size'], max(2, -(-p['size'] // 10))) for p in plan),
                   model_calls=0, reviews_recorded=dict(L1=len(records['L1']), L2=len(records['L2']), L3=len(records['L3'])))
    payload = dict(kind='review_queue', date=date, summary=summary, questions={k: v for k, v in questions.items() if k != '_sha256'},
                   questions_sha256=questions['_sha256'], units=unit_rows, l3_plan=plan, stages=stages,
                   note='Tooling only: no L1/L2/L3 review has been run yet. Records are written by tools/review.py with a named human reviewer.')
    path = ROOT / 'docs/data/review-queue.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    return summary


def safe(name):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', name)


def record(level, unit_id, reviewer, decision, notes, date, model_review=None, model_id=None):
    registry, catalog, workbench, units = context()
    if unit_id not in units:
        raise SystemExit('Unknown review unit: ' + unit_id)
    if not reviewer or not reviewer.strip():
        raise SystemExit('A named human reviewer is required')
    rec = dict(level=level, unit=unit_id, decision=decision, notes=notes or '', date=date,
               reviewer=dict(kind='human', name=reviewer.strip()), bindings=rs.bindings(units[unit_id], registry)[level])
    if model_review:
        text = Path(model_review).read_bytes()
        rec['model_reviews'] = [dict(model=model_id, output_sha256=rs.sha(text), output=text.decode('utf-8'))]
    rs.validate_record(rec)
    folder = rs.REVIEWS / level
    folder.mkdir(parents=True, exist_ok=True)
    n = 1
    while (folder / ('%s-%s-%d.json' % (safe(unit_id), date, n))).exists():
        n += 1
    rec['seq'] = n
    path = folder / ('%s-%s-%d.json' % (safe(unit_id), date, n))
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    return path


def l3_prompts(batch, out):
    registry, catalog, workbench, units = context()
    records = rs.load_records()
    questions = rs.load_questions()
    items = rs.instances(catalog)
    plan = rs.plan_l3(items, records['L3'], batch)
    by_id = {q['id']: q for q in catalog['questions']}
    students = {s['id']: s for s in workbench['student_packets']}
    teachers = {t['id']: t for t in workbench['teacher_answers']}
    out = Path(out)
    if out.exists():
        raise SystemExit('Output exists; use a new directory')
    (out / 'prompts').mkdir(parents=True)
    manifest = []
    for p in plan:
        for cid in p['ids']:
            rec = by_id[cid]
            inst = rec.get('familyInstance')
            text = rs.l3_prompt(cid, student_text(students.get(inst), rec), rs.reviewer_packet(teachers.get(inst), rec), questions)
            (out / 'prompts' / ('%s.txt' % cid)).write_text(text, encoding='utf-8', newline='\n')
            manifest.append(dict(id=cid, unit=p['unit'], source=p['source'], stratum=p['stratum'], prompt_sha256=rs.sha(text)))
    (out / 'manifest.json').write_text(json.dumps(dict(batch=batch, questions_sha256=questions['_sha256'], plan=plan, prompts=manifest),
                                                  ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    return len(manifest)


def record_l3(batch, model_results, human, date):
    registry, catalog, workbench, units = context()
    questions = rs.load_questions()
    items = {it['id']: it for it in rs.instances(catalog)}
    results = [rs.validate_l3(json.loads(line), questions) for line in Path(model_results).read_text(encoding='utf-8').splitlines() if line.strip()]
    humans = json.loads(Path(human).read_text(encoding='utf-8')) if human else {}
    for iid, h in humans.items():
        if h.get('decision') not in ('pass', 'fail') or not (h.get('reviewer') or '').strip():
            raise SystemExit('Human verdicts need decision pass/fail and a named reviewer: ' + iid)
    tri = rs.triage(results, batch)
    rows = []
    for r in results:
        it = items[r['instance']]
        needs_human = r['instance'] in tri['flagged'] or r['instance'] in tri['calibration']
        h = humans.get(r['instance'])
        final = h['decision'] if h else ('pending' if needs_human else 'pass')
        rows.append(dict(id=r['instance'], unit=it['unit'], source=it['source'], cell=it['cell'], model=r, human=h,
                         needs_human=needs_human, final=final))
    folder = rs.REVIEWS / 'L3' / safe(batch)
    if folder.exists():
        raise SystemExit('Batch already recorded; use a new batch name')
    folder.mkdir(parents=True)
    path = folder / 'results.json'
    path.write_text(json.dumps(dict(batch=batch, date=date, questions_sha256=questions['_sha256'], triage=tri, results=rows),
                               ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    return path


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('queue')
    q.add_argument('--date', default=datetime.date.today().isoformat())
    for level in ('l1', 'l2'):
        r = sub.add_parser('record-' + level)
        r.add_argument('--unit', required=True)
        r.add_argument('--reviewer', required=True)
        r.add_argument('--decision', required=True, choices=['approved', 'revise'])
        r.add_argument('--notes', default='')
        r.add_argument('--date', default=datetime.date.today().isoformat())
        if level == 'l2':
            r.add_argument('--model-review')
            r.add_argument('--model-id')
    lp = sub.add_parser('l3-prompts')
    lp.add_argument('--batch', required=True)
    lp.add_argument('--out')
    lr = sub.add_parser('record-l3')
    lr.add_argument('--batch', required=True)
    lr.add_argument('--model-results', required=True)
    lr.add_argument('--human')
    lr.add_argument('--date', required=True)
    a = p.parse_args()
    if a.cmd == 'queue':
        print(json.dumps(queue(a.date), ensure_ascii=False))
    elif a.cmd in ('record-l1', 'record-l2'):
        level = a.cmd[-2:].upper()
        if level == 'L2' and bool(a.model_review) != bool(a.model_id):
            raise SystemExit('--model-review and --model-id go together')
        print(record(level, a.unit, a.reviewer, a.decision, a.notes, a.date, getattr(a, 'model_review', None), getattr(a, 'model_id', None)))
    elif a.cmd == 'l3-prompts':
        print(l3_prompts(a.batch, a.out or ROOT / 'runs' / ('review-' + safe(a.batch))), 'prompts written')
    else:
        print(record_l3(a.batch, a.model_results, a.human, a.date))
