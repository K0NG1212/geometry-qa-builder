"""What the 10th meeting (2026-11-05) asked the site to say, pinned so it cannot quietly stop saying it.

B1 one ability colour system across the whole site, B2 a reason on every blank cell of the coordinate map,
B3 the reason the scale axis starts at 0.1 nm and stops at 1000 nm, B4 the id letters and every abbreviation
explained on the page, B5 what the classification is based on, B6 an overview page that folds.

Two of these can rot silently, which is why they are tests rather than prose. A reason table drifts out of
step with the map it explains the moment a subdomain gains a scale, so the reasons are checked cell by cell
against docs/data/subdomain-map.json. And a new Chinese string on a page that is not in docs/i18n.js shows
up as Chinese on an English-by-default site, so the strings these sections added are checked too.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'

MAP = json.loads((DOCS / 'data/subdomain-map.json').read_text(encoding='utf-8'))
GAPS = json.loads((DOCS / 'content/gap-reasons.json').read_text(encoding='utf-8'))
LEGEND = json.loads((DOCS / 'content/legend.json').read_text(encoding='utf-8'))
STYLES = (DOCS / 'styles.css').read_text(encoding='utf-8')
FRAMEWORK_CSS = (DOCS / 'framework.css').read_text(encoding='utf-8')
FRAMEWORK_JS = (DOCS / 'framework.js').read_text(encoding='utf-8')
PIXELMAP_JS = (DOCS / 'pixelmap.js').read_text(encoding='utf-8')
LEGEND_HTML = (DOCS / 'legend.html').read_text(encoding='utf-8')
INDEX = (DOCS / 'index.html').read_text(encoding='utf-8')
I18N = (DOCS / 'i18n.js').read_text(encoding='utf-8')

NAV_PAGES = ('index.html', 'cards.html', 'subdomains.html', 'system.html')


def blank_cells():
    """The cells of the detailed map that hold no question, and which kind of blank each is."""
    out = {}
    for pixel in MAP['pixels']:
        if not pixel['meaningful']:
            out['%s|%s' % (pixel['l1'], pixel['scale'])] = 'na'
        elif not pixel['questions']:
            out['%s|%s' % (pixel['l1'], pixel['scale'])] = 'gap'
    return out


class GapReasonTests(unittest.TestCase):
    """B2: 「你要填个 NA，就要给个原因」."""

    def test_every_blank_cell_has_a_reason_and_no_reason_names_a_cell_that_is_not_blank(self):
        self.assertEqual(sorted(GAPS['pixels']), sorted(blank_cells()),
                         '空白格与理由必须一一对应：改了子领域的尺度，就要改 docs/content/gap-reasons.json')

    def test_a_reason_says_which_of_the_four_kinds_it_is_in_both_languages(self):
        for key, entry in GAPS['pixels'].items():
            self.assertIn(entry['kind'], GAPS['kinds'], key)
            for field in ('zh', 'en'):
                self.assertTrue(entry[field].strip(), (key, field))
            self.assertTrue(entry['name'].strip(), key)

    def test_the_kind_agrees_with_what_the_map_says_about_the_cell(self):
        """A cell outside the subdomain's scales cannot be "not collected yet", and a meaningful cell cannot
        be "no such object": that would contradict the taxonomy that drew the map."""
        kinds = blank_cells()
        for key, entry in GAPS['pixels'].items():
            self.assertEqual(entry['blank'], kinds[key], key)
            if kinds[key] == 'na':
                self.assertNotEqual(entry['kind'], 'uncollected', key)
            else:
                self.assertNotIn(entry['kind'], ('absent', 'elsewhere'), key)

    def test_the_real_gaps_are_the_ones_the_advisor_asked_about(self):
        real = [k for k, v in GAPS['pixels'].items() if v['kind'] in ('uncollected', 'hard')]
        self.assertEqual(len(real), MAP['summary']['empty_meaningful_pixels'])

    def test_the_counts_in_the_file_are_the_counts_in_the_file(self):
        c = GAPS['counts']
        self.assertEqual(c['na'], sum(1 for v in GAPS['pixels'].values() if v['blank'] == 'na'))
        self.assertEqual(c['gap'], sum(1 for v in GAPS['pixels'].values() if v['blank'] == 'gap'))
        for kind, n in c['by_kind'].items():
            self.assertEqual(n, sum(1 for v in GAPS['pixels'].values() if v['kind'] == kind), kind)

    def test_the_file_says_it_is_not_confirmed(self):
        self.assertEqual(GAPS['status'], 'draft')
        for field in ('status_zh', 'status_en'):
            self.assertTrue(GAPS[field].strip())

    def test_the_map_reads_the_reasons_and_still_draws_without_them(self):
        self.assertIn("fetch('content/gap-reasons.json')", PIXELMAP_JS)
        self.assertIn('r.ok ? r.json() : null', PIXELMAP_JS)      # a missing file must not blank the map


class AbilityColourTests(unittest.TestCase):
    """B1: 「一个题型一种颜色，那个颜色贯穿始终」."""

    def test_the_three_ability_colours_are_defined_once_as_tokens(self):
        root = re.search(r':root\{(.*?)\}', STYLES, re.S).group(1)
        for token in ('--ab-p', '--ab-i', '--ab-d'):
            self.assertIn(token + ':', root, token)
            self.assertIn(token + '-tint:', root, token)

    def test_no_page_tints_an_ability_with_its_own_hex(self):
        """These six hexes were the same three abilities in six slightly different colours."""
        for stale in ('#edf3eb', '#eaf0f5', '#f0eaf5', '#f0f5ed', '#edf2f7', '#f4eef7'):
            # assertFalse, not assertNotIn: the latter prints the whole stylesheet on failure
            self.assertFalse(stale in STYLES, 'styles.css 还留着能力色的硬编码 ' + stale)
            self.assertFalse(stale in FRAMEWORK_CSS, 'framework.css 还留着能力色的硬编码 ' + stale)

    def test_a_coverage_cell_shows_the_three_numbers_as_a_proportion_and_names_them_on_hover(self):
        self.assertIn('ability-bar', FRAMEWORK_JS)
        self.assertIn('style="flex:${s.n}"', FRAMEWORK_JS)       # width is the share, not a fixed size
        self.assertIn('title="${esc(share(s.ab,s.n,n))}"', FRAMEWORK_JS)
        self.assertIn('Perception', FRAMEWORK_JS)                # and the hover text exists in English too
        self.assertIn('pix-split', PIXELMAP_JS)

    def test_the_three_abilities_carry_the_same_three_names_everywhere(self):
        names = {'perception': '感知', 'inference': '推断', 'design': '设计'}
        for page in ('app.js', 'framework.js', 'pixelmap.js', 'subdomains.js'):
            body = (DOCS / page).read_text(encoding='utf-8')
            for key, name in names.items():
                if re.search(r'\b%s\s*:\s*[\'"\[]' % key, body):
                    self.assertNotIn('推理', body.split(key, 1)[1][:60],
                                     '%s 把 inference 写成了「推理」' % page)
                    del name            # the name itself is asserted by the ability definitions below

    def test_the_legend_names_the_colour_token_each_ability_uses(self):
        letters = []
        for ability in LEGEND['abilities']['items']:
            self.assertIn(ability['token'] + ':', STYLES, ability['token'])
            letters.append(ability['letter'])
            for field in ('zh', 'en', 'def_zh', 'def_en'):
                self.assertTrue(ability[field].strip(), (ability['key'], field))
        self.assertEqual(letters, ['P', 'I', 'D'])


class ScaleBoundTests(unittest.TestCase):
    """B3: 「为什么没有 0.01？为什么没有 10000 nm？」."""

    def test_both_bounds_and_the_decade_choice_are_argued(self):
        questions = ' '.join(b['q_zh'] + b['q_en'] for b in LEGEND['scales']['boundaries'])
        self.assertIn('0.01', questions)
        self.assertIn('10000', questions)
        self.assertIn('十倍', questions)
        for b in LEGEND['scales']['boundaries']:
            for field in ('q_zh', 'q_en', 'a_zh', 'a_en'):
                self.assertGreater(len(b[field].strip()), 8, field)

    def test_the_reason_is_on_the_overview_page_as_well_as_the_legend(self):
        self.assertIn('legend.html#scales', FRAMEWORK_JS)
        self.assertIn('0.154', FRAMEWORK_JS)                     # the bond length the lower bound rests on
        self.assertIn('method-scale', FRAMEWORK_JS)

    def test_the_methodology_document_carries_it_too(self):
        text = (ROOT / 'METHODOLOGY.md').read_text(encoding='utf-8')
        self.assertIn('尺度区间边界的理由', text)
        self.assertIn('子领域分类依据', text)


class IdAndAbbreviationTests(unittest.TestCase):
    """B4: 「所有的缩写你都要解释出来」."""

    def test_all_three_id_systems_are_explained(self):
        names = [s['name_en'] for s in LEGEND['ids']['systems']]
        self.assertEqual(len(names), 3)
        for system in LEGEND['ids']['systems']:
            self.assertTrue(system['example'].strip(), system['name_en'])
            self.assertTrue(system['parts'], system['name_en'])
            for part in system['parts']:
                for field in ('pos_zh', 'pos_en', 'detail_zh', 'detail_en'):
                    self.assertTrue(part[field].strip(), (system['name_en'], field))

    def test_the_question_id_explains_every_letter_and_says_the_number_is_not_global(self):
        question = next(s for s in LEGEND['ids']['systems'] if s['example'].startswith('BNI'))
        detail = ' '.join(p['detail_zh'] for p in question['parts'])
        for letter in ('B 生物', 'C 化学', 'M 材料', 'P 感知', 'I 推断'):
            self.assertIn(letter, detail)
        self.assertIn('不是全局唯一', detail)
        # and the honest part: the middle letter carries no meaning
        self.assertIn('不编码任何信息', detail)
        self.assertTrue(question['caveats'], '首字母与现在的领域可能不一致，必须写出来')

    def test_the_letters_match_the_code_that_mints_the_ids(self):
        minter = (ROOT / 'tools/extend_admission_map.py').read_text(encoding='utf-8')
        self.assertIn("biology='B'", minter)
        self.assertIn("ABILITY_LETTER = dict(perception='P', inference='I', design='D')", minter)
        self.assertIn("'%sN%s'", minter)                        # the fixed N the legend calls meaningless

    def test_the_abbreviations_the_pages_use_are_all_listed(self):
        listed = {item['t'] for group in LEGEND['abbreviations'] for item in group['items']}
        for must in ('PDB', 'COD', 'QM7-X', 'EC', 'CATH / SCOP', 'MOF', 'FRET', 'LLM / VLM', 'Å'):
            self.assertIn(must, listed, must + ' 没解释')
        for group in LEGEND['abbreviations']:
            for item in group['items']:
                for field in ('zh', 'en'):
                    self.assertTrue(item[field].strip(), (item['t'], field))

    def test_the_review_levels_are_described_as_they_actually_stand(self):
        entry = next(i for g in LEGEND['abbreviations'] for i in g['items'] if i['t'].startswith('L0'))
        self.assertIn('L0', entry['zh'])
        self.assertIn('pending', entry['zh'])                   # not "passed": L1-L4 have never been run
        exporter = (ROOT / 'tools/export_qa_folders.py').read_text(encoding='utf-8')
        self.assertIn("'L1': 'pending'", exporter)


class TaxonomyBasisTests(unittest.TestCase):
    """B5: 「具体分类的依据，回头得写下来」."""

    def test_each_domain_says_what_its_split_is_based_on_and_matches_the_tree(self):
        tree = json.loads((ROOT / 'templates/subdomain-draft.json').read_text(encoding='utf-8'))
        schemes = {d['id']: d['scheme'] for d in tree['domains']}
        self.assertEqual(sorted(s['domain'] for s in LEGEND['taxonomy_basis']['schemes']), sorted(schemes))
        for s in LEGEND['taxonomy_basis']['schemes']:
            for field in ('basis_zh', 'basis_en'):
                self.assertTrue(s[field].strip(), (s['domain'], field))
        # the arXiv question the advisor asked: only physics follows it, and the tree has to agree
        self.assertIn('arXiv', schemes['physics'])
        physics = next(s for s in LEGEND['taxonomy_basis']['schemes'] if s['domain'] == 'physics')
        self.assertIn('arXiv', physics['basis_zh'])
        for other in ('chemistry', 'materials', 'biology'):
            basis = next(s for s in LEGEND['taxonomy_basis']['schemes'] if s['domain'] == other)
            self.assertNotIn('arXiv', basis['basis_zh'], other + ' 不是按 arXiv 分的')

    def test_the_filing_rules_are_the_ones_in_the_tree(self):
        tree = json.loads((ROOT / 'templates/subdomain-draft.json').read_text(encoding='utf-8'))
        self.assertEqual(len(LEGEND['taxonomy_basis']['rules_zh']), len(tree['assignment_rules']))
        self.assertEqual(len(LEGEND['taxonomy_basis']['rules_en']), len(tree['assignment_rules']))

    def test_it_says_the_tree_is_still_a_draft(self):
        for field in ('caveat_zh', 'caveat_en'):
            self.assertIn('draft', LEGEND['taxonomy_basis'][field])


class LegendPageTests(unittest.TestCase):
    def test_the_page_is_reachable_from_every_main_page(self):
        for page in NAV_PAGES:
            nav = re.search(r'<nav[^>]*>.*?</nav>', (DOCS / page).read_text(encoding='utf-8'), re.S).group(0)
            self.assertIn('legend.html', nav, page + ' 的导航里没有读图指南')

    def test_the_page_has_a_section_for_each_of_the_five_things_it_explains(self):
        for anchor in ('abilities', 'scales', 'ids', 'taxonomy', 'gaps', 'abbr'):
            self.assertIn('id="%s"' % anchor, LEGEND_HTML, anchor)

    def test_the_page_reads_hand_written_prose_and_computed_numbers_from_separate_places(self):
        """Prose is written by hand under content/; every number is computed into data/source-coverage.json.

        Until the sources section (C1, 2026-11-09) this test said the page reads nothing from data/ at all,
        because everything it showed was prose. That stopped being right: a coverage figure that is typed by
        hand goes stale the moment a question is added, so the figures have to come from the generated file.
        What still has to hold is the split -- the page may read the coverage file, and nothing else
        generated, so no number on it is hand-maintained and no prose on it is machine-generated."""
        js = (DOCS / 'legend.js').read_text(encoding='utf-8')
        body = js.split('*/', 1)[1]
        for hand in ('content/legend.json', 'content/gap-reasons.json', 'content/sources.json'):
            self.assertIn("fetch('%s')" % hand, js, hand)
        self.assertIn("fetch('data/source-coverage.json')", js)
        others = [m for m in re.findall(r"fetch\('(data/[^']+)'\)", body) if m != 'data/source-coverage.json']
        self.assertEqual(others, [], '读图指南只许读 data/source-coverage.json 这一个生成文件')


class FoldTests(unittest.TestCase):
    """B6: 「这肯定不能都展开来」."""

    def test_the_overview_folds_and_keeps_the_markup(self):
        self.assertIn('<details class="fold"', INDEX)
        self.assertGreaterEqual(INDEX.count('<details class="fold"'), 3)
        self.assertIn('<details class="fold" open>', INDEX)      # the map the coverage is planned against
        for kept in ('id="pixel-section"', 'id="questions"', 'id="coverage"', 'id="pixelmap"'):
            self.assertIn(kept, INDEX, kept)

    def test_the_page_lists_its_own_sections(self):
        toc = re.search(r'<nav class="page-toc".*?</nav>', INDEX, re.S)
        self.assertIsNotNone(toc, '概览页没有分区列表')
        for anchor in ('#coverage-section', '#pixel-section', '#questions'):
            self.assertIn(anchor, toc.group(0), anchor)

    def test_a_link_into_a_folded_section_opens_it(self):
        self.assertIn('openFold', FRAMEWORK_JS)
        self.assertIn("closest('details')", FRAMEWORK_JS)
        self.assertIn("addEventListener('hashchange'", FRAMEWORK_JS)


class TranslationTests(unittest.TestCase):
    """The site defaults to English, so a new Chinese string that is not in the dictionary is a regression."""

    def strings(self, html):
        """Chinese text nodes and summaries a reader actually sees."""
        body = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S)
        out = []
        for text in re.findall(r'>([^<>]+)<', body):
            text = text.strip()
            if text and re.search(r'[一-鿿]', text):
                out.append(text)
        return out

    def test_every_chinese_string_the_legend_page_shows_has_an_english_entry(self):
        missing = [s for s in self.strings(LEGEND_HTML) if ("'%s'" % s) not in I18N]
        self.assertEqual(missing, [], '读图指南页有没翻译的中文：%s' % missing)

    def test_the_folds_and_the_section_list_are_translated(self):
        wanted = re.findall(r'<summary>([^<]+)</summary>', INDEX)
        wanted += re.findall(r'<nav class="page-toc".*?</nav>', INDEX, re.S) and \
            re.findall(r'>([^<>]+)<', re.search(r'<nav class="page-toc".*?</nav>', INDEX, re.S).group(0))
        missing = [s.strip() for s in wanted
                   if re.search(r'[一-鿿]', s) and ("'%s'" % s.strip()) not in I18N]
        self.assertEqual(missing, [], '概览页折叠／分区列表有没翻译的中文：%s' % missing)


if __name__ == '__main__':
    unittest.main()
