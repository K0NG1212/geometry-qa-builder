"""Build paper-parameter models of colloidal (opal) photonic crystals (materials, 100-1000 nm).

Parameters (numbers only; no text or figures redistributed):
  * Polystyrene opals: Gazmeh et al., "Investigation of optical properties of three dimensional reflectance
    rulers fabricated by size-controlled monodisperse polystyrene colloidal particles", Sci. Rep. 15, 38349
    (2025), doi:10.1038/s41598-025-22161-5 (PMC12583473, CC BY-NC-ND 4.0). Table 3: FESEM sphere diameters and
    measured normal-incidence reflection peaks; PS index 1.59 (simulation table).
  * Silica opal: Fookes, Polo Parada, Fidalgo, "A Robust Method for the Elaboration of SiO2-Based Colloidal
    Crystals as a Template for Inverse Opal Structures", Sensors 23, 1433 (2023), doi:10.3390/s23031433
    (PMC9920682, CC BY 4.0). Parameter table: particle size 266 nm, n(SiO2) 1.46, n_eff 1.35, incidence 30 deg;
    expected band gap ~547 nm; measured peaks 528-538 nm.

Model: touching spheres on an ideal FCC lattice (nearest-neighbour distance = sphere diameter D, a = D*sqrt(2)),
all lattice points within 2.2 a of a lattice point, rotated by the SHA-256-derived rotation of the file name.
One row per sphere centre: "sphere x y z" in nanometres (6 decimals), after a count line and a comment line.

python tools/build_opal_assets.py
"""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_superlattice_assets import crystallite, RADIUS_CELLS  # noqa: E402

OUT = ROOT / 'docs/assets/families/opals'
PS = dict(citation='Gazmeh M. et al., Sci. Rep. 15, 38349 (2025)', doi='https://doi.org/10.1038/s41598-025-22161-5',
          open_copy='https://pmc.ncbi.nlm.nih.gov/articles/PMC12583473/', license='CC BY-NC-ND 4.0 (numbers only are used)',
          table='Table 3 (FESEM diameter, experimental peak at normal incidence); simulation table: material index 1.59')
SIO2 = dict(citation='Fookes F., Polo Parada L., Fidalgo M., Sensors 23, 1433 (2023)', doi='https://doi.org/10.3390/s23031433',
            open_copy='https://pmc.ncbi.nlm.nih.gov/articles/PMC9920682/', license='CC BY 4.0',
            table='Parameter table: particle size 266 nm, SiO2 index 1.46, air 1, n_eff 1.35, m = 1, incidence 30 deg; '
                  'text: band gap expected at ~547 nm, measured peaks 528-538 nm')
# name: (paper, sample, FESEM/SEM diameter nm, measured peak nm or None)
SAMPLES = {'PS-S2': ('ps', 'S2', 369.38, 872.5), 'PS-S3': ('ps', 'S3', 341.83, 805.0), 'PS-S4': ('ps', 'S4', 326.97, 765.0),
           'PS-S5': ('ps', 'S5', 258.62, 614.5), 'PS-S6': ('ps', 'S6', 249.11, 592.0), 'PS-S7': ('ps', 'S7', 224.76, 532.0),
           'PS-S8': ('ps', 'S8', 208.85, 492.0), 'SiO2-266': ('sio2', '266 nm', 266.0, None)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for key, (paper, sample, d, peak) in SAMPLES.items():
        name = 'opal-%s.xyz' % key
        pts = crystallite(d * math.sqrt(2), name)
        material = 'polystyrene' if paper == 'ps' else 'silica'
        text = '\n'.join([str(len(pts)), 'Sphere centres of a model %s opal crystallite (touching spheres, FCC), nanometres' % material] +
                         ['sphere %.6f %.6f %.6f' % p for p in pts]) + '\n'
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
        files[name] = dict(paper=paper, sample=sample, diameter_nm=d, measured_peak_nm=peak, material=material,
                           model='touching spheres, ideal FCC, a = D*sqrt(2), lattice points within %.1f a, rotated by the '
                                 'SHA-256-derived rotation of the file name' % RADIUS_CELLS,
                           spheres=len(pts), asset_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())
    (OUT / 'sources.json').write_text(json.dumps(dict(route='paper_parameter_model', papers=dict(ps=PS, sio2=SIO2), files=files,
                                                      note='Model coordinates are generated here; only the listed numbers come from the papers.'),
                                                 ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v['spheres'] for k, v in files.items()}))


if __name__ == '__main__':
    main()
