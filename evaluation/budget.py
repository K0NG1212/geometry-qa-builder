"""What one pass over the bank costs, and which questions a model cannot be shown at all.

This exists because the bank is not the size it looks. The median question is about 1 200 tokens, but the
137 questions that carry a coordinate dump are between 8 000 and 155 000, and they hold 88% of the tokens;
biology alone is 7.5M of the 10.0M. Two consequences the harness has to handle rather than discover halfway
through a paid run:

  cost     -- a full pass is ~10M input tokens per model, so the bill is set by 16% of the questions.
  context  -- at a 64k window, 53 questions do not fit. They are biology and materials almost entirely, so
              counting them as wrong would make a model look bad at biology for a reason that has nothing
              to do with the model. A question that could not be shown is recorded as oversize and kept out
              of the score's denominator, and every report says how many were dropped per discipline.

Token counts come from tiktoken's cl100k_base. That is the wrong tokenizer for every model we actually
call -- it is here to size and to decide what fits, with a margin, not to bill. The real usage numbers come
back from the API and are what the record stores.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'evaluation' / 'models.json'

# Coordinate text tokenizes at about 1.7 characters per token, prose at about 2.7, so a character-based
# guess is out by a factor of two on exactly the questions that matter. Used only if tiktoken is missing.
CHARS_PER_TOKEN_FALLBACK = 1.9

# A prompt is not the whole request: the chat wrapper, the system message and the reply all take room.
# The fit test leaves this much of the window free.
RESERVE_TOKENS = 1024


def load_models(path=MODELS):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def encoder():
    """cl100k_base, or None. tiktoken downloads its table on first use; a machine without it still gets a
    sized report, marked as estimated from characters."""
    try:
        import tiktoken
        return tiktoken.get_encoding('cl100k_base')
    except Exception:                                   # not installed, or no cached table to load
        return None


def count(text, enc=None):
    if enc is None:
        return int(len(text) / CHARS_PER_TOKEN_FALLBACK)
    return len(enc.encode(text))


def measure(questions, setting='coords', enc=None):
    """Per question: how many tokens its prompt is. The expensive part of a pass, done once."""
    enc = enc if enc is not None else encoder()
    return [dict(id=q.id, family=q.family, domain=q.domain, ability=q.ability,
                 tokens=count(q.prompt(setting), enc))
            for q in questions], enc is not None


def fit(sizes, spec):
    """Split the questions into the ones a model can be shown and the ones it cannot.

    A model with no declared window is treated as fitting everything, and the report says the window was
    not declared rather than implying it was checked.
    """
    window = spec.get('context_tokens')
    if not window:
        return list(sizes), [], None
    room = window - spec.get('max_output_tokens', 0) - RESERVE_TOKENS
    return [s for s in sizes if s['tokens'] <= room], [s for s in sizes if s['tokens'] > room], room


def estimate(sizes, spec, reply_tokens=None):
    """What a pass over `sizes` would cost this model, in its own declared prices.

    Output is billed too, so a reply length has to be assumed; the default is the configured ceiling, which
    makes the figure an upper bound rather than a hopeful one.
    """
    shown, dropped, room = fit(sizes, spec)
    reply = spec.get('max_output_tokens', 0) if reply_tokens is None else reply_tokens
    input_tokens = sum(s['tokens'] for s in shown)
    output_tokens = reply * len(shown)
    rate_in = spec.get('usd_per_million_input')
    rate_out = spec.get('usd_per_million_output')
    cost = None
    if rate_in is not None and rate_out is not None:
        cost = round(input_tokens / 1e6 * rate_in + output_tokens / 1e6 * rate_out, 2)
    return dict(
        model=spec.get('model_id'),
        label=spec.get('label'),
        context_tokens=spec.get('context_tokens'),
        room_for_prompt=room,
        shown=len(shown),
        oversize=len(dropped),
        oversize_ids=[s['id'] for s in dropped],
        oversize_by_domain=tally(dropped, 'domain'),
        input_tokens=input_tokens,
        assumed_output_tokens=output_tokens,
        usd_upper_bound=cost,
        priced_on=spec.get('priced_on'),
        price_source=spec.get('price_source'))


def tally(sizes, key):
    out = {}
    for row in sizes:
        bucket = out.setdefault(row[key], dict(n=0, tokens=0))
        bucket['n'] += 1
        bucket['tokens'] += row['tokens']
    return dict(sorted(out.items()))


def report(questions, specs, setting='coords'):
    """The whole estimate: the bank's own profile, then one row per model."""
    sizes, exact = measure(questions, setting)
    total = sum(s['tokens'] for s in sizes)
    ordered = sorted(sizes, key=lambda s: -s['tokens'])
    heavy = [s for s in sizes if s['tokens'] >= 8000]
    return dict(
        kind='geobench_eval_estimate',
        setting=setting,
        questions=len(sizes),
        token_counts_are_exact=exact,
        tokenizer='cl100k_base' if exact else 'characters/%.1f' % CHARS_PER_TOKEN_FALLBACK,
        total_input_tokens=total,
        median_tokens=sorted(s['tokens'] for s in sizes)[len(sizes) // 2] if sizes else 0,
        largest=[dict(id=s['id'], family=s['family'], tokens=s['tokens']) for s in ordered[:10]],
        heavy_questions=dict(
            over_8k=len(heavy),
            share_of_tokens=round(sum(s['tokens'] for s in heavy) / total, 4) if total else None),
        by_domain=tally(sizes, 'domain'),
        models=[estimate(sizes, spec) for spec in specs])
