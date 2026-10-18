"""Evidence-to-conclusion families (evidence_quantity, evidence_elimination) and their checker."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checkers  # noqa: E402
from task_families import evidence  # noqa: E402

MANIFEST = {x['id']: x for x in json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))['items']}
SPECS = [x for x in MANIFEST.values() if x['family'].startswith('evidence_')]
SEED = 'test-seed'


def build(instance, target=1, **change):
    spec = dict(MANIFEST[instance], target_position=target, **change)
    fn = evidence.build_quantity if spec['family'] == 'evidence_quantity' else evidence.build_elimination
    return spec, fn(spec, ROOT, SEED)


def check(spec, built, **packet_change):
    packet = dict(id=spec['id'], family=spec['family'], question=built['question'], inputs=built['inputs'], options=built['options'])
    packet.update(packet_change)
    key = dict(id=spec['id'], family=spec['family'], correct_label=built['correct_label'], numeric_answer=None,
               input_hashes=built['input_hashes'])
    return checkers.check(packet, key)


class QuantityTests(unittest.TestCase):
    def test_twenty_seven_cards_and_every_position_passes(self):
        self.assertEqual(len(SPECS), 27)                 # batch 1 (13) + batch 2 (6) + batch 3 (8)
        for spec in SPECS:
            for target in (1, 2, 3, 4):
                s, built = build(spec['id'], target)
                self.assertEqual(built['correct_label'], 'ABCD'[target - 1])
                self.assertEqual(check(s, built)['status'], 'pass', (spec['id'], target))

    def test_values_match_the_papers(self):
        expect = {'FA-EVQ-CAO-COHERENCE': '25.8', 'FA-EVQ-CAO-SQUID': '0.092', 'FA-EVQ-CAO-PAULI': '36.54',
                  'FA-EVQ-KER-STRAIN': '1.18', 'FA-EVQ-SCH-FLUX': '28.6', 'FA-EVQ-SHA-BAND': '85.9', 'FA-EVQ-DIN-HTP': '0.76',
                  'FA-EVQ-FOO-LAYERS': '5.93',
                  'FA-EVQ-FIL-RBCS': '0.075', 'FA-EVQ-JIA-CLAMP': '16.13'}
        for instance, shown in expect.items():     # paper: ~26 nm, 0.09 µm², ~36 T, 1.18°, 28.6, 85.6 nm measured, 76 %
            self.assertEqual(build(instance)[1]['checks']['shown'], shown, instance)

    def test_structure_values_come_from_the_si_coordinates(self):
        self.assertEqual(build('FA-EVQ-ALT-OHSHIFT')[1]['checks']['shown'], '-0.196')    # O6···O14 2.538 − O5···N11 2.734 Å
        self.assertEqual(build('FA-EVQ-ALT-NHO')[1]['checks']['shown'], '0.126')         # N9···O8 2.789 − N3···O13 2.664 Å

    def test_options_are_the_four_combinations(self):
        spec, built = build('FA-EVQ-CAO-SQUID')
        rules = sorted(a['rule'] for a in built['option_audit'])
        self.assertEqual(rules, sorted(['correct', 'uniform_whole_device', 'normal_flux_quantum', 'normal_flux_quantum+uniform_whole_device']))

    def test_checker_rejects_tampering(self):
        spec, built = build('FA-EVQ-CAO-COHERENCE')
        evidence_txt = copy.deepcopy(built['inputs'])
        evidence_txt[0]['text'] = evidence_txt[0]['text'].replace('1.5 × 10^11', '1.2 × 10^11')
        self.assertEqual(check(spec, built, inputs=evidence_txt)['status'], 'fail')
        swapped = copy.deepcopy(built['options'])
        swapped[0]['value'], swapped[1]['value'] = swapped[1]['value'], swapped[0]['value']
        self.assertEqual(check(spec, built, options=swapped)['status'], 'fail')
        spec2, built2 = build('FA-EVQ-ALT-NHO')
        moved = copy.deepcopy(built2['inputs'])
        moved[1]['text'] = moved[1]['text'].replace('-1.5658', '-1.6658')
        self.assertEqual(check(spec2, built2, inputs=moved)['status'], 'fail')

    def test_mistake_too_close_is_refused(self):
        spec = dict(MANIFEST['FA-EVQ-DIN-HTP'], target_position=1)
        card, raw = evidence.load(ROOT, spec['asset'])
        card['quantity']['min_separation'] = '0.5'
        original = evidence.load
        evidence.load = lambda root, rel: (card, raw)
        try:
            with self.assertRaises(ValueError):
                evidence.build_quantity(spec, ROOT, SEED)
        finally:
            evidence.load = original


class EliminationTests(unittest.TestCase):
    def test_only_the_paper_conclusion_survives(self):
        for instance in [s['id'] for s in SPECS if s['family'] == 'evidence_elimination']:
            spec, built = build(instance)
            contradicted = built['checks']['contradicted_by']
            self.assertEqual(contradicted['paper_conclusion'], [])
            self.assertTrue(all(v for k, v in contradicted.items() if k != 'paper_conclusion'), instance)

    def test_racemic_control_is_what_rules_out_handedness(self):
        spec, built = build('FA-EVE-SHA-IONS')
        self.assertEqual(built['checks']['contradicted_by']['right_handed_helix'], ['E3'])

    def test_a_second_survivor_is_refused(self):
        card, _ = evidence.load(ROOT, MANIFEST['FA-EVE-COT-BEND']['asset'])
        card = copy.deepcopy(card)
        card['hypotheses'][3]['predicts'] = dict(dark_bands=True)          # magnetic domains no longer contradicted
        survivors, _ = evidence.eliminate(card)
        self.assertEqual(len(survivors), 2)

    def test_checker_rejects_a_wrong_key(self):
        spec, built = build('FA-EVE-ALT-THREE', 2)
        packet = dict(id=spec['id'], family=spec['family'], question=built['question'], inputs=built['inputs'], options=built['options'])
        key = dict(id=spec['id'], family=spec['family'], correct_label='A', numeric_answer=None, input_hashes=built['input_hashes'])
        self.assertEqual(checkers.check(packet, key)['status'], 'fail')


class CardTests(unittest.TestCase):
    def test_every_fact_and_conclusion_has_a_locator(self):
        for spec in SPECS:
            card, _ = evidence.load(ROOT, spec['asset'])
            self.assertTrue(all(f['locator'].strip() for f in card['facts']), spec['id'])
            if card['family'] == 'evidence_quantity':
                self.assertTrue(card['conclusions']['paper']['locator'] and card['conclusions']['rejected']['locator'])
            else:
                self.assertTrue(all(h['locator'].strip() for h in card['hypotheses']))

    def test_sources_record_every_card(self):
        sources = json.loads((ROOT / 'docs/assets/families/evidence/sources.json').read_text(encoding='utf-8'))
        recorded = {c['file'] for p in sources['papers'].values() for c in p['cards']}
        self.assertEqual(recorded, {Path(s['asset']).name for s in SPECS})


if __name__ == '__main__':
    unittest.main()
