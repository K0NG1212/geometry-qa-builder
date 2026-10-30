"""Links on the published site must resolve: a reviewer who clicks one must land on the question it names.

The 2026-10-28 demo failed here. docs/families.js kept a hand-written list of family names and used it as the
family dropdown; the three families added on 2026-10-19 were not in it, so their 20 questions could not be
selected, and templates.html?instance=<one of them> rendered an empty workbench with an error banner. These
tests pin the two things that have to hold: the dropdown is built from the data (so no family can be left out),
and every link in the published data and pages resolves.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import check_links  # noqa: E402

FAMILIES_JS = (ROOT / 'docs/families.js').read_text(encoding='utf-8')
WORKBENCH = json.loads((ROOT / 'docs/data/family-workbench.json').read_text(encoding='utf-8'))
CATALOG = json.loads((ROOT / 'docs/data/catalog.json').read_text(encoding='utf-8'))


class FamilySelectionTests(unittest.TestCase):
    def test_the_dropdown_is_built_from_the_run_data(self):
        build = re.search(r'\$\(.fam-select.\)\.innerHTML=(.*)', FAMILIES_JS).group(1)
        self.assertIn('families.map', build)                       # the options come from the data, not a list
        self.assertIn('new Set(fam.teacher_answers.map(t=>t.family))', FAMILIES_JS)

    def test_no_hand_written_list_of_family_names_is_left_in_the_page(self):
        # Such a list is what broke: it has to be kept in step with the data by hand, and was not. A single
        # family named in a display-name fallback is fine; a list of them is the thing that goes stale.
        names = {t['family'] for t in WORKBENCH['teacher_answers']}
        for literal in re.findall(r'=\[(.*?)\];', FAMILIES_JS, re.S):
            quoted = set(re.findall(r"'([a-z0-9_]+)'", literal))
            self.assertEqual(sorted(quoted & names), [], 'family names must not be listed in docs/families.js')

    def test_every_question_in_the_catalog_points_at_an_instance_that_exists(self):
        wanted = {q['id']: q['traceUrl'].split('instance=')[1].split('#')[0]
                  for q in CATALOG['questions'] if (q.get('traceUrl') or '').startswith('templates.html?instance=')}
        have = {t['id'] for t in WORKBENCH['teacher_answers']}
        self.assertEqual(sorted(i for i in wanted.values() if i not in have), [])
        self.assertEqual(len(wanted), len(have))                   # and the run carries nothing else


def source_links(source, page=None):
    """The rules docs/sources.js follows, so the data can be checked without a JavaScript engine."""
    source = source or ''
    if re.match(r'^https?://', source.strip()):
        return [source.strip()]
    inside = list(dict.fromkeys(re.findall(r'https?://[^\s;,，、）)]+', source)))[:3]
    if inside:
        return inside
    out = []
    doi = re.search(r'\bdoi:?\s*(10\.\S+?)(?:[\s;,，（(。]|$)', source, re.I)
    pmc = re.search(r'\b(PMC\d+)\b', source)
    arxiv = re.search(r'arXiv:\s*(\d{4}\.\d{4,5})', source, re.I)
    if doi:
        out.append('https://doi.org/' + doi.group(1))
    if pmc:
        out.append('https://europepmc.org/article/PMC/' + pmc.group(1))
    if arxiv:
        out.append('https://arxiv.org/abs/' + arxiv.group(1))
    return out or ([page] if page else [])


class SourceLinkTests(unittest.TestCase):
    """Two thirds of the sources are a citation, not a URL. index.html used to put the citation straight into
    href=, which gave 151 questions a link that could only 404."""

    def test_no_page_puts_a_citation_into_an_href(self):
        for js in sorted((ROOT / 'docs').glob('*.js')):
            for expression in re.findall(r'href="\$\{([^}]*)\}"', js.read_text(encoding='utf-8')):
                self.assertNotIn('source', expression, '%s builds an href out of %s' % (js.name, expression))

    def test_every_page_that_uses_the_helper_loads_it(self):
        for page in sorted((ROOT / 'docs').glob('*.html')):
            scripts = re.findall(r'<script[^>]+src="([^"?]+)', page.read_text(encoding='utf-8'))
            users = [s for s in scripts if s != 'sources.js'
                     and (ROOT / 'docs' / s).exists()
                     and 'sourceLinks(' in (ROOT / 'docs' / s).read_text(encoding='utf-8')]
            if users:
                self.assertIn('sources.js', scripts, '%s loads %s without sources.js' % (page.name, users))
                self.assertLess(scripts.index('sources.js'), min(scripts.index(u) for u in users), page.name)

    def test_every_question_in_the_pool_has_a_source_link(self):
        pages = {r['id']: r.get('url') for r in CATALOG['resources']}
        for q in CATALOG['questions']:
            if q.get('traceUrl'):
                self.assertTrue(source_links(q.get('source'), pages.get(q['paper'])), q['id'])

    def test_the_card_page_links_every_card_it_can(self):
        cards = json.loads((ROOT / 'docs/data/cards.json').read_text(encoding='utf-8'))['cards']
        # The card page has no resource list to fall back on, so a card is linked only through an identifier in
        # its own citation. Every one of the 336 carries a DOI, a PMCID, an arXiv id or a URL; keep it that way.
        self.assertEqual([c['id'] for c in cards if not source_links(c.get('source'))], [])


class LinkCheckTests(unittest.TestCase):
    def test_no_internal_link_is_broken(self):
        broken, external, routed = check_links.run()
        self.assertEqual([(w, l, r) for w, l, r in broken], [])
        self.assertGreater(len(external), 100)                     # the sweep really did reach the data

    def test_the_checker_catches_an_instance_that_is_not_in_the_run(self):
        data = check_links.published()
        self.assertIsNone(check_links.check('templates.html?instance=%s#workbench'
                                            % sorted(data['instance'])[0], data))
        self.assertIn('not in the published data',
                      check_links.check('templates.html?instance=FA-DES-NOPE#workbench', data))

    def test_the_checker_catches_a_missing_file_and_a_missing_anchor(self):
        data = check_links.published()
        self.assertIn('does not exist', check_links.check('no-such-page.html', data))
        # Windows would open this file; GitHub Pages serves paths case-sensitively and would not.
        self.assertIn('does not exist', check_links.check('Templates.html', data))
        self.assertIn('no element', check_links.check('templates.html#no-such-anchor', data))
        self.assertIsNone(check_links.check('templates.html#workbench', data))


if __name__ == '__main__':
    unittest.main()
