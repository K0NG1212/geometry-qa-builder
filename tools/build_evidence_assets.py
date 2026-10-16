"""Coordinates for the evidence-to-conclusion families (docs/assets/families/evidence/).

The evidence cards (*.json in that folder) are transcribed by hand from the papers and checked against the full
texts kept locally in inputs/papers/ (not in the repository; see SOURCES.md there). This tool only writes the two
extra conformers of Altun, Bleda & Trindle (2021) that the hydrogen-bond cards need, copied unchanged from the
SI coordinate tables (CC BY 4.0), and refuses to overwrite a file whose content would change.

  python tools/build_evidence_assets.py --si ../paper-batch-v04-001/materials/hbond-si.txt
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/families/evidence'
SYSTEMS = {'ONE': 'altun2021-ONE.xyz', 'ELEVEN': 'altun2021-ELEVEN.xyz'}
ROW = re.compile(r'^\s*(\d+)\s+([A-Z][a-z]?)(\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+([A-Z][a-z]?)\s*$')


def system_rows(text, name):
    """Rows of one 'System NAME' table of the SI text: (index, element, x, y, z) with x, y, z as printed."""
    head = re.search(r'^\s*SYSTEM\s+%s\s*$' % name, text, re.I | re.M)
    if not head:
        raise ValueError('System not found: ' + name)
    rows = []
    for line in text[head.end():].splitlines():
        m = ROW.match(line)
        if m:
            index, element, label, x, y, z, element2 = m.groups()
            if element != element2 or int(label) != int(index) or int(index) != len(rows) + 1:
                raise ValueError('Unexpected row in %s: %s' % (name, line))
            rows.append((element, x, y, z))
        elif rows and re.match(r'^\s*\S+…|^\s*[A-Z]H|.*distance', line):
            break                                     # the caption line ends the table
    if not rows:
        raise ValueError('No coordinates for ' + name)
    return rows


def xyz(name, rows):
    body = ''.join('%s %s %s %s\n' % r for r in rows)
    return ('%d\nAltun, Bleda & Trindle (2021) SI, system %s; coordinates in angstrom as printed; atoms numbered from 1.\n%s'
            % (len(rows), name, body))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--si', required=True, help='plain-text extraction of the Altun 2021 SI coordinate tables')
    a = p.parse_args()
    text = Path(a.si).read_text(encoding='utf-8', errors='replace')
    OUT.mkdir(parents=True, exist_ok=True)
    for name, file in SYSTEMS.items():
        new = xyz(name, system_rows(text, name))
        path = OUT / file
        if path.exists() and path.read_text(encoding='utf-8') != new:
            raise SystemExit('Refusing to change existing asset ' + file)
        path.write_text(new, encoding='utf-8', newline='\n')
        print(file, len(new.splitlines()) - 2, 'atoms')


if __name__ == '__main__':
    main()
