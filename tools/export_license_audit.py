"""W2: every upstream source, what the bank publishes from it, and the licence that allows that.

Why one source at a time rather than one licence for the whole bank: the 336 questions draw on 36 upstream
sources whose terms differ, and what we publish from each differs too. Three cases have to be told apart,
because only the first is a redistribution question at all:

  upstream coordinates   the numbers in the attachment are the source's own (copied, symmetry-expanded,
                         reduced to centroids, rigidly rotated or format-converted). Publishing them needs
                         terms that allow redistribution.
  our coordinates        the geometry is built here from scalars the paper printed (a lattice constant, a
                         twist angle, a pitch). Nothing of the source's own is republished.
  our text               an evidence or design card: facts and numbers transcribed here, with a locator.
                         Facts are not protected, but a sentence copied word for word would be, so each
                         card's prose is scanned against the paper's own full text.

The licence of a source is read off a record, never asserted. Strongest first: the publisher's own
<permissions> block in the JATS XML we hold locally, or a licence line in the PDF; then a repo record
(docs/assets/.../sources.json, a trace, the dataset's own licence file). Where the two disagree, or where
nothing in the repo states the licence, the row says so and the finding is listed instead of smoothed over.

    python tools/export_license_audit.py          # writes docs/data/license-audit.json
    python tools/export_license_audit.py --print  # and prints the per-source table
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import export_qa_folders as folders            # the same provenance labels the per-question folders carry

# A run of this many consecutive words shared with the paper's own text is sent to L1 for rewording. Short
# factual clauses overlap unavoidably ("the critical current is largest at B = 0"); the threshold marks where
# a sentence stops being a restatement and starts being a copy.
QUOTE_WORDS = 8

LICENCES = {
    'CC0-1.0': dict(label='CC0 1.0', republish=True, attribution=False, share_alike=False),
    'public-domain': dict(label='公有领域（COD 贡献者声明）', republish=True, attribution=False, share_alike=False),
    'CC-BY-4.0': dict(label='CC BY 4.0', republish=True, attribution=True, share_alike=False),
    'CC-BY-3.0': dict(label='CC BY 3.0', republish=True, attribution=True, share_alike=False),
    'CC-BY-SA-4.0': dict(label='CC BY-SA 4.0', republish=True, attribution=True, share_alike=True),
    'CC-BY-NC-ND-4.0': dict(label='CC BY-NC-ND 4.0', republish=False, attribution=True, share_alike=False),
    'MIT': dict(label='MIT（只覆盖代码）', republish=True, attribution=True, share_alike=False),
    'arxiv-nonexclusive': dict(label='arXiv 非独占许可（授权 arXiv 分发，不授权第三方转载）',
                               republish=False, attribution=True, share_alike=False),
    'author-manuscript': dict(label='PMC 作者稿（非 CC）', republish=False, attribution=True, share_alike=False),
    'all-rights-reserved': dict(label='版权归出版方，保留所有权利', republish=False, attribution=True, share_alike=False),
}

# One row per upstream source: the name to print, the licence the repo declares for it, the repo files that
# declare it, and the local full text (outside the repository) to verify it against. `fulltext` doubles as the
# text the card prose is scanned against.
SOURCES = {
    'pdb-bio-nm': dict(name='RCSB PDB / wwPDB', kind='database', declared='CC0-1.0',
                       where=['docs/assets/families/assemblies/sources.json', 'docs/assets/bio/sources-2026-10-03.json']),
    'pdb-dna-origami': dict(name='RCSB PDB / wwPDB（DNA 折纸）', kind='database', declared='CC0-1.0',
                            where=['docs/assets/families/assemblies/sources.json']),
    'pdb-1aa5-vancomycin': dict(name='RCSB PDB 1AA5', kind='database', declared='CC0-1.0',
                                where=['docs/assets/families/assemblies/sources.json']),
    'cod-materials-cell': dict(name='Crystallography Open Database', kind='database', declared='public-domain',
                               where=['docs/assets/materials/sources-cod-2026-10-03.json',
                                      'docs/assets/materials/sources-noncubic.json'],
                               also='COD 文件头要求引用原始文献；52 道中只有 9 道在许可字段里记了原始文献'),
    'cod-mof': dict(name='Crystallography Open Database（MOF）', kind='database', declared='public-domain',
                    where=['docs/assets/materials/sources-cod-2026-10-03.json']),
    'qm7x': dict(name='QM7-X（Zenodo 4288677）', kind='dataset', declared='CC-BY-4.0',
                 where=['docs/assets/families/conformers/QM7X-7032-i1-opt.json']),
    'oe62': dict(name='OE62（TUM mediaTUM 1507656）', kind='dataset', declared='CC-BY-SA-4.0',
                 where=['docs/data/traces/QNP007.json']),
    'sampl9': dict(name='SAMPL9 挑战赛（samplchallenges/SAMPL9）', kind='dataset', declared='CC-BY-4.0',
                   where=['docs/data/SAMPL9-LICENSE.txt', 'docs/pilot-chem.html'],
                   also='仓库 README 的 LICENSE 节：代码 MIT，其余材料 CC BY 4.0。我们用的是主客体结构与 ITC 实测表，属“其余材料”'),
    'paper-landscape17-azobenzene': dict(name='Landscape17（Figshare 29949230）', kind='dataset', declared='CC-BY-4.0',
                                         where=['docs/assets/families/reaction/sources.json']),
    'hbond2021': dict(name='Altun, Bleda & Trindle, Molecules 26, 2623 (2021)', kind='paper', declared='CC-BY-4.0',
                      where=['docs/assets/families/evidence/sources.json'],
                      fulltext='../paper-batch-v04-001/materials/hbond-article.xml'),
    'paper-cao-magic-angle': dict(name='Cao et al., Nature 556, 43 (2018) / arXiv:1803.02342', kind='paper',
                                  declared='arxiv-nonexclusive',
                                  where=['docs/assets/families/evidence/sources.json', 'docs/assets/families/moire/sources.json'],
                                  fulltext='inputs/papers/cao2018/cao2018-arxiv-1803.02342.pdf'),
    'paper-kerelsky-tbg-stm': dict(name='Kerelsky et al., Nature 572, 95 (2019) / arXiv:1812.08776', kind='paper',
                                   declared='arxiv-nonexclusive',
                                   where=['docs/assets/families/evidence/sources.json', 'docs/assets/families/moire/sources.json'],
                                   fulltext='inputs/papers/kerelsky2019/kerelsky2019-arxiv-1812.08776.pdf'),
    'paper-cottet-mgb2-vortex': dict(name='Cottet et al., arXiv:1401.4062', kind='paper', declared='arxiv-nonexclusive',
                                     where=['docs/assets/families/evidence/sources.json', 'docs/assets/families/vortex/sources.json'],
                                     fulltext='inputs/papers/cottet2014/cottet2014-arxiv-1401.4062.pdf'),
    'paper-schaefermeier-bscco-vortex': dict(name='Schäfermeier et al., arXiv:2602.13060', kind='paper',
                                             declared='CC-BY-NC-ND-4.0',
                                             where=['docs/assets/families/vortex/sources.json'],
                                             fulltext='inputs/papers/schaefermeier2026/schaefermeier2026-arxiv-2602.13060.pdf'),
    'paper-ps-opal-rulers': dict(name='Gazmeh et al., Sci. Rep. 15, 38349 (2025)', kind='paper', declared='CC-BY-NC-ND-4.0',
                                 where=['docs/assets/families/opals/sources.json'],
                                 fulltext='inputs/papers/gazmeh2025/gazmeh2025-scirep.pdf'),
    'paper-silica-opal': dict(name='Fookes, Polo Parada & Fidalgo, Sensors 23, 1433 (2023)', kind='paper',
                              declared='CC-BY-4.0', where=['docs/assets/families/opals/sources.json'],
                              fulltext='inputs/papers/fookes2023/fookes2023-PMC9920682.xml'),
    'paper-shaban-cholesteric': dict(name='Shaban et al., Materials 17, 5080 (2024)', kind='paper', declared='CC-BY-4.0',
                                     where=['docs/assets/families/cholesteric/sources.json'],
                                     fulltext='inputs/papers/shaban2024/shaban2024-PMC11509098.xml'),
    'paper-dinc-isosorbide': dict(name='Dinç et al., Org. Chem. Front. (2024)', kind='paper', declared='CC-BY-3.0',
                                  where=['docs/assets/families/cholesteric/sources.json'],
                                  fulltext='inputs/papers/dinc2024/dinc2024-PMC11492181.xml'),
    'paper-yu-cdse-2003': dict(name='Yu, Qu, Guo & Peng, Chem. Mater. 15, 2854 (2003)', kind='paper', declared=None,
                               where=['docs/assets/families/qdots/sources.json'],
                               also='只用拟合系数（事实数据），不转载任何内容，因此不依赖许可'),
    'paper-dna-au-superlattice': dict(name='Hill et al., Nano Lett. 8, 2341 (2008)', kind='paper', declared=None,
                                      where=['docs/assets/families/superlattices/sources.json'],
                                      also='只用 Table 1 的数值（事实数据），不转载任何内容'),
    'paper-muhlbauer-mnsi-skyrmion': dict(name='Mühlbauer et al., Science 323, 915 (2009) / arXiv:0902.1968',
                                          kind='paper', declared='arxiv-nonexclusive',
                                          where=['docs/assets/families/evidence/sources.json'],
                                          fulltext='inputs/papers/muhlbauer2009/muhlbauer2009-arxiv-0902.1968.pdf'),
    'paper-filip-perovskite-steric': dict(name='Filip et al., Nat. Commun. 5, 5757 (2014)', kind='paper',
                                          declared='all-rights-reserved',
                                          where=['docs/assets/families/evidence/sources.json'],
                                          fulltext='inputs/papers/filip2014/filip2014-ncomms.pdf'),
    'paper-jiang-anthrax-pa-pore': dict(name='Jiang et al., Nature 521, 545 (2015)', kind='paper',
                                        declared='author-manuscript',
                                        where=['docs/assets/families/evidence/sources.json'],
                                        fulltext='inputs/papers/jiang2015/jiang2015-PMC4519040.xml'),
    'paper-rasmussen-b2ar-gs': dict(name='Rasmussen et al., Nature 477, 549 (2011)', kind='paper',
                                    declared='author-manuscript',
                                    where=['docs/assets/families/evidence/sources.json'],
                                    fulltext='inputs/papers/rasmussen2011/rasmussen2011-PMC3184188.xml'),
    'paper-cuello-kcsa-gating': dict(name='Cuello et al., eLife 6, e28032 (2017)', kind='paper', declared='CC-BY-4.0',
                                     where=['docs/assets/families/evidence/sources.json'],
                                     fulltext='inputs/papers/kcsa2017/kcsa2017-PMC5711375.xml'),
    'paper-vincent-molecular-clips': dict(name='Vincent et al., Chem. Eur. J. (2025)', kind='paper', declared='CC-BY-4.0',
                                          where=['docs/assets/families/design/sources.json'],
                                          fulltext='inputs/papers/vincent2025/vincent2025-PMC12415320.xml'),
    'paper-rando-bambusuril': dict(name='Rando et al., Chem. Sci. (2025)', kind='paper', declared='CC-BY-4.0',
                                   where=['docs/assets/families/design/sources.json'],
                                   fulltext='inputs/papers/rando2025/rando2025-PMC11639902.xml'),
    'paper-chetry-mof-isotopologue': dict(name='Chetry et al., ACS Appl. Mater. Interfaces (2026)', kind='paper',
                                          declared='CC-BY-4.0', where=['docs/assets/families/design/sources.json'],
                                          fulltext='inputs/papers/chetry2026/chetry2026-PMC13022808.xml'),
    'paper-blom-bisporphyrin-tweezers': dict(name='Blom et al., Molecules 21, 16 (2015)', kind='paper',
                                             declared='CC-BY-4.0', where=['docs/assets/families/design/resolved'],
                                             fulltext='inputs/paper-candidates/PMC6274253.xml'),
    'paper-wilde-ceue-licam': dict(name='Wilde et al., Sci. Rep. 7, 45941 (2017)', kind='paper', declared='CC-BY-4.0',
                                   where=['docs/assets/families/design/resolved'],
                                   fulltext='inputs/paper-candidates/PMC5382913.xml'),
    'paper-zhai-synthetic-lectin': dict(name='Zhai et al., ACS Cent. Sci. 11, 1753 (2025)', kind='paper',
                                        declared='CC-BY-4.0', where=['docs/assets/families/design/resolved'],
                                        fulltext='inputs/paper-candidates/PMC12464755.xml'),
    'paper-dellasala-prismarene': dict(name='Della Sala et al., Chem. Sci. 12, 9952 (2021)', kind='paper',
                                       declared='CC-BY-3.0', where=['docs/assets/families/design/resolved'],
                                       fulltext='inputs/paper-candidates/PMC8317625.xml'),
    'paper-gomez-pillararene-alkylsulfonate': dict(name='Gómez-González et al., Pharmaceutics 14, 60 (2021)',
                                                   kind='paper', declared='CC-BY-4.0',
                                                   where=['docs/assets/families/design/resolved'],
                                                   fulltext='inputs/paper-candidates/PMC8777861.xml'),
    'paper-kaabel-cychc8-anions': dict(name='Kaabel et al., Chem. Sci. 8, 2184 (2017)', kind='paper',
                                       declared='CC-BY-3.0', where=['docs/assets/families/design/resolved'],
                                       fulltext='inputs/paper-candidates/PMC5477839.xml'),
    'paper-shuto-closed-cavity-dipeptide': dict(name='Shuto et al., JACS Au 3, 2905 (2023)', kind='paper',
                                                declared='CC-BY-4.0', where=['docs/assets/families/design/resolved'],
                                                fulltext='inputs/paper-candidates/PMC10598568.xml'),
    'paper-ikeda-fau-methanol': dict(name='Ikeda et al., Membranes 11, 627 (2021)', kind='paper', declared='CC-BY-4.0',
                                     where=['docs/assets/families/design/resolved'],
                                     fulltext='inputs/paper-candidates/PMC8399176.xml'),
    'paper-kim-ace2-disulfide': dict(name='Kim et al., Int. J. Mol. Sci. 25, 9919 (2024)', kind='paper',
                                     declared='CC-BY-4.0', where=['docs/assets/families/design/resolved'],
                                     fulltext='inputs/paper-candidates/PMC11432317.xml',
                                     also='卡片已发布，但没有在库题目用它'),
}

PUBLISHES = {'database_verbatim': 'upstream_coordinates', 'database_reduced': 'upstream_coordinates',
             'database_symmetry_expanded': 'upstream_coordinates', 'database_rigid_transform': 'upstream_coordinates',
             'database_format_converted': 'upstream_coordinates', 'database_source': 'upstream_coordinates',
             'generated_by_this_project': 'our_coordinates', 'evidence_from_paper_no_coordinates': 'our_text',
             'measured_values_from_paper_no_coordinates': 'our_text'}
PUBLISHES_LABEL = {'upstream_coordinates': '上游坐标（照抄／展开／约简／旋转／转格式）',
                   'our_coordinates': '本项目生成的坐标（只用论文数值）',
                   'our_text': '本项目转述的事实（证据卡／设计卡，无坐标）'}


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def words(text):
    """A text as its bare words, so that punctuation, case and dash style cannot hide a copied run."""
    text = text.lower().replace('−', '-').replace('–', '-').replace('—', '-')
    return re.findall(r'[a-z0-9]+', text)


def full_text(rel):
    """The paper as plain text: the JATS with its tags stripped, or the PDF's extracted pages."""
    path = ROOT / rel
    if path.suffix == '.xml':
        return re.sub(r'<[^>]+>', ' ', path.read_text(encoding='utf-8', errors='replace'))
    import pypdf
    return '\n'.join((page.extract_text() or '') for page in pypdf.PdfReader(str(path)).pages)


def licence_in(rel):
    """The licence the source itself states, if its local copy states one.

    A JATS <permissions> block is the publisher's own statement; an open-access PDF usually carries the same
    sentence on its first or last page. An arXiv preprint carries none, which is itself the answer: there is
    no licence to rely on, only the fact that numbers are not protected.
    """
    path = ROOT / rel
    if not path.exists():
        return None, 'local copy absent'
    if path.suffix == '.xml':
        block = re.search(r'<permissions>(.*?)</permissions>', path.read_text(encoding='utf-8', errors='replace'), re.S)
        text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', block.group(1))).strip() if block else ''
    else:
        pages = pdf_edges(path)
        found = re.findall(r'[^\n]{0,80}(?:Creative Commons|creativecommons\.org|CC[ -]BY|[Aa]ll rights reserved)[^\n]{0,80}',
                           pages)
        text = ' '.join(' '.join(f.split()) for f in list(dict.fromkeys(found))[:3])
    if not text:
        return None, 'copy states no licence'
    low = text.lower()
    for pattern, name in (('by-nc-nd', 'CC-BY-NC-ND-4.0'), ('noncommercial-noderiv', 'CC-BY-NC-ND-4.0'),
                          ('licenses/by-sa', 'CC-BY-SA-4.0'), ('licenses/by/3.0', 'CC-BY-3.0'),
                          ('attribution 3.0', 'CC-BY-3.0'), ('licenses/by/4.0', 'CC-BY-4.0'),
                          ('cc-by 4.0', 'CC-BY-4.0'), ('attribution 4.0', 'CC-BY-4.0'),
                          ('all rights reserved', 'all-rights-reserved'),
                          ('view, print, copy', 'author-manuscript')):
        if pattern in low:
            return name, text[:240]
    return None, text[:240]


def pdf_edges(path):
    import pypdf
    pages = pypdf.PdfReader(str(path)).pages
    chosen = list(pages[:2]) + list(pages[-2:])
    return '\n'.join((page.extract_text() or '') for page in chosen)


def card_prose(card):
    """The strings of a card that a reader of the published question actually sees."""
    out = []
    for key in ('topic', 'ask', 'setting', 'goal'):
        if isinstance(card.get(key), str):
            out.append((key, card[key]))
    for fact in card.get('facts') or []:
        if fact.get('text'):
            out.append(('fact ' + str(fact.get('id', '')), fact['text']))
    for name, value in (card.get('conclusions') or {}).items():
        if isinstance(value, dict) and value.get('text'):
            out.append(('conclusion ' + name, value['text']))
    for candidate in card.get('candidates') or []:
        for key in ('description', 'note', 'paper_name', 'label'):
            if isinstance(candidate.get(key), str) and len(candidate[key].split()) > 4:
                out.append(('candidate %s/%s' % (candidate.get('id'), key), candidate[key]))
    return out


def longest_run(ours, index, theirs):
    """The longest run of consecutive words our text shares with theirs, and that run."""
    best, at, previous = 0, None, {}
    for i, word in enumerate(ours):
        current = {}
        for j in index.get(word, ()):
            length = previous.get(j - 1, 0) + 1
            current[j] = length
            if length > best:
                best, at = length, i
        previous = current
    return (best, ' '.join(ours[at - best + 1:at + 1])) if at is not None else (0, '')


def cards():
    """Every published evidence or design card, with the file it was published as."""
    out = []
    for folder in ('evidence', 'design', 'design/resolved'):
        for path in sorted((ROOT / 'docs/assets/families' / folder).glob('*.json')):
            card = json.loads(path.read_text(encoding='utf-8'))
            if card.get('kind') in ('evidence_card', 'design_card'):
                out.append((path.relative_to(ROOT).as_posix(), card))
    return out


def quote_scan():
    """Each card's longest verbatim run against its own paper. A card whose paper is not on this machine is
    recorded as unchecked, so a run elsewhere cannot turn an unknown into a clean result."""
    texts, rows = {}, []
    for rel, card in cards():
        key = card.get('paper')
        source = SOURCES.get(key) or {}
        text = source.get('fulltext')
        if not text or not (ROOT / text).exists():
            rows.append(dict(card=rel, source=key, checked=False,
                             why='全文不在本机：%s' % (text or '未登记全文位置')))
            continue
        if key not in texts:
            sequence, index = words(full_text(text)), {}
            for i, word in enumerate(sequence):
                index.setdefault(word, []).append(i)
            texts[key] = (sequence, index)
        sequence, index = texts[key]
        worst = (0, '', None)
        for field, prose in card_prose(card):
            length, run = longest_run(words(prose), index, sequence)
            if length > worst[0]:
                worst = (length, run, field)
        rows.append(dict(card=rel, source=key, checked=True, longest_run=worst[0], field=worst[2],
                         run=worst[1], needs_rewording=worst[0] >= QUOTE_WORDS))
    rows.sort(key=lambda r: (-(r.get('longest_run') or 0), r['card']))
    return rows


def build():
    catalog = read('docs/data/catalog.json')
    workbench = read('docs/data/family-workbench.json')
    manifest = {s['id']: s for s in read('templates/family-manifest.json')['items']}
    packets = {p['id']: p for p in workbench['student_packets']}
    teachers = {t['id']: t for t in workbench['teacher_answers']}
    questions = [q for q in catalog['questions']
                 if q.get('lifecycle') == 'active' and q.get('familyInstance')]

    rows, findings = [], []
    scan = quote_scan()
    by_source = {}
    for question in questions:
        by_source.setdefault(question['paper'], []).append(question)

    for key in sorted(SOURCES, key=lambda k: (-len(by_source.get(k, [])), k)):
        source = SOURCES[key]
        mine = by_source.get(key, [])
        kinds, families = {}, set()
        for question in mine:
            family = packets[question['familyInstance']]['family']
            families.add(family)
            card = ({'kind': 'design_pointer_card'} if family == 'design_choice' else
                    {'kind': 'evidence_card'} if family.startswith('evidence_') else None)
            label = PUBLISHES[folders.coordinates_kind(question, card)]
            kinds[label] = kinds.get(label, 0) + 1
        stated, statement = (licence_in(source['fulltext']) if source.get('fulltext') else (None, None))
        declared = source['declared']
        licence = stated or declared
        terms = LICENCES.get(licence) if licence else None
        where = [w for w in source['where'] if (ROOT / w).exists()]
        flagged = [r for r in scan if r['source'] == key and r.get('needs_rewording')]
        unchecked = [r for r in scan if r['source'] == key and not r['checked']]
        # Who says so. A licence the source's own copy states is settled; one that only a record of ours
        # states was written down by an assistant from the database's web page at download time, and is what
        # a pre-upload check has to look at again.
        confirmation = 'publisher_copy' if stated else ('repo_record_only' if licence else 'not_relied_on')
        republished = 'upstream_coordinates' in kinds
        if republished and terms and not terms['republish']:
            verdict, note = 'blocked', '不能转载的来源却发布了它的坐标'
        elif republished and terms and terms['share_alike']:
            verdict, note = 'decision_open', '相同方式共享：整库许可要先定（见 findings）'
        elif terms and not terms['republish'] and flagged:
            verdict, note = 'recheck', '该来源不允许转载原文，而卡片里有逐词相同的句子'
        elif republished and confirmation == 'repo_record_only':
            verdict, note = 'recheck', '发布了它的坐标，而许可只有我们自己的记录，没有本机可核对的上游副本'
        elif licence is None:
            verdict, note = 'clear', '只用数值与事实，不依赖该来源的许可'
        else:
            verdict, note = 'clear', ''
        rows.append(dict(
            source=key, name=source['name'], kind=source['kind'], questions=len(mine),
            families=sorted(families), publishes=kinds,
            publishes_label=[PUBLISHES_LABEL[k] for k in sorted(kinds)],
            license=licence, license_label=terms['label'] if terms else '不依赖许可（只用事实数值）',
            declared_in_repo=declared, stated_by_source=stated, source_statement=statement,
            confirmation=confirmation, evidence_paths=where,
            fulltext_checked=source.get('fulltext') if stated else None,
            obligations=([] if not terms else
                         ([] if not terms['attribution'] else ['署名'])
                         + (['相同方式共享'] if terms['share_alike'] else [])
                         + ([] if terms['republish'] else ['不得转载原文内容，只能用事实与数值'])),
            also=source.get('also'), verdict=verdict, verdict_note=note,
            cards_to_reword=[r['card'] for r in flagged],
            cards_unchecked=[r['card'] for r in unchecked]))
        if stated and declared and stated != declared:
            findings.append(dict(id='licence-mismatch:' + key, severity='must_check',
                                 what='仓库记作 %s，论文自带的 JATS 许可块写的是 %s' % (declared, stated),
                                 where=where + [source['fulltext']],
                                 fix='以出版方声明为准：上传前在出版方页面确认，然后改仓库记录'))
        if verdict == 'decision_open':
            findings.append(dict(id='licence-share-alike:' + key, severity='decision',
                                 what='%s 是相同方式共享许可，本库发布了它的坐标（%d 道）' % (licence, len(mine)),
                                 where=where, fix='三条路：整库 CC BY-SA；这几道单独成一个 CC BY-SA 子集；或撤掉这几道'))
        if verdict == 'blocked':
            findings.append(dict(id='licence-blocked:' + key, severity='must_fix', what=note,
                                 where=where, fix='撤掉这些附件，或改成只用数值重建'))

    # The licence recorded per question, which is what the per-question folders and the site show.
    missing = sorted(i for i, t in teachers.items() if not t.get('license') and i in packets)
    mit = sorted(i for i, t in teachers.items()
                 if 'MIT' in (t.get('license') or '') and i in packets)
    manifest_missing = sorted(i for i, s in manifest.items() if not s.get('license'))
    manifest_mit = sorted(i for i, s in manifest.items() if 'MIT' in (s.get('license') or ''))
    if manifest_missing:
        findings.append(dict(id='manifest-licence-blank', severity='must_fix',
                             what='%d 个族实例在 templates/family-manifest.json 里没有许可' % len(manifest_missing),
                             where=['templates/family-manifest.json'], fix='逐条填上来源的许可'))
    if manifest_mit:
        findings.append(dict(id='manifest-licence-mit', severity='must_fix',
                             what='%d 个 SAMPL9 实例记作 MIT；MIT 只覆盖代码，结构与实测表是 CC BY 4.0' % len(manifest_mit),
                             where=['templates/family-manifest.json'], fix='改成 CC BY 4.0'))
    if missing or mit:
        findings.append(dict(id='published-licence-stale', severity='pending_rerun',
                             what='已发布数据里还有 %d 道没有许可、%d 道记作 MIT；清单已在 manifest 改好，'
                                  '要等下一次重跑题库才会生效' % (len(missing), len(mit)),
                             where=['docs/data/family-workbench.json'],
                             fix='11/05–11/08 A1 重跑时一起带出；重跑后 tests/test_license.py 的待办清单会变红，删掉即可'))
    record_only = [r for r in rows if r['verdict'] == 'recheck' and r['confirmation'] == 'repo_record_only'
                   and 'upstream_coordinates' in r['publishes']]
    if record_only:
        findings.append(dict(
            id='licence-recorded-by-us-only', severity='must_check',
            what='%d 个数据库／数据集的坐标已发布，而许可只有我们自己的记录：%s'
                 % (len(record_only), '、'.join(r['source'] for r in record_only)),
            where=sorted({p for r in record_only for p in r['evidence_paths']}),
            fix='上传前逐个到来源页面核对一次（PDB CC0、COD 公有领域、QM7-X / OE62 / Landscape17 的 CC 声明），'
                '把看到的原话和日期写进对应的 sources.json（PDB 与 COD 是下载时记的，SAMPL9 的分节许可只写在仓库外的 README 里）'))
    reword = [r for r in scan if r.get('needs_rewording')]
    if reword:
        findings.append(dict(id='card-prose-verbatim', severity='must_check',
                             what='%d 张卡里有 ≥%d 个词与原文逐词相同（最长 %d 词）'
                                  % (len(reword), QUOTE_WORDS, max(r['longest_run'] for r in reword)),
                             where=[r['card'] for r in reword],
                             fix='L1 改写这些句子；非 CC 来源（Filip 2014、Jiang 2015、Rasmussen 2011）优先'))

    published = {k: sum(1 for r in rows if r['verdict'] == k)
                 for k in ('clear', 'recheck', 'decision_open', 'blocked')}
    return dict(
        kind='license_audit', date=date.today().isoformat(), bank_run=workbench['run'],
        questions=len(questions), sources=len(SOURCES),
        scope='逐来源核对：我们从它那里发布了什么、它的许可允许什么、许可写在哪。'
              '只读本仓库记录与本机论文全文，不联网；没有记录的写成 unverified，不替它断定。',
        verdicts=published,
        quote_threshold=QUOTE_WORDS,
        quote_scan=scan,
        pending_rerun=dict(
            note='下面这些已在 templates/family-manifest.json 改好，但要等下一次重跑题库才会进已发布数据。',
            published_without_license=missing, published_as_mit=mit),
        rows=rows, findings=findings)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--print', action='store_true', dest='show')
    args = parser.parse_args()
    audit = build()
    out = ROOT / 'docs/data/license-audit.json'
    out.write_bytes((json.dumps(audit, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    print('License audit: %d sources, %d questions; %s' %
          (audit['sources'], audit['questions'],
           '，'.join('%s %d' % (k, v) for k, v in audit['verdicts'].items())))
    print('%d findings; %d cards scanned, %d to reword, %d unchecked' %
          (len(audit['findings']), sum(1 for r in audit['quote_scan'] if r['checked']),
           sum(1 for r in audit['quote_scan'] if r.get('needs_rewording')),
           sum(1 for r in audit['quote_scan'] if not r['checked'])))
    if args.show:
        for row in audit['rows']:
            print('%-9s %3d  %-42s %-18s %s' % (row['verdict'], row['questions'], row['source'],
                                                row['license'] or '-', ','.join(sorted(row['publishes']))))
        for finding in audit['findings']:
            print('  [%s] %s — %s' % (finding['severity'], finding['id'], finding['what']))


if __name__ == '__main__':
    main()
