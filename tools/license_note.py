"""The licence wording a source publishes on its own page, for the sources.json an asset builder writes.

One record holds every statement (docs/data/license-statements.json, read from the pages on 2026-11-02); builders copy the
block from here rather than repeating the quote, and tests/test_license.py checks the copies word for word.
"""
import json
from collections import OrderedDict
from pathlib import Path

RECORD = 'docs/data/license-statements.json'
ROOT = Path(__file__).resolve().parents[1]
KEYS = ('license', 'url', 'read_on', 'quote', 'quote_is', 'obligation')


def statement(statement_id):
    """The license_statement block for one statement id, in the order the sources.json files already use."""
    entry = json.loads((ROOT / RECORD).read_text(encoding='utf-8'))['statements'][statement_id]
    block = OrderedDict(statement=statement_id, record=RECORD)
    for key in KEYS:
        if entry.get(key):
            block[key] = entry[key]
    return block
