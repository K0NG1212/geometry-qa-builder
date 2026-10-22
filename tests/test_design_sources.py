"""Design cards whose measured values are read from the paper's JATS XML (pointer cards, HANDOFF_2026-10-21 §1).

The rendering tests run anywhere. The rest need the local full texts in inputs/papers/ (not in the repository)
and are skipped, with a message, where they are missing.
"""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from xml.dom import minidom
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checkers  # noqa: E402
from checkers import paper_sources  # noqa: E402
from task_families import paper_design  # noqa: E402
from tools import jats, resolve_design_cards  # noqa: E402

DESIGN = ROOT / 'docs/assets/families/design'
POINTERS = sorted((DESIGN / 'pointers').glob('*.json'))
MANIFEST = {x['id']: x for x in json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))['items']}
SPECS = [x for x in MANIFEST.values() if x['family'] == 'design_choice']
XML_PATHS = {json.loads(p.read_text(encoding='utf-8'))['paper_xml']['path'] for p in POINTERS}
HAVE_XML = bool(XML_PATHS) and all((ROOT / x).exists() for x in XML_PATHS)
NEEDS_XML = unittest.skipUnless(HAVE_XML, 'paper XML not in inputs/papers/ on this machine')

SAMPLE = ('<article><body><sec><title>Results</title><p>UTSA&#173;-16(Co) gives S<sub>D2/H2</sub> &gt; 16 and '
          '2.7 mmol g<sup>&#8211;1</sup><xref ref-type="bibr">12</xref>.</p>'
          '<table-wrap id="t1"><label>Table 1</label><table><thead><tr><th>Anion</th><th colspan="2">K<sub>a</sub> '
          '[M<sup>&#8722;1</sup>]</th></tr></thead><tbody>'
          '<tr><td rowspan="2">NO<sub>3</sub><sup>&#8722;</sup></td><td>(1.07 &#177; 0.10) &#215; 10<sup>7[</sup>'
          '<xref ref-type="table-fn"><sup>a</sup></xref><sup>]</sup></td><td>x</td></tr>'
          '<tr><td>5.1 &#215; 10<sup>5</sup></td><td>y</td></tr></tbody></table></table-wrap></sec></body></article>')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def resolved_rel(pointer_path):
    return 'assets/families/design/resolved/' + pointer_path.name


def build(spec, asset, target):
    return paper_design.build(dict(spec, asset=asset, target_position=target), ROOT, 'test-seed')


class RenderingTests(unittest.TestCase):
    """Both readers must render the same text under the documented rules."""

    def test_entities_soft_hyphens_superscripts_and_markers(self):
        tree = ET.fromstring(SAMPLE)
        self.assertEqual(jats.render(tree.find('.//p')), 'UTSA-16(Co) gives SD2/H2 > 16 and 2.7 mmol g^-1.')
        doc = minidom.parseString(SAMPLE)
        self.assertEqual(paper_sources.text_of(doc.getElementsByTagName('p')[0]), jats.render(tree.find('.//p')))

    def test_spans_expand_identically_in_both_grids(self):
        grid = jats.table(ET.fromstring(SAMPLE), 'Table 1')
        self.assertEqual(grid, [['Anion', 'Ka [M^-1]', 'Ka [M^-1]'],
                                ['NO3^-', '(1.07 ± 0.10) × 10^7', 'x'],
                                ['NO3^-', '5.1 × 10^5', 'y']])
        self.assertEqual(paper_sources.grid_of(minidom.parseString(SAMPLE), 'Table 1'), grid)

    def test_ambiguous_labels_are_refused(self):
        with self.assertRaises(ValueError):          # two rows labelled NO3^- after the rowspan
            jats.cell(ET.fromstring(SAMPLE), 'Table 1', 'NO3^-', 'Anion')

    def test_exact_values(self):
        self.assertEqual(resolve_design_cards.exact_value('5.1 × 10^5'), 510000.0)
        self.assertEqual(resolve_design_cards.exact_value('(1.07 ± 0.10) × 10^7'), 10700000.0)
        self.assertEqual(resolve_design_cards.exact_value('> 16'), 16.0)


@NEEDS_XML
class ResolvedCardTests(unittest.TestCase):
    def test_six_pointer_cards_resolve_to_the_stored_cards_and_pass(self):
        self.assertEqual(len(POINTERS), 6)
        for p in POINTERS:
            rel = 'assets/families/design/pointers/' + p.name
            self.assertEqual(resolve_design_cards.dump(resolve_design_cards.resolve(rel)),
                             (ROOT / 'docs' / resolved_rel(p)).read_bytes(), p.name)
            self.assertEqual(paper_sources.check_card(resolved_rel(p), ROOT)['status'], 'pass', p.name)

    def test_every_value_read_from_the_paper_matches_the_transcription(self):
        for p in POINTERS:
            card = json.loads((ROOT / 'docs' / resolved_rel(p)).read_text(encoding='utf-8'))
            old = json.loads((ROOT / 'docs' / card['derived_from_card']).read_text(encoding='utf-8'))
            for c, o in zip(card['candidates'], old['candidates']):
                self.assertEqual(c['id'], o['id'])
                for prop, entry in c['measured'].items():
                    was = o['measured'][prop]
                    self.assertEqual((entry['display'], entry['value'], entry.get('bound')),
                                     (was['display'], was['value'], was.get('bound')), (p.name, c['id'], prop))

    def test_questions_from_resolved_cards_equal_the_v39_questions(self):
        self.assertEqual(len(SPECS), 6)
        for spec in SPECS:
            new_asset = spec['asset']                    # the manifest builds from the resolved card since v40
            self.assertTrue(new_asset.startswith('assets/families/design/resolved/'), spec['id'])
            old_asset = json.loads((ROOT / 'docs' / new_asset).read_text(encoding='utf-8'))['derived_from_card']
            for target in (1, 2, 3, 4):
                old, new = build(spec, old_asset, target), build(spec, new_asset, target)
                for field in ('question', 'options', 'correct_label', 'inputs', 'numeric'):
                    self.assertEqual(old[field], new[field], (spec['id'], target, field))
                packet = dict(id=spec['id'], family=spec['family'], question=new['question'], inputs=new['inputs'],
                              options=new['options'])
                key = dict(id=spec['id'], family=spec['family'], correct_label=new['correct_label'],
                           numeric_answer=None, input_hashes=new['input_hashes'])
                self.assertEqual(checkers.check(packet, key)['status'], 'pass', (spec['id'], target))


@NEEDS_XML
class TamperTests(unittest.TestCase):
    """A paper whose numbers differ from the ones resolved must fail, even with every hash brought up to date."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def copy(self, name, xml_edit=None, card_edit=None):
        """A self-consistent copy (all hashes recomputed) of one pointer card, its resolved card and its XML."""
        pointer = json.loads((DESIGN / 'pointers' / name).read_text(encoding='utf-8'))
        resolved = json.loads((DESIGN / 'resolved' / name).read_text(encoding='utf-8'))
        xml = (ROOT / pointer['paper_xml']['path']).read_bytes()
        if xml_edit:
            changed = xml.replace(*xml_edit)
            self.assertNotEqual(changed, xml, 'edit did not apply')
            xml = changed
        if card_edit:
            card_edit(pointer, resolved)
        (self.tmp / pointer['paper_xml']['path']).parent.mkdir(parents=True)
        (self.tmp / pointer['paper_xml']['path']).write_bytes(xml)
        pointer['paper_xml']['sha256'] = sha(xml)
        raw = resolve_design_cards.dump(pointer)
        (self.tmp / 'docs/assets/families/design/pointers').mkdir(parents=True)
        (self.tmp / 'docs/assets/families/design/pointers' / name).write_bytes(raw)
        resolved['paper_xml']['sha256'] = sha(xml)
        resolved['resolved_from'].update(pointer_sha256=sha(raw), paper_xml_sha256=sha(xml))
        (self.tmp / 'docs/assets/families/design/resolved').mkdir(parents=True)
        (self.tmp / 'docs/assets/families/design/resolved' / name).write_bytes(resolve_design_cards.dump(resolved))
        return paper_sources.check_card('assets/families/design/resolved/' + name, self.tmp)

    def test_untouched_copy_passes(self):
        self.assertEqual(self.copy('rando2025-nitrate-ptr.json')['status'], 'pass')

    def test_hash_mismatch_alone_is_caught(self):
        name = 'rando2025-nitrate-ptr.json'
        self.copy(name)
        xml = next(self.tmp.rglob('*.xml'))
        xml.write_bytes(xml.read_bytes() + b' ')
        report = paper_sources.check_card('assets/families/design/resolved/' + name, self.tmp)
        self.assertEqual(report['status'], 'fail')
        self.assertIn('hash mismatch', report['problem'])

    def test_one_changed_table_cell_fails(self):
        report = self.copy('rando2025-nitrate-ptr.json',
                           xml_edit=(b'<td rowspan="1" colspan="1">1.8 \xc3\x97 10<sup>9</sup>',
                                     b'<td rowspan="1" colspan="1">1.9 \xc3\x97 10<sup>9</sup>'))
        self.assertEqual(report['status'], 'fail')
        self.assertIn('the paper prints', report['problem'])

    def test_one_changed_number_in_the_prose_fails(self):
        report = self.copy('chetry2026-sieving-ptr.json', xml_edit=(b'= 15)', b'= 13)'))
        self.assertEqual(report['status'], 'fail')
        self.assertIn('quote found 0 times', report['problem'])

    def test_a_number_filed_under_the_wrong_candidate_fails(self):
        def swap(pointer, resolved):                   # Cu-4Py-Me's selectivity of 8 claimed for Ag-Bpz
            for card in (pointer, resolved):
                ag = next(c for c in card['candidates'] if c['id'] == 'Ag-Bpz')
                cu = next(c for c in card['candidates'] if c['id'] == 'Cu-4Py-Me')
                ag['measured']['S_30K'] = json.loads(json.dumps(cu['measured']['S_30K']))
                src = ag['measured']['S_30K'].get('source', ag['measured']['S_30K'])
                src['subject'] = 'Ag-Bpz'
        report = self.copy('chetry2026-sieving-ptr.json', card_edit=swap)
        self.assertEqual(report['status'], 'fail')
        self.assertIn('nearest candidate', report['problem'])

    def test_resolved_card_edited_after_resolving_fails(self):
        def edit(pointer, resolved):
            resolved['candidates'][0]['geometry'] += ' (edited)'
        report = self.copy('vincent2025-walls-ptr.json', card_edit=edit)
        self.assertEqual(report['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
