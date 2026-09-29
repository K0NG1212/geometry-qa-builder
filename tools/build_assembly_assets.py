"""Reduce large PDB assemblies (downloaded to inputs/pdb, not in Git) into small public assets.

Deterministic reductions, all disclosed in docs/assets/families/assemblies/sources.json:
  * 1AON, 1KX5: one point per residue (protein CA, nucleic-acid P) of the deposited model.
  * 1A34 (STMV): capsid-protein CA atoms expanded by the 60 deposited icosahedral operators,
    plus a table of the 60 subunit centroids.
  * 6CGR (HSV-1): CA centroid of every protein chain of the asymmetric unit, expanded by the
    60 deposited operators (about 3,000 points, labelled by component).
  * 6NCL (PBCV-1): CA centroid of every protein chain of the asymmetric unit, expanded by the 60
    deposited operators (6,900 points; major capsid protein labelled Vp54, others by their entity names).
  * 7ARQ (DNA-origami 16-helix bundle, cryo-EM pseudo-atomic model): the C1' atom of every
    nucleotide, labelled scaffold or staple (one table row per nucleotide).
Operators come from the files' own _pdbx_struct_oper_list; nothing is guessed.

python tools/build_assembly_assets.py
"""
import gzip
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'inputs/pdb'
OUT = ROOT / 'docs/assets/families/assemblies'
URL = 'https://files.rcsb.org/download/%s'
SHORT = {'Major capsid protein': 'VP5', 'Small capsomere-interacting protein': 'VP26', 'Triplex capsid protein 1': 'VP19C',
         'Triplex capsid protein 2': 'VP23', 'Capsid vertex component 1': 'pUL25', 'Capsid vertex component 2': 'pUL17',
         'Large tegument protein deneddylase': 'pUL36'}


def read(name):
    raw = (RAW / name).read_bytes()
    text = gzip.decompress(raw).decode() if name.endswith('.gz') else raw.decode()
    return text, hashlib.sha256(raw).hexdigest(), len(raw)


# CIF tokens: a quote only closes when followed by whitespace (so O5' and 'a b' both work).
TOKEN = re.compile(r"'(?:[^']|'(?=\S))*'(?=\s|$)|\"(?:[^\"]|\"(?=\S))*\"(?=\s|$)|\S+")


def tokens(line):
    return [t[1:-1] if t[:1] in ('"', "'") and t[-1:] == t[:1] and len(t) > 1 else t for t in TOKEN.findall(line)]


def cif_loop(text, prefix):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == 'loop_' and lines[i + 1].startswith(prefix + '.'):
            j, cols = i + 1, []
            while lines[j].startswith(prefix + '.'):
                cols.append(lines[j].split('.', 1)[1].strip())
                j += 1
            rows, buf = [], []
            while j < len(lines) and not lines[j].startswith(('loop_', '_', '#')):
                buf += tokens(lines[j])
                j += 1
                while len(buf) >= len(cols):
                    rows.append(dict(zip(cols, buf[:len(cols)])))
                    buf = buf[len(cols):]
            return rows
    return []


def operators(text):
    ops = {}
    for r in cif_loop(text, '_pdbx_struct_oper_list'):
        m = [[float(r['matrix[%d][%d]' % (i, j)]) for j in (1, 2, 3)] for i in (1, 2, 3)]
        v = [float(r['vector[%d]' % i]) for i in (1, 2, 3)]
        ops[r['id']] = (m, v)
    return [ops[str(k)] for k in range(1, 61)]


def apply(op, p):
    m, v = op
    return tuple(sum(m[i][k] * p[k] for k in range(3)) + v[i] for i in range(3))


def centroid(points):
    return tuple(sum(p[k] for p in points) / len(points) for k in range(3))


def xyz(points, comment):
    return '\n'.join([str(len(points)), comment] + ['%s %.3f %.3f %.3f' % (e, *p) for e, p in points]) + '\n'


def table(rows, comment):
    return '\n'.join([comment + '; columns: component copy x y z (angstrom)'] +
                     ['%s %s %.3f %.3f %.3f' % (c, k, *p) for c, k, p in rows]) + '\n'


def pdb_residue_points(text):
    out = []
    for line in text.splitlines():
        if line.startswith('ENDMDL'):
            break
        if line.startswith('ATOM') and line[16] in ' A' and line[12:16].strip() in ('CA', 'P'):
            out.append(('C' if line[12:16].strip() == 'CA' else 'P', tuple(float(line[c:c + 8]) for c in (30, 38, 46))))
    return out


def cif_atoms(text):
    rows = cif_loop(text, '_atom_site')
    return [r for r in rows if r['group_PDB'] == 'ATOM' and r.get('pdbx_PDB_model_num', '1') == '1'
            and r['label_alt_id'] in ('.', 'A')]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources, files = {}, {}
    for pdb, what in (('1AON', 'GroEL–GroES–(ADP)7 chaperonin'), ('1KX5', 'nucleosome core particle NCP147')):
        text, digest, size = read(pdb + '.pdb')
        pts = pdb_residue_points(text)
        name = '%s-residue-points.xyz' % pdb
        files[name] = xyz(pts, '%s %s: one point per residue (protein CA as C, nucleic-acid P as P), deposited model, angstrom' % (pdb, what))
        sources[name] = dict(pdb=pdb, source=URL % (pdb + '.pdb'), sha256=digest, bytes=size, points=len(pts),
                             reduction='CA of every protein residue and P of every nucleotide, main alternate location')
    text, digest, size = read('1A34.cif')
    ops = operators(text)
    atoms = cif_atoms(text)
    entity = {r['id']: r.get('pdbx_description', '') for r in cif_loop(text, '_entity')}
    protein = [r for r in atoms if r['label_atom_id'] == 'CA' and 'MOSAIC' in entity.get(r['label_entity_id'], '').upper()]
    ca = [(float(r['Cartn_x']), float(r['Cartn_y']), float(r['Cartn_z'])) for r in protein]
    expanded = [('C', apply(op, p)) for op in ops for p in ca]
    files['1A34-capsid-CA.xyz'] = xyz(expanded, '1A34 satellite tobacco mosaic virus capsid: capsid-protein CA atoms x 60 deposited icosahedral operators, angstrom')
    files['1A34-subunit-centroids.txt'] = table([('CP', '%02d' % (k + 1), apply(op, centroid(ca))) for k, op in enumerate(ops)],
                                                '1A34 STMV capsid: CA centroid of each of the 60 capsid-protein copies')
    for name, pts in (('1A34-capsid-CA.xyz', len(expanded)), ('1A34-subunit-centroids.txt', 60)):
        sources[name] = dict(pdb='1A34', source=URL % '1A34.cif', sha256=digest, bytes=size, points=pts,
                             reduction='capsid-protein CA atoms (%d per copy) expanded by operators 1-60 of assembly 1' % len(ca))
    text, digest, size = read('6CGR.cif.gz')
    ops = operators(text)
    entity = {r['id']: SHORT.get(r.get('pdbx_description', '').strip("'"), r.get('pdbx_description', '')) for r in cif_loop(text, '_entity')}
    chains = {}
    for r in cif_atoms(text):
        if r['label_atom_id'] == 'CA':
            chains.setdefault((r['label_entity_id'], r['label_asym_id']), []).append(
                (float(r['Cartn_x']), float(r['Cartn_y']), float(r['Cartn_z'])))
    rows = []
    for k, op in enumerate(ops):
        for (ent, asym), pts in sorted(chains.items()):
            rows.append((entity[ent], '%s.%02d' % (asym, k + 1), apply(op, centroid(pts))))
    files['6CGR-chain-centroids.txt'] = table(rows, '6CGR HSV-1 capsid with tegument complexes: CA centroid of every protein chain '
                                                    'of the asymmetric unit x 60 deposited icosahedral operators')
    sources['6CGR-chain-centroids.txt'] = dict(pdb='6CGR', source=URL % '6CGR.cif.gz', sha256=digest, bytes=size, points=len(rows),
                                               chains_per_unit=len(chains),
                                               components={c: sum(1 for x in rows if x[0] == c) for c in sorted({x[0] for x in rows})},
                                               reduction='CA centroid per protein chain, expanded by operators 1-60 of assembly 1')
    text, digest, size = read('6NCL.cif.gz')
    ops = operators(text)
    entity = {r['id']: r.get('pdbx_description', '').strip("'") for r in cif_loop(text, '_entity')}
    entity = {k: ('Vp54' if v == 'Major capsid protein' else v) for k, v in entity.items()}
    chains = {}
    for r in cif_atoms(text):
        if r['label_atom_id'] == 'CA':
            chains.setdefault((r['label_entity_id'], r['label_asym_id']), []).append(
                (float(r['Cartn_x']), float(r['Cartn_y']), float(r['Cartn_z'])))
    rows = []
    for k, op in enumerate(ops):
        for (ent, asym), pts in sorted(chains.items()):
            rows.append((entity[ent], '%s.%02d' % (asym, k + 1), apply(op, centroid(pts))))
    files['6NCL-chain-centroids.txt'] = table(rows, '6NCL PBCV-1 capsid (cryo-EM 3.5 A, icosahedrally averaged): CA centroid of every protein '
                                                    'chain of the asymmetric unit x 60 deposited icosahedral operators')
    sources['6NCL-chain-centroids.txt'] = dict(pdb='6NCL', source=URL % '6NCL.cif.gz', sha256=digest, bytes=size, points=len(rows),
                                               chains_per_unit=len(chains),
                                               components={c: sum(1 for x in rows if x[0] == c) for c in sorted({x[0] for x in rows})},
                                               reduction='CA centroid per protein chain, expanded by operators 1-60 of assembly 1')
    text, digest, size = read('7ARQ.cif.gz')
    entity = {r['id']: r.get('pdbx_description', '').strip("'") for r in cif_loop(text, '_entity')}
    rows = [('scaffold' if entity[r['label_entity_id']] == 'SCAFFOLD STRAND' else 'staple', '%s.%04d' % (r['auth_asym_id'], int(r['auth_seq_id'])),
             (float(r['Cartn_x']), float(r['Cartn_y']), float(r['Cartn_z'])))
            for r in cif_atoms(text) if r['label_atom_id'] == "C1'"]
    files['7ARQ-nucleotide-points.txt'] = table(rows, "7ARQ DNA-origami 16-helix bundle (cryo-EM, 10 A pseudo-atomic model): C1' atom of every "
                                                      'nucleotide, component = scaffold or staple strand, copy = chain.residue')
    sources['7ARQ-nucleotide-points.txt'] = dict(pdb='7ARQ', source=URL % '7ARQ.cif.gz', sha256=digest, bytes=size, points=len(rows),
                                                 components={c: sum(1 for x in rows if x[0] == c) for c in ('scaffold', 'staple')},
                                                 reduction="C1' atom of every nucleotide of the deposited model (single copy; no symmetry operators)")
    for name, text in files.items():
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
        sources[name]['asset_sha256'] = hashlib.sha256(text.encode('utf-8')).hexdigest()
    (OUT / 'sources.json').write_text(json.dumps(dict(license='wwPDB data: CC0 1.0', note='Raw downloads are kept locally in inputs/pdb (not in Git).',
                                                      files=sources), ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v['points'] for k, v in sources.items()}))


if __name__ == '__main__':
    main()
