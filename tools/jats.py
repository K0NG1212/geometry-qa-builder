"""Read tables and section text out of a JATS full-text XML (Europe PMC fullTextXML).

Used on the generation side to resolve design-card pointers (tools/resolve_design_cards.py): a measured value
is named by where it stands in the paper - a table cell, or a verbatim quote inside a section - and the value is
read from there instead of being typed in. checkers/paper_sources.py re-reads the same places with its own
parser; it must not import this module.

Rendering rules, the same for table cells, header labels and section text:
  * <xref> (citation and footnote markers) is dropped;
  * <sup>x</sup> becomes "^x"; square brackets inside a superscript are dropped (a footnote marker glued to an
    exponent, "10<sup>7[</sup><xref/><sup>]</sup>", reads "10^7"), and so is a superscript left empty;
    a minus sign or en dash inside a superscript becomes "-" ("M<sup>−1</sup>" reads "M^-1"); a superscript nested
    in a superscript adds no second caret (some publishers wrap exponents twice: "cm<sup><sup>–3</sup></sup>" reads
    "cm^-3");
  * <sub>x</sub> is kept as plain text ("NO<sub>3</sub>" reads "NO3");
  * soft hyphens (U+00AD) are removed and runs of whitespace collapse to one space.
XML entities are decoded by the parser ("&gt; 16" reads "> 16").
"""
import xml.etree.ElementTree as ET

SKIP = {'xref'}
NOT_PROSE = {'table-wrap', 'fig', 'supplementary-material', 'title', 'label'}
SUP_DASHES = str.maketrans({'−': '-', '–': '-'})


def load(path):
    return ET.parse(str(path)).getroot()


def _text(elem, skip, in_sup=False):
    parts = [elem.text or '']
    for child in elem:
        tag = child.tag
        if tag in SKIP or tag in skip:
            pass
        elif tag == 'sup':
            inner = _text(child, skip, True).replace('[', '').replace(']', '').strip().translate(SUP_DASHES)
            if inner:
                parts.append(inner if in_sup else '^' + inner)
        else:
            parts.append(_text(child, skip, in_sup))
        parts.append(child.tail or '')
    return ''.join(parts)


def render(elem, skip=()):
    return ' '.join(_text(elem, set(skip)).replace('­', '').split())


def _label(wrap):
    lab = wrap.find('label')
    return render(lab) if lab is not None else wrap.get('id')


def table(root, label):
    """The table whose <label> renders to `label`, as a grid of rendered cells with row/col spans expanded."""
    wraps = [w for w in root.iter('table-wrap') if _label(w) == label]
    if len(wraps) != 1:
        raise ValueError('%d tables labelled %r' % (len(wraps), label))
    grid, pending = [], {}                       # pending: column -> (text, rows still to fill)
    for tr in wraps[0].iter('tr'):
        row, col = [], 0
        cells = list(tr)
        while cells or col in pending:
            if col in pending:
                text, left = pending.pop(col)
                row.append(text)
                if left > 1:
                    pending[col] = (text, left - 1)
                col += 1
                continue
            cell = cells.pop(0)
            text = render(cell)
            for _ in range(int(cell.get('colspan', '1'))):
                if int(cell.get('rowspan', '1')) > 1:
                    pending[col] = (text, int(cell.get('rowspan')) - 1)
                row.append(text)
                col += 1
        grid.append(row)
    if len({len(r) for r in grid}) != 1:
        raise ValueError('Table %r is not rectangular after expanding spans' % label)
    return grid


def header_path(column):
    """A column is named by its header text, or by a list of header texts from the top row down when the table has
    several header rows (["Flux", "Methanol"]); the length of the list is the number of header rows."""
    return [column] if isinstance(column, str) else list(column)


def cell(root, label, row, column, row_column=None):
    """The rendered cell in the row labelled `row` and the column whose header path is `column`.

    The row label is read from the first column, or from the column named by `row_column` (same header path form)
    when the first column only numbers the entries. Every label must match exactly one row and one column;
    anything else is refused rather than guessed."""
    grid = table(root, label)
    path = header_path(column)
    depth = len(path)
    find = lambda p: [j for j in range(len(grid[0])) if [grid[k][j] for k in range(depth)] == p]
    cols = find(path)
    if row_column is None:
        key = 0
    else:
        keys = find(header_path(row_column))
        if len(header_path(row_column)) != depth or len(keys) != 1:
            raise ValueError('Table %r: row label column %r not found exactly once' % (label, row_column))
        key = keys[0]
    rows = [i for i in range(depth, len(grid)) if grid[i][key] == row]
    if len(cols) != 1 or len(rows) != 1:
        raise ValueError('Table %r: %d rows labelled %r, %d columns labelled %r' % (label, len(rows), row, len(cols), column))
    return grid[rows[0]][cols[0]]


def section(root, title):
    """Rendered prose of the one <sec> whose title is `title` (subsections included; tables, figures and titles left out)."""
    secs = [s for s in root.iter('sec') if s.find('title') is not None and render(s.find('title')) == title]
    if len(secs) != 1:
        raise ValueError('%d sections titled %r' % (len(secs), title))
    return render(secs[0], skip=NOT_PROSE)


def quote(root, title, text):
    """`text` must occur exactly once in the section; returns it unchanged."""
    n = section(root, title).count(text)
    if n != 1:
        raise ValueError('Quote occurs %d times in section %r: %r' % (n, title, text))
    return text
