"""W1: the benchmark must be able to call a real model, and must never misreport what it called.

No test here touches the network. The transport is injected, so what is pinned is the harness's own
behaviour: that the key comes from the environment and reaches no record; that a model is named by its own
reply rather than by our config; that a failed call and a prompt too large for the window are recorded as
`error` and `oversize` and kept out of the score instead of counting as wrong answers; that nothing is paid
for twice; and that the table carries a denominator per cell, because two models with different context
windows were not asked the same exam.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation import benchmark, budget, exam, providers, remote, scoring  # noqa: E402

KEY = 'sk-not-a-real-key-0123456789'
SPEC = dict(label='fake', api='openai-chat', endpoint='https://example.invalid/v1/chat/completions',
            model_id='fake-1', key_env='GEOBENCH_TEST_KEY', context_tokens=4096, max_output_tokens=16,
            usd_per_million_input=1.0, usd_per_million_output=2.0, priced_on='2026-11-03',
            price_source='test')


def reply_body(text, model='fake-1-20261103', prompt_tokens=100, completion_tokens=2):
    return json.dumps(dict(model=model, choices=[dict(message=dict(role='assistant', content=text))],
                           usage=dict(prompt_tokens=prompt_tokens,
                                      completion_tokens=completion_tokens))).encode('utf-8')


class Transport:
    """Stands in for the network. Records what it was handed and replays a scripted list of responses."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.seen = []

    def __call__(self, url, headers, body, timeout):
        self.seen.append(dict(url=url, headers=dict(headers), body=json.loads(body.decode('utf-8'))))
        return self.responses.pop(0) if self.responses else (200, reply_body('A'))


def model(responses=(), env=None, **kwargs):
    return remote.HTTPModel(SPEC, transport=Transport(responses),
                            env={'GEOBENCH_TEST_KEY': KEY} if env is None else env, **kwargs)


class Q:
    """The few attributes a provider and the scorer touch."""

    def __init__(self, id='BND001', form='choice'):
        self.id, self.form = id, form
        self.family, self.ability, self.domain = 'fam', 'inference', 'biology'

    def prompt(self, setting='coords'):
        return 'What is the answer?'


class KeyHandlingTests(unittest.TestCase):
    def test_the_key_comes_from_the_environment_and_reaches_no_record(self):
        answerer = model()
        answerer.answer(Q(), 'prompt')
        self.assertEqual(answerer.transport.seen[0]['headers']['Authorization'], 'Bearer ' + KEY)
        # everything the harness keeps or prints about the call
        kept = json.dumps([answerer.identity(), answerer.log, answerer.spec], ensure_ascii=False)
        self.assertNotIn(KEY, kept)

    def test_no_key_in_the_environment_says_which_variable_to_set(self):
        with self.assertRaises(remote.MissingKey) as refused:
            model(env={}).answer(Q(), 'prompt')
        self.assertIn('GEOBENCH_TEST_KEY', str(refused.exception))

    def test_a_failure_message_does_not_carry_the_key_or_the_prompt(self):
        body = json.dumps(dict(error=dict(message='bad key: Bearer ' + KEY))).encode('utf-8')
        answerer = model([(401, body)])
        with self.assertRaises(remote.CallFailed) as failure:
            answerer.answer(Q(), 'the prompt text')
        self.assertNotIn('the prompt text', str(failure.exception))
        self.assertIn('401', str(failure.exception))


class CallTests(unittest.TestCase):
    def test_the_model_is_named_by_its_own_reply_not_by_our_config(self):
        answerer = model([(200, reply_body('B', model='fake-1-20261103'))])
        answerer.answer(Q(), 'prompt')
        self.assertEqual(answerer.name, 'fake-1-20261103')     # not SPEC['model_id']
        self.assertTrue(answerer.named_itself)
        self.assertEqual(answerer.identity()['requested'], 'fake-1')

    def test_a_reply_that_names_no_model_is_recorded_as_unconfirmed(self):
        answerer = model([(200, json.dumps(dict(choices=[dict(message=dict(content='B'))])).encode())])
        answerer.answer(Q(), 'prompt')
        self.assertEqual(answerer.name, 'fake-1')
        self.assertFalse(answerer.named_itself)

    def test_a_rate_limit_is_retried_and_a_bad_request_is_not(self):
        answerer = model([(429, b'{}'), (200, reply_body('C'))], retries=3)
        answerer.pause = 0
        self.assertEqual(answerer.answer(Q(), 'prompt'), 'C')
        self.assertEqual(answerer.model_calls, 2)

        refused = model([(400, b'{"error":{"message":"context length"}}')], retries=3)
        with self.assertRaises(remote.CallFailed):
            refused.answer(Q(), 'prompt')
        self.assertEqual(refused.model_calls, 1)               # retrying a 400 only spends money

    def test_cost_comes_from_the_usage_the_api_reported(self):
        answerer = model([(200, reply_body('A', prompt_tokens=2_000_000, completion_tokens=1_000_000))])
        answerer.answer(Q(), 'prompt')
        self.assertEqual(answerer.usage, dict(input_tokens=2_000_000, output_tokens=1_000_000))
        self.assertEqual(answerer.cost(), 4.0)                  # 2M @ $1 + 1M @ $2


class BudgetTests(unittest.TestCase):
    def test_a_prompt_larger_than_the_window_is_separated_before_anything_is_called(self):
        sizes = [dict(id='SMALL', tokens=100, domain='biology', family='f', ability='a'),
                 dict(id='BIG', tokens=99_000, domain='biology', family='f', ability='a')]
        shown, oversize, room = budget.fit(sizes, SPEC)
        self.assertEqual([s['id'] for s in shown], ['SMALL'])
        self.assertEqual([s['id'] for s in oversize], ['BIG'])
        self.assertEqual(room, 4096 - 16 - budget.RESERVE_TOKENS)

    def test_a_model_with_no_declared_window_is_reported_as_unchecked_not_as_fitting(self):
        sizes = [dict(id='BIG', tokens=10 ** 6, domain='biology', family='f', ability='a')]
        shown, oversize, room = budget.fit(sizes, dict(model_id='unknown'))
        self.assertEqual(len(shown), 1)
        self.assertEqual(oversize, [])
        self.assertIsNone(room)                                 # the report prints None, not a number

    def test_the_estimate_prices_only_what_would_be_sent(self):
        sizes = [dict(id='SMALL', tokens=1000, domain='biology', family='f', ability='a'),
                 dict(id='BIG', tokens=99_000, domain='materials', family='f', ability='a')]
        row = budget.estimate(sizes, SPEC)
        self.assertEqual(row['input_tokens'], 1000)             # the oversize one is not billed
        self.assertEqual(row['oversize_by_domain'], {'materials': dict(n=1, tokens=99_000)})
        self.assertEqual(row['usd_upper_bound'], round(1000 / 1e6 * 1.0 + 16 / 1e6 * 2.0, 2))


class OutcomeTests(unittest.TestCase):
    """error and oversize are not wrong answers."""

    def setUp(self):
        self.questions = [Q('Q%d' % i) for i in range(4)]
        self.key = {q.id: dict(label='A', numeric=None) for q in self.questions}
        self.cells = scoring.cells

    def tally(self, results):
        scoring.cells = lambda root=None: {q.id: 'biology 1-10 nm' for q in self.questions}
        try:
            return scoring.tally(results, self.questions)
        finally:
            scoring.cells = self.cells

    def test_a_failed_call_and_an_oversize_prompt_stay_out_of_the_denominator(self):
        results = [scoring.grade(self.questions[0], self.key['Q0'], 'A'),          # correct
                   scoring.grade(self.questions[1], self.key['Q1'], 'B'),          # wrong
                   scoring.not_asked(self.questions[2], 'error', 'HTTP 503'),
                   scoring.not_asked(self.questions[3], 'oversize', '99000 token')]
        summary = self.tally(results)
        self.assertEqual((summary['n'], summary['asked']), (4, 2))
        self.assertEqual(summary['score'], 0.5)                 # 1 of the 2 it was actually asked
        self.assertEqual((summary['error'], summary['oversize']), (1, 1))
        group = summary['groups']['domain']['biology']
        self.assertEqual((group['n'], group['asked'], group['score']), (4, 2, 0.5))

    def test_an_unreadable_reply_stays_in_the_denominator(self):
        # The model was shown the question and answered in a shape we could not read; that is the model's
        # problem, unlike a 503, so it counts against it.
        results = [scoring.grade(self.questions[0], self.key['Q0'], 'A'),
                   scoring.grade(self.questions[1], self.key['Q1'], 'A or B')]
        summary = self.tally(results)
        self.assertEqual((summary['asked'], summary['unparsed'], summary['score']), (2, 1, 0.5))


class CacheTests(unittest.TestCase):
    def test_a_second_pass_calls_nothing_and_an_interrupted_one_resumes(self):
        questions = [Q('Q%d' % i) for i in range(3)]
        key = {q.id: dict(label='A', numeric=None) for q in questions}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cache.jsonl'
            first = model([(200, reply_body('A'))] * 3)
            session = benchmark.Session(first, questions, key, 'coords', path)
            results = session.run()
            self.assertEqual([r['result'] for r in results], ['correct'] * 3)
            self.assertEqual(first.model_calls, 3)
            self.assertEqual(session.resumed, 0)

            again = model([(200, reply_body('A'))] * 3)
            second = benchmark.Session(again, questions, key, 'coords', path)
            self.assertEqual([r['result'] for r in second.run()], ['correct'] * 3)
            self.assertEqual(again.model_calls, 0)              # nothing paid for twice
            self.assertEqual(second.resumed, 3)

    def test_an_oversize_question_is_written_down_without_being_sent(self):
        questions = [Q('SMALL'), Q('BIG')]
        key = {q.id: dict(label='A', numeric=None) for q in questions}
        with tempfile.TemporaryDirectory() as folder:
            answerer = model([(200, reply_body('A'))])
            session = benchmark.Session(answerer, questions, key, 'coords', Path(folder) / 'c.jsonl')
            results = session.run(oversize=[dict(id='BIG', tokens=99_000)])
            self.assertEqual({r['id']: r['result'] for r in results},
                             dict(SMALL='correct', BIG='oversize'))
            self.assertEqual(len(answerer.transport.seen), 1)
            self.assertEqual(answerer.transport.seen[0]['body']['messages'][-1]['content'],
                             'What is the answer?')
            self.assertIn('99000 token', [r.get('detail') for r in results if r['id'] == 'BIG'][0])

    def test_a_rebuilt_question_is_asked_again_and_the_others_are_not(self):
        # The stamp is per question, so rebuilding the bank re-asks only what actually changed -- and a
        # thirty-question trial run is not paid for twice by the full pass.
        class Changing(Q):
            text = 'What is the answer?'

            def prompt(self, setting='coords'):
                return self.text

        questions = [Changing('Q0'), Changing('Q1')]
        key = {q.id: dict(label='A', numeric=None) for q in questions}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cache.jsonl'
            first = model([(200, reply_body('A'))] * 2)
            benchmark.Session(first, questions, key, 'coords', path).run()
            self.assertEqual(first.model_calls, 2)

            questions[1].text = 'What is the answer, really?'     # one question rebuilt
            again = model([(200, reply_body('A'))] * 2)
            session = benchmark.Session(again, questions, key, 'coords', path)
            self.assertEqual(session.resumed, 1)                  # only Q0 is still answerable from disk
            self.assertEqual([r['result'] for r in session.run()], ['correct', 'correct'])
            self.assertEqual(again.model_calls, 1)                # and only Q1 was asked again

    def test_a_cache_file_is_one_per_answerer_form_and_setting(self):
        self.assertNotEqual(benchmark.cache_path('fake-1', 'coords', 'choice').name,
                            benchmark.cache_path('fake-1', 'coords', 'numeric').name)
        self.assertNotEqual(benchmark.cache_path('fake-1', 'coords', 'choice').name,
                            benchmark.cache_path('fake-1', 'coords+code', 'choice').name)


class TableTests(unittest.TestCase):
    def rows(self):
        questions = [Q('Q%d' % i) for i in range(2)]
        key = {q.id: dict(label='A', numeric=None) for q in questions}
        cells = scoring.cells
        scoring.cells = lambda root=None: {q.id: 'biology 1-10 nm' for q in questions}
        try:
            wide = scoring.tally([scoring.grade(questions[0], key['Q0'], 'A'),
                                  scoring.grade(questions[1], key['Q1'], 'A')], questions)
            narrow = scoring.tally([scoring.grade(questions[0], key['Q0'], 'A'),
                                    scoring.not_asked(questions[1], 'oversize', '99000 token')], questions)
        finally:
            scoring.cells = cells
        return [dict(answerer='wide-window', answerer_is_a_model=True, summary=wide),
                dict(answerer='narrow-window', answerer_is_a_model=True, summary=narrow)]

    def test_every_cell_carries_its_own_denominator(self):
        grid = benchmark.table(self.rows())
        self.assertEqual(grid['columns'], ['biology'])
        self.assertEqual([r['cells']['biology'] for r in grid['rows']],
                         [dict(score=1.0, asked=2, n=2), dict(score=1.0, asked=1, n=2)])

    def test_the_printed_table_marks_the_row_that_was_asked_less(self):
        record = dict(bank_run='run-x', setting_label='坐标文本', questions=2, exam_fingerprint='f' * 64,
                      runs=self.rows(), table=benchmark.table(self.rows()))
        text = benchmark.markdown(record)
        self.assertIn('1/2', text)                              # the narrow window is visible in the cell
        self.assertIn('| 0 / 0 |', text)                        # the wide one dropped nothing
        self.assertIn('| 1 / 0 |', text)


class RealTransportTests(unittest.TestCase):
    """The one path the injected transport cannot cover: urllib against a server that speaks the wire
    format. Nothing leaves the machine -- the server is this process, on a port the OS picked."""

    @classmethod
    def setUpClass(cls):
        import http.server
        import threading as t

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                cls.received.append(dict(auth=self.headers.get('Authorization'),
                                         payload=json.loads(body.decode('utf-8'))))
                if len(cls.received) == 1:                      # make it retry once, for real
                    self.send_response(429)
                    self.end_headers()
                    self.wfile.write(b'{"error":{"message":"slow down"}}')
                    return
                out = reply_body('C', model='fake-served-1')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *args):
                pass

        cls.received = []
        cls.server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = t.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_a_real_request_goes_out_retries_and_comes_back_scored(self):
        host, port = self.server.server_address
        spec = dict(SPEC, endpoint='http://%s:%d/v1/chat/completions' % (host, port))
        answerer = remote.HTTPModel(spec, retries=2, timeout=10, env={'GEOBENCH_TEST_KEY': KEY})
        question = Q('BND001')
        self.assertEqual(answerer.answer(question, question.prompt()), 'C')
        self.assertEqual(answerer.model_calls, 2)                # the 429, then the answer
        self.assertEqual(answerer.name, 'fake-served-1')
        self.assertEqual(self.received[-1]['auth'], 'Bearer ' + KEY)
        self.assertEqual(self.received[-1]['payload']['messages'][-1]['content'], 'What is the answer?')
        self.assertEqual(self.received[-1]['payload']['model'], 'fake-1')
        row = scoring.grade(question, dict(label='C', numeric=None), 'C')
        self.assertEqual(row['result'], 'correct')


class EndToEndTests(unittest.TestCase):
    """The whole command against a model that really answers over HTTP: a few real questions from the
    published bank, one of them too large for the window, scored into the table the report prints."""

    def test_the_benchmark_runs_a_model_over_real_questions_and_reports_honestly(self):
        import http.server
        import threading as t

        served = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                served.append(json.loads(body.decode('utf-8')))
                out = reply_body('A', model='fake-served-1', prompt_tokens=1234, completion_tokens=3)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        t.Thread(target=server.serve_forever, daemon=True).start()
        try:
            host, port = server.server_address
            # A window that admits the ordinary questions and refuses the coordinate dump.
            spec = dict(SPEC, endpoint='http://%s:%d/v1/chat/completions' % (host, port),
                        context_tokens=6000, model_id='fake-served')
            questions = exam.load(form='choice')
            sizes, _ = budget.measure(questions)
            big = max(sizes, key=lambda s: s['tokens'])['id']
            small = [s['id'] for s in sorted(sizes, key=lambda s: s['tokens'])[:3]]
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / 'docs' / 'data').mkdir(parents=True)
                for name in ('family-workbench.json', 'catalog.json', 'prototype-progress.json'):
                    (root / 'docs' / 'data' / name).write_bytes((ROOT / 'docs' / 'data' / name).read_bytes())
                record = benchmark.run(['fake-served', 'seeded'], ids=set(small + [big]), root=root,
                                       models={'fake-served': spec},
                                       env={'GEOBENCH_TEST_KEY': KEY})
        finally:
            server.shutdown()
            server.server_close()

        model_run = record['runs'][0]
        self.assertEqual(model_run['answerer'], 'fake-served-1')          # named by its own reply
        self.assertTrue(model_run['answerer_is_a_model'])
        self.assertEqual(model_run['summary']['oversize'], 1)            # the dump was never sent
        self.assertEqual(model_run['summary']['asked'], 3)
        self.assertEqual(len(served), 3)
        self.assertEqual(model_run['usage'], dict(input_tokens=3 * 1234, output_tokens=9))
        self.assertEqual(model_run['usd_from_reported_usage'],
                         round(3 * 1234 / 1e6 * 1.0 + 9 / 1e6 * 2.0, 4))
        for sent in served:
            self.assertNotIn('is_correct', json.dumps(sent))              # no teacher side on the wire

        baseline = record['runs'][1]
        self.assertFalse(baseline['answerer_is_a_model'])
        self.assertEqual(baseline['summary']['asked'], 4)                 # a baseline is asked everything
        self.assertIn('fake-served-1', benchmark.markdown(record))


class WiringTests(unittest.TestCase):
    def test_the_shipped_model_table_is_complete_enough_to_price_and_to_fit(self):
        for name, spec in providers.catalogue().items():
            for field in ('endpoint', 'model_id', 'key_env', 'context_tokens', 'max_output_tokens',
                          'usd_per_million_input', 'usd_per_million_output', 'priced_on'):
                self.assertIsNotNone(spec.get(field), '%s 缺 %s' % (name, field))
            self.assertTrue(spec['endpoint'].startswith('https://'), name)

    def test_no_api_key_is_committed_anywhere_in_the_harness(self):
        table = budget.load_models()
        self.assertIsNone(table['verified_by_user_on'])         # the user has not confirmed prices yet
        text = json.dumps(table, ensure_ascii=False) + ''.join(
            path.read_text(encoding='utf-8') for path in sorted((ROOT / 'evaluation').glob('*.py')))
        for marker in ('sk-', 'AIza', 'Bearer ey'):
            self.assertNotIn(marker + 'x', text)
            for line in text.splitlines():
                self.assertFalse(line.strip().startswith(marker), line[:40])

    def test_a_baseline_and_a_model_report_themselves_the_same_way(self):
        baseline = providers.get('seeded')
        self.assertEqual(baseline.identity()['model_calls'], 0)
        self.assertFalse(baseline.is_model)
        self.assertEqual(baseline.cost(), 0.0)
        wired = providers.get(next(iter(providers.catalogue())))
        self.assertTrue(wired.is_model)
        self.assertEqual(wired.model_calls, 0)                  # asking for it calls nothing
        self.assertEqual(set(baseline.identity()), set(wired.identity()))


if __name__ == '__main__':
    unittest.main()
