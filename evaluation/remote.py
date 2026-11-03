"""Calling a real model over HTTP. One class, one wire format: OpenAI-style /chat/completions.

DeepSeek and Gemini both serve that shape, which is why the first two models in models.json are those two
and why adding a third is a table entry rather than code.

Three rules this file exists to keep:

  The key is never stored. It is read from the environment at call time, put in one header, and never
  written into a record, a log line or an exception message. A record that leaked a key would be worse than
  a lost run.

  The model names itself. `name` is not what we asked for -- it is what the API echoed back in the
  response, so a record cannot say deepseek-chat because a config file said so while something else
  answered. If the reply names no model, the record says so with `(claimed)` on the requested id.

  A failed call is not a wrong answer. After the retries are spent the call raises CallFailed and the
  caller records `error`, which is kept out of the score. Burying a 429 in the error rate would read as the
  model getting the chemistry wrong.
"""
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request

RETRY_STATUS = (408, 409, 429, 500, 502, 503, 504)
SYSTEM = ('You are answering questions about molecular and nanoscale geometry. '
          'Follow the answer format exactly.')


class CallFailed(Exception):
    """The model could not be reached or kept refusing. Not an answer, right or wrong."""


class MissingKey(Exception):
    """No API key in the environment. The user holds the keys; this repository never ships one."""


def urllib_transport(url, headers, body, timeout):
    request = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as problem:           # a status is an answer, not a transport failure
        return problem.code, problem.read()
    except Exception as problem:                        # DNS, TLS, timeout, reset
        return 0, str(problem).encode('utf-8')


class HTTPModel:
    """One model, answering one question at a time.

    Totals (`model_calls`, `usage`) and a per-question log are kept on the instance; the benchmark reads
    them after the run rather than threading them through every return value.
    """

    is_model = True

    def __init__(self, spec, transport=urllib_transport, retries=4, timeout=180, pause=0.0,
                 temperature=0.0, env=None):
        self.spec = spec
        self.requested = spec['model_id']
        self.name = spec['model_id']                    # replaced by whatever the API says answered
        self.named_itself = False
        self.transport = transport
        self.retries = retries
        self.timeout = timeout
        self.pause = pause
        self.temperature = temperature
        self.env = env if env is not None else os.environ
        self.model_calls = 0
        self.usage = dict(input_tokens=0, output_tokens=0)
        self.log = []
        self.lock = threading.Lock()               # the benchmark may run several questions at once

    def key(self):
        env = self.spec.get('key_env')
        value = (self.env.get(env) or '').strip() if env else ''
        if not value:
            raise MissingKey(
                '环境变量 %s 里没有 API 密钥。密钥由用户自己配，本仓库不内置、也不会把它写进任何记录；'
                '配好后重跑同一条命令即可（已经答过的题从缓存里取，不会重复花钱）。' % env)
        return value

    def request_body(self, prompt):
        return json.dumps(dict(
            model=self.requested,
            messages=[dict(role='system', content=SYSTEM), dict(role='user', content=prompt)],
            temperature=self.temperature,
            max_tokens=self.spec.get('max_output_tokens', 512)), ensure_ascii=False).encode('utf-8')

    def answer(self, question, prompt):
        headers = {'Authorization': 'Bearer ' + self.key(), 'Content-Type': 'application/json'}
        body = self.request_body(prompt)
        url = self.spec['endpoint']
        started, attempts, last = time.time(), 0, 'no attempt made'
        while attempts <= self.retries:
            attempts += 1
            with self.lock:
                self.model_calls += 1
            status, raw = self.transport(url, headers, body, self.timeout)
            if status == 200:
                text, usage, named = self.read(raw)
                if text is not None:
                    self.account(question, attempts, started, usage, named)
                    return text
                last = 'HTTP 200 但回包里没有文本'
            else:
                last = 'HTTP %s %s' % (status, self.short(raw))
            if status not in RETRY_STATUS and status != 200:
                break                                   # 400/401/403: retrying cannot help
            if attempts <= self.retries:
                time.sleep(min(30.0, (2 ** (attempts - 1)) * (1 + random.random())))
        with self.lock:
            self.log.append(dict(id=question.id, status='error', attempts=attempts,
                                 seconds=round(time.time() - started, 2), detail=last))
        raise CallFailed('%s 第 %d 次仍然失败：%s' % (self.requested, attempts, last))

    def read(self, raw):
        """Pull the reply, the usage and the model's own name out of one response body."""
        try:
            payload = json.loads(raw.decode('utf-8', 'replace'))
        except ValueError:
            return None, {}, None
        choices = payload.get('choices') or []
        message = (choices[0].get('message') or {}) if choices else {}
        text = message.get('content')
        if isinstance(text, list):                      # some servers return content as parts
            text = ''.join(part.get('text', '') for part in text if isinstance(part, dict))
        usage = payload.get('usage') or {}
        return text, usage, payload.get('model')

    def account(self, question, attempts, started, usage, named):
        with self.lock:
            if named:
                self.name, self.named_itself = named, True
            self.usage['input_tokens'] += int(usage.get('prompt_tokens') or 0)
            self.usage['output_tokens'] += int(usage.get('completion_tokens') or 0)
            self.log.append(dict(id=question.id, status='ok', attempts=attempts,
                                 seconds=round(time.time() - started, 2),
                                 input_tokens=usage.get('prompt_tokens'),
                                 output_tokens=usage.get('completion_tokens')))
        if self.pause:
            time.sleep(self.pause)

    @staticmethod
    def short(raw):
        """An error body, trimmed. Providers echo the request in errors, and the request holds the prompt."""
        try:
            payload = json.loads(raw.decode('utf-8', 'replace'))
            message = (payload.get('error') or {}).get('message') or payload.get('message') or ''
        except ValueError:
            message = raw.decode('utf-8', 'replace')
        return str(message)[:200]

    def identity(self):
        """What the record says about who answered."""
        return dict(answerer=self.name, requested=self.requested, named_itself=self.named_itself,
                    endpoint=self.spec['endpoint'], model_calls=self.model_calls, usage=dict(self.usage))

    def cost(self):
        """Dollars from the API's own token counts, at the prices in models.json."""
        rate_in, rate_out = self.spec.get('usd_per_million_input'), self.spec.get('usd_per_million_output')
        if rate_in is None or rate_out is None:
            return None
        return round(self.usage['input_tokens'] / 1e6 * rate_in
                     + self.usage['output_tokens'] / 1e6 * rate_out, 4)
