"""Recompute the bio-nm-v04-002 batch (6LYZ lysozyme, 1EHZ tRNA) from
original PDB files, standard library only. Supplemental answer calculator,
not a registered generic semantic grader. Mirrors the double-check pattern
of tools/recompute_bio_batch.py but is a separate script: this batch's
tRNA merges ATOM+HETATM C1' rows (modified nucleotides) and adds an
anticodon-angle check that the first batch's script does not need.
Usage: python tools/recompute_bio_batch2.py PATH_TO_PDB_DIRECTORY --out metrics.json
"""
import argparse, json, math, itertools
from pathlib import Path
from decimal import Decimal, localcontext

def atoms(path, name, exclude_resn=('HOH', 'MG', 'MN'), record_types=('ATOM', 'HETATM')):
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('ENDMDL'):
            break
        rec = line[:6].strip()
        if rec not in record_types or line[12:16].strip() != name:
            continue
        resn = line[17:20].strip()
        if resn in exclude_resn:
            continue
        if line[16].strip() or line[26].strip():
            raise ValueError('Alternate location/insertion code requires explicit handling')
        rows.append(dict(chain=line[21], residue=int(line[22:26]), resname=resn,
                          xyz=[float(line[a:b]) for a, b in [(30, 38), (38, 46), (46, 54)]]))
    rows.sort(key=lambda r: r['residue'])
    return rows

def distance(a, b):
    return math.dist(a, b)

def full_scan_max(xyz):
    n = len(xyz)
    best, bi, bj = max((distance(xyz[i], xyz[j]), i, j) for i in range(n) for j in range(i + 1, n))
    return best, bi, bj

def rg_centroid(xyz):
    n = len(xyz)
    center = [sum(p[k] for p in xyz) / n for k in range(3)]
    return math.sqrt(sum(distance(p, center) ** 2 for p in xyz) / n)

def rg_pairwise_identity_decimal(xyz):
    with localcontext() as ctx:
        ctx.prec = 40
        d = [[Decimal(str(v)) for v in p] for p in xyz]
        n = len(d)
        pair_sum = sum(sum((a - b) ** 2 for a, b in zip(p, q)) for p, q in itertools.combinations(d, 2))
        return float((pair_sum / Decimal(n * n)).sqrt())

def angle_acos(a, vertex, b):
    u = [x - y for x, y in zip(a, vertex)]
    v = [x - y for x, y in zip(b, vertex)]
    dot = sum(x * y for x, y in zip(u, v))
    nu, nv = math.dist(u, [0, 0, 0]), math.dist(v, [0, 0, 0])
    return math.degrees(math.acos(max(-1, min(1, dot / (nu * nv)))))

def angle_atan2(a, vertex, b):
    u = [x - y for x, y in zip(a, vertex)]
    v = [x - y for x, y in zip(b, vertex)]
    cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    cross_mag = math.sqrt(sum(c * c for c in cross))
    dot = sum(x * y for x, y in zip(u, v))
    return math.degrees(math.atan2(cross_mag, dot))

def calculate(directory):
    out = {}

    lyz = atoms(directory / '6LYZ.pdb', 'CA', record_types=('ATOM',))
    assert len(lyz) == 129 and [r['residue'] for r in lyz] == list(range(1, 130))
    lyz_by_resi = {r['residue']: r for r in lyz}
    assert lyz_by_resi[35]['resname'] == 'GLU' and lyz_by_resi[52]['resname'] == 'ASP'
    lyz_xyz = [r['xyz'] for r in lyz]
    dmax, i, j = full_scan_max(lyz_xyz)
    rg_a = rg_centroid(lyz_xyz)
    rg_b = rg_pairwise_identity_decimal(lyz_xyz)
    assert abs(rg_a - rg_b) < 1e-9
    out['lysozyme'] = dict(
        count=len(lyz), rows=lyz,
        end_to_end_A=distance(lyz_xyz[0], lyz_xyz[-1]),
        diameter_A=dmax, diameter_pair=[lyz[i]['residue'], lyz[j]['residue']],
        catalytic_glu35_asp52_A=distance(lyz_by_resi[35]['xyz'], lyz_by_resi[52]['xyz']),
        rg_A=rg_a, independent_rg_A=rg_b,
    )

    trna = atoms(directory / '1EHZ.pdb', "C1'")
    assert len(trna) == 76 and [r['residue'] for r in trna] == list(range(1, 77))
    trna_by_resi = {r['residue']: r for r in trna}
    trna_xyz = [r['xyz'] for r in trna]
    path_len = sum(distance(trna_xyz[k], trna_xyz[k + 1]) for k in range(len(trna_xyz) - 1))
    chord = distance(trna_xyz[0], trna_xyz[-1])
    dmax_t, it, jt = full_scan_max(trna_xyz)
    a34, a35, a36 = trna_by_resi[34], trna_by_resi[35], trna_by_resi[36]
    assert (a34['resname'], a35['resname'], a36['resname']) == ('OMG', 'A', 'A')
    ang1 = angle_acos(a34['xyz'], a35['xyz'], a36['xyz'])
    ang2 = angle_atan2(a34['xyz'], a35['xyz'], a36['xyz'])
    assert abs(ang1 - ang2) < 1e-6
    r_probe = distance(trna_by_resi[76]['xyz'], trna_by_resi[35]['xyz'])
    with localcontext() as ctx:
        ctx.prec = 40
        r_dec = Decimal(str(r_probe / 10))
        R0 = Decimal('3.5')
        e_dec = 1 / (1 + (r_dec / R0) ** 6)
    e_float = 1 / (1 + (r_probe / 10 / 3.5) ** 6)
    assert abs(float(e_dec) - e_float) < 1e-9
    out['trna'] = dict(
        count=len(trna), rows=trna,
        path_length_A=path_len, end_to_end_A=chord,
        diameter_A=dmax_t, diameter_pair=[trna[it]['residue'], trna[jt]['residue']],
        anticodon_triplet=[a34['residue'], a35['residue'], a36['residue']],
        anticodon_resnames=[a34['resname'], a35['resname'], a36['resname']],
        anticodon_angle_deg_acos=ang1, anticodon_angle_deg_atan2=ang2,
        acceptor76_to_anticodon35_A=r_probe,
        fret_R0_nm=3.5, fret_efficiency=e_float, fret_efficiency_decimal_check=float(e_dec),
    )

    out['comparison_context'] = {
        'rg_1UBQ_nm_from_bio_nm_v04_001': 1.149289,
        'rg_1CRN_nm_from_bio_nm_v04_001': 0.967550,
    }
    return out

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('directory', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = calculate(a.directory)
    a.out.write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'rows'} for k, v in result.items()}, indent=2))
