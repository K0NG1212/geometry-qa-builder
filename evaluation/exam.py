"""The exam a model sits: the student packets of one run, and nothing else.

A model may see exactly what a question's folder calls student/ -- the question, the scope line, the
attachments and the response format. The teacher side is loaded by scoring.py instead, so a prompt cannot
carry it by accident. The instance id is teacher side too: some ids spell out their own answer
(FA-SREL-7029-SAME), and they are printed on the published workbench links, so an id never enters a prompt.
Questions are addressed by their catalog id (BND016), which says nothing about the answer.

Two forms of the same question exist. The choice form offers four labelled options; the numeric form asks for
the number itself and exists for 547 of the 988, and the pair is what tells us how much of a score is
four-way guessing.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# What evidence a model is given. The difference between two settings is the measurement, so each one states
# exactly what changes; a setting that cannot be served yet must say so rather than quietly degrade.
SETTINGS = {
    'coords': dict(
        label='坐标文本，不许跑代码',
        instruction='Work from the supplied text alone. Do not write or execute code; reason it out.',
        available=True),
    'coords+code': dict(
        label='坐标文本，可以跑代码',
        instruction='You may write and execute code to analyse the supplied files.',
        available=True),
    'renders': dict(
        label='只给渲染图，不给坐标',
        instruction='',
        available=False,
        unavailable_because='渲染器还没写；且只有 602/988 道题带原子级三维坐标附件（xyz 或 pdb 片段）可直接渲染，报分时必须说明是子集'),
}


class Question:
    """One question as a model will receive it, plus the labels a report groups by."""

    def __init__(self, id, instance, family, ability, domain, form, text, scope, inputs, options, response):
        self.id = id                  # catalog id, e.g. BND016 -- what reports and the answer key use
        self.instance = instance      # teacher side: never put this in a prompt
        self.family = family
        self.ability = ability
        self.domain = domain
        self.form = form              # 'choice' or 'numeric'
        self.text = text
        self.scope = scope
        self.inputs = inputs          # [{'name','format','unit','text'}]
        self.options = options        # [{'label','value','unit'}], empty for the numeric form
        self.response = response

    def prompt(self, setting):
        """The whole of what is sent. Everything in it comes from the student packet."""
        rule = SETTINGS[setting]
        if not rule['available']:
            raise ValueError('设置 %s 还不能用：%s' % (setting, rule['unavailable_because']))
        parts = [self.text, '', 'Scope: ' + self.scope, '']
        for item in self.inputs:
            parts += ['File %s (%s, %s):' % (item['name'], item['format'], item['unit']), item['text'], '']
        if self.options:
            parts += ['%s. %s' % (o['label'], value_of(o)) for o in self.options] + ['']
        parts += [rule['instruction'], 'Answer with ' + response_rule(self.response)]
        return '\n'.join(parts)


def value_of(option):
    return '%s %s' % (option['value'], option['unit']) if option.get('unit') else str(option['value'])


def response_rule(response):
    if isinstance(response, str):
        return response + ', and nothing else.'
    return '%s (%s), and nothing else.' % (response['value'], response['unit'])


def plain_name(item, instance):
    """An attachment named after its instance would carry the id into the prompt, and some ids spell their
    own answer. 56 questions are named that way (FA-PEAK-B5H9-cell.txt); no question text refers to such a
    name, so the prompt gives the file a plain one and keeps the published name for the record."""
    name = item['name']
    if instance in name:
        name = name.replace(instance + '-', '').replace(instance, '').strip('-_') or 'input'
    return dict(item, name=name, published_name=item['name'])


def read_asset(item):
    """An attachment too large to inline is stored under docs/; its recorded hash must still match."""
    path = ROOT / 'docs' / item['url']
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != item['sha256']:
        raise ValueError('附件哈希对不上：%s' % item['url'])
    return raw.decode('utf-8')


def load(form='choice', ids=None, root=ROOT):
    """Every admitted question of the published run, in the asked-for form.

    The numeric form exists for part of the bank only; asking for it returns that part, and the caller
    reports how many questions it covered rather than pretending the two forms are the same exam.
    """
    workbench = json.loads((root / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
    catalog = json.loads((root / 'docs/data/catalog.json').read_text(encoding='utf-8'))
    admitted = {q['familyInstance']: q for q in catalog['questions']
                if q.get('lifecycle') == 'active' and q.get('familyInstance')}
    packets = {p['id']: p for p in workbench['student_packets']}
    numeric = {p['id']: p for p in workbench['numeric_student_packets']}

    out = []
    for instance, entry in sorted(admitted.items(), key=lambda kv: kv[1]['id']):
        if ids and entry['id'] not in ids:
            continue
        choice = packets[instance]
        packet = choice if form == 'choice' else numeric.get('N-' + instance)
        if packet is None:
            continue                                  # no numeric form for this question
        inputs = [plain_name(dict(i, text=i.get('text') if 'text' in i else read_asset(i)), instance)
                  for i in (choice['inputs'] or [])]  # the numeric form reuses the choice form's files
        out.append(Question(id=entry['id'], instance=instance, family=choice['family'],
                            ability=choice['ability'], domain=entry['domain'], form=form,
                            text=packet['question'], scope=packet['scope'], inputs=inputs,
                            options=choice['options'] if form == 'choice' else [],
                            response=packet['response_format']))
    return out


def fingerprint(questions):
    """Which exam a report is about: the ids and the prompts' content, hashed."""
    text = '\n'.join('%s\t%s' % (q.id, hashlib.sha256(q.prompt('coords').encode('utf-8')).hexdigest())
                     for q in questions)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
