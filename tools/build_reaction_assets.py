"""Coordinates for the reaction-path families (docs/assets/families/reaction/).

Landscape17 (CC BY 4.0) publishes, for six molecules, every local minimum and transition state plus the
approximate steepest-descent paths connecting them, at omega-B97x/6-31G(d). Its XYZ files carry seven columns
(element, position, force) and an energy in the comment line. This tool copies the azobenzene structures we use
into plain four-column XYZ, which is what the project's parser accepts, and changes nothing else: the published
coordinates are written out digit for digit.

Energies and forces are left out of the published assets on purpose. Every question built on them is purely
geometric, and an energy in the comment line would be a cue the question does not intend to give. The energies
stay on the reviewer side, in sources.json, together with the source file and its hash.

  python tools/build_reaction_assets.py --landscape17 inputs/landscape17/extracted/Landscape17
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/families/reaction'
CITATION = ('Carare, Thiemann, Morrow, Wales, Pyzer-Knapp & Dicks, "Global properties of the energy landscape: '
            'a testing and training arena for machine learned potentials", npj Comput. Mater. (2025), '
            'doi:10.1038/s41524-025-01878-x; dataset Landscape17, doi:10.6084/m9.figshare.29949230')
LICENSE = 'CC BY 4.0 (Landscape17); coordinates copied unchanged, forces and energies not republished'
LEVEL = 'omega-B97x/6-31G(d) (Psi4), as published in Landscape17'

# published asset -> (path inside the Landscape17 tree, what the structure is)
WANTED = {
    'azobenzene-min-0.xyz': ('azobenzene/Conformations/coordsmin_0.xyz', 'local minimum 0'),
    'azobenzene-min-1.xyz': ('azobenzene/Conformations/coordsmin_1.xyz', 'local minimum 1'),
    'azobenzene-ts-0-1.xyz': ('azobenzene/Conformations/coordsts_0_1.xyz', 'transition state connecting minima 0 and 1'),
    'azobenzene-ts-1-1.xyz': ('azobenzene/Conformations/coordsts_1_1.xyz', 'transition state connecting minimum 1 to itself'),
    'azobenzene-ts-0-0-2.xyz': ('azobenzene/Conformations/coordsts_0_0_2.xyz', 'second transition state connecting minimum 0 to itself'),
    'azobenzene-path-01-plus-004.xyz': ('azobenzene/SteepestDescent/01/coordsplus_004.xyz', 'frame 004 of the plus branch of the path from the 0-1 transition state'),
    'azobenzene-path-01-plus-008.xyz': ('azobenzene/SteepestDescent/01/coordsplus_008.xyz', 'frame 008 of the same branch'),
    'azobenzene-path-01-plus-010.xyz': ('azobenzene/SteepestDescent/01/coordsplus_010.xyz', 'frame 010 of the same branch'),
    'azobenzene-path-01-plus-016.xyz': ('azobenzene/SteepestDescent/01/coordsplus_016.xyz', 'frame 016 of the same branch'),
}


def read_source(path):
    """(elements, coordinate strings as printed, energy string) of a Landscape17 XYZ."""
    lines = path.read_text(encoding='utf-8').splitlines()
    count = int(lines[0].strip())
    comment = lines[1]
    if 'forces' not in comment or 'energy=' not in comment:
        raise ValueError('Not a Landscape17 XYZ: ' + str(path))
    energy = comment.split('energy=')[1].split()[0]
    rows = [line.split() for line in lines[2:] if line.strip()]
    if len(rows) != count or any(len(r) != 7 for r in rows):
        raise ValueError('Expected %d rows of element, position and force in %s' % (count, path))
    return [(r[0], r[1], r[2], r[3]) for r in rows], energy


def xyz(rows, what):
    body = ''.join('%s %s %s %s\n' % r for r in rows)
    return ('%d\nAzobenzene, %s, from Landscape17 (CC BY 4.0); %s; coordinates in angstrom exactly as published; '
            'atoms numbered from 1.\n%s' % (len(rows), what, LEVEL, body))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--landscape17', required=True, help='the extracted Landscape17 tree (local, not in the repository)')
    a = p.parse_args()
    tree = Path(a.landscape17)
    OUT.mkdir(parents=True, exist_ok=True)
    record, order = {}, []
    for name, (relative, what) in sorted(WANTED.items()):
        source = tree / relative
        rows, energy = read_source(source)
        new = xyz(rows, what)
        path = OUT / name
        if path.exists() and path.read_text(encoding='utf-8') != new:
            raise SystemExit('Refusing to change existing asset ' + name)
        path.write_text(new, encoding='utf-8', newline='\n')
        order.append(name)
        record[name] = dict(
            source_file='Landscape17/' + relative, structure=what, atoms=len(rows),
            energy_eV=energy, level_of_theory=LEVEL,
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            asset_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        print('%-34s %2d atoms  E = %s eV' % (name, len(rows), energy))
    sources = dict(
        kind='reaction_sources', updated='2026-10-19', citation=CITATION, license=LICENSE,
        dataset='Landscape17 (Figshare doi:10.6084/m9.figshare.29949230), local copy inputs/landscape17/ '
                '(not in the repository; checksums in its SOURCES.md)',
        built_by='python tools/build_reaction_assets.py --landscape17 '
                 'inputs/landscape17/extracted/Landscape17',
        note='仅去掉力列与注释行中的能量，坐标逐位照抄；能量留在本文件供审核侧使用。',
        assets={name: record[name] for name in order})
    (OUT / 'sources.json').write_bytes(
        (json.dumps(sources, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    print('sources.json', len(order), 'assets')


if __name__ == '__main__':
    main()
