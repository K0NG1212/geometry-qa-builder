"""Build paper-parameter models of cholesteric (chiral nematic) liquid-crystal films (chemistry, 100-1000 nm).

Numbers only (no text or figures redistributed):
  * Shaban, Wu, Jia, Lee, "Overlooked Ionic Contribution of a Chiral Dopant in Cholesteric Liquid Crystals", Materials 17, 5080
    (2024), doi:10.3390/ma17205080 (PMC11509098, CC BY 4.0): host E44 (ne = 1.7904, no = 1.5484 at 589 nm, 20 C); HTP of
    R5011/S5011 in E44 = 107.5 /um; 2.62 wt% R5011 (right-handed) and 2.57 wt% S5011 (left-handed), pitch from p = 1/(HTP c)
    = 0.355 / 0.362 um; measured reflection centres 585 +- 1 and 593 +- 3 nm, bandwidth 85.6 nm (R5011, 20 C).
  * Dinc, Lub, Kragt, Schenning, Org. Chem. Front. (2024), doi:10.1039/d4qo01672f (PMC11492181, CC BY 3.0): reactive
    isosorbide dopants; reflection 670 nm (left-handed LRCD coating) and 603 nm (right-handed RRCD coating), pitch from
    lambda = n p with average index 1.6 (419 and 377 nm).

Model: ideal cholesteric helix with a uniform director twist, sites every 5 nm along a helix axis of arbitrary (SHA-256-derived)
direction over 1500 nm; rows "site x y z nx ny nz" (position in nm, unit director). Right-handed: the director turns
counter-clockwise (from e1 towards e2) when advancing along the axis u, with (e1, e2, u) right-handed.

python tools/build_cholesteric_assets.py
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/families/cholesteric'
HTP = 107.5            # /um, R5011 or S5011 in E44
PAPERS = dict(shaban=dict(citation='Shaban H. et al., Materials 17, 5080 (2024)', doi='https://doi.org/10.3390/ma17205080',
                          open_copy='https://pmc.ncbi.nlm.nih.gov/articles/PMC11509098/', license='CC BY 4.0'),
              dinc=dict(citation='Dinc R. U. et al., Org. Chem. Front. (2024)', doi='https://doi.org/10.1039/d4qo01672f',
                        open_copy='https://pmc.ncbi.nlm.nih.gov/articles/PMC11492181/', license='CC BY 3.0'))
# name: (paper, handedness +1 right / -1 left, pitch nm, description, measured reflection nm or None)
FILMS = {'E44-R5011-2.62wt': ('shaban', +1, 1e3 / (HTP * 0.0262), 'E44 + 2.62 wt% R5011', 585.0),
         'E44-S5011-2.57wt': ('shaban', -1, 1e3 / (HTP * 0.0257), 'E44 + 2.57 wt% S5011', 593.0),
         'LRCD-coating': ('dinc', -1, 670.0 / 1.6, 'reactive mesogen + 5.6 wt% LRCD', 670.0),
         'RRCD-coating': ('dinc', +1, 603.0 / 1.6, 'reactive mesogen + 4.7 wt% RRCD', 603.0)}
for c in (2.2, 2.4, 2.9, 3.0, 3.4):          # design candidates: R5011 in E44 at other concentrations (model, not measured)
    FILMS['E44-R5011-%.2fwt' % c] = ('shaban', +1, 1e3 / (HTP * c / 100), 'E44 + %.2f wt%% R5011 (model concentration)' % c, None)
LENGTH, STEP = 1500.0, 5.0


def frame(name):
    h = hashlib.sha256(name.encode('utf-8')).digest()
    u1, u2, u3 = (int.from_bytes(h[i:i + 8], 'big') / 2 ** 64 for i in (0, 8, 16))
    z = 2 * u1 - 1
    r = math.sqrt(1 - z * z)
    u = (r * math.cos(2 * math.pi * u2), r * math.sin(2 * math.pi * u2), z)
    t = (1.0, 0.0, 0.0) if abs(u[0]) < 0.9 else (0.0, 1.0, 0.0)
    e1 = cross(t, u)
    e1 = norm(e1)
    e2 = cross(u, e1)
    phi0 = 2 * math.pi * u3
    c, s = math.cos(phi0), math.sin(phi0)
    return u, tuple(c * a + s * b for a, b in zip(e1, e2)), tuple(-s * a + c * b for a, b in zip(e1, e2))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


def film(name, hand, pitch):
    u, e1, e2 = frame(name)
    rows = []
    for k in range(int(LENGTH / STEP) + 1):
        s = k * STEP
        phi = hand * 2 * math.pi * s / pitch
        n = tuple(math.cos(phi) * a + math.sin(phi) * b for a, b in zip(e1, e2))
        rows.append(tuple(s * x for x in u) + n)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for key, (paper, hand, pitch, desc, measured) in FILMS.items():
        name = 'clc-%s.txt' % key
        rows = film(name, hand, pitch)
        text = '\n'.join([str(len(rows)), 'Director field of a model cholesteric film (%s); site x y z (nm) nx ny nz (unit director)' % desc] +
                         ['site %.6f %.6f %.6f %.8f %.8f %.8f' % r for r in rows]) + '\n'
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
        files[name] = dict(paper=paper, handedness='right' if hand > 0 else 'left', pitch_nm=pitch, description=desc,
                           measured_reflection_nm=measured, sites=len(rows), asset_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())
    (OUT / 'sources.json').write_text(json.dumps(dict(route='paper_parameter_model', papers=PAPERS, htp_per_um=HTP,
                                                      e44=dict(ne=1.7904, no=1.5484, wavelength_nm=589, T_C=20),
                                                      model='ideal uniform twist; sites every 5 nm over 1500 nm along a SHA-256-derived axis',
                                                      files=files), ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: (v['handedness'], round(v['pitch_nm'], 2)) for k, v in files.items()}))


if __name__ == '__main__':
    main()
