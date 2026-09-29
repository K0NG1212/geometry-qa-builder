"""Build paper-parameter models of DNA-linked gold-nanoparticle superlattices (materials, 10-100 nm).

Source of the parameters: Hill, Macfarlane, Senesi, Lee, Park, Mirkin, "Controlling the Lattice
Parameters of Gold Nanoparticle FCC Crystals with Duplex DNA Linkers", Nano Lett. 2008, 8, 2341-2344,
doi:10.1021/nl8011787 (NIH author manuscript PMC8191496), Table 1: SAXS-measured FCC unit-cell edge
lengths for five linkers. Only these numbers are used; no text or figure is redistributed.

Each model is an ideal FCC crystallite of particle centres (all lattice points within 2.2 a of a lattice
point at the origin), rotated by a deterministic rotation derived from SHA-256 of the model name, so that
the lattice has to be recognised from the coordinates. Coordinates are in nanometres, 6 decimals.
It is a model built from reported parameters, not an observed particle list.

python tools/build_superlattice_assets.py
"""
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/families/superlattices'
PAPER = dict(citation='Hill HD, Macfarlane RJ, Senesi AJ, Lee B, Park SY, Mirkin CA. Nano Lett. 2008, 8(8), 2341-2344.',
             doi='https://doi.org/10.1021/nl8011787', open_copy='https://pmc.ncbi.nlm.nih.gov/articles/PMC8191496/',
             table='Table 1 (trends in FCC crystal parameters)', particle='~10 nm Au cores (10.3 nm stated in the SAXS discussion)')
# linker: (nearest-neighbour distance nm, unit-cell edge nm, % Au) exactly as printed in Table 1
TABLE1 = {'X-linker': (28.1, 39.8, 3.74), '13-linker': (32.4, 45.9, 2.44), '26-linker': (40.3, 57.0, 1.27),
          '39-linker': (47.7, 67.5, 0.77), '52-linker': (54.2, 76.6, 0.52)}
RADIUS_CELLS = 2.2


def rotation(name):
    """Uniform random rotation (Shoemake) from three hash-derived numbers in [0, 1)."""
    h = hashlib.sha256(name.encode('utf-8')).digest()
    u1, u2, u3 = (int.from_bytes(h[i:i + 8], 'big') / 2 ** 64 for i in (0, 8, 16))
    a, b = math.sqrt(1 - u1), math.sqrt(u1)
    x, y, z, w = a * math.sin(2 * math.pi * u2), a * math.cos(2 * math.pi * u2), b * math.sin(2 * math.pi * u3), b * math.cos(2 * math.pi * u3)
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def crystallite(a, name):
    basis = [(0, 0, 0), (0.5, 0.5, 0), (0.5, 0, 0.5), (0, 0.5, 0.5)]
    n = math.ceil(RADIUS_CELLS) + 1
    pts = set()
    for i, j, k in itertools.product(range(-n, n + 1), repeat=3):
        for b in basis:
            p = ((i + b[0]) * a, (j + b[1]) * a, (k + b[2]) * a)
            if math.sqrt(sum(c * c for c in p)) <= RADIUS_CELLS * a + 1e-9:
                pts.add(p)
    r = rotation(name)
    rotated = [tuple(sum(r[m][c] * p[c] for c in range(3)) for m in range(3)) for p in sorted(pts)]
    return sorted(rotated, key=lambda p: (round(p[2], 6), round(p[1], 6), round(p[0], 6)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for linker, (nn, a, gold) in TABLE1.items():
        name = 'Au-FCC-%s.xyz' % linker
        pts = crystallite(a, name)
        text = '\n'.join([str(len(pts)), 'Au nanoparticle centres of a model DNA-linked superlattice crystallite (%s), nanometres' % linker] +
                         ['Au %.6f %.6f %.6f' % p for p in pts]) + '\n'
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
        files[name] = dict(linker=linker, table1=dict(nearest_neighbor_nm=nn, unit_cell_edge_nm=a, percent_gold=gold),
                           model='ideal FCC, conventional edge a = %.1f nm (Table 1), lattice points within %.1f a of the origin, '
                                 'rotated by the SHA-256-derived rotation of the file name' % (a, RADIUS_CELLS),
                           particles=len(pts), asset_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())
    (OUT / 'sources.json').write_text(json.dumps(dict(route='paper_parameter_model', paper=PAPER,
                                                      note='Numbers from Table 1 only; nearest-neighbour distances in the model follow a/sqrt(2) '
                                                           'from the printed edge length and may differ from the printed D in the last digit.',
                                                      files=files), ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v['particles'] for k, v in files.items()}))


if __name__ == '__main__':
    main()
