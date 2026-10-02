"""Build paper-parameter models of Abrikosov vortex lattices (quantum, 100-1000 nm).

Numbers only (no text or figures redistributed):
  * Cottet et al., "Quantitative imaging of flux vortices in type-II superconductor MgB2 using Cryo-Lorentz Transmission
    Electron Microscopy", arXiv:1401.4062: MgB2 single crystal at 5 K, applied fields 50.8, 56.1, 117.3 and 188.7 G; measured
    vortex spacings compared with the triangular-lattice value r = 1.075 (Phi0/B)^1/2 (their Fig. 5B).
  * Schaefermeier et al., "Quantitative imaging of Abrikosov vortices by scanning quantum magnetometry", arXiv:2602.13060
    (CC BY-NC-ND 4.0): BSCCO-2212 single crystal at 71 K, field-cooled at 3.7 mT, measured lattice constant a ~ 0.855 um
    (effective field ~3.26 mT from B = (2/sqrt 3) Phi0 / a^2).

Model: ideal triangular vortex lattice (one flux quantum per vortex) with a = (2 Phi0 / (sqrt(3) B))^1/2 for the MgB2 fields and
a = 855 nm for BSCCO; vortex centres within 5.2 a of one vortex, rows "V x y" in nm (6 decimals), rotated in-plane by a
SHA-256-derived angle.

python tools/build_vortex_assets.py
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/families/vortex'
PHI0 = 2.067833848e-15            # Wb, h / 2e
PAPERS = dict(cottet=dict(citation='Cottet M. J. G. et al., arXiv:1401.4062 (MgB2, cryo-Lorentz TEM, 5 K)', url='https://arxiv.org/abs/1401.4062'),
              schaefermeier=dict(citation='Schaefermeier C. et al., arXiv:2602.13060 (BSCCO-2212, scanning NV magnetometry, 71 K)',
                                 url='https://arxiv.org/abs/2602.13060', license='CC BY-NC-ND 4.0 (numbers only are used)'))
SAMPLES = {'MgB2-508G': ('cottet', 5.08e-3, None), 'MgB2-561G': ('cottet', 5.61e-3, None), 'MgB2-1173G': ('cottet', 11.73e-3, None),
           'MgB2-1887G': ('cottet', 18.87e-3, None), 'BSCCO-855nm': ('schaefermeier', None, 855.0)}


def spacing(b_tesla):
    return math.sqrt(2 * PHI0 / (math.sqrt(3) * b_tesla)) * 1e9          # nm


def angle(name):
    return int.from_bytes(hashlib.sha256(name.encode('utf-8')).digest()[:8], 'big') / 2 ** 64 * 2 * math.pi


def lattice(a, name, radius_cells=5.2):
    phi, n = angle(name), int(radius_cells) + 2
    pts = []
    for i in range(-2 * n, 2 * n + 1):
        for j in range(-2 * n, 2 * n + 1):
            x, y = a * (i + j / 2), a * j * math.sqrt(3) / 2
            if math.hypot(x, y) <= radius_cells * a + 1e-9:
                pts.append((x * math.cos(phi) - y * math.sin(phi), x * math.sin(phi) + y * math.cos(phi)))
    return sorted(pts, key=lambda p: (round(p[1], 6), round(p[0], 6)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for key, (paper, b, a_measured) in SAMPLES.items():
        a = a_measured if a_measured else spacing(b)
        name = 'vortex-%s.txt' % key
        pts = lattice(a, name)
        text = '\n'.join([str(len(pts)), 'Vortex centres of a model Abrikosov lattice (%s), nanometres' % key] + ['V %.6f %.6f' % p for p in pts]) + '\n'
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
        files[name] = dict(paper=paper, field_T=b, measured_spacing_nm=a_measured, spacing_nm=a, vortices=len(pts),
                           asset_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())
    (OUT / 'sources.json').write_text(json.dumps(dict(route='paper_parameter_model', papers=PAPERS, phi0_Wb=PHI0,
                                                      model='ideal triangular lattice, one flux quantum per vortex; a = (2 Phi0/(sqrt3 B))^1/2 '
                                                            '(MgB2 fields) or the measured a (BSCCO); centres within 5.2 a; SHA-256-derived rotation',
                                                      files=files), ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: (v['vortices'], round(v['spacing_nm'], 2)) for k, v in files.items()}))


if __name__ == '__main__':
    main()
