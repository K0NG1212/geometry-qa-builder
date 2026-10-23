"""Pre-screen candidate papers by the shape of their tables (B2, HANDOFF_2026-10-21 §1).

For every downloaded JATS XML, every table is parsed with tools/jats.py and kept when it looks like a measured
series: at least MIN_ROWS data rows, and at least one column (not the first, which labels the rows) in which
MIN_NUMERIC cells read as numbers and whose header (or the table caption) names a unit or a measured quantity. That is all it checks.
Each kept table is then given a keyword tier (see tier()): 'excluded', 'strong' or 'shape_only'; a paper takes its
best table's tier. It does not decide whether geometry determines the property, whether the rows are structural variants, or
whether the numbers are measured rather than computed: that is B3 and L1.

The XML files are downloaded data: they are only parsed, never executed, and live in their own directory.

    python -I tools/prefilter_tables.py --search runs/paper-search-v01 --xml inputs/paper-candidates --out runs/paper-prefilter-v01
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import jats  # noqa: E402

MIN_ROWS = 4
MIN_NUMERIC = 4
NUMBER = re.compile(r'^[(~∼≈<>≤≥]*\s*[-−–]?\d+(?:\.\d+)?')
UNIT = re.compile(r'\^-\d|\b(?:M|mM|µM|μM|nM|mmol|mol|kJ|kcal|K|°C|nm|Å|pm|%|h|min|s|g|mg|L|bar|mbar|Pa|kPa|MPa|eV|cm|mL|GPU|LMH)\b'
                  r'|[\[(][^\])]*[\])]')
QUANTITY = re.compile(r'\b(?:K_?a|K_?d|K_?i|K_?D|IC50|EC50|ΔG|ΔH|logK|log K|selectivit(?:y|ies)|uptakes?|permeances?|'
                      r'permeabilit(?:y|ies)|rejections?|yields?|T_?m|melting|half-lives|half-life|binding|affinit(?:y|ies)|'
                      r'constants?|capacit(?:y|ies)|flux(?:es)?|conductivit(?:y|ies)|rates?)\b', re.I)

# Captions of tables that hold no measured series of structural variants: refinement statistics, simulation or
# docking set-ups and scores (computed), pharmacokinetics, formulations, method or literature comparisons.
EXCLUDE = re.compile(r'refinement|data collection|crystallographic data|crystal data|simulation|docking|predicted|prediction|'
                     r'pharmacokinetic|composition|formulation|druggability|ADMET|comparison (?:of|with) (?:the )?'
                     r'(?:present|this|other|previous|reported|literature)|reported in (?:the )?literature|'
                     r'model parameters|parameters (?:of|for) the .{0,40}model|fitting parameters|primer|sequences|'
                     r'characteristics of (?:the )?(?:patients|participants)|demographic', re.I)

# Diagnostic only (B2b): papers whose title or kept-table captions read as pharmacology. Counted among strong
# papers to measure query noise; it never changes a status or a tier. A plain "receptor" is not counted:
# supramolecular anion receptors are on topic.
PHARMA = re.compile(r'inhibit|agonist|antagon|kinase|\bdrugs?\b|IC50|\bKi\b|antitumou?r|anti-?cancer|cytotox|'
                    r'antivir|antibacter|antimicrob|pharmacolog|chemokine|in vivo', re.I)


def pharma_like(paper):
    text = (paper.get('title') or '') + ' ' + ' '.join(t['caption'] for t in paper.get('kept', []))
    return bool(PHARMA.search(text))


def tier(caption, measured):
    """'excluded' (caption names a non-measured or off-topic table), 'strong' (a measured quantity is named in the
    caption or a measured column header), else 'shape_only'. Keyword heuristics only: B3 and L1 decide."""
    if EXCLUDE.search(caption):
        return 'excluded'
    if QUANTITY.search(caption) or any(QUANTITY.search(h) for h in measured):
        return 'strong'
    return 'shape_only'


def is_number(cell):
    return bool(NUMBER.match(cell.strip()))


def names_quantity(text):
    return bool(UNIT.search(text) or QUANTITY.search(text))


def measured_columns(grid, caption=''):
    """Header text of every column (after the first) with numbers below it and a unit or measured quantity named in
    its header - or in the caption, for tables whose column headers are the compounds (Rando 2025, Table 1)."""
    header, data = grid[0], grid[1:]
    out = []
    for j in range(1, len(header)):
        numeric = sum(is_number(row[j]) for row in data)
        if numeric >= MIN_NUMERIC and (names_quantity(header[j]) or names_quantity(caption)):
            out.append(header[j])
    return out


def screen(xml_path):
    """Per-paper result: tables found, tables kept (label, caption start, header, rows, measured columns)."""
    root = jats.load(xml_path)
    kept, unparsed, labels = [], [], []
    for wrap in root.iter('table-wrap'):
        label = jats._label(wrap)
        labels.append(label)
        try:
            grid = jats.table(root, label)
        except ValueError as error:
            unparsed.append(dict(label=label, reason=str(error)))
            continue
        cap = wrap.find('caption')
        caption = jats.render(cap) if cap is not None else ''
        cols = measured_columns(grid, caption)
        if len(grid) - 1 >= MIN_ROWS and cols:
            kept.append(dict(label=label, caption=caption[:160], header=grid[0],
                             rows=len(grid) - 1, measured_columns=cols, tier=tier(caption, cols)))
    rank = {'strong': 2, 'shape_only': 1, 'excluded': 0}
    best = max((t['tier'] for t in kept), key=rank.get, default=None)
    return dict(tables=len(labels), kept=kept, unparsed=unparsed, tier=best)


def markdown(rows, status, tiers):
    """Readable list of kept papers, strong tier first: identifiers, title start, and the best table's shape only."""
    rank = {'strong': 0, 'shape_only': 1, 'excluded': 2}
    kept = sorted((r for r in rows if r['status'] == 'kept'), key=lambda r: (rank[r['tier']], r['queries'][0], r['pmcid']))
    lines = ['# Pre-screened candidate papers', '',
             'status: ' + ', '.join('%s %d' % kv for kv in sorted(status.items())),
             'tiers: ' + ', '.join('%s %d' % kv for kv in sorted(tiers.items())), '',
             '| tier | query | PMCID | year | title | table | rows | measured columns |', '|---|---|---|---|---|---|---|---|']
    for r in kept:
        t = max(r['kept'], key=lambda t: (-rank[t['tier']], t['rows']))
        title = (r['title'] or '').replace('|', '/')[:70]
        cols = '; '.join(c.replace('|', '/') for c in t['measured_columns'][:3])
        lines.append('| %s | %s | %s | %s | %s | %s | %d | %s |' % (r['tier'], ','.join(r['queries']), r['pmcid'], r['year'],
                                                                 title, t['label'], t['rows'], cols))
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--search', required=True, help='paper-search run directory (candidates.json)')
    ap.add_argument('--xml', required=True, help='directory holding <PMCID>.xml files')
    ap.add_argument('--out', required=True, help='new run directory')
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    out = ROOT / args.out
    if out.exists():
        raise SystemExit('Refusing to overwrite ' + args.out)
    candidates = json.loads((ROOT / args.search / 'candidates.json').read_text(encoding='utf-8'))
    rows, by_query = [], {}
    for c in candidates:
        path = ROOT / args.xml / ('%s.xml' % c['pmcid'])
        rec = dict(pmcid=c['pmcid'], doi=c.get('doi'), title=c.get('title'), year=c.get('pubYear'),
                   license=c.get('license'), queries=c.get('queries', []), already_used=c.get('already_used'))
        if not path.exists():
            rec['status'] = 'no_xml'
        else:
            try:
                rec.update(screen(path))
                rec['status'] = 'kept' if rec['kept'] else 'no_matching_table' if rec['tables'] else 'no_tables'
            except Exception as error:                 # malformed downloads are recorded, not fatal
                rec.update(status='parse_error', reason='%s: %s' % (type(error).__name__, error))
        rows.append(rec)
        for q in rec['queries']:
            by_query.setdefault(q, {}).setdefault(rec['status'], 0)
            by_query[q][rec['status']] += 1
    status, tiers = {}, {}
    for r in rows:
        status[r['status']] = status.get(r['status'], 0) + 1
        if r['status'] == 'kept':
            tiers[r['tier']] = tiers.get(r['tier'], 0) + 1
            for q in r['queries']:
                by_query[q].setdefault('tier_' + r['tier'], 0)
                by_query[q]['tier_' + r['tier']] += 1
            r['pharma_like'] = pharma_like(r)
    strong_pharma = sum(1 for r in rows if r.get('tier') == 'strong' and r.get('pharma_like'))
    tiers['strong_pharma_like'] = strong_pharma
    out.mkdir(parents=True)
    rule = dict(min_rows=MIN_ROWS, min_numeric=MIN_NUMERIC, number=NUMBER.pattern, unit=UNIT.pattern, quantity=QUANTITY.pattern,
                exclude=EXCLUDE.pattern, pharma_diagnostic=PHARMA.pattern)
    (out / 'prefilter.json').write_text(json.dumps(dict(kind='paper_prefilter_run', search=args.search, xml=args.xml,
                                                        rule=rule, status=status, tiers=tiers, by_query=by_query, papers=rows),
                                                   ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (out / 'candidates.md').write_text(markdown(rows, status, tiers), encoding='utf-8')
    print(json.dumps(dict(status=status, tiers=tiers, by_query=by_query), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
