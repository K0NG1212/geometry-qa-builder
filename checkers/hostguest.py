"""Independent checker for the SAMPL9 WP6 evidence families (chemistry, 1-10 nm).
No generation code is imported. The checker reads the transcribed measurement table named in the answer key
(hash-verified), confirms that every supplied structure is the published SAMPL9 file for the guest its option
names, that the question states the measurement conditions, and re-derives the choice from the measured
binding free energies with the same policy margins.
"""
import json
import re
from .common import need, find, verify_hashes

MARGIN = 0.8
THRESHOLD_GAP = 0.3


def evidence_and_guests(packet, key):
    paths = verify_hashes(key)
    ev_path = [p for rel, p in paths.items() if rel.endswith('WP6-binding.json')]
    need(len(ev_path) == 1, 'Evidence table not recorded in the key')
    evidence = json.loads(ev_path[0].read_text(encoding='utf-8'))
    q = packet['question']
    need('pH 7.40' in q and '298.15 K' in q and 'isothermal titration calorimetry' in q, 'Measurement conditions not stated')
    by_name = {p.name: p for p in paths.values()}
    for inp in packet['inputs']:
        need(inp['name'] in by_name and by_name[inp['name']].read_bytes() == inp['text'].encode('utf-8'), 'Input is not the published file: ' + inp['name'])
    guests = []
    for o in packet['options']:
        m = re.fullmatch(r'(G\d+): (.+) \(WP6-(G\d+)\.xyz\)', o['value'])
        need(m is not None and m.group(1) == m.group(3), 'Option does not name one guest file')
        g = m.group(1)
        need(g in evidence['guests'] and evidence['guests'][g]['name'] == m.group(2), 'Guest name does not match the table')
        need('WP6-%s.xyz' % g in {i['name'] for i in packet['inputs']}, 'Structure for option guest not supplied')
        guests.append((o['label'], g))
    return evidence, guests


def binding_evidence_choice(packet, key):
    evidence, guests = evidence_and_guests(packet, key)
    need('most negative measured binding free energy' in packet['question'], 'Criterion not stated')
    dg = {label: evidence['guests'][g]['DG_kcal_mol'] for label, g in guests}
    ranked = sorted(dg, key=dg.get)
    need(dg[ranked[1]] - dg[ranked[0]] >= MARGIN, 'Measured winner does not lead by the margin')
    need(key['correct_label'] == ranked[0], 'Key label disagrees with the measured ranking')
    return dict(label=ranked[0], parameters=dict(measured_DG=dg), method='measured ITC ΔG from the SAMPL9 table')


def binding_design_choice(packet, key):
    evidence, guests = evidence_and_guests(packet, key)
    q = packet['question']
    ref = find(r'You start from guest (G\d+)', q, 'Reference guest not stated').group(1)
    gain = float(find(r'at least ([\d.]+) kcal/mol more strongly', q, 'Target gain not stated').group(1))
    stated = float(find(r'under these conditions is (−?-?[\d.]+) kcal/mol', q, 'Reference value not stated').group(1).replace('−', '-'))
    dg0 = evidence['guests'][ref]['DG_kcal_mol']
    need(abs(stated - dg0) < 1e-9, 'Stated reference ΔG differs from the table')
    gains = {label: dg0 - evidence['guests'][g]['DG_kcal_mol'] for label, g in guests}
    need(all(g != ref for _, g in guests), 'Reference guest offered as a candidate')
    ok = [label for label, v in gains.items() if v >= gain]
    need(len(ok) == 1, 'Not exactly one candidate meets the target')
    need(all(abs(v - gain) >= THRESHOLD_GAP for v in gains.values()), 'A candidate sits too close to the threshold')
    need(key['correct_label'] == ok[0], 'Key label disagrees with the measured data')
    return dict(label=ok[0], parameters=dict(reference=ref, improvement=gains), method='measured ITC ΔG; design threshold')


CHECKERS = {'binding_evidence_choice': binding_evidence_choice, 'binding_design_choice': binding_design_choice}
