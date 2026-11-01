"""Who answers the exam.

Only answer-without-looking baselines are built in. They are not filler: four-way choice makes a quarter of
the score free, and a real model's number means nothing until it is read against the floor measured on the
same questions in the same run.

No provider here calls a model. Wiring a real one needs an API key, a budget and the user's go-ahead, and
whatever runs must record its own name -- a record that says claude or gpt when a mock produced it would be
a fabricated result.
"""
import hashlib

LABELS = ('A', 'B', 'C', 'D')


class Mock:
    """A baseline. `calls` stays at zero because nothing is called."""

    model_calls = 0
    is_model = False

    def __init__(self, name, pick):
        self.name = name
        self.pick = pick

    def answer(self, question, prompt):
        if question.form == 'numeric':
            return '0'
        return self.pick(question)


def seeded_label(question):
    """A fixed label per question, from the id alone. Deterministic, so the floor is the same every run."""
    digest = hashlib.sha256(question.id.encode('utf-8')).digest()
    return LABELS[digest[0] % 4]


BASELINES = {
    'always-a': lambda: Mock('baseline-always-a', lambda q: 'A'),
    'seeded': lambda: Mock('baseline-seeded', seeded_label),
    'blank': lambda: Mock('baseline-blank', lambda q: ''),
}


def get(name):
    if name in BASELINES:
        return BASELINES[name]()
    raise ValueError(
        '没有这个作答者：%s。目前只内置基线 %s。要跑真模型得先接一个 provider：需要 API 密钥与预算，'
        '本仓库不内置密钥，也不会自己联网；接好以后 provider 必须如实报自己的名字和调用次数。'
        % (name, '、'.join(sorted(BASELINES))))
