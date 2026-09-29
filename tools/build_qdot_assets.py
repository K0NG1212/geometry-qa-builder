"""Build model CdSe nanocrystals (quantum, 1-10 nm) for the Yu et al. (2003) sizing-curve families.

Paper parameters (numbers only; read from the article, not redistributed): Yu, Qu, Guo, Peng, "Experimental
Determination of the Extinction Coefficient of CdTe, CdSe, and CdS Nanocrystals", Chem. Mater. 15, 2854-2860
(2003), doi:10.1021/cm034081k:
  CdSe: D = 1.6122e-9 L^4 - 2.6575e-6 L^3 + 1.6242e-3 L^2 - 0.4277 L + 41.57  (D in nm, L = first excitonic
  absorption peak in nm); extinction coefficient at that peak eps = 5857 D^2.65 (1/(M cm)). The paper warns
  the polynomial may be invalid outside the sizes it was fitted to.

Model particles (built here, disclosed as models): spheres cut from ideal zinc-blende CdSe with an assumed
lattice constant of 6.08 A, centred between a Cd and a Se site, rotated by a SHA-256-derived rotation.
XYZ in angstrom (4 decimals). Only the coordinates matter for the answers.

python tools/build_qdot_assets.py
"""
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_superlattice_assets import rotation  # noqa: E402

OUT = ROOT / 'docs/assets/families/qdots'
A = 6.08
PAPER = dict(citation='Yu W. W., Qu L., Guo W., Peng X., Chem. Mater. 15, 2854-2860 (2003)', doi='https://doi.org/10.1021/cm034081k',
             numbers='CdSe sizing polynomial D(lambda) and eps = 5857 D^2.65 (eqs. 2 and 6)',
             caveat='polynomial fitting functions; may be invalid outside the fitted size range')
TARGETS = {'CdSe-QD-A': 2.8, 'CdSe-QD-B': 3.3, 'CdSe-QD-C': 3.8, 'CdSe-QD-D': 4.3, 'CdSe-QD-E': 5.0}   # nominal cut diameters, nm


def particle(diameter_nm, name):
    r = diameter_nm * 10 / 2
    centre = (A / 8, A / 8, A / 8)
    n = int(r / A) + 2
    atoms = []
    for i, j, k in itertools.product(range(-n, n + 1), repeat=3):
        for b in ((0, 0, 0), (0.5, 0.5, 0), (0.5, 0, 0.5), (0, 0.5, 0.5)):
            for element, shift in (('Cd', 0.0), ('Se', 0.25)):
                p = tuple((c + s + shift) * A - o for c, s, o in zip((i, j, k), b, centre))
                if math.sqrt(sum(x * x for x in p)) <= r:
                    atoms.append((element, p))
    rot = rotation(name)
    out = [(e, tuple(sum(rot[m][c] * p[c] for c in range(3)) for m in range(3))) for e, p in atoms]
    return sorted(out, key=lambda a: (a[0], round(a[1][2], 4), round(a[1][1], 4), round(a[1][0], 4)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for key, d in TARGETS.items():
        name = '%s.xyz' % key
        atoms = particle(d, name)
        text = '\n'.join([str(len(atoms)), 'Model zinc-blende CdSe nanocrystal %s (spherical cut, no ligands), angstrom' % key] +
                         ['%s %.4f %.4f %.4f' % (e, *p) for e, p in atoms]) + '\n'
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
        pts = [p for _, p in atoms]
        dmax = max(math.dist(p, q) for p, q in itertools.combinations(pts, 2)) / 10
        files[name] = dict(nominal_diameter_nm=d, atoms=len(atoms), cd=sum(e == 'Cd' for e, _ in atoms), dmax_nm=dmax,
                           asset_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())
    (OUT / 'sources.json').write_text(json.dumps(dict(route='paper_parameter_model', paper=PAPER, lattice_constant_A=A,
                                                      model='spheres cut from ideal zinc-blende CdSe (assumed a = 6.08 A), centred at (1/8,1/8,1/8)a, '
                                                            'rotated by the SHA-256-derived rotation of the file name; no ligands or relaxation',
                                                      files=files), ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: (v['atoms'], round(v['dmax_nm'], 3)) for k, v in files.items()}))


if __name__ == '__main__':
    main()
