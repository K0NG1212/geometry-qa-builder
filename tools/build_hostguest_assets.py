"""Build the SAMPL9 WP6 host-guest evidence assets (chemistry, 1-10 nm).

Source: SAMPL9 challenge repository (MIT License), https://github.com/samplchallenges/SAMPL9
  * experimental_data/experimental_measurements.csv: ITC binding free energies (Isaacs lab), 1x PBS, pH 7.40,
    298.15 K, all complexes 1:1 (host_guest/WP6/README.md).
  * host_guest/WP6/guest_files/G*.pdb: the challenge's 3D guest structures.
Downloads (with the user's permission) are kept in inputs/sampl9 (not in Git). This script writes
  * docs/assets/families/hostguest/WP6-G<n>.xyz: guest coordinates copied from the PDB files (element from
    columns 77-78, coordinates unchanged, angstrom);
  * docs/assets/families/hostguest/WP6-binding.json: the WP6 rows of the measurement table transcribed
    verbatim (DG, dDG, Ka, dKa, name, SMILES), with the SHA-256 of the downloaded table.
The host is the existing docs/assets/qa/WP6.xyz (SAMPL9 host file).

python tools/build_hostguest_assets.py
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'inputs/sampl9'
OUT = ROOT / 'docs/assets/families/hostguest'
REPO = 'https://github.com/samplchallenges/SAMPL9'


def guest_xyz(pdb_text, name):
    rows = []
    for line in pdb_text.splitlines():
        if line.startswith(('HETATM', 'ATOM')):
            element = line[76:78].strip().capitalize()
            rows.append('%s %s %s %s' % (element, line[30:38].strip(), line[38:46].strip(), line[46:54].strip()))
    return '\n'.join([str(len(rows)), 'SAMPL9 WP6 guest %s (challenge 3D structure; coordinates copied unchanged), angstrom' % name] + rows) + '\n'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    table_path = RAW / 'experimental_data_experimental_measurements.csv'
    table_raw = table_path.read_bytes()
    rows = [r for r in csv.DictReader(table_raw.decode('utf-8').splitlines(), delimiter=';') if r['ID'].startswith('WP6-')]
    guests, files = {}, {}
    for r in rows:
        g = r['ID'].split('-', 1)[1]
        raw = (RAW / ('WP6-%s.pdb' % g)).read_bytes()
        text = guest_xyz(raw.decode('utf-8'), g)
        name = 'WP6-%s.xyz' % g
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
        files[name] = dict(source='%s/blob/main/host_guest/WP6/guest_files/%s.pdb' % (REPO, g), source_sha256=hashlib.sha256(raw).hexdigest(),
                           asset_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(), atoms=int(text.split('\n', 1)[0]))
        guests[g] = dict(name=r['name'], smiles=r['SMILES'], DG_kcal_mol=float(r['DG']), dDG=float(r['dDG']), Ka_per_M=float(r['Ka']),
                         dKa=float(r['dKa']), asset='assets/families/hostguest/' + name)
    evidence = dict(source='%s/blob/main/experimental_data/experimental_measurements.csv' % REPO, license='MIT (SAMPL9 repository)',
                    table_sha256=hashlib.sha256(table_raw).hexdigest(), host='assets/qa/WP6.xyz',
                    conditions='ITC, 1x PBS (137 mM NaCl, 2.7 mM KCl, 10 mM phosphate), pH 7.40, 298.15 K; all complexes 1:1 '
                               '(host_guest/WP6/README.md)',
                    units='DG and dDG in kcal/mol; Ka in 1/M', guests=guests, files=files)
    (OUT / 'WP6-binding.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({g: (v['DG_kcal_mol'], files['WP6-%s.xyz' % g]['atoms']) for g, v in guests.items()}))


if __name__ == '__main__':
    main()
