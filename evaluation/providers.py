"""Who answers the exam: a baseline that looks at nothing, or a model named in models.json.

The baselines are not filler. Four-way choice makes a quarter of the score free, and a real model's number
means nothing until it is read against the floor measured on the same questions in the same run.

A baseline and a model are asked for the same way and report themselves the same way, so a record can
always be read for what it is: `answerer_is_a_model` and `model_calls` come from the answerer itself, and a
baseline's are False and 0 because nothing was called. A record that said claude or deepseek when a mock
produced it would be a fabricated result.
"""
import hashlib

from . import budget, remote

LABELS = ('A', 'B', 'C', 'D')


class Mock:
    """A baseline. `model_calls` stays at zero because nothing is called."""

    is_model = False

    def __init__(self, name, pick):
        self.name = name
        self.pick = pick
        self.model_calls = 0
        self.usage = dict(input_tokens=0, output_tokens=0)
        self.log = []

    def answer(self, question, prompt):
        if question.form == 'numeric':
            return '0'
        return self.pick(question)

    def identity(self):
        return dict(answerer=self.name, requested=self.name, named_itself=False, endpoint=None,
                    model_calls=0, usage=dict(self.usage))

    def cost(self):
        return 0.0


def seeded_label(question):
    """A fixed label per question, from the id alone. Deterministic, so the floor is the same every run."""
    digest = hashlib.sha256(question.id.encode('utf-8')).digest()
    return LABELS[digest[0] % 4]


BASELINES = {
    'always-a': lambda: Mock('baseline-always-a', lambda q: 'A'),
    'seeded': lambda: Mock('baseline-seeded', seeded_label),
    'blank': lambda: Mock('baseline-blank', lambda q: ''),
}


def catalogue(path=budget.MODELS):
    return budget.load_models(path)['models']


def get(name, models=None, **kwargs):
    """A baseline by name, or a model from models.json. Asking for a model does not call anything yet, and
    does not need a key until the first question is put to it."""
    if name in BASELINES:
        return BASELINES[name]()
    table = catalogue() if models is None else models
    if name in table:
        return remote.HTTPModel(table[name], **kwargs)
    raise ValueError(
        '没有这个作答者：%s。内置基线 %s；models.json 里配好的模型 %s。要加一个真模型，'
        '在 evaluation/models.json 里加一条（端点、model_id、放 API 密钥的环境变量名、上下文窗口、价格），'
        'API 密钥由用户自己配到环境变量里，本仓库不内置密钥，provider 必须如实报自己的名字和调用次数。'
        % (name, '、'.join(sorted(BASELINES)), '、'.join(sorted(table)) or '（还没有）'))
