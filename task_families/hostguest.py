"""Host-guest binding with measured evidence (chemistry, 1-10 nm): SAMPL9 WP6.

The model receives the WP6 host and four candidate guests as 3D structures; the answer comes from the
measured ITC binding free energies (SAMPL9 experimental table, transcribed in WP6-binding.json), not from
a calculation. This is the evidence route of roadmap A2 (inference) and A3 (design with experimental
evidence): every candidate has a measured value, the winner must lead clearly (policy margin), and each
distractor carries its measured value as the reason.
"""
import json
from . import kit

VERSION = '0.1.0'
EVIDENCE = 'assets/families/hostguest/WP6-binding.json'
MARGIN = 0.8          # kcal/mol between the best and the second candidate (about 20x the ITC uncertainties here)
THRESHOLD_GAP = 0.3   # kcal/mol: no candidate may sit this close to a design threshold

CONTEXT = ('The files give the SAMPL9 WP6 host (a carboxylated pillar[6]arene; host file shown with 12 carboxylates) and four candidate '
           'guests as 3D structures (XYZ, angstrom). Binding to WP6 was measured by isothermal titration calorimetry in 1× PBS at '
           'pH 7.40 and 298.15 K; all complexes are 1:1.')


def load(root):
    raw = (root / 'docs' / EVIDENCE).read_bytes()
    return json.loads(raw.decode('utf-8')), kit.sha256(raw)


def inputs_for(root, evidence, guests):
    inputs, hashes = [], {}
    host = (root / 'docs' / evidence['host']).read_bytes()
    inputs.append(dict(name=evidence['host'].rsplit('/', 1)[1], format='xyz', unit='angstrom', text=host.decode('utf-8')))
    hashes[evidence['host']] = kit.sha256(host)
    for g in guests:
        path = evidence['guests'][g]['asset']
        raw = (root / 'docs' / path).read_bytes()
        inputs.append(dict(name=path.rsplit('/', 1)[1], format='xyz', unit='angstrom', text=raw.decode('utf-8')))
        hashes[path] = kit.sha256(raw)
    return inputs, hashes, kit.dmax(kit.parse_xyz(host.decode('utf-8'))[1]) / 10


def label(evidence, g):
    return '%s: %s (WP6-%s.xyz)' % (g, evidence['guests'][g]['name'], g)


def finish(spec, root, seed, question, correct, others, reason, evidence, digest, checks):
    order = kit.place(('correct', label(evidence, correct), reason, 3), others, spec.get('target_position'), seed, spec['id'], key=lambda p: p[0])
    options = [dict(label=l, value=p[1]) for l, p in zip(kit.LABELS, order)]
    key = kit.validate_verdicts(options, [p[0] == 'correct' for p in order])
    audit = [dict(label=l, value=p[1], rule=p[0], reason=p[2], is_correct=p[0] == 'correct') for l, p in zip(kit.LABELS, order)]
    guests = spec['guests']
    inputs, hashes, host_nm = inputs_for(root, evidence, guests)
    hashes[EVIDENCE] = digest
    return dict(question=question, scope=spec['scope'], inputs=inputs, numeric=None, options=options, correct_label=key,
                option_audit=audit, excluded_candidates=[], rank=None,
                checks=dict(checks, evidence_source=evidence['source'], conditions=evidence['conditions'],
                            limits='答案来自实测 ΔG（证据在审核侧，不给考生）；几何结构只是候选的呈现，不能单凭几何算出答案。'),
                scales=dict(input_nm=host_nm, reasoning_nm=host_nm, reasoning_definition='主体 WP6 的最大原子间距（主客体复合物尺度）'),
                input_hashes=hashes)


def build_evidence(spec, root, seed):
    evidence, digest = load(root)
    dg = {g: evidence['guests'][g]['DG_kcal_mol'] for g in spec['guests']}
    ranked = sorted(dg, key=dg.get)
    best, second = ranked[0], ranked[1]
    if dg[second] - dg[best] < MARGIN:
        raise ValueError('Measured winner does not lead by the policy margin')
    charge = lambda g: evidence['guests'][g]['smiles'].count('+]')
    others = []
    for g in ranked[1:]:
        rule = 'next_strongest' if g == second else ('dication_but_weaker' if charge(g) >= 2 else 'weaker_binder')
        why = {'next_strongest': '实测 ΔG = %.2f kcal/mol，次强，比最强弱 %.2f。',
               'dication_but_weaker': '虽为双阳离子，实测 ΔG = %.2f kcal/mol，比最强弱 %.2f（仅凭电荷判断会误选）。',
               'weaker_binder': '实测 ΔG = %.2f kcal/mol，比最强弱 %.2f。'}[rule] % (dg[g], dg[g] - dg[best])
        others.append((rule, label(evidence, g), why, 3 if rule != 'weaker_binder' else 2))
    question = ('%s Which guest binds WP6 most strongly, i.e. has the most negative measured binding free energy?' % CONTEXT)
    return finish(spec, root, seed, question, best, others, '实测 ΔG = %.2f ± %.2f kcal/mol，最负；领先 %.2f。'
                  % (dg[best], evidence['guests'][best]['dDG'], dg[second] - dg[best]), evidence, digest,
                  dict(measured_DG=dg, margin_kcal_mol=dg[second] - dg[best], policy_margin=MARGIN))


def build_design(spec, root, seed):
    evidence, digest = load(root)
    ref, gain = spec['reference'], spec['gain']
    dg0 = evidence['guests'][ref]['DG_kcal_mol']
    dg = {g: evidence['guests'][g]['DG_kcal_mol'] for g in spec['guests']}
    improvement = {g: dg0 - dg[g] for g in dg}
    ok = [g for g in dg if improvement[g] >= gain]
    if len(ok) != 1 or ref in dg:
        raise ValueError('Exactly one candidate must meet the target and the reference must not be a candidate')
    if any(abs(improvement[g] - gain) < THRESHOLD_GAP for g in dg):
        raise ValueError('A candidate sits too close to the design threshold')
    others = []
    charge = lambda g: evidence['guests'][g]['smiles'].count('+]')
    for g in dg:
        if g == ok[0]:
            continue
        if charge(g) >= 2:
            others.append(('dication_not_sufficient', label(evidence, g), '双阳离子（仅凭电荷会以为结合更强），实测 ΔG = %.2f，变化 %+.2f kcal/mol，未达 %.1f。'
                           % (dg[g], improvement[g], gain), 3))
        elif improvement[g] > 0:
            others.append(('improves_but_below_target', label(evidence, g), '实测 ΔG = %.2f，只改善 %.2f kcal/mol，未达 %.1f。' % (dg[g], improvement[g], gain), 3))
        else:
            others.append(('weakens_binding', label(evidence, g), '实测 ΔG = %.2f，反而减弱 %.2f kcal/mol。' % (dg[g], -improvement[g]), 2))
    name = evidence['guests'][ref]['name']
    question = ('%s You start from guest %s (%s), whose measured binding free energy to WP6 under these conditions is %.2f kcal/mol, and '
                'want a replacement guest that binds WP6 at least %.1f kcal/mol more strongly (measured ΔG ≤ %.2f kcal/mol). Exactly one of '
                'the four candidates achieves this in the measured data. Which one?' % (CONTEXT, ref, name, dg0, gain, dg0 - gain))
    return finish(spec, root, seed, question, ok[0], others, '实测 ΔG = %.2f，改善 %.2f kcal/mol，达到目标。' % (dg[ok[0]], improvement[ok[0]]),
                  evidence, digest, dict(reference=ref, reference_DG=dg0, target_gain=gain, measured_DG=dg, improvement=improvement,
                                         design_note='设计选择：四个候选均有实测值，恰好一个达到目标。'))
