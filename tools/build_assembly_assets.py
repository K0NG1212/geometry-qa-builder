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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import license_note  # noqa: E402

RAW = ROOT / 'inputs/pdb'
OUT = ROOT / 'docs/assets/families/assemblies'
URL = 'https://files.rcsb.org/download/%s'
SHORT = {'Major capsid protein': 'VP5', 'Small capsomere-interacting protein': 'VP26', 'Triplex capsid protein 1': 'VP19C',
         'Triplex capsid protein 2': 'VP23', 'Capsid vertex component 1': 'pUL25', 'Capsid vertex component 2': 'pUL17',
         'Large tegument protein deneddylase': 'pUL36'}

# These local PDB copies are reduced as deposited models, never expanded to a biological assembly.
# Some copies were already published under docs/assets/bio before this batch; no download is needed.
DEPOSITED_MODELS = (
    ('12E8', 'docs/assets/bio/12E8.pdb', '2E8 Fab fragment', 'biology'),
    ('1HHK', 'docs/assets/bio/1HHK.pdb', 'peptide/MHC HLA-A2 complexes', 'biology'),
    ('1WNR', 'inputs/pdb/1WNR.pdb', 'Thermus thermophilus Cpn10', 'biology'),
    ('1G31', 'inputs/pdb/1G31.pdb', 'bacteriophage T4 gp31 co-chaperonin', 'biology'),
    ('355D', 'docs/assets/bio/355D.pdb', 'B-DNA dodecamer', 'chemistry'),
    ('477D', 'inputs/pdb/477D.pdb', 'calcium-form B-DNA dodecamer', 'chemistry'),
    ('4GLG', 'inputs/pdb/4GLG.pdb', 'DNA dodecamer containing 5-methylcytosine', 'chemistry'),
    ('4GLH', 'inputs/pdb/4GLH.pdb', 'DNA dodecamer containing 5-hydroxymethylcytosine', 'chemistry'),
    ('4F3U', 'inputs/pdb/4F3U.pdb', "DNA dodecamer containing 5-hydroxy-2'-deoxycytidine", 'chemistry'),
    ('3T8P', 'inputs/pdb/3T8P.pdb', 'two deposited DNA chains from a Holliday-junction crystal entry', 'chemistry'),
    ('1DCW', 'inputs/pdb/1DCW.pdb', 'four deposited DNA chains from an inverted-repeat four-way-junction entry', 'chemistry'),
    ('1JUC', 'inputs/pdb/1JUC.pdb', 'two deposited DNA chains from a Holliday-junction crystal entry', 'chemistry'),
    ('1BNA', 'docs/assets/bio/1BNA.pdb', 'B-DNA dodecamer (two deposited DNA chains)', 'chemistry'),
)


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


def assembly_operators(text, assembly='1'):
    """Operators and chains of a biological assembly as the file defines it (_pdbx_struct_assembly_gen), e.g. '(1-60)'
    or '(1,6,11,...,56)' (1STM: 12 operators applied to a 5-chain asymmetric unit)."""
    ops = {}
    for r in cif_loop(text, '_pdbx_struct_oper_list'):
        ops[r['id']] = ([[float(r['matrix[%d][%d]' % (i, j)]) for j in (1, 2, 3)] for i in (1, 2, 3)],
                        [float(r['vector[%d]' % i]) for i in (1, 2, 3)])
    [gen] = [g for g in cif_loop(text, '_pdbx_struct_assembly_gen') if g['assembly_id'] == assembly]
    ids = []
    for part in gen['oper_expression'].strip('()').split(','):
        lo, _, hi = part.partition('-')
        ids += [str(k) for k in range(int(lo), int(hi or lo) + 1)]
    return [ops[i] for i in ids], set(gen['asym_id_list'].split(','))


def chain_ca(text, chains=None):
    """CA coordinates per protein chain (label_asym_id), deposited model, main alternate location."""
    out = {}
    for r in cif_atoms(text):
        if r['label_atom_id'] == 'CA' and (chains is None or r['label_asym_id'] in chains):
            out.setdefault(r['label_asym_id'], []).append((float(r['Cartn_x']), float(r['Cartn_y']), float(r['Cartn_z'])))
    return out


def extra_assets(files, sources):
    """Particles added on 2026-10-03 (user-approved downloads)."""
    text, digest, size = read('1RYP.cif')
    pts = [('C', p) for ch, ps in sorted(chain_ca(text).items()) for p in ps]
    files['1RYP-residue-points.xyz'] = xyz(pts, '1RYP yeast 20S proteasome: one point per residue (protein CA as C), all 28 chains of the deposited model, angstrom')
    sources['1RYP-residue-points.xyz'] = dict(pdb='1RYP', source=URL % '1RYP.cif', sha256=digest, bytes=size, points=len(pts),
                                              reduction='CA of every protein residue, main alternate location; the deposited model is the whole particle')
    for pdb, what in (('1STM', 'satellite panicum mosaic virus'), ('2BUK', 'satellite tobacco necrosis virus')):
        text, digest, size = read(pdb + '.cif')
        ops, chains = assembly_operators(text)
        ca = chain_ca(text, chains)
        expanded = [('C', apply(op, p)) for op in ops for ch in sorted(ca) for p in ca[ch]]
        cents = [('CP', '%s.%02d' % (ch, k + 1), apply(op, centroid(ca[ch]))) for k, op in enumerate(ops) for ch in sorted(ca)]
        files['%s-capsid-CA.xyz' % pdb] = xyz(expanded, '%s %s capsid: capsid-protein CA atoms of assembly 1 (%d chains x %d deposited operators), angstrom'
                                              % (pdb, what, len(ca), len(ops)))
        files['%s-subunit-centroids.txt' % pdb] = table(cents, '%s %s capsid: CA centroid of each capsid-protein copy of assembly 1' % (pdb, what))
        for name, n in (('%s-capsid-CA.xyz' % pdb, len(expanded)), ('%s-subunit-centroids.txt' % pdb, len(cents))):
            sources[name] = dict(pdb=pdb, source=URL % (pdb + '.cif'), sha256=digest, bytes=size, points=n,
                                 reduction='capsid-protein CA atoms of chains %s expanded by the %d operators of assembly 1 (_pdbx_struct_assembly_gen)'
                                           % (','.join(sorted(ca)), len(ops)))
    for pdb, what, comp in (('1CWP', 'cowpea chlorotic mottle virus', 'CP'), ('1SVA', 'simian virus 40', 'VP1'),
                            ('2FT1', 'bacteriophage HK97 head II', 'gp5')):
        text, digest, size = read(pdb + '.cif')
        ops, chains = assembly_operators(text)
        ca = chain_ca(text, chains)
        rows = [(comp, '%s.%02d' % (ch, k + 1), apply(op, centroid(ca[ch]))) for k, op in enumerate(ops) for ch in sorted(ca)]
        name = '%s-chain-centroids.txt' % pdb
        files[name] = table(rows, '%s %s capsid: CA centroid of every protein chain of assembly 1 (%d chains x %d deposited operators)'
                            % (pdb, what, len(ca), len(ops)))
        sources[name] = dict(pdb=pdb, source=URL % (pdb + '.cif'), sha256=digest, bytes=size, points=len(rows), chains_per_unit=len(ca),
                             reduction='CA centroid per protein chain, expanded by the operators of assembly 1 (_pdbx_struct_assembly_gen)')



def deposited_assets(files, sources):
    """Reuse local PDB files for the selected positive-occupancy ATOM CA/P points of the first model.

    This pre-filter applies only to this batch. The older residue-point assets keep their original byte contract.
    Modified residues written as HETATM, missing phosphate atoms and unrecorded symmetry copies are not inferred.
    """
    from collections import Counter

    for pdb, raw_path, what, domain in DEPOSITED_MODELS:
        raw = (ROOT / raw_path).read_bytes()
        text = raw.decode('utf-8')
        lines = []
        for line in text.splitlines():
            if line.startswith('ENDMDL'):
                break
            lines.append(line)
        selected = [line for line in lines if line.startswith('ATOM') and line[16] in ' A'
                    and line[12:16].strip() in ('CA', 'P') and float(line[54:60]) > 0]
        keys = [(line[21], line[22:27], line[12:16].strip()) for line in selected]
        if len(keys) < 2 or len(set(keys)) != len(keys):
            raise ValueError('Too few or duplicate residue marker records in ' + pdb)
        excluded = [line for line in lines if line.startswith('ATOM') and float(line[54:60]) <= 0]
        omitted = [line for line in lines if line.startswith('HETATM') and line[16] in ' A'
                   and line[12:16].strip() in ('CA', 'P')]
        filtered = '\n'.join(line for line in lines if line not in excluded) + '\n'
        pts = pdb_residue_points(filtered)
        if len(pts) != len(selected):
            raise ValueError('Residue-point reader and selected records disagree for ' + pdb)
        chains = dict(sorted(Counter(line[21] for line in selected).items()))
        atoms = dict(sorted(Counter(line[12:16].strip() for line in selected).items()))
        omitted_residues = dict(sorted(Counter(line[17:20].strip() for line in omitted).items()))
        zero_markers = sum(line[16] in ' A' and line[12:16].strip() in ('CA', 'P') for line in excluded)
        name = '%s-deposited-residue-points.xyz' % pdb
        comment = ('%s %s: selected positive-occupancy ATOM CA as C and P as P, first deposited model, '
                   'original record order, no HETATM or symmetry expansion, angstrom' % (pdb, what))
        files[name] = xyz(pts, comment)
        sources[name] = dict(
            pdb=pdb, source=URL % (pdb + '.pdb'), raw_path=raw_path,
            sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), points=len(pts),
            title=' '.join(line[10:80].strip() for line in text.splitlines() if line.startswith('TITLE')),
            model='first deposited MODEL; the unnumbered deposited model when MODEL is absent',
            chains=chains, selected_atom_names=atoms,
            excluded_zero_occupancy_atom_records=len(excluded), excluded_zero_occupancy_marker_records=zero_markers,
            omitted_hetatm_ca_or_p_records=len(omitted), omitted_hetatm_residue_names=omitted_residues,
            reduction='Keep ATOM records of the first deposited model with occupancy > 0, alternate location blank or A, '
                      'and atom name CA or P; preserve original record order and coordinates; label CA as C and P as P. '
                      'Apply no crystallographic or biological-assembly symmetry operators.',
            limits=['This is only the selected deposited point set, not a claim of a complete biological assembly.',
                    'All HETATM records are omitted, including modified nucleotides and ions; absent markers are not reconstructed.',
                    'Zero-occupancy ATOM records are excluded; retained coordinates are a static deposited model, not solution dynamics.',
                    'Points carry equal weight in the geometric/scattering tasks; C and P labels do not imply atomic-mass or scattering-factor weights.'])



def a1_mmcif_deposited_assets(files, sources):
    """A1 second pass: one representation per new PDB entry, selected by the actual positive-occupancy CA count.

    Do not apply assembly or crystal operators. Over 20,000 selected CA points use one CA centroid per deposited
    protein chain. No capsid or complete-particle claim is inferred from the title, chain count or planned pixel.
    """
    import math
    from collections import Counter

    index_path = RAW / 'a1-assemblies.json'
    if not index_path.exists():
        return
    index = json.loads(index_path.read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'templates/structures.json').read_text(encoding='utf-8'))
    for pdb, record in sorted(index['files'].items()):
        # Future application must not add a second representation with the same EN-{PDB}-... id space.
        prior = [p for p in registry['assemblies'] if p['pdb'] == pdb]
        if prior and not all(p['asset'].rsplit('/', 1)[-1].startswith(pdb + '-a1-deposited-CA') for p in prior):
            # Reuse an already registered deposited-point representation; do not create a second ID space.
            continue
        path = ROOT / record['raw_path']
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('A1 raw input hash differs from the download record: ' + pdb)
        text = gzip.decompress(raw).decode('utf-8')
        rows = cif_loop(text, '_atom_site')
        if not rows:
            raise ValueError('Missing atom_site rows: ' + pdb)
        model = rows[0].get('pdbx_PDB_model_num', '1')
        points, groups, selected_keys, excluded = [], {}, set(), Counter()
        for row in rows:
            if row.get('pdbx_PDB_model_num', '1') != model:
                continue
            if row['label_atom_id'] != 'CA':
                continue
            if row['group_PDB'] != 'ATOM':
                excluded['HETATM_CA'] += 1
                continue
            if row['label_alt_id'] not in ('.', '?', 'A'):
                excluded['other_alternate_CA'] += 1
                continue
            if float(row['occupancy']) <= 0:
                excluded['zero_occupancy_CA'] += 1
                continue
            chain = row['label_asym_id']
            if not chain or any(c.isspace() for c in chain):
                raise ValueError('Unusable deposited chain label: ' + pdb)
            key = (chain, row['label_seq_id'], row.get('pdbx_PDB_ins_code', '?'))
            if key in selected_keys:
                raise ValueError('Duplicate selected residue CA: %s %s' % (pdb, key))
            selected_keys.add(key)
            point = tuple(float(row[k]) for k in ('Cartn_x', 'Cartn_y', 'Cartn_z'))
            if not all(math.isfinite(x) for x in point):
                raise ValueError('Non-finite coordinate: ' + pdb)
            points.append(point)
            groups.setdefault(chain, []).append(point)
        if len(points) < 2:
            raise ValueError('Fewer than two selected protein CA points: ' + pdb)
        if len(points) > 20000:
            name = pdb + '-a1-deposited-CA-chain-centroids.txt'
            reduced = [('ALL', ch, centroid(pts)) for ch, pts in sorted(groups.items())]
            if len(reduced) < 12:
                raise ValueError('Too few chain-centroid points for the existing table enumerator: ' + pdb)
            comment = (pdb + ' first deposited model: one equal-weight point at the centroid of the selected '
                       'positive-occupancy ATOM CA coordinates of each protein chain; component ALL; '
                       'no assembly/crystal symmetry expansion; angstrom')
            body = table(reduced, comment)
            representation = 'equal-weight deposited-chain CA centroids'
            kind = 'table'
            n = len(reduced)
        else:
            name = pdb + '-a1-deposited-CA.xyz'
            comment = (pdb + ' first deposited model: positive-occupancy ATOM CA coordinates as equal-weight C points; '
                       'original record order, alternate location blank or A; no symmetry expansion; angstrom')
            body = xyz([('C', point) for point in points], comment)
            representation, kind, n = 'equal-weight selected deposited ATOM CA points', 'xyz', len(points)
        existing_path = OUT / name
        if existing_path.exists() and existing_path.read_bytes() != body.encode('utf-8'):
            raise ValueError('Refusing to overwrite an existing A1 representation: ' + name)
        files[name] = body
        sources[name] = dict(
            pdb=pdb, source=record['url'], page=record['page'], raw_path=record['raw_path'],
            sha256=record['sha256'], bytes=len(raw), points=n, original_selected_CA=len(points),
            model=model, chains={ch: len(pts) for ch, pts in sorted(groups.items())},
            excluded_CA_records=dict(excluded), representation=representation, suggested_registry_kind=kind,
            planned_pixel=record['planned_pixel'], planned_subdomain=record.get('planned_subdomain'),
            selection_reason=record.get('why'), title=record['title'],
            coordinate_precision='Coordinates and chain centroids serialized to 0.001 angstrom by the existing builder.',
            reduction='First deposited model only; ATOM CA, occupancy > 0, alternate location blank or A. '
                      'No symmetry operators; no missing atom reconstruction. Over 20000 selected CA points, '
                      'replace each protein chain by its selected-CA centroid and weight every retained centroid equally.',
            limits=['The represented point set is not asserted to be a complete biological assembly or a native solution particle.',
                    'Chain centroids have different extent and radius of gyration from the residue points; report only the stated representation.',
                    'Equal-weight points are not mass weighting or atom-specific scattering-factor weighting.',
                    'No capsid architecture is inferred. Missing residues, HETATM and unselected alternate conformers are omitted.',
                    'The planned pixel is a source-selection goal; assign the final scale from measured geometry.'])


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
    extra_assets(files, sources)
    deposited_assets(files, sources)
    a1_mmcif_deposited_assets(files, sources)
    for name, text in files.items():
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
        sources[name]['asset_sha256'] = hashlib.sha256(text.encode('utf-8')).hexdigest()
    (OUT / 'sources.json').write_text(json.dumps(dict(license='wwPDB data: CC0 1.0',
                                                      license_statement=license_note.statement('rcsb-usage-policy'),
                                                      note='Raw downloads are kept locally in inputs/pdb (not in Git).',
                                                      files=sources), ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v['points'] for k, v in sources.items()}))


if __name__ == '__main__':
    main()
