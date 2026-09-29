"""Build paper-parameter models of twisted bilayer graphene (quantum, 10-100 nm).

Twist angles (numbers only; no text or figures redistributed):
  * Cao, Fatemi, Fang, Watanabe, Taniguchi, Kaxiras, Jarillo-Herrero, "Magic-angle graphene superlattices: a new
    platform for unconventional superconductivity", arXiv:1803.02342 (Nature 556, 43 (2018)): devices M1 (1.16 deg),
    M2 (1.05 deg), D1 (1.08 deg); definitions n_s = 4/A, A ~ sqrt(3) a^2 / (2 theta^2), a = 0.246 nm.
  * Kerelsky et al., "Magic Angle Spectroscopy", arXiv:1812.08776 (Nature 572, 95 (2019)): STM regions at 1.10 and
    0.79 deg; unstrained moire period lambda = a / (2 sin(theta/2)).

Two representations of a rigid (unrelaxed, unstrained) twisted bilayer at each angle:
  * AA-site map: centres of the AA-stacked regions (the bright spots of an STM topograph) within 45 nm of one AA
    site, rows "AA x y" in nm (6 decimals), rotated in-plane by a SHA-256-derived angle.
  * Atomistic patch (1.10 deg only): all carbon atoms of both layers within 2.0 nm of an AA site (layer spacing
    3.35 A), XYZ in angstrom, the whole patch rotated in-plane by a SHA-256-derived angle.

python tools/build_moire_assets.py
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/families/moire'
A_NM = 0.246
PAPERS = dict(cao=dict(citation='Cao Y. et al., arXiv:1803.02342 (Nature 556, 43 (2018))', url='https://arxiv.org/abs/1803.02342',
                       numbers='devices M1 1.16 deg, M2 1.05 deg, D1 1.08 deg; n_s = 4/A; a = 0.246 nm'),
              kerelsky=dict(citation='Kerelsky A. et al., arXiv:1812.08776 (Nature 572, 95 (2019))', url='https://arxiv.org/abs/1812.08776',
                            numbers='STM regions at 1.10 deg and 0.79 deg; lambda = a/(2 sin(theta/2)) without strain'))
SAMPLES = {'M1': ('cao', 1.16), 'M2': ('cao', 1.05), 'D1': ('cao', 1.08), 'K110': ('kerelsky', 1.10), 'K079': ('kerelsky', 0.79)}
MAP_RADIUS = 45.0


def hash_angle(name):
    return int.from_bytes(hashlib.sha256(name.encode('utf-8')).digest()[:8], 'big') / 2 ** 64 * 2 * math.pi


def rot(p, phi):
    c, s = math.cos(phi), math.sin(phi)
    return (c * p[0] - s * p[1], s * p[0] + c * p[1])


def period(theta_deg):
    return A_NM / (2 * math.sin(math.radians(theta_deg) / 2))


def aa_map(theta_deg, name):
    lam, phi = period(theta_deg), hash_angle(name)
    n = int(MAP_RADIUS / lam) + 2
    pts = []
    for i in range(-2 * n, 2 * n + 1):
        for j in range(-2 * n, 2 * n + 1):
            p = (lam * (i + j / 2), lam * j * math.sqrt(3) / 2)
            if math.hypot(*p) <= MAP_RADIUS + 1e-9:
                pts.append(rot(p, phi))
    return sorted(pts, key=lambda p: (round(p[1], 6), round(p[0], 6)))


def patch(theta_deg, name, radius_nm=2.0, spacing_nm=0.335):
    a = A_NM
    phi = hash_angle(name)
    atoms = []
    n = int(radius_nm / a) + 3
    for layer, sign in ((0, -1), (1, 1)):
        t = sign * math.radians(theta_deg) / 2
        for i in range(-2 * n, 2 * n + 1):
            for j in range(-2 * n, 2 * n + 1):
                for b in ((0.0, 0.0), (a / 2, a / (2 * math.sqrt(3)))):
                    p = (a * (i + j / 2) + b[0], a * j * math.sqrt(3) / 2 + b[1])
                    if math.hypot(*p) <= radius_nm + 1e-9:
                        q = rot(rot(p, t), phi)
                        atoms.append((q[0] * 10, q[1] * 10, layer * spacing_nm * 10))
    return sorted(atoms, key=lambda p: (p[2], round(p[1], 6), round(p[0], 6)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for key, (paper, theta) in SAMPLES.items():
        name = 'TBG-%s-AA-map.txt' % key
        pts = aa_map(theta, name)
        text = '\n'.join([str(len(pts)), 'AA-stacked region centres of a model rigid twisted bilayer graphene (sample %s), nanometres' % key] +
                         ['AA %.6f %.6f' % p for p in pts]) + '\n'
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
        files[name] = dict(paper=paper, sample=key, twist_deg=theta, period_nm=period(theta), points=len(pts), kind='AA-site map',
                           asset_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())
    for key in ('K110',):
        paper, theta = SAMPLES[key]
        name = 'TBG-%s-atoms.xyz' % key
        atoms = patch(theta, name)
        text = '\n'.join([str(len(atoms)), 'Carbon atoms of both layers of a model rigid twisted bilayer graphene near an AA site (sample %s), angstrom' % key] +
                         ['C %.6f %.6f %.6f' % p for p in atoms]) + '\n'
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
        files[name] = dict(paper=paper, sample=key, twist_deg=theta, period_nm=period(theta), points=len(atoms), kind='atomistic patch',
                           asset_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())
    (OUT / 'sources.json').write_text(json.dumps(dict(route='paper_parameter_model', papers=PAPERS, lattice_constant_nm=A_NM,
                                                      model='rigid twist (no lattice relaxation, no heterostrain); AA map within %.0f nm; '
                                                            'atomistic patch within 2.0 nm, layer spacing 3.35 A' % MAP_RADIUS,
                                                      files=files), ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: (v['points'], round(v['period_nm'], 3)) for k, v in files.items()}))


if __name__ == '__main__':
    main()
