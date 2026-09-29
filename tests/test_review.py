"""Review system L1-L3 (A6): record formats, hash binding, sampling rules and the published queue."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import review_system as rs  # noqa: E402
import review as tool  # noqa: E402

QUEUE = json.loads((ROOT / 'docs/data/review-queue.json').read_text(encoding='utf-8'))
CATALOG = json.loads((ROOT / 'docs/data/catalog.json').read_text(encoding='utf-8'))
QUESTIONS = rs.load_questions()


def rec(**k):
    base = dict(level='L1', unit='named_bond_angle', decision='approved', date='2026-09-30', reviewer=dict(kind='human', name='Reviewer'),
                bindings={'registry_row': 'a', 'task_families/local_geometry.py': 'b'})
    base.update(k)
    return base


def l3(instance, verdicts):
    return dict(instance=instance, reviewer=dict(kind='model', name='some-model'), questions_sha256=QUESTIONS['_sha256'],
                answers={q['id']: dict(verdict=v, reason='r') for q, v in zip(QUESTIONS['questions'], verdicts)})


class RecordTests(unittest.TestCase):
    def test_l1_l2_need_a_named_human(self):
        rs.validate_record(rec())
        for bad in (rec(reviewer=dict(kind='model', name='x')), rec(reviewer=dict(kind='human', name=' ')), rec(decision='ok'),
                    rec(level='L3'), rec(bindings={}), rec(date='30/09/2026')):
            with self.assertRaises(ValueError):
                rs.validate_record(bad)

    def test_changed_code_makes_a_record_stale(self):
        records = dict(L1=[rec()], L2=[], L3=[])
        self.assertEqual(rs.unit_state('named_bond_angle', 'L1', rec()['bindings'], records)[0], 'approved')
        changed = dict(rec()['bindings'], **{'task_families/local_geometry.py': 'c'})
        self.assertEqual(rs.unit_state('named_bond_angle', 'L1', changed, records)[0], 'stale')
        self.assertEqual(rs.unit_state('other', 'L1', changed, records)[0], 'pending')
        later = rec(decision='revise', date='2026-10-01')
        self.assertEqual(rs.unit_state('named_bond_angle', 'L1', rec()['bindings'], dict(L1=[rec(), later], L2=[], L3=[]))[0], 'revise')

    def test_l3_results_must_answer_the_fixed_four_questions(self):
        rs.validate_l3(l3('X1', ['pass'] * 4), QUESTIONS)
        bad = l3('X1', ['pass'] * 4)
        bad['answers'].pop(QUESTIONS['questions'][0]['id'])
        with self.assertRaises(ValueError):
            rs.validate_l3(bad, QUESTIONS)
        with self.assertRaises(ValueError):
            rs.validate_l3(dict(l3('X1', ['pass'] * 4), questions_sha256='0' * 64), QUESTIONS)
        with self.assertRaises(ValueError):
            rs.validate_l3(l3('X1', ['pass', 'maybe', 'pass', 'pass']), QUESTIONS)

    def test_records_are_append_only_and_need_a_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = rs.REVIEWS
            rs.REVIEWS = Path(tmp)
            try:
                p1 = tool.record('L1', 'named_bond_angle', 'Reviewer', 'approved', 'ok', '2026-09-30')
                p2 = tool.record('L1', 'named_bond_angle', 'Reviewer', 'revise', 'fix', '2026-09-30')
                self.assertNotEqual(p1, p2)
                self.assertEqual(json.loads(p1.read_text(encoding='utf-8'))['decision'], 'approved')
                with self.assertRaises(SystemExit):
                    tool.record('L1', 'named_bond_angle', ' ', 'approved', '', '2026-09-30')
                with self.assertRaises(SystemExit):
                    tool.record('L1', 'no_such_family', 'Reviewer', 'approved', '', '2026-09-30')
                loaded = rs.load_records(Path(tmp))
                self.assertEqual(len(loaded['L1']), 2)
            finally:
                rs.REVIEWS = old


class SamplingTests(unittest.TestCase):
    ITEMS = [dict(id='A%02d' % i, unit='u1', source='s1', cell='chemistry 1-10', l0=True) for i in range(30)] + \
            [dict(id='B%02d' % i, unit='u2', source='s2', cell='quantum 0.1-1', l0=True) for i in range(5)]

    def test_first_batch_is_checked_in_full(self):
        plan = rs.plan_l3(self.ITEMS, [], 'seed')
        self.assertEqual(sum(p['sample'] for p in plan), 35)

    def test_stable_strata_get_max_two_or_ten_percent(self):
        history = [dict(results=[dict(unit='u1', source='s1', final='pass'), dict(unit='u2', source='s2', final='pass')])]
        plan = {p['unit']: p for p in rs.plan_l3(self.ITEMS, history, 'seed')}
        self.assertEqual(plan['u1']['sample'], 3)            # ceil(10% of 30)
        self.assertEqual(plan['u2']['sample'], 2)            # minimum 2
        self.assertEqual(plan['u1']['ids'], rs.plan_l3(self.ITEMS, history, 'seed')[0]['ids'])   # deterministic
        self.assertNotEqual(plan['u1']['ids'], {p['unit']: p for p in rs.plan_l3(self.ITEMS, history, 'other')}['u1']['ids'])

    def test_flags_and_calibration_go_to_a_human(self):
        results = [l3('P%02d' % i, ['pass'] * 4) for i in range(20)] + [l3('F1', ['pass', 'flag', 'pass', 'pass'])]
        tri = rs.triage(results, 'seed')
        self.assertEqual(tri['flagged'], ['F1'])
        self.assertEqual(len(tri['calibration']), 3)          # max(3, 10% of 20 passes)
        self.assertTrue(all(i.startswith('P') for i in tri['calibration']))

    def test_status_flow(self):
        item = dict(id='X', unit='u', l0=True)
        self.assertEqual(rs.instance_stage(item, {}, {}), 'L0')
        self.assertEqual(rs.instance_stage(item, {'u': ('approved', 'pending')}, {}), 'L0')
        self.assertEqual(rs.instance_stage(item, {'u': ('approved', 'approved')}, {}), 'L1+L2')
        self.assertEqual(rs.instance_stage(item, {'u': ('approved', 'approved')}, {'X': 'pass'}), 'formal')
        self.assertEqual(rs.instance_stage(item, {'u': ('approved', 'stale')}, {'X': 'pass'}), 'L0')
        self.assertEqual(rs.instance_stage(dict(item, l0=False), {}, {}), 'not-verified')


class PublishedQueueTests(unittest.TestCase):
    def test_queue_covers_every_active_record_once(self):
        active = sorted(q['id'] for q in CATALOG['questions'] if q['lifecycle'] == 'active')
        planned = sorted(i for p in QUEUE['l3_plan'] for i in p['ids'])
        self.assertEqual(planned, active)                     # first batch: everything, each once
        self.assertEqual(sorted(QUEUE['stages']), active)
        self.assertEqual(QUEUE['summary']['model_calls'], 0)
        self.assertEqual(QUEUE['questions_sha256'], QUESTIONS['_sha256'])

    def test_every_unit_has_a_card_and_bindings(self):
        units = {u['unit']: u for u in QUEUE['units']}
        for q in CATALOG['questions']:
            if q['lifecycle'] == 'active':
                self.assertIn(q['family'] if q.get('familyInstance') else 'legacy:' + (q.get('family') or q['id']), units)
        for u in QUEUE['units']:
            self.assertTrue(u['bindings']['L1'].get('registry_row'), u['unit'])
            if u['kind'] == 'family':
                self.assertTrue(u['checker'] and all(u['bindings']['L2'].values()), u['unit'])
                if u['instances']:
                    self.assertGreaterEqual(len(u['card']['samples']), 1, u['unit'])

    def test_no_review_is_recorded_on_anyones_behalf(self):
        self.assertFalse(any((ROOT / 'reviews' / lvl).exists() and any((ROOT / 'reviews' / lvl).iterdir()) for lvl in ('L1', 'L2', 'L3')))
        self.assertEqual(QUEUE['summary']['stages']['formal'], 0)

    def test_prompt_contains_packets_and_the_four_questions(self):
        text = rs.l3_prompt('X1', 'QUESTION TEXT', dict(correct_label='B'), QUESTIONS)
        for q in QUESTIONS['questions']:
            self.assertIn(q['id'], text)
        self.assertIn('=== STUDENT PACKET ===\nQUESTION TEXT', text)
        self.assertIn('"correct_label": "B"', text)


if __name__ == '__main__':
    unittest.main()
