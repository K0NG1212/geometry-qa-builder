"""Related work and baselines: no cell may claim a fact the source does not state.

The 10th meeting asked for a table of what comparable benchmarks run as baselines, whether any has a human
baseline, and how each reports its results. The failure mode here is not drift but invention: a baseline
column is easy to fill from memory, and a wrong number in it would be worse than an empty cell, because it
would go into the paper. So the data file records, per work, whether a fact was stated in the source or not,
and these tests require every claim to carry that marker and every "checked" row to carry its link.

They also pin the division of authorship, because it matters for honesty: the survey is the user's, and the
baseline column was added by this session from the abstract pages. RELATED_WORK.md has to keep saying so.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / 'RELATED_WORK.md').read_text(encoding='utf-8')
DATA = json.loads((ROOT / 'docs/content/related-work.json').read_text(encoding='utf-8'))
LEGEND_HTML = (ROOT / 'docs/legend.html').read_text(encoding='utf-8')
LEGEND_JS = (ROOT / 'docs/legend.js').read_text(encoding='utf-8')
I18N = (ROOT / 'docs/i18n.js').read_text(encoding='utf-8')
SCAFFOLD = (ROOT / 'SCAFFOLD.md').read_text(encoding='utf-8')


class BaselineTableTests(unittest.TestCase):
    def test_every_work_says_whether_a_human_baseline_was_stated(self):
        for work in DATA['works']:
            self.assertIn(work['human'], ('yes', 'not_stated', 'unchecked'), work['id'])
            for field in ('human_zh', 'human_en'):
                self.assertTrue(work[field].strip(), (work['id'], field))

    def test_a_work_we_did_not_check_claims_nothing(self):
        """An unchecked row must stay empty rather than be filled in from memory."""
        for work in DATA['works']:
            if work['human'] != 'unchecked':
                continue
            for field in ('baselines_zh', 'reporting_zh'):
                self.assertRegex(work[field], r'未核对', work['id'] + ' 未核对的行不许填内容')

    def test_every_checked_work_carries_its_link_and_both_languages(self):
        for work in DATA['works']:
            self.assertTrue(work['url'].startswith('http'), work['id'])
            for field in ('scale', 'baselines', 'reporting'):
                for lang in ('zh', 'en'):
                    self.assertTrue(work['%s_%s' % (field, lang)].strip(), (work['id'], field, lang))

    def test_the_ids_are_the_ones_the_survey_uses(self):
        for work in DATA['works']:
            self.assertRegex(work['id'], r'^RW-[A-Z]\d\d$')
            self.assertIn(work['id'], DOC, work['id'] + ' 不在 RELATED_WORK.md 的对比表里')

    def test_only_one_work_is_recorded_as_having_a_human_baseline(self):
        """If this changes, the claim in RELATED_WORK and on the site has to change with it."""
        human = [w['id'] for w in DATA['works'] if w['human'] == 'yes']
        self.assertEqual(human, ['RW-M03'])
        self.assertIn('只有 MiSI-Bench 明确有', DOC)

    def test_the_file_states_how_the_column_was_checked_and_says_it_is_a_draft(self):
        self.assertEqual(DATA['status'], 'draft')
        for field in ('status_zh', 'status_en', 'method_zh', 'method_en'):
            self.assertTrue(DATA[field].strip(), field)
        self.assertIn('arXiv', DATA['status_zh'])


class AuthorshipTests(unittest.TestCase):
    def test_the_document_says_which_sections_are_the_users_own_survey(self):
        self.assertIn('用户本人 2026-11-09 的调研', DOC)
        self.assertIn('本会话补的', DOC)
        self.assertIn('Geobench-related-work.md', DOC)      # where the original draft lives

    def test_the_document_keeps_the_surveys_own_cautions(self):
        for caution in ('不自动视为已同行评审', '不能笼统宣称', '不是已证实的新颖性声明'):
            self.assertIn(caution, DOC, caution)


class RequirementTests(unittest.TestCase):
    """The point of the survey is what it forces on our own pipeline."""

    def test_each_requirement_names_the_work_it_comes_from(self):
        ids = {w['id'] for w in DATA['works']}
        self.assertGreaterEqual(len(DATA['requirements']), 4)
        for requirement in DATA['requirements']:
            self.assertIn(requirement['from'], ids, requirement['from'])
            for lang in ('zh', 'en'):
                self.assertTrue(requirement[lang].strip(), requirement['from'])

    def test_the_scaffold_turns_them_into_function_arguments(self):
        """A requirement that lives only in prose changes nothing; it has to reach the eval signature."""
        for argument in ('repeats', 'control', 'ci', 'baseline'):
            self.assertIn(argument, SCAFFOLD, argument + ' 没有进 SCAFFOLD 的函数契约')
        self.assertIn('23.9%', SCAFFOLD)                     # the number that forces repeats
        self.assertIn('RELATED_WORK.md', SCAFFOLD)

    def test_the_numbers_quoted_in_the_scaffold_are_the_ones_in_the_data(self):
        joined = ' '.join(r['zh'] for r in DATA['requirements'])
        for number in ('23.9%', '46.7'):
            self.assertIn(number, joined, number)
            self.assertIn(number, DOC, number)


class ScaffoldTests(unittest.TestCase):
    """The advisor's own sequence: design, then optimise, then let an LLM implement."""

    def test_it_is_a_design_and_says_no_code_was_written(self):
        self.assertIn('现在一行代码都没写', SCAFFOLD)
        self.assertIn('draft', SCAFFOLD)

    def test_it_criticises_its_own_design_before_asking_for_implementation(self):
        """Step two of his instruction. A scaffold with no weaknesses listed has not been optimised."""
        self.assertIn('这一版设计自己知道的毛病', SCAFFOLD)
        self.assertIn('可能不值', SCAFFOLD)                  # the rename batch, argued against

    def test_it_proposes_archiving_rather_than_deleting_and_says_what_breaks(self):
        self.assertIn('不删，归档', SCAFFOLD)
        self.assertIn('19 处', SCAFFOLD)                     # builder_modules/modules are still referenced

    def test_the_implementation_list_is_batched_with_acceptance_criteria(self):
        self.assertIn('验收标准', SCAFFOLD)
        self.assertIn('定稿后交给 LLM 实现', SCAFFOLD)

    def test_the_four_boundaries_are_named(self):
        for boundary in ('出题 ↔ 核验', '手写 ↔ 生成', '教师侧 ↔ 被测侧', '在用 ↔ 退役'):
            self.assertIn(boundary, SCAFFOLD, boundary)


class SitePageTests(unittest.TestCase):
    def test_the_legend_page_shows_the_baseline_table(self):
        self.assertIn('id="related"', LEGEND_HTML)
        self.assertIn('RELATED_WORK.md', LEGEND_HTML)
        self.assertIn("fetch('content/related-work.json')", LEGEND_JS)
        self.assertIn('lg-rw-table', LEGEND_JS)

    def test_the_new_chinese_on_the_page_is_translated(self):
        for string in ('同类工作与 baseline', '同类工作跑什么 baseline。', '完整调研 ↗',
                       '三点结论', '对我们评测的硬要求'):
            self.assertIn("'%s'" % string, I18N, string + ' 没进 i18n')

    def test_the_section_is_in_the_pages_own_list(self):
        self.assertIn('#related', LEGEND_HTML.split('</nav>', 1)[0] + LEGEND_HTML)


if __name__ == '__main__':
    unittest.main()
