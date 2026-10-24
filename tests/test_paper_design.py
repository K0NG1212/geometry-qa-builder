"""The design_choice family (design route 1: a documented optimization campaign) and its checker."""
import copy
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checkers  # noqa: E402
from checkers import paper_design as checker_design  # noqa: E402
from checkers.common import CheckError  # noqa: E402
from task_families import paper_design  # noqa: E402

MANIFEST = {x['id']: x for x in json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))['items']}
SPECS = [x for x in MANIFEST.values() if x['family'] == 'design_choice']
SEED = 'test-seed'


def build(instance, target=1, **change):
    spec = dict(MANIFEST[instance], target_position=target, **change)
    return spec, paper_design.build(spec, ROOT, SEED)


def check(spec, built, **packet_change):
    packet = dict(id=spec['id'], family=spec['family'], question=built['question'], inputs=built['inputs'],
                  options=built['options'])
    packet.update(packet_change)
    key = dict(id=spec['id'], family=spec['family'], correct_label=built['correct_label'], numeric_answer=None,
               input_hashes=built['input_hashes'])
    return checkers.check(packet, key)


class FamilyTests(unittest.TestCase):
    def test_six_cards_and_every_position_passes(self):
        self.assertEqual(len(SPECS), 15)                 # 3 papers x 2 targets (v39) + 9 cards from the B3 pilot
        for spec in SPECS:
            for target in (1, 2, 3, 4):
                s, built = build(spec['id'], target)
                self.assertEqual(built['correct_label'], 'ABCD'[target - 1])
                self.assertEqual(check(s, built)['status'], 'pass', (spec['id'], target))

    def test_choices_are_the_ones_the_papers_report(self):
        expect = {'FA-DES-VIN-WALLS': 'H2-NMeAc', 'FA-DES-VIN-MV': 'H1-MV',
                  'FA-DES-RAN-NITRATE': 'BnBU-CHCl3', 'FA-DES-RAN-BROMIDE': 'BU2-CHCl3',
                  'FA-DES-CHE-SIEVE': 'UTSA-16(Co)', 'FA-DES-CHE-FLOW': 'Cu-4Py-Me'}
        for instance, choice in expect.items():
            built = build(instance)[1]
            self.assertEqual(built['checks']['paper_choice'], choice, instance)
            self.assertEqual(built['options'][0]['value'].split(':')[0], choice, instance)

    def test_two_targets_over_one_table_pick_opposite_structures(self):
        """The same four measured frameworks, two different targets, two different answers."""
        sieve, flow = build('FA-DES-CHE-SIEVE')[1], build('FA-DES-CHE-FLOW')[1]
        self.assertEqual({o['value'] for o in sieve['options']}, {o['value'] for o in flow['options']})
        self.assertNotEqual(sieve['checks']['paper_choice'], flow['checks']['paper_choice'])

    def test_measured_values_are_not_shown_to_the_student(self):
        """The reviewer-side table must not leak into the question, the attachment or the options.

        Only the displays that carry a unit or a power of ten are searched for: a bare '8' or '15' collides
        with ordinary numbers in the setting text, so the leak that matters is the property itself, which the
        second half of this test covers.
        """
        marks = ('mmol', '× 10^', '> ')
        for spec in SPECS:
            s, built = build(spec['id'])
            shown = built['question'] + built['inputs'][0]['text'] + ''.join(o['value'] for o in built['options'])
            for values in built['checks']['measured'].values():
                for display in values.values():
                    if any(mark in display for mark in marks):
                        self.assertNotIn(display, shown, (spec['id'], display))
            described = built['inputs'][0]['text'] + ''.join(o['value'] for o in built['options'])
            for word in ('selectivity', 'uptake', 'binding constant', 'association constant', 'Ka'):
                self.assertNotIn(word, described, (spec['id'], word))

    def test_candidate_attachment_order_does_not_track_the_answer(self):
        lines = [l.split(':')[0] for l in build('FA-DES-VIN-WALLS', 1)[1]['inputs'][0]['text'].rstrip().split('\n')]
        self.assertEqual(lines, sorted(lines))
        for target in (2, 3, 4):
            other = [l.split(':')[0] for l in build('FA-DES-VIN-WALLS', target)[1]['inputs'][0]['text'].rstrip().split('\n')]
            self.assertEqual(lines, other)


class CardRuleTests(unittest.TestCase):
    """The card rules the engine enforces; each is checked by breaking a copy of a real card."""

    def setUp(self):
        self.spec = dict(MANIFEST['FA-DES-CHE-SIEVE'], target_position=1)
        self.card = json.loads((ROOT / 'docs' / self.spec['asset']).read_text(encoding='utf-8'))

    def broken(self, mutate):
        card = copy.deepcopy(self.card)
        mutate(card)
        return card

    def run_with(self, card):
        original = paper_design.load
        paper_design.load = lambda root, rel: (card, json.dumps(card).encode('utf-8'))
        try:
            return paper_design.build(self.spec, ROOT, SEED)
        finally:
            paper_design.load = original

    def assert_refused(self, message, mutate):
        with self.assertRaisesRegex(ValueError, message):
            self.run_with(self.broken(mutate))

    def test_an_unmeasured_candidate_is_refused(self):
        def drop(card):
            del card['candidates'][1]['measured']['uptake_30K']
        self.assert_refused('no measured', drop)

    def test_a_measured_value_without_a_place_in_the_paper_is_refused(self):
        def blank(card):
            card['candidates'][1]['measured']['uptake_30K']['locator'] = ''
        self.assert_refused('no place in the paper', blank)

    def test_a_value_that_differs_from_the_printed_one_is_refused(self):
        def tamper(card):
            card['candidates'][0]['measured']['uptake_30K']['value'] = 9.9
        self.assert_refused('not stored as the paper prints it', tamper)

    def test_a_threshold_not_printed_in_the_target_is_refused(self):
        def tamper(card):
            card['constraints'][0]['value'] = 7
        self.assert_refused('not printed in the target', tamper)

    def test_a_second_candidate_meeting_the_target_is_refused(self):
        def tamper(card):
            card['candidates'][1]['measured']['uptake_30K'].update(value=3.0, display='3.0 mmol g^-1')
        self.assert_refused('2 candidates meet the target', tamper)

    def test_a_candidate_sitting_on_a_threshold_is_refused(self):
        def tamper(card):
            card['candidates'][2]['measured']['S_30K'].update(value=11.0, display='11')
        self.assert_refused('within the margin', tamper)

    def test_a_lower_bound_may_not_refute_a_lower_bound_target(self):
        """'> 16' proves the selectivity target is met; it can never prove one is missed."""
        def tamper(card):
            card['constraints'][0].update(value=40, display='40', text='... at least 40')
            card['candidates'][0]['measured']['S_30K'].update(value=60.0, display='60')
        self.assert_refused('lower bound cannot settle', tamper)

    def test_the_winner_must_be_the_candidate_the_paper_chose(self):
        def tamper(card):
            card['paper_choice'] = 'Ag-Bpz'
        self.assert_refused('not the one the paper chose', tamper)


class CheckerTests(unittest.TestCase):
    def test_a_swapped_key_label_is_caught(self):
        spec, built = build('FA-DES-RAN-NITRATE', 2)
        built = copy.deepcopy(built)
        built['correct_label'] = 'C'
        self.assertEqual(check(spec, built)['status'], 'fail')

    def test_an_altered_candidate_attachment_is_caught(self):
        spec, built = build('FA-DES-RAN-NITRATE')
        text = built['inputs'][0]['text'].replace('3.13 A', '3.50 A')
        report = check(spec, built, inputs=[dict(built['inputs'][0], text=text)])
        self.assertEqual(report['status'], 'fail')
        self.assertIn('differs from the card', report['problem'])

    def test_a_question_without_the_stated_target_is_caught(self):
        spec, built = build('FA-DES-CHE-FLOW')
        question = built['question'].replace('at least 5 mmol g^-1', 'at least 1 mmol g^-1')
        report = check(spec, built, question=question)
        self.assertEqual(report['status'], 'fail')
        self.assertIn('not stated in the question', report['problem'])

    def test_a_tampered_card_fails_the_hash(self):
        spec, built = build('FA-DES-VIN-WALLS')
        built = copy.deepcopy(built)
        built['input_hashes'][spec['asset']] = '0' * 64
        self.assertIn('hash mismatch', check(spec, built)['problem'])


class MarginKindTests(unittest.TestCase):
    """B1e: a ratio margin suits a quantity with a true zero, an absolute one a logarithm or a Celsius
    temperature. Both the family and the checker must agree on which test applies."""

    CARD = dict(margin=1.2)

    def con(self, value, **kw):
        return dict(dict(key='k', property='p', op='>=', value=value), **kw)

    def near(self, con, value):
        """The family and the checker must reach the same verdict on the same numbers."""
        own = con.get('margin')
        mine = paper_design.clear_of(con, self.CARD, value)
        theirs = checker_design.far_enough(con.get('margin_kind', 'ratio'),
                                           Decimal(repr(own)) if own is not None else Decimal(repr(self.CARD['margin'])),
                                           Decimal(repr(value)), Decimal(repr(con['value'])))
        self.assertEqual(mine, theirs, (con, value))
        return mine

    def test_ratio_margin_is_the_default_and_unchanged(self):
        self.assertTrue(self.near(self.con(1e5), 2.5e5))           # 2.5x above
        self.assertTrue(self.near(self.con(1e5), 4.7e3))           # far below
        self.assertFalse(self.near(self.con(1e5), 1.1e5))          # 1.1x: inside the margin

    def test_a_celsius_threshold_needs_an_absolute_margin(self):
        hot = self.con(59, margin=2, margin_kind='absolute')
        self.assertTrue(self.near(hot, 61.2))                      # 2.2 degrees clear
        self.assertTrue(self.near(hot, 55.4))                      # 3.6 degrees clear
        self.assertFalse(self.near(hot, 60.5))                     # 1.5 degrees: too close
        # Why a Celsius card must not use the ratio test: what counts as "clear" then depends on where zero
        # sits. The same 1.2-fold margin rejects a 1.5 K gap just above 59 degrees but accepts a 10 K one.
        self.assertFalse(self.near(self.con(59), 60.5))
        self.assertTrue(self.near(self.con(49), 59))

    def test_an_absolute_margin_accepts_negative_values_and_zero_thresholds(self):
        shift = self.con(0, margin=1.5, margin_kind='absolute')    # a delta-Tm, which may be negative
        self.assertTrue(self.near(shift, -3.8))
        self.assertTrue(self.near(shift, 8.1))
        self.assertFalse(self.near(shift, 0.8))

    def test_bad_margins_are_refused_on_both_sides(self):
        with self.assertRaises(ValueError):
            paper_design.clear_of(self.con(5, margin=0, margin_kind='absolute'), self.CARD, 9)
        with self.assertRaises(ValueError):
            paper_design.clear_of(self.con(5, margin=1.0), self.CARD, 9)
        with self.assertRaises(ValueError):
            paper_design.clear_of(self.con(0), self.CARD, 9)        # ratio against zero
        with self.assertRaises(ValueError):
            paper_design.clear_of(self.con(5, margin_kind='logarithmic'), self.CARD, 9)
        for bad in (dict(kind='absolute', margin=Decimal(0)), dict(kind='ratio', margin=Decimal(1))):
            with self.assertRaises(CheckError):
                checker_design.far_enough(bad['kind'], bad['margin'], Decimal(9), Decimal(5))

    @unittest.skipUnless((ROOT / 'docs/assets/families/design/resolved/kim2024-ace2-disulfide-ptr.json').exists(),
                         'the absolute-margin card is not present')
    def test_the_celsius_card_builds_and_passes_at_every_position(self):
        spec = dict(id='FA-DES-ACE2-SS', family='design_choice', scope='B1e 验证用例',
                    asset='assets/families/design/resolved/kim2024-ace2-disulfide-ptr.json')
        for target in (1, 2, 3, 4):
            built = paper_design.build(dict(spec, target_position=target), ROOT, SEED)
            self.assertEqual(built['correct_label'], 'ABCD'[target - 1])
            answer = [o['value'] for o in built['options'] if o['label'] == built['correct_label']][0]
            self.assertTrue(answer.startswith('M2:'), answer)
            self.assertEqual(check(spec, built)['status'], 'pass')


if __name__ == '__main__':
    unittest.main()
