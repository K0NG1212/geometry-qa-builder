"""Small-molecule XYZ assets for the local-geometry enumerators (named bond distance / angle).

  python tools/build_molecule_assets.py      # -> docs/assets/families/molecules/ + sources.json

QM7-X molecules already stored in docs/assets/families/{stereo,conformers}/*.json are written out as one XYZ per
molecule: the first DFTB3+MBD-optimized conformer of stereoisomer i1, coordinates unchanged, atom order as in QM7-X.
Deterministic; nothing is downloaded. SAMPL9 guests and hosts are used directly from their existing XYZ files.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/families/molecules'
FORMULA_ORDER = ('C', 'H', 'N', 'O', 'S', 'Cl')


def formula(elements):
    counts = {e: elements.count(e) for e in set(elements)}
    order = [e for e in FORMULA_ORDER if e in counts] + sorted(e for e in counts if e not in FORMULA_ORDER)
    return ''.join('%s%s' % (e, counts[e] if counts[e] > 1 else '') for e in order)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources, seen = {}, set()
    for folder in ('stereo', 'conformers'):
        for path in sorted((ROOT / 'docs/assets/families' / folder).glob('QM7X-*.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            mol = data['molecule']
            if mol in seen:
                continue
            first = next((c for c in data['conformers'] if c.get('isomer', data.get('isomer')) == 'i1'), data['conformers'][0])
            elements = data['elements']
            name = 'QM7X-%s.xyz' % mol
            lines = [str(len(elements)), 'QM7-X molecule %s (%s), conformer %s, DFTB3+MBD-optimized geometry, angstrom'
                     % (mol, formula(elements), first['id'])]
            lines += ['%s %.6f %.6f %.6f' % (e, *p) for e, p in zip(elements, first['xyz'])]
            text = '\n'.join(lines) + '\n'
            (OUT / name).write_text(text, encoding='utf-8', newline='\n')
            seen.add(mol)
            sources[name] = dict(molecule=mol, formula=formula(elements), conformer=first['id'], atoms=len(elements),
                                 derived_from='docs/assets/families/%s/%s' % (folder, path.name),
                                 derived_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                 asset_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(), **data['source'])
    (OUT / 'sources.json').write_text(json.dumps(dict(note='XYZ copies of QM7-X geometries already in the repository; no new download.',
                                                      files=sources), ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(len(sources), 'molecules')


if __name__ == '__main__':
    main()
