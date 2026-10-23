"""Independent re-reading of resolved design cards against the paper's JATS XML. No generation code is imported.

tools/resolve_design_cards.py fills every measured value of a design card from a pointer into the paper (a table
cell, or a short quote in a section). This module checks the result with its own reading of the XML (minidom and
an occupancy-map table grid, where the resolver uses ElementTree and a row scan):

  * the XML is byte-identical to the copy the pointers were written against (SHA-256);
  * the resolved card is the pointer card plus filled values: nothing else was changed;
  * every table value is the cell at the named row and column, rendered as the paper prints it;
  * every quoted value stands once in a quote that occurs once in its section, and the nearest candidate name
    printed before it is the candidate it is filed under;
  * value and bound agree with the printed display.

Needs the local XML (inputs/papers/, not in the repository). Whether the right table, column or sentence was
chosen in the first place - that the quoted number means the property the card says it does - is still L1.
"""
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from xml.dom import minidom
from .common import CheckError, need
from .paper_design import parse_display

SKIP = ('xref',)
NOT_PROSE = ('table-wrap', 'fig', 'supplementary-material', 'title', 'label')


def _flat(node, skip, depth=0):
    """depth counts enclosing <sup> elements: only the outermost superscript is marked with a caret."""
    out = []
    for n in node.childNodes:
        if n.nodeType == n.TEXT_NODE or n.nodeType == n.CDATA_SECTION_NODE:
            out.append(n.data)
        elif n.nodeType == n.ELEMENT_NODE and n.tagName not in SKIP and n.tagName not in skip:
            sup = n.tagName == 'sup'
            inner = _flat(n, skip, depth + sup)
            if sup:
                inner = re.sub(r'[\[\]]', '', inner).strip().replace('−', '-').replace('–', '-')
                out.append(('^' if inner and depth == 0 else '') + inner)
            else:
                out.append(inner)
    return ''.join(out)


def text_of(node, skip=()):
    return re.sub(r'\s+', ' ', _flat(node, skip).replace('­', '')).strip()


def children(node, tag):
    return [n for n in node.childNodes if n.nodeType == n.ELEMENT_NODE and n.tagName == tag]


def grid_of(doc, label):
    wraps = [w for w in doc.getElementsByTagName('table-wrap')
             if (text_of(children(w, 'label')[0]) if children(w, 'label') else w.getAttribute('id')) == label]
    need(len(wraps) == 1, '%d tables labelled %r' % (len(wraps), label))
    taken, r = {}, 0
    for tr in wraps[0].getElementsByTagName('tr'):
        c = 0
        for cell in [n for n in tr.childNodes if n.nodeType == n.ELEMENT_NODE and n.tagName in ('td', 'th')]:
            while (r, c) in taken:
                c += 1
            rs, cs = int(cell.getAttribute('rowspan') or 1), int(cell.getAttribute('colspan') or 1)
            for i in range(rs):
                for j in range(cs):
                    taken[(r + i, c + j)] = text_of(cell)
            c += cs
        r += 1
    width = 1 + max(j for _, j in taken)
    need(all((i, j) in taken for i in range(r) for j in range(width)), 'Table %r has holes after expanding spans' % label)
    return [[taken[(i, j)] for j in range(width)] for i in range(r)]


def section_text(doc, title):
    secs = [s for s in doc.getElementsByTagName('sec') if children(s, 'title') and text_of(children(s, 'title')[0]) == title]
    need(len(secs) == 1, '%d sections titled %r' % (len(secs), title))
    return text_of(secs[0], NOT_PROSE)


def columns_named(grid, name):
    """Column indices whose header cells, read down the header rows, equal `name` (a string: one header row)."""
    path = [name] if isinstance(name, str) else list(name)
    return [j for j in range(len(grid[0])) if all(grid[k][j] == h for k, h in enumerate(path))], len(path)


# Printed forms the shared number parser would misread: "× 10" with no exponent (read as ×1) and thousands separators
# ("13,800" read as 13). Refused here until the parser handles them.
UNSAFE_DISPLAY = re.compile(r'×\s*10(?!\s*\^)|^\(?\s*[<>]?\s*\d{1,3},\d{3}')


def check_entry(doc, names, cand, prop, entry):
    p = entry['source']
    need(not UNSAFE_DISPLAY.search(entry['display']), '%s/%s: %r is a printed form the number parser misreads'
         % (cand, prop, entry['display']))
    if 'table' in p:
        grid = grid_of(doc, p['table'])
        cols, depth = columns_named(grid, p['column'])
        key = 0
        if p.get('row_column') is not None:
            keys, key_depth = columns_named(grid, p['row_column'])
            need(len(keys) == 1 and key_depth == depth, '%s/%s: row label column %r not unique' % (cand, prop, p['row_column']))
            key = keys[0]
        rows = [i for i in range(depth, len(grid)) if grid[i][key] == p['row']]
        need(len(rows) == 1 and len(cols) == 1, '%s/%s: row %r or column %r not unique' % (cand, prop, p['row'], p['column']))
        need(grid[rows[0]][cols[0]] == entry['display'], '%s/%s: the paper prints %r, the card has %r'
             % (cand, prop, grid[rows[0]][cols[0]], entry['display']))
    else:
        text = section_text(doc, p['section'])
        need(text.count(p['quote']) == 1, '%s/%s: quote found %d times in %r' % (cand, prop, text.count(p['quote']), p['section']))
        need(p['display'] == entry['display'], '%s/%s: display differs from the pointer' % (cand, prop))
        hits = [i for i in range(len(p['quote'])) if p['quote'].startswith(entry['display'], i)
                and not (i > 0 and re.match(r'[\d.]', p['quote'][i - 1]))
                and not re.match(r'[\d.]', p['quote'][i + len(entry['display']):][:1])]
        need(len(hits) == 1, '%s/%s: %r does not stand once in the quote' % (cand, prop, entry['display']))
        at = text.index(p['quote']) + hits[0]
        found = []
        for name in names:
            start = text.rfind(name, 0, at)
            while start >= 0 and re.match(r'[A-Za-z0-9]', text[start + len(name):][:1]):
                start = text.rfind(name, 0, start)
            if start >= 0:
                found.append((start, name))
        need(found and max(found)[1] == p['subject'], '%s/%s: nearest candidate before the quote is %r, not %r'
             % (cand, prop, max(found)[1] if found else None, p['subject']))
    bound, value = parse_display(entry['display'])
    need(bound == entry.get('bound') and value == Decimal(repr(entry['value'])),
         '%s/%s: stored value or bound disagrees with %r' % (cand, prop, entry['display']))


def check_card(rel, root, xml_path=None):
    """Report dict; status 'pass' only if every measured value is re-read from the paper as stored."""
    report = dict(card=rel)
    try:
        root = Path(root)
        card = json.loads((root / 'docs' / rel).read_text(encoding='utf-8'))
        src = card.get('resolved_from')
        need(card.get('kind') == 'design_card' and src, 'Not a resolved design card')
        raw_pointer = (root / 'docs' / src['pointer_card']).read_bytes()
        need(hashlib.sha256(raw_pointer).hexdigest() == src['pointer_sha256'], 'Pointer card changed since resolving')
        pointer = json.loads(raw_pointer.decode('utf-8'))
        need(pointer['paper_xml'] == dict(path=src['paper_xml'], sha256=src['paper_xml_sha256']), 'XML record differs')
        xml = Path(xml_path) if xml_path else root / src['paper_xml']
        need(xml.exists(), 'Paper XML not available locally: ' + src['paper_xml'])
        raw = xml.read_bytes()
        need(hashlib.sha256(raw).hexdigest() == src['paper_xml_sha256'], 'Paper XML hash mismatch: ' + src['paper_xml'])
        bare = lambda d: {k: v for k, v in d.items() if k not in ('kind', 'candidates', 'resolved_from')}
        need(bare(card) == bare(pointer), 'Resolved card differs from its pointer card outside the measured values')
        need(len(card['candidates']) == len(pointer['candidates']), 'Candidate count differs')
        doc = minidom.parseString(raw)
        names = sorted({c['paper_name'] for c in pointer['candidates'] if c.get('paper_name')})
        n = 0
        for c, pc in zip(card['candidates'], pointer['candidates']):
            need({k: v for k, v in c.items() if k != 'measured'} == {k: v for k, v in pc.items() if k != 'measured'},
                 'Candidate %s differs from its pointer card' % c['id'])
            need(set(c['measured']) == set(pc['measured']), 'Candidate %s: measured properties differ' % c['id'])
            for prop, entry in c['measured'].items():
                need(entry.get('source') == pc['measured'][prop], '%s/%s: pointer differs' % (c['id'], prop))
                check_entry(doc, names, c['id'], prop, entry)
                n += 1
        report.update(status='pass', values=n)
    except CheckError as error:
        report.update(status='fail', problem=str(error))
    except (KeyError, ValueError, OSError) as error:
        report.update(status='fail', problem='%s: %s' % (type(error).__name__, error))
    return report
