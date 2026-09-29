"""Review system L1-L3 (roadmap A6): records, hash bindings, instance status and stratified sampling.

Design (HANDOFF section 7b):
  L0  automatic verification of every instance (independent checkers; already in place)
  L1  task-family review, once per family: a human reads the family card and two samples
  L2  checker review, once per family: a human reads the independent checker (optionally with one model code review)
  L3  stratified spot check per batch: a lightweight model answers four fixed questions; every flag goes to a human,
      and a calibration sample of model passes also goes to a human
Records live in reviews/ (append-only JSON). Each L1/L2 record is bound to SHA-256 hashes of the code and
registry row it approved; when those change the record becomes stale and the family must be reviewed again.
Nothing here calls a model or approves anything by itself: records are written only by tools/review.py with a
named reviewer.
"""
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = ROOT / 'reviews'
QUESTIONS = ROOT / 'templates/review-l3-questions.json'
DECISIONS = {'L1': ('approved', 'revise'), 'L2': ('approved', 'revise')}
VERDICTS = ('pass', 'flag')
STAGES = ('L0', 'L1+L2', 'L3', 'formal')


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode('utf-8')).hexdigest()


def file_sha(rel):
    path = ROOT / rel
    return sha(path.read_bytes()) if path.exists() else None


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


# ------------------------------------------------------------------ review units and bindings
def registry_row(registry, family):
    for t in registry['templates']:
        if family in t.get('engine_families', []) or family == t['id'] or family in t.get('legacy_families', []):
            return t
    return None


def units(registry, families, checkers, catalog):
    """One review unit per task family in use (engine families) plus one per legacy template family still active."""
    out = {}
    for f, info in families.items():
        row = registry_row(registry, f)
        fn = checkers.get(f)
        checker_file = fn.__module__.replace('.', '/') + '.py' if fn else None
        out[f] = dict(unit=f, kind='family', ability=info['ability'], registry_id=row['id'] if row else None,
                      generator=info['module'], checker=checker_file, checker_function=fn.__name__ if fn else None)
    for q in catalog['questions']:
        if q.get('lifecycle') == 'active' and not q.get('familyInstance'):
            f = 'legacy:' + (q.get('family') or q['id'])
            if f not in out:
                row = registry_row(registry, q.get('family') or '')
                out[f] = dict(unit=f, kind='legacy', ability=q['ability'], registry_id=row['id'] if row else None,
                              generator=None, checker=None, checker_function=None,
                              code=[c for c in (row or {}).get('code', []) if (ROOT / c).exists()])
    return out


def bindings(unit, registry):
    """Hashes an L1 / L2 record is bound to. Any change makes the record stale."""
    row = next((t for t in registry['templates'] if t['id'] == unit['registry_id']), None)
    row_sha = sha(canonical(row)) if row else None
    if unit['kind'] == 'family':
        l1 = {'registry_row': row_sha, unit['generator']: file_sha(unit['generator'])}
        l2 = {unit['checker']: file_sha(unit['checker']), 'checkers/common.py': file_sha('checkers/common.py')} if unit['checker'] else {}
    else:
        l1 = {'registry_row': row_sha}
        l2 = {c: file_sha(c) for c in unit.get('code', [])}
    return dict(L1=l1, L2=l2)


# ------------------------------------------------------------------ records
def validate_record(rec):
    """Schema check for an L1 / L2 record; returns the record or raises ValueError."""
    need(rec.get('level') in DECISIONS, 'level must be L1 or L2')
    need(isinstance(rec.get('unit'), str) and rec['unit'], 'unit missing')
    need(rec.get('decision') in DECISIONS[rec['level']], 'decision must be approved or revise')
    reviewer = rec.get('reviewer') or {}
    need(reviewer.get('kind') == 'human' and reviewer.get('name', '').strip(), 'L1/L2 decisions need a named human reviewer')
    need(isinstance(rec.get('bindings'), dict) and rec['bindings'], 'bindings missing')
    need(isinstance(rec.get('date'), str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', rec['date']), 'date must be YYYY-MM-DD')
    for m in rec.get('model_reviews', []):
        need(m.get('model') and m.get('output_sha256'), 'model review needs model id and output hash')
    return rec


def validate_l3(result, questions):
    ids = [q['id'] for q in questions['questions']]
    need(isinstance(result.get('instance'), str), 'instance missing')
    need((result.get('reviewer') or {}).get('kind') in ('model', 'human'), 'reviewer kind must be model or human')
    need((result.get('reviewer') or {}).get('name', '').strip(), 'reviewer name/model id missing')
    answers = result.get('answers') or {}
    need(sorted(answers) == sorted(ids), 'answers must cover exactly the four fixed questions')
    for k, v in answers.items():
        need(v.get('verdict') in VERDICTS and isinstance(v.get('reason', ''), str), 'bad verdict for ' + k)
    need(result.get('questions_sha256') == questions['_sha256'], 'result was produced with a different question set')
    return result


def load_questions():
    raw = QUESTIONS.read_bytes()
    q = json.loads(raw.decode('utf-8'))
    q['_sha256'] = sha(raw)
    return q


def load_records(root=REVIEWS):
    recs = dict(L1=[], L2=[], L3=[])
    for level in ('L1', 'L2'):
        for p in sorted((root / level).glob('*.json')) if (root / level).exists() else []:
            recs[level].append(validate_record(json.loads(p.read_text(encoding='utf-8'))))
    if (root / 'L3').exists():
        for p in sorted((root / 'L3').glob('*/results.json')):
            batch = json.loads(p.read_text(encoding='utf-8'))
            recs['L3'].append(batch)
    return recs


def unit_state(unit_id, level, current, records):
    """approved (current) | revise (current) | stale | pending: the latest record for the unit decides."""
    mine = [r for r in records[level] if r['unit'] == unit_id]
    if not mine:
        return 'pending', None
    last = sorted(mine, key=lambda r: (r['date'], r.get('seq', 0)))[-1]
    if last['bindings'] != current:
        return 'stale', last
    return last['decision'], last


# ------------------------------------------------------------------ instances, strata, sampling
def cell(reasoning_nm):
    for lo, hi in ((0.1, 1), (1, 10), (10, 100), (100, 1000)):
        if reasoning_nm is not None and lo <= reasoning_nm < hi:
            return '%g-%g' % (lo, hi)
    return 'out-of-range'


def instances(catalog):
    """Active catalog records with the unit, source and scale cell used for stratification."""
    out = []
    for q in catalog['questions']:
        if q.get('lifecycle') != 'active':
            continue
        unit = q['family'] if q.get('familyInstance') else 'legacy:' + (q.get('family') or q['id'])
        out.append(dict(id=q['id'], unit=unit, instance=q.get('familyInstance'), source=q.get('paper') or 'unknown',
                        cell='%s %s' % (q['domain'], cell(q.get('reasoningSizeNm'))), ability=q['ability'],
                        l0=(q.get('independentCheck') == 'pass') if q.get('familyInstance') else bool(q.get('prototypeScreeningPassed'))))
    return out


def stratum(item):
    return '%s | %s | %s' % (item['unit'], item['source'], item['cell'])


def rank_key(seed, item_id):
    return sha('%s|%s' % (seed, item_id))


def plan_l3(items, history, seed, fraction=0.10, minimum=2):
    """Stratified sample. A stratum whose unit or source has never passed an L3 batch is checked in full
    (first batch of a new family or source); stable strata get max(minimum, ceil(fraction * n))."""
    passed_units, passed_sources = set(), set()
    for batch in history:
        for r in batch.get('results', []):
            if r.get('final') == 'pass':
                passed_units.add(r['unit'])
                passed_sources.add(r['source'])
    groups = {}
    for it in items:
        groups.setdefault(stratum(it), []).append(it)
    plan = []
    for key, members in sorted(groups.items()):
        first = members[0]['unit'] not in passed_units or members[0]['source'] not in passed_sources
        n = len(members) if first else min(len(members), max(minimum, math.ceil(fraction * len(members))))
        chosen = sorted(members, key=lambda it: rank_key(seed, it['id']))[:n]
        plan.append(dict(stratum=key, unit=members[0]['unit'], source=members[0]['source'], cell=members[0]['cell'],
                         size=len(members), sample=n, rule='first batch: all' if first else 'stable: max(%d, %d%%)' % (minimum, fraction * 100),
                         ids=sorted(it['id'] for it in chosen)))
    return plan


def calibration_sample(model_results, seed, fraction=0.10, minimum=3):
    """Model passes that also go to a human, to calibrate the model reviewer."""
    passes = [r['instance'] for r in model_results if all(a['verdict'] == 'pass' for a in r['answers'].values())]
    n = min(len(passes), max(minimum, math.ceil(fraction * len(passes))))
    return sorted(sorted(passes, key=lambda i: rank_key(seed + '/calibration', i))[:n])


def triage(model_results, seed):
    """Human queue after the model pass: every flagged instance plus the calibration sample."""
    flagged = sorted(r['instance'] for r in model_results if any(a['verdict'] == 'flag' for a in r['answers'].values()))
    return dict(flagged=flagged, calibration=calibration_sample(model_results, seed))


def instance_stage(item, unit_states, l3_final):
    if not item['l0']:
        return 'not-verified'
    l1, l2 = unit_states.get(item['unit'], ('pending', 'pending'))
    if l1 != 'approved' or l2 != 'approved':
        return 'L0'
    if l3_final.get(item['id']) != 'pass':
        return 'L1+L2'
    return 'formal'


# ------------------------------------------------------------------ L3 prompt
def reviewer_packet(teacher, record):
    """What the model reviewer sees besides the student packet: answer, option audit, source and limits."""
    if teacher:
        return dict(correct_label=teacher['correct_label'], numeric_answer=teacher.get('numeric_answer'),
                    option_audit=[{k: o.get(k) for k in ('label', 'value', 'rule', 'source_id', 'reason', 'is_correct') if k in o} for o in teacher['option_audit']],
                    source=teacher['source'], license=teacher.get('license'), limits=(teacher.get('checks') or {}).get('limits'),
                    scales=teacher.get('scales'))
    return dict(answer=record.get('answer'), source=record.get('source'), attribution=record.get('attribution'),
                validation=record.get('validation'), rubric=record.get('rubric'))


def l3_prompt(item_id, student_text, reviewer, questions):
    lines = [questions['instructions'], '', 'Instance: %s' % item_id, '', '=== STUDENT PACKET ===', student_text, '',
             '=== REVIEWER PACKET ===', json.dumps(reviewer, ensure_ascii=False, indent=1), '', '=== QUESTIONS ===']
    lines += ['%s: %s' % (q['id'], q['prompt']) for q in questions['questions']]
    lines += ['', 'Output schema: ' + json.dumps(questions['output_schema'], ensure_ascii=False)]
    return '\n'.join(lines) + '\n'
