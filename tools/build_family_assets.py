"""Extract small public inputs for task families from the local QM7-X file 8000.hdf5.

QM7-X (Hoja et al., Sci. Data 8, 43 (2021); Zenodo 10.5281/zenodo.4288677) is CC BY 4.0.
The hdf5 file is not in Git; this script records what was taken so the committed
JSON assets can be traced. Existing assets are never overwritten.

python tools/build_family_assets.py --hdf5 PATH/8000.hdf5 --force 7001 7002 7035 --conformers 7050 7206 7049
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/families'
SYMBOL = {1: 'H', 6: 'C', 7: 'N', 8: 'O', 16: 'S', 17: 'Cl'}
SOURCE = dict(dataset='QM7-X', doi="https://www.nature.com/articles/s41597-021-00812-2",
              record="https://zenodo.org/records/4288677", license='CC BY 4.0', file='8000.xz / 8000.hdf5')


def write(path, data):
    if path.exists():
        raise SystemExit('Refusing to overwrite ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8', newline='\n')


def check_published(qa_prefix, data):
    """Where an existing QA used the same pair, confirm identical coordinates."""
    for key, suffix in (('reference_xyz', 'A'), ('displaced_xyz', 'B')):
        hits = sorted((ROOT / 'docs/assets/qa').glob('%s*-%s.xyz' % (qa_prefix, suffix)))
        if not hits:
            return None
        rows = [l.split()[1:] for l in hits[0].read_text().splitlines()[2:] if l.strip()]
        if max(abs(float(x) - y) for r, p in zip(rows, data[key]) for x, y in zip(r, p)) > 1e-5:
            raise SystemExit('Published asset mismatch for ' + qa_prefix)
    return qa_prefix


def main(args):
    import h5py
    digest = hashlib.sha256(Path(args.hdf5).read_bytes()).hexdigest()
    f = h5py.File(args.hdf5, 'r')
    published = {'7001': 'QNP001', '7002': 'QNI001', '7035': 'QNI002'}
    for mol in args.force or []:
        ref, disp = f[mol]['Geom-m%s-i1-c1-opt' % mol], f[mol]['Geom-m%s-i1-c1-d1' % mol]
        data = dict(source=dict(SOURCE, hdf5_sha256=digest), molecule=mol,
                    reference_id='Geom-m%s-i1-c1-opt' % mol, displaced_id='Geom-m%s-i1-c1-d1' % mol,
                    coordinate_unit='angstrom', force_unit='eV/angstrom', force_key='totFOR',
                    elements=[SYMBOL[int(z)] for z in ref['atNUM'][:]],
                    reference_xyz=[[float(x) for x in r] for r in ref['atXYZ'][:]],
                    displaced_xyz=[[float(x) for x in r] for r in disp['atXYZ'][:]],
                    forces_at_displaced=[[float(x) for x in r] for r in disp['totFOR'][:]])
        data['matches_published_qa'] = check_published(published.get(mol, 'none'), data)
        write(OUT / 'force-path' / ('QM7X-%s-c1-d1.json' % mol), data)
    for mol in args.conformers or []:
        opts = sorted(k for k in f[mol].keys() if k.endswith('-opt') and '-i1-' in k)
        first = f[mol][opts[0]]
        data = dict(source=dict(SOURCE, hdf5_sha256=digest), molecule=mol, isomer='i1',
                    level='PBE0+MBD single points at DFTB3+MBD-optimized geometries (QM7-X "opt" structures)',
                    elements=[SYMBOL[int(z)] for z in first['atNUM'][:]], conformers=[])
        for k in opts:
            g = f[mol][k]
            if [SYMBOL[int(z)] for z in g['atNUM'][:]] != data['elements']:
                raise SystemExit('Atom order differs within ' + mol)
            data['conformers'].append(dict(id=k, xyz=[[float(x) for x in r] for r in g['atXYZ'][:]],
                                           e_pbe0_mbd_eV=float(g['ePBE0+MBD'][0]), dipole_eA=float(g['DIP'][0]),
                                           vdip_eA=[float(x) for x in g['vDIP'][:]]))
        write(OUT / 'conformers' / ('QM7X-%s-i1-opt.json' % mol), data)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hdf5', required=True)
    p.add_argument('--force', nargs='*')
    p.add_argument('--conformers', nargs='*')
    main(p.parse_args())
