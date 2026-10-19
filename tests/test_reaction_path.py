"""The reaction-path families (azobenzene, Landscape17) and their checkers."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checkers  # noqa: E402
import task_families  # noqa: E402
from task_families import reaction_path  # noqa: E402

MANIFEST = {x['id']: x for x in json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))['items']}
MECHANISM = [x for x in MANIFEST.values() if x['family'] == 'reaction_mechanism_choice']
TARGET = [x for x in MANIFEST.values() if x['family'] == 'reaction_geometry_target']
PERCEPTION = [x for x in MANIFEST.values() if x['id'].startswith('FA-RXN-') and x['family'].startswith('named_')]
SEED = 'test-seed'


def build(instance, target=1, **change):
    spec = dict(MANIFEST[instance], target_position=target, **change)
    return spec, task_families.FAMILIES[spec['family']]['build'](spec, ROOT, SEED)


def check(spec, built, **packet_change):
    packet = dict(id=spec['id'], family=spec['family'], question=built['question'], inputs=built['inputs'],
                  options=built['options'])
    packet.update(packet_change)
    key = dict(id=spec['id'], family=spec['family'], correct_label=built['correct_label'],
               numeric_answer=built.get('numeric'), input_hashes=built['input_hashes'])
    return checkers.check(packet, key)


class FamilyTests(unittest.TestCase):
    def test_eleven_instances_and_every_position_passes(self):
        self.assertEqual((len(PERCEPTION), len(MECHANISM), len(TARGET)), (6, 3, 2))
        for spec in PERCEPTION + MECHANISM + TARGET:
            for target in (1, 2, 3, 4):
                s, built = build(spec['id'], target)
                self.assertEqual(check(s, built)['status'], 'pass', (spec['id'], target))

    def test_the_new_families_place_the_answer_at_the_batch_target(self):
        for spec in MECHANISM + TARGET:
            for target in (1, 2, 3, 4):
                self.assertEqual(build(spec['id'], target)[1]['correct_label'], 'ABCD'[target - 1], spec['id'])

    def test_published_geometry_of_the_inversion_transition_state(self):
        """Landscape17 coordsts_0_1: one C-N=N angle opens to 179 degrees, the other stays bent."""
        d = build('FA-RXN-MECH-TS01')[1]['checks']['descriptors']
        self.assertEqual(round(d['angle_a'], 3), 115.941)
        self.assertEqual(round(d['angle_b'], 3), 179.228)
        self.assertEqual(round(d['nn_distance'], 4), 1.2190)
        self.assertEqual((d['near_linear_count'], d['ring_plane']), (1, 'undefined'))

    def test_the_dihedral_is_declared_undefined_once_an_angle_has_opened(self):
        """A C-N=N angle near 180 degrees makes the dihedral ill-conditioned, so the rule must not use it."""
        inversion = build('FA-RXN-MECH-TS01')[1]['checks']['descriptors']
        self.assertEqual(inversion['ring_plane'], 'undefined')
        for instance in ('FA-RXN-MECH-TS11', 'FA-RXN-MECH-TS002'):
            d = build(instance)[1]['checks']['descriptors']
            self.assertEqual((d['near_linear_count'], d['ring_plane']), (0, 'planar'), instance)

    def test_each_transition_state_gets_the_mechanism_its_geometry_implies(self):
        expect = {'FA-RXN-MECH-TS01': 'inversion_at_one_nitrogen',
                  'FA-RXN-MECH-TS11': 'no_configuration_change',
                  'FA-RXN-MECH-TS002': 'no_configuration_change'}
        for instance, rule in expect.items():
            self.assertEqual(build(instance)[1]['checks']['conclusion'], rule, instance)

    def test_measured_perception_values_match_the_published_coordinates(self):
        expect = {'FA-RXN-TS01-ANG-CB': '179.23', 'FA-RXN-TS01-ANG-CA': '115.94', 'FA-RXN-MIN1-ANG-CB': '114.40',
                  'FA-RXN-TS01-NN': '1.219', 'FA-RXN-MIN1-NN': '1.245', 'FA-RXN-TS01-CN': '1.336'}
        for instance, value in expect.items():
            self.assertEqual(build(instance)[1]['numeric']['value'], value, instance)

    def test_candidate_files_carry_no_hint_of_the_answer(self):
        for spec in TARGET:
            for target in (1, 2, 3, 4):
                built = build(spec['id'], target)[1]
                names = [i['name'] for i in built['inputs']]
                self.assertEqual(names, ['candidate-%d.xyz' % (i + 1) for i in range(4)])
                self.assertEqual([o['value'] for o in built['options']],
                                 ['candidate-%d' % (i + 1) for i in range(4)])
                for item in built['inputs']:
                    self.assertNotIn('coordsts', item['text'])
                    self.assertNotIn('coordsplus', item['text'])


class CardRuleTests(unittest.TestCase):
    def setUp(self):
        self.spec = dict(MANIFEST['FA-RXN-MECH-TS01'], target_position=1)
        self.card = json.loads((ROOT / 'docs' / self.spec['asset']).read_text(encoding='utf-8'))

    def run_with(self, card, spec=None):
        original = reaction_path.load
        reaction_path.load = lambda root, rel, family: (card, json.dumps(card).encode('utf-8'))
        try:
            spec = spec or self.spec
            return task_families.FAMILIES[spec['family']]['build'](spec, ROOT, SEED)
        finally:
            reaction_path.load = original

    def assert_refused(self, message, mutate, spec=None, source=None):
        card = copy.deepcopy(source if source is not None else self.card)
        mutate(card)
        with self.assertRaisesRegex(ValueError, message):
            self.run_with(card, spec)

    def test_a_hypothesis_that_predicts_too_little_is_refused(self):
        def drop(card):
            del card['hypotheses'][0]['predicts']['ring_plane']
        self.assert_refused('must predict exactly', drop)

    def test_two_surviving_hypotheses_are_refused(self):
        def clash(card):
            card['hypotheses'][1]['predicts'] = dict(card['hypotheses'][0]['predicts'])
        self.assert_refused('Exactly one hypothesis', clash)

    def test_a_conclusion_that_does_not_survive_is_refused(self):
        def move(card):
            for h in card['hypotheses']:
                h.pop('mechanism_conclusion', None)
            card['hypotheses'][1]['mechanism_conclusion'] = True
        self.assert_refused('Exactly one hypothesis', move)

    def test_reference_minima_on_the_same_side_are_refused(self):
        def same(card):
            [a] = [f for f in card['files'] if f['key'] == 'min_a']
            [b] = [f for f in card['files'] if f['key'] == 'min_b']
            a['asset'] = b['asset']
        self.assert_refused('one cis and one trans', same)

    def test_a_fragment_atom_of_the_wrong_element_is_refused(self):
        def wrong(card):
            card['atoms']['c_a'] = 7            # row 7 is a hydrogen in every azobenzene file
        self.assert_refused('is not C', wrong)

    def test_a_threshold_not_printed_in_its_requirement_is_refused(self):
        spec = dict(MANIFEST['FA-RXN-TARGET-ANGLE'], target_position=1)
        source = json.loads((ROOT / 'docs' / spec['asset']).read_text(encoding='utf-8'))

        def tamper(card):
            card['constraints'][0]['value'] = 140
        self.assert_refused('not printed in the requirement', tamper, spec, source)

    def test_a_candidate_sitting_on_a_threshold_is_refused(self):
        spec = dict(MANIFEST['FA-RXN-TARGET-ANGLE'], target_position=1)
        source = json.loads((ROOT / 'docs' / spec['asset']).read_text(encoding='utf-8'))

        def tamper(card):
            card['constraints'][0].update(value=134, display='134',
                                          text='the larger of the two C-N=N angles is at most 134 degrees')
        self.assert_refused('within', tamper, spec, source)

    def test_a_winner_other_than_the_expected_candidate_is_refused(self):
        spec = dict(MANIFEST['FA-RXN-TARGET-SPEC'], target_position=1)
        source = json.loads((ROOT / 'docs' / spec['asset']).read_text(encoding='utf-8'))

        def tamper(card):
            card['expected'] = 'azobenzene-min-0'
        self.assert_refused('not the one the card expects', tamper, spec, source)


class CheckerTests(unittest.TestCase):
    def test_a_swapped_key_label_is_caught(self):
        spec, built = build('FA-RXN-MECH-TS01', 2)
        built = copy.deepcopy(built)
        built['correct_label'] = 'D'
        self.assertEqual(check(spec, built)['status'], 'fail')

    def test_an_altered_transition_state_is_caught(self):
        spec, built = build('FA-RXN-MECH-TS01')
        inputs = copy.deepcopy(built['inputs'])
        inputs[0]['text'] = inputs[0]['text'].replace('C 0.00000000', 'C 0.10000000', 1)
        report = check(spec, built, inputs=inputs)
        self.assertEqual(report['status'], 'fail')
        self.assertIn('differs from its asset', report['problem'])

    def test_a_question_with_a_moved_threshold_is_caught(self):
        """Raise the near-linear threshold past 180 and the rule stops recognising the opened angle, so the
        checker reclassifies the structure as planar and the card's conclusion no longer survives."""
        spec, built = build('FA-RXN-MECH-TS01')
        question = built['question'].replace('exceed 160 degrees', 'exceed 190 degrees')
        report = check(spec, built, question=question)
        self.assertEqual(report['status'], 'fail')
        self.assertIn('not the one the card concludes', report['problem'])

    def test_a_relaxed_requirement_in_the_question_is_caught(self):
        spec, built = build('FA-RXN-TARGET-ANGLE')
        question = built['question'].replace('at most 132 degrees', 'at most 140 degrees')
        report = check(spec, built, question=question)
        self.assertEqual(report['status'], 'fail')
        self.assertIn('not stated in the question', report['problem'])

    def test_a_tampered_card_fails_the_hash(self):
        spec, built = build('FA-RXN-TARGET-SPEC')
        built = copy.deepcopy(built)
        built['input_hashes'][spec['asset']] = '0' * 64
        self.assertIn('hash mismatch', check(spec, built)['problem'])


if __name__ == '__main__':
    unittest.main()
