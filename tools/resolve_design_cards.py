"""Resolve design pointer cards against the paper's JATS XML into ordinary design cards.

A pointer card (docs/assets/families/design/pointers/<id>.json, kind "design_pointer_card") is a design card in
which no measured value is typed in. Each measured entry says where the value stands in the paper instead:

  table cell   {"table": "Table 1", "row": "NO3^-", "column": "BnBU"}
               the value is the rendered cell (tools/jats.py), so it is read, not transcribed;
  prose quote  {"section": "...", "quote": "...", "display": "15", "subject": "UTSA-16(Co)"}
               the quote must occur exactly once in that section, the display must stand in the quote as a whole
               number, and the nearest candidate name printed before the quote must be the subject - so a number
               cannot be pinned on the wrong candidate. The quote is kept short: numbers, not the paper's prose.

The resolved card (docs/assets/families/design/resolved/<id>.json) is an ordinary design_card that
task_families/paper_design.py builds unchanged: value, display, bound and locator are filled in by code, and
the pointer, the XML path and the hashes of the pointer card and the XML are kept for audit. The XML stays in
inputs/ (not in the repository), so resolving needs the local copy; building questions from a resolved card
does not. checkers/paper_sources.py re-reads every pointer with its own parser.

    python tools/resolve_design_cards.py            # resolve every pointer card, then run the independent check
"""
import argparse
import copy
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import jats  # noqa: E402
from task_families.paper_design import EXPONENT, MANTISSA, parse_display  # noqa: E402

POINTERS = 'assets/families/design/pointers'
RESOLVED = 'assets/families/design/resolved'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def exact_value(display):
    """The printed number as the nearest float to its decimal value (5.1 × 10^5 -> 510000.0, not 509999.99...)."""
    exponent = EXPONENT.search(display)
    return float(Decimal(MANTISSA.match(display).group(2)) * Decimal(10) ** (int(exponent.group(1)) if exponent else 0))


def standalone(display, quote):
    """Positions where display occurs in quote not glued to further digits or a decimal point."""
    return [m.start() for m in re.finditer(re.escape(display), quote)
            if not re.match(r'[\d.]', quote[m.end():m.end() + 1]) and not re.search(r'[\d.]$', quote[:m.start()])]


def nearest_subject(text, before, names):
    """The candidate name printed last before position `before` (whole-word match), or None."""
    best = None
    for name in names:
        for m in re.finditer(re.escape(name), text[:before]):
            if not re.match(r'[A-Za-z0-9]', text[m.end():m.end() + 1]) and (best is None or m.start() > best[0]):
                best = (m.start(), name)
    return best[1] if best else None


def misreadable(display):
    """True for printed numbers the shared parser would misread: '× 10' with no exponent (it reads ×1) and
    thousands separators ('13,800' reads 13). Such values are refused until the parser handles them."""
    return bool(re.search(r'×\s*10(?!\s*\^)', display) or re.match(r'\(?\s*[<>]?\s*\d{1,3},\d{3}', display))


def resolve_entry(xml, names, pointer):
    if 'table' in pointer:
        display = jats.cell(xml, pointer['table'], pointer['row'], pointer['column'], pointer.get('row_column'))
        name = lambda c: c if isinstance(c, str) else ' / '.join(c)
        locator = '%s, row %s, column %s' % (pointer['table'], pointer['row'], name(pointer['column']))
        if pointer.get('row_column') is not None:
            locator += ' (row label in column %s)' % name(pointer['row_column'])
    else:
        jats.quote(xml, pointer['section'], pointer['quote'])
        display = pointer['display']
        if len(standalone(display, pointer['quote'])) != 1:
            raise ValueError('%r does not stand exactly once in the quote %r' % (display, pointer['quote']))
        text = jats.section(xml, pointer['section'])
        subject = nearest_subject(text, text.index(pointer['quote']) + pointer['quote'].index(display), names)
        if subject != pointer['subject']:
            raise ValueError('Nearest candidate before %r is %r, not %r' % (pointer['quote'], subject, pointer['subject']))
        locator = 'Section "%s": "%s"' % (pointer['section'], pointer['quote'])
    if misreadable(display):
        raise ValueError('%r is a printed form the number parser misreads; not usable yet' % display)
    bound, _ = parse_display(display)
    entry = dict(value=exact_value(display), display=display, locator=locator, source=pointer)
    if bound:
        entry['bound'] = bound
    return entry


def resolve(rel, root=ROOT):
    raw = (root / 'docs' / rel).read_bytes()
    card = json.loads(raw.decode('utf-8'))
    if card.get('kind') != 'design_pointer_card':
        raise ValueError('Not a design pointer card: ' + rel)
    xml_raw = (root / card['paper_xml']['path']).read_bytes()
    if sha256(xml_raw) != card['paper_xml']['sha256']:
        raise ValueError('Paper XML differs from the copy the pointers were written against: ' + card['paper_xml']['path'])
    xml = jats.load(root / card['paper_xml']['path'])
    names = sorted({c['paper_name'] for c in card['candidates'] if c.get('paper_name')})
    out = copy.deepcopy(card)
    out['kind'] = 'design_card'
    for c in out['candidates']:
        c['measured'] = {k: resolve_entry(xml, names, p) for k, p in c['measured'].items()}
    out['resolved_from'] = dict(pointer_card=rel, pointer_sha256=sha256(raw), paper_xml=card['paper_xml']['path'],
                                paper_xml_sha256=card['paper_xml']['sha256'], tool='tools/resolve_design_cards.py')
    return out


def dump(card):
    return (json.dumps(card, ensure_ascii=False, indent=1) + '\n').encode('utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check-only', action='store_true', help='compare with the stored resolved cards, write nothing')
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    from checkers import paper_sources
    failed = 0
    for path in sorted((ROOT / 'docs' / POINTERS).glob('*.json')):
        rel = '%s/%s' % (POINTERS, path.name)
        target = ROOT / 'docs' / RESOLVED / path.name
        data = dump(resolve(rel))
        if target.exists() and target.read_bytes() != data:
            print('DIFFERS  %s (resolved cards are append-only: give the card a new id instead)' % target.name)
            failed += 1
            continue
        if not target.exists():
            if args.check_only:
                print('MISSING  %s' % target.name)
                failed += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        report = paper_sources.check_card('%s/%s' % (RESOLVED, path.name), ROOT)
        print('%-8s %s %s' % (report['status'].upper(), target.name, report.get('problem', '%d values' % report.get('values', 0))))
        failed += report['status'] != 'pass'
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
