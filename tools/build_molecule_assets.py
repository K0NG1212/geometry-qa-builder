"""Small-molecule XYZ assets for the local-geometry enumerators (named bond distance / angle).

  python tools/build_molecule_assets.py      # -> docs/assets/families/molecules/ + sources.json

QM7-X molecules already stored in docs/assets/families/{stereo,conformers}/*.json are written out as one XYZ per
molecule: the first DFTB3+MBD-optimized conformer of stereoisomer i1, coordinates unchanged, atom order as in QM7-X.
The force-path assets also supply optimized reference structures; identical references shared by displacement
assets are exported once. The local SAMPL9 bCD guest PDB files are copied with their atom order and printed
coordinates unchanged. Charge is checked against the measurement-table SMILES and PDB CONECT records.
Deterministic; nothing is downloaded. Existing XYZ files must remain byte-for-byte unchanged.
"""
import csv
import hashlib
import re
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import license_note  # noqa: E402
from tools.build_hostguest_assets import guest_xyz  # noqa: E402
from task_families import kit  # noqa: E402

OUT = ROOT / 'docs/assets/families/molecules'
FORMULA_ORDER = ('C', 'H', 'N', 'O', 'S', 'Cl')


def formula(elements):
    counts = {e: elements.count(e) for e in set(elements)}
    order = [e for e in FORMULA_ORDER if e in counts] + sorted(e for e in counts if e not in FORMULA_ORDER)
    return ''.join('%s%s' % (e, counts[e] if counts[e] > 1 else '') for e in order)



def write_asset(name, text):
    """Refuse to silently change a published coordinate asset; validate with the production XYZ reader."""
    kit.parse_xyz(text)
    blob = text.encode('utf-8')
    path = OUT / name
    if path.exists() and path.read_bytes() != blob:
        raise ValueError('Refusing to change existing molecule asset ' + name)
    path.write_bytes(blob)
    return hashlib.sha256(blob).hexdigest()


def force_references():
    """One asset per optimized reference, not per displacement paired with that reference."""
    refs = {}
    for path in sorted((ROOT / 'docs/assets/families/force-path').glob('QM7X-*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        key = (data['molecule'], data['reference_id'])
        payload = (data['elements'], data['reference_xyz'])
        if key in refs and refs[key][0] != payload:
            raise ValueError('Conflicting coordinates for the same QM7-X reference: ' + data['reference_id'])
        refs.setdefault(key, (payload, data, []))[2].append(path)
    return refs


def add_local_sources(sources, seen):
    for (mol, conformer), ((elements, points), data, paths) in sorted(force_references().items()):
        if mol in seen:
            continue
        # reference_id contains the isomer, conformer and opt dimensions; displacement d1/d2 is not part of this asset.
        suffix = conformer.split('-i', 1)[1]
        name = 'QM7X-%s-i%s.xyz' % (mol, suffix)
        text = '\n'.join([str(len(elements)),
            'QM7-X molecule %s (%s), conformer %s, DFTB3+MBD-optimized geometry, angstrom'
            % (mol, formula(elements), conformer)] +
            ['%s %.6f %.6f %.6f' % (e, *p) for e, p in zip(elements, points)]) + '\n'
        sources[name] = dict(molecule=mol, formula=formula(elements), conformer=conformer, atoms=len(elements),
            derived_from=paths[0].relative_to(ROOT).as_posix(),
            derived_sha256=hashlib.sha256(paths[0].read_bytes()).hexdigest(),
            reference_inputs=[dict(path=p.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                              for p in paths],
            deduplication='Identical elements and reference_xyz for one reference_id are exported once.',
            asset_sha256=write_asset(name, text), **data['source'])
        seen.add(mol)

    table = ROOT / 'inputs/sampl9/experimental_data_experimental_measurements.csv'
    raw_table = table.read_bytes()
    skipped = {}
    rows = [r for r in csv.DictReader(raw_table.decode('utf-8').splitlines(), delimiter=';')
            if r['ID'].startswith('bCD-')]
    for row in sorted(rows, key=lambda r: r['ID']):
        ident = row['ID']
        path = ROOT / 'inputs/sampl9' / (ident + '.pdb')
        raw = path.read_bytes()
        pdb = raw.decode('utf-8')
        atoms, neighbors = {}, {}
        for line in pdb.splitlines():
            if line.startswith(('ATOM', 'HETATM')):
                atoms[int(line[6:11])] = line[76:78].strip().capitalize()
            elif line.startswith('CONECT'):
                ids = [int(line[i:i + 5]) for i in range(6, len(line), 5) if line[i:i + 5].strip()]
                neighbors.setdefault(ids[0], set()).update(ids[1:])
        # These five published SMILES use [NH+] for protonated nitrogens. Do not infer a different protonation state.
        charge = row['SMILES'].count('[NH+]')
        protonated = sum(e == 'N' and len(neighbors.get(i, ())) == 4 and
                         any(atoms[j] == 'H' for j in neighbors.get(i, ())) for i, e in atoms.items())
        if charge != protonated:
            skipped[ident] = dict(reason='Measurement-table SMILES has %d [NH+] atoms but the PDB CONECT records '
                                  'have %d four-coordinate N atoms bonded to H; protonation is not reconciled.'
                                  % (charge, protonated), source_sha256=hashlib.sha256(raw).hexdigest(),
                                  table_smiles=row['SMILES'])
            continue
        text = guest_xyz(pdb, ident).replace('SAMPL9 WP6 guest', 'SAMPL9 bCD guest', 1)
        elements, points = kit.parse_xyz(text)
        name = 'SAMPL9-%s.xyz' % ident
        sources[name] = dict(molecule=ident, name=row['name'], formula=formula(elements), atoms=len(elements),
            source='https://github.com/samplchallenges/SAMPL9', source_directory='host_guest/bCD/guest_files',
            derived_from=path.relative_to(ROOT).as_posix(), derived_sha256=hashlib.sha256(raw).hexdigest(),
            asset_sha256=write_asset(name, text), license='CC BY 4.0',
            license_statement=license_note.statement('sampl9-readme'),
            charge=charge, charge_basis='[NH+] count in experimental_data/experimental_measurements.csv SMILES; '
                                       'confirmed by four-coordinate N-H atoms in the PDB CONECT records.',
            smiles=row['SMILES'], table_row=ident, table_sha256=hashlib.sha256(raw_table).hexdigest(),
            table_source='https://github.com/samplchallenges/SAMPL9/blob/main/experimental_data/experimental_measurements.csv',
            handling='PDB element and coordinate fields copied unchanged; energies and experimental affinities not included.')
    return skipped


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
            write_asset(name, text)
            seen.add(mol)
            sources[name] = dict(molecule=mol, formula=formula(elements), conformer=first['id'], atoms=len(elements),
                                 derived_from='docs/assets/families/%s/%s' % (folder, path.name),
                                 derived_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                 asset_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(), **data['source'])
    skipped = add_local_sources(sources, seen)
    (OUT / 'sources.json').write_text(json.dumps(dict(note='XYZ copies of QM7-X and SAMPL9 geometries already stored locally; no new download.',
                                                      license_statement=license_note.statement('zenodo-qm7x'),
                                                      license_statement_covers='QM7X-*.xyz; SAMPL9 files carry their own license_statement.',
                                                      skipped=skipped, files=sources), ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(len(sources), 'molecules')


if __name__ == '__main__':
    main()
