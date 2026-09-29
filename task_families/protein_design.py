"""Protein design choices with computed geometric evidence (biology 0.1-1 and 1-10 nm).

disulfide_design (0.1-1 nm): choose the one residue pair (of four) that meets stated disulfide-engineering
    screening windows for the Cα–Cα and Cβ–Cβ distances; every other pair misses a window by a margin.
fret_design (1-10 nm): choose the labelling-site pair (of four) whose point-dye FRET efficiency for a stated R0
    is closest to a target; the winner must lead clearly.
Inputs are ATOM records of the residues involved, copied unchanged from the PDB entry.
"""
import math
from . import kit
from .local_geometry import read_pdb_residues

VERSION = '0.1.0'
CA_WINDOW = (4.4, 6.8)
CB_WINDOW = (3.45, 4.50)
MARGIN = 0.2          # angstrom: failing pairs miss a window by at least this much


def excerpt(spec, root, numbers):
    raw = (root / 'docs' / spec['asset']).read_bytes()
    residues, order, altloc = read_pdb_residues(raw.decode('utf-8'), spec['chain'])
    if any(n not in residues for n in numbers) or altloc & set(numbers):
        raise ValueError('Residue missing or has alternate locations')
    text = '\n'.join(line for n in sorted(set(numbers)) for line in residues[n]['lines']) + '\nEND\n'
    return residues, text, kit.sha256(raw)


def name(res, n):
    return '%s%d' % (res[n]['name'].strip().title(), n)


def finish(spec, seed, correct, others, reason, question, text, digest, checks, reasoning_nm, definition, pdb):
    order = kit.place(('correct', correct, reason, 3), others, spec.get('target_position'), seed, spec['id'], key=lambda p: p[0])
    options = [dict(label=l, value=p[1]) for l, p in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [p[0] == 'correct' for p in order])
    audit = [dict(label=l, value=p[1], rule=p[0], reason=p[2], is_correct=p[0] == 'correct') for l, p in zip(kit.LABELS, order)]
    return dict(question=question, scope=spec['scope'],
                inputs=[dict(name='%s-%s-design-excerpt.pdb' % (pdb, spec['id'].split('-')[-1]), format='pdb-excerpt', unit='angstrom', text=text)],
                numeric=None, options=options, correct_label=key, option_audit=audit, excluded_candidates=[], rank=None, checks=checks,
                scales=dict(input_nm=reasoning_nm, reasoning_nm=reasoning_nm, reasoning_definition=definition), input_hashes={spec['asset']: digest})


def build_disulfide(spec, root, seed):
    pairs = [tuple(p) for p in spec['pairs']]
    residues, text, digest = excerpt(spec, root, [n for p in pairs for n in p])
    rows = []
    for i, j in pairs:
        if residues[i]['name'] in ('CYS', 'GLY') or residues[j]['name'] in ('CYS', 'GLY') or abs(i - j) < 3:
            raise ValueError('Pairs must be non-Cys, non-Gly and at least three residues apart')
        a, b = residues[i]['atoms'], residues[j]['atoms']
        dca, dcb = math.dist(a['CA'], b['CA']), math.dist(a['CB'], b['CB'])
        miss_ca = max(CA_WINDOW[0] - dca, dca - CA_WINDOW[1], 0)
        miss_cb = max(CB_WINDOW[0] - dcb, dcb - CB_WINDOW[1], 0)
        rows.append(dict(pair=(i, j), label='%s–%s' % (name(residues, i), name(residues, j)), dca=dca, dcb=dcb, miss_ca=miss_ca, miss_cb=miss_cb))
    ok = [r for r in rows if r['miss_ca'] == 0 and r['miss_cb'] == 0]
    if len(ok) != 1:
        raise ValueError('Exactly one pair must meet both windows')
    if any(0 < max(r['miss_ca'], r['miss_cb']) < MARGIN for r in rows if r is not ok[0]):
        raise ValueError('A failing pair sits too close to a window')
    others = []
    for r in rows:
        if r is ok[0]:
            continue
        if r['miss_ca'] == 0:
            others.append(('calpha_only', r['label'], 'Cα–Cα %.2f Å 在窗口内，但 Cβ–Cβ %.2f Å 不在 3.45–4.50 Å（只看 Cα 会误选）。' % (r['dca'], r['dcb']), 3))
        elif r['miss_cb'] == 0:
            others.append(('cbeta_only', r['label'], 'Cβ–Cβ %.2f Å 在窗口内，但 Cα–Cα %.2f Å 不在 4.4–6.8 Å（只看 Cβ 会误选）。' % (r['dcb'], r['dca']), 3))
        else:
            others.append(('both_out', r['label'], 'Cα–Cα %.2f Å、Cβ–Cβ %.2f Å 均不在窗口内。' % (r['dca'], r['dcb']), 2))
    w = ok[0]
    question = ('The excerpt contains the ATOM records of the %d residues involved, from chain %s of PDB entry %s (%s), copied unchanged (angstrom). '
                'To engineer a new disulfide bond, both residues of one pair will be mutated to cysteine. Use these screening windows: '
                'Cα–Cα distance between 4.4 and 6.8 Å and Cβ–Cβ distance between 3.45 and 4.50 Å (both inclusive). Exactly one of the '
                'four candidate pairs meets both windows. Which pair should you mutate?' % (len({n for p in pairs for n in p}), spec['chain'], spec['pdb'], spec['context']))
    return finish(spec, seed, w['label'], others, 'Cα–Cα %.2f Å，Cβ–Cβ %.2f Å，两项均在窗口内。' % (w['dca'], w['dcb']), question, text, digest,
                  dict(pairs=[{k: r[k] for k in ('label', 'dca', 'dcb', 'miss_ca', 'miss_cb')} for r in rows], windows=dict(CA=CA_WINDOW, CB=CB_WINDOW),
                       design_note='设计选择：蛋白工程中筛选可引入二硫键的位点；证据为计算的几何距离。',
                       limits='只用几何窗口筛选；不评估二面角、应变能或对折叠稳定性的实际影响。'),
                  max(r['dca'] for r in rows) / 10, '候选残基对中最大的 Cα–Cα 距离', spec['pdb'])


def efficiency(r, r0, power=6):
    return 1 / (1 + (r / r0) ** power)


def build_fret(spec, root, seed):
    pairs = [tuple(p) for p in spec['pairs']]
    atom, r0, t = spec['atom'], spec['r0_nm'], spec['target']
    residues, text, digest = excerpt(spec, root, [n for p in pairs for n in p])
    rows = []
    for i, j in pairs:
        r = math.dist(residues[i]['atoms'][atom], residues[j]['atoms'][atom]) / 10
        rows.append(dict(label='%s–%s' % (name(residues, i), name(residues, j)), r=r, E=efficiency(r, r0),
                         wrong=dict(complement=1 - efficiency(r, r0), inverse_square=efficiency(r, r0, 2), angstrom_as_nm=efficiency(r * 10, r0 * 10 / 10))))
    if any(not 1.0 <= x['r'] < 10 for x in rows):
        raise ValueError('Label distances must lie in the 1-10 nm cell')
    ranked = sorted(rows, key=lambda x: abs(x['E'] - t))
    best, runner = ranked[0], ranked[1]
    if abs(runner['E'] - t) < 1.5 * abs(best['E'] - t) or abs(runner['E'] - t) - abs(best['E'] - t) < 0.05:
        raise ValueError('Winning margin too small')
    notes = dict(complement='把效率算成 1 − E', inverse_square='把 r⁶ 写成 r²')
    why = {}
    for rule in notes:
        pick = min(rows, key=lambda x: abs(x['wrong'][rule] - t))
        if pick is not best and pick['label'] not in why:
            why[pick['label']] = (rule, '%s时它最接近目标（%.3f）。' % (notes[rule], pick['wrong'][rule]), 3)
    for x in rows:
        if x is not best and x['label'] not in why:
            why[x['label']] = ('farther_from_target', 'r = %.2f nm，E = %.3f，离目标更远。' % (x['r'], x['E']), 2)
    others = [(why[x['label']][0], x['label'], why[x['label']][1], why[x['label']][2]) for x in rows if x is not best]
    kind = 'nucleotide' if spec.get('nucleic') else 'residue'
    question = ('The excerpt contains the ATOM records of the %d %ss involved, from chain %s of PDB entry %s (%s), copied unchanged (angstrom). You will '
                'attach a donor and an acceptor dye to one of the four candidate pairs; treat each dye as a point at the %s atom of its %s, '
                'with Förster radius R0 = %.1f nm and the standard point-dipole Förster law. You want a steady-state FRET efficiency as close '
                'as possible to %.2f. Which pair should you label?' % (len({n for p in pairs for n in p}), kind, spec['chain'], spec['pdb'], spec['context'], atom, kind, r0, t))
    return finish(spec, seed, best['label'], others, 'r = %.2f nm，E = %.3f，最接近目标。' % (best['r'], best['E']), question, text, digest,
                  dict(pairs=[{k: x[k] for k in ('label', 'r', 'E')} for x in rows], r0_nm=r0, target=t, atom=atom,
                       design_note='设计选择：按目标效率选择标记位点（推断的逆问题）；证据为计算的距离与 Förster 定律。',
                       limits='点偶极、取向因子已含于 R0；不含染料连接臂长度与构象涨落。'),
                  max(x['r'] for x in rows), '候选标记对中最大的点间距离', spec['pdb'])
