"""How much of each source's structure space the question pool actually samples.

  python -m review_system.datasources            # -> docs/data/source-coverage.json
  python -m review_system.datasources --fetch    # also re-queries RCSB and rewrites the cached facts

The advisor's question (written, 2026-11-09): "why choose this source, e.g. PDB, whether this source cover
the structure space for a particular data object as much as possible". The second half is the quantitative
one, and the naive reading of it is useless: 49 PDB entries out of 262513 is 0.02%, and no benchmark is ever
going to move that number. What the question is really about is *strata*. The sub-domain tree already says
how each subdomain picks its structures -- B1 "按 EC 大类各取代表", B2 "按 CATH 类别", M2 "按结构原型",
C2 "按元素组成、柔性、分子大小分层" -- so the honest measurement is: of the strata we declared, how many do
we actually have a structure in, and are the ones we have the big strata or the small ones.

That is what this module computes. It takes the numerator from the repository (the catalog, the family
manifest and the published assets) and the denominator from docs/content/external-counts.json, where every
external number carries its provenance: queried from the source's own API, or cited from its paper. Nothing
here is hand-entered.

Facts about individual PDB entries (method, resolution, polymer types, EC class) come from the RCSB GraphQL
service and are cached in docs/content/pdb-entry-facts.json, so an ordinary run and the tests need no
network. --fetch refreshes that cache; the RCSB id validation is a side effect of it, since the service
returns only entries it knows, which is how the 100-odd false positives from id-shaped strings in our own
metadata (arXiv numbers, QM7-X indices, variant labels like 00WT) get dropped.
"""
import argparse
import collections
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = 'docs/data/source-coverage.json'
COUNTS = 'docs/content/external-counts.json'
FACTS = 'docs/content/pdb-entry-facts.json'
AGENT = 'GeoBench-coverage-audit/0.1'
GRAPHQL = 'https://data.rcsb.org/graphql'
SEARCH = 'https://search.rcsb.org/rcsbsearch/v2/query'
PDB_SHAPED = re.compile(r'\b([0-9][A-Za-z0-9]{3})\b')
EC_NAMES = {'1': ('氧化还原酶', 'oxidoreductases'), '2': ('转移酶', 'transferases'),
            '3': ('水解酶', 'hydrolases'), '4': ('裂合酶', 'lyases'),
            '5': ('异构酶', 'isomerases'), '6': ('连接酶', 'ligases'),
            '7': ('易位酶', 'translocases')}

# Which source a question's material came from. The catalog's `paper` field is the batch label, and it is
# the only field that distinguishes the five buckets without guessing from prose.
BUCKETS = (('rcsb_pdb', re.compile(r'^pdb-|^pdb_')),
           ('cod', re.compile(r'^cod-|^cod_')),
           ('qm7x', re.compile(r'^qm7x$')),
           ('sampl9', re.compile(r'^sampl9$')),
           ('oe62', re.compile(r'^oe62$')))


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def pool():
    """Active questions with the manifest item each one was built from."""
    items = {i['id']: i for i in read('templates/family-manifest.json')['items']}
    active = [q for q in read('docs/data/catalog.json')['questions'] if q['lifecycle'] == 'active']
    return [(q, items.get(q.get('familyInstance')) or {}) for q in active]


def bucket_of(question):
    label = (question.get('paper') or '').strip()
    for name, pattern in BUCKETS:
        if pattern.match(label):
            return name
    return 'papers'                      # an individual paper, named one per batch label


def pdb_candidates(rows):
    """Every id-shaped token in our own metadata, for RCSB to accept or reject."""
    ids = set(read('templates/subdomain-draft.json')['assignment']['pdb'])
    for question, item in rows:
        if item.get('pdb'):
            ids.add(item['pdb'].upper())
        blob = json.dumps(item, ensure_ascii=False) + ' ' + str(question.get('source', '')) + ' ' + question['title']
        ids.update(h.upper() for h in PDB_SHAPED.findall(blob))
    return sorted(ids)


def post(url, payload):
    import urllib.request
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'), method='POST',
        headers={'Content-Type': 'application/json', 'User-Agent': AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode('utf-8'))


def fetch_facts(ids):
    """Ask RCSB about each candidate id; unknown ids simply do not come back."""
    found = {}
    for start in range(0, len(ids), 40):
        query = ('{entries(entry_ids:%s){rcsb_id exptl{method} '
                 'rcsb_entry_info{resolution_combined selected_polymer_entity_types} struct{title} '
                 'polymer_entities{rcsb_polymer_entity{rcsb_ec_lineage{id depth}}}}}'
                 % json.dumps(ids[start:start + 40]))
        data = post(GRAPHQL, {'query': query})
        if 'errors' in data:
            raise SystemExit('RCSB GraphQL 报错：' + json.dumps(data['errors'], ensure_ascii=False)[:300])
        for entry in data['data']['entries'] or []:
            if not entry:
                continue
            info = entry['rcsb_entry_info']
            found[entry['rcsb_id']] = dict(
                method=(entry['exptl'] or [{}])[0].get('method', ''),
                resolution=(info.get('resolution_combined') or [None])[0],
                types=info.get('selected_polymer_entity_types'),
                ec1=sorted({l['id'] for pe in (entry.get('polymer_entities') or [])
                            for l in ((pe['rcsb_polymer_entity'] or {}).get('rcsb_ec_lineage') or [])
                            if l['depth'] == 1}),
                title=entry['struct']['title'])
        time.sleep(0.4)
    return found


def space_groups():
    """The space group of every crystal we publish, read from the CIF we ship."""
    groups = collections.Counter()
    for path in sorted((ROOT / 'docs/assets').rglob('*.cif')):
        text = path.read_text(encoding='utf-8', errors='replace')
        found = (re.search(r"_symmetry_space_group_name_H-M\s+'?\"?([^'\"\n]+)", text)
                 or re.search(r"_space_group_name_H-M_alt\s+'?\"?([^'\"\n]+)", text))
        groups[found.group(1).strip() if found else '(CIF 未写空间群)'] += 1
    return groups


def molecule_strata(rows):
    """Heavy-atom count and heavy-element set of every QM7-X molecule we use, from the xyz we ship."""
    names = sorted({str(item['molecule']) for _, item in rows
                    if str(item.get('molecule', '')).upper().startswith('QM7X')})
    heavy, elements, missing = collections.Counter(), collections.Counter(), []
    for name in names:
        index = re.search(r'(\d{4})', name)
        hits = sorted((ROOT / 'docs/assets').rglob('*%s*.xyz' % index.group(1))) if index else []
        if not hits:
            missing.append(name)
            continue
        lines = hits[0].read_text(encoding='utf-8', errors='replace').splitlines()[2:]
        symbols = [line.split()[0].upper() for line in lines if line.split()]
        rest = [s for s in symbols if s != 'H']
        heavy[len(rest)] += 1
        elements[''.join(sorted(set(rest)))] += 1
    return names, heavy, elements, missing


def build(facts, counts):
    rows = pool()
    questions = collections.Counter(bucket_of(q) for q, _ in rows)

    # which PDB entries the active questions actually name
    per_entry = collections.Counter()
    for question, item in rows:
        blob = json.dumps(item, ensure_ascii=False) + ' ' + str(question.get('source', '')) + ' ' + question['title']
        for hit in {h.upper() for h in PDB_SHAPED.findall(blob)}:
            if hit in facts:
                per_entry[hit] += 1
    entries = sorted(per_entry)
    pdb = dict(
        questions=questions['rcsb_pdb'],
        distinct_entries=len(entries), entries=entries,
        methods=dict(collections.Counter(facts[e]['method'] for e in entries)),
        polymer_types=dict(collections.Counter(facts[e]['types'] for e in entries)),
        resolution=dict(
            known=sum(1 for e in entries if facts[e]['resolution'] is not None),
            at_or_below_2A=sum(1 for e in entries
                               if facts[e]['resolution'] is not None and facts[e]['resolution'] <= 2.0),
            median=sorted(facts[e]['resolution'] for e in entries
                          if facts[e]['resolution'] is not None)[len(entries) // 2] if entries else None),
        ec_strata=[])
    ours = collections.Counter()
    for entry in entries:
        for ec in facts[entry]['ec1']:
            ours[ec] += 1
    for ec in '1234567':
        pdb['ec_strata'].append(dict(
            ec=ec, zh=EC_NAMES[ec][0], en=EC_NAMES[ec][1],
            in_source=counts['sources']['rcsb_pdb']['counts']['ec_%s' % ec]['n'],
            ours=ours.get(ec, 0)))
    pdb['entries_with_ec'] = sum(1 for e in entries if facts[e]['ec1'])
    pdb['ec_classes_covered'] = sum(1 for s in pdb['ec_strata'] if s['ours'])

    groups = space_groups()
    named = {k: v for k, v in groups.items() if not k.startswith('(')}
    cod = dict(questions=questions['cod'], cif_files=sum(groups.values()),
               space_groups_used=len(named),
               space_groups_possible=counts['sources']['cod']['counts']['space_groups_possible']['n'],
               entries_in_source=counts['sources']['cod']['counts']['entries']['n'],
               by_space_group=dict(sorted(named.items(), key=lambda kv: (-kv[1], kv[0]))),
               cif_without_space_group=groups.get('(CIF 未写空间群)', 0))

    names, heavy, elements, missing = molecule_strata(rows)
    qm = counts['sources']['qm7x']['counts']
    qm7x = dict(questions=questions['qm7x'], distinct_molecules=len(names),
                formulae_in_source=qm['molecular_formulae']['n'],
                equilibrium_structures_in_source=qm['equilibrium_structures']['n'],
                heavy_atoms_max_in_source=qm['heavy_atoms_max']['n'],
                by_heavy_atom_count={str(k): v for k, v in sorted(heavy.items())},
                by_heavy_elements=dict(elements), molecules_without_local_xyz=missing)

    # SAMPL9-<host>[-<guest>]: the host is the second field, and bCD and BCD are the same host written
    # two ways (the tree's canonical name is SAMPL9-BCD), so they are folded together.
    hosts, guests, unattributed = collections.Counter(), set(), 0
    for question, item in rows:
        if bucket_of(question) != 'sampl9':
            continue
        name = str(item.get('molecule') or '')
        parts = name.split('-')
        if len(parts) >= 2 and parts[0].upper() == 'SAMPL9':
            host = parts[1].upper()
            hosts['BCD' if host == 'BCD' else host] += 1
            if len(parts) >= 3:
                guests.add('-'.join(parts[1:]))
        else:
            unattributed += 1
    sampl = dict(questions=questions['sampl9'], hosts_used=len(hosts), by_host=dict(hosts),
                 distinct_guest_complexes=len(guests), questions_without_a_host_name=unattributed,
                 hosts_in_challenge=counts['sources']['sampl9']['counts']['hosts']['n'])

    labels = collections.Counter((q.get('paper') or '').strip() for q, _ in rows)
    papers = dict(questions=questions['papers'] + questions['oe62'],
                  distinct_labels=sum(1 for k in labels if bucket_of({'paper': k}) in ('papers', 'oe62')),
                  by_label={k: v for k, v in sorted(labels.items(), key=lambda kv: -kv[1])
                            if bucket_of({'paper': k}) in ('papers', 'oe62')})

    return dict(
        kind='source_coverage',
        note_zh='分子（我们用到多少）来自本仓库；分母（源里有多少）来自 docs/content/external-counts.json，'
                '每个数字带出处。覆盖率按「分层」算，不按条目总数算：见 DATA_SOURCES.md 的说明。',
        note_en='Numerators come from this repository; denominators come from docs/content/external-counts.json '
                'with a provenance on every number. Coverage is measured over strata, not over entry totals; '
                'DATA_SOURCES.md explains why.',
        external_counts_fetched_on=counts['fetched_on'],
        questions_by_source=dict(questions),
        questions_total=sum(questions.values()),
        rcsb_pdb=pdb, cod=cod, qm7x=qm7x, sampl9=sampl, papers=papers)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--fetch', action='store_true',
                        help='重新向 RCSB 查每个候选编号的方法、分辨率与 EC 号，并更新缓存')
    args = parser.parse_args(argv)

    if args.fetch:
        candidates = pdb_candidates(pool())
        print('候选编号 %d 个，交给 RCSB 裁定…' % len(candidates))
        facts = fetch_facts(candidates)
        rejected = [c for c in candidates if c not in facts]
        (ROOT / FACTS).write_text(json.dumps(
            dict(kind='pdb_entry_facts', fetched_on=time.strftime('%Y-%m-%d'),
                 note_zh='RCSB GraphQL 的回答。只有它认识的编号会回来，所以这份缓存同时起到校验作用：'
                         '我们自己元数据里那些长得像 PDB 号的字符串（arXiv 编号、QM7-X 序号、00WT 这类变体标签）'
                         '不会出现在这里。',
                 rejected_candidates=rejected, entries=facts), ensure_ascii=False, indent=1) + '\n',
            encoding='utf-8', newline='\n')
        print('  真条目 %d 个，RCSB 不认的 %d 个；写出 %s' % (len(facts), len(rejected), FACTS))

    cached = read(FACTS)
    result = build(cached['entries'], read(COUNTS))
    (ROOT / OUT).write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n',
                            encoding='utf-8', newline='\n')
    print('写出 %s' % OUT)
    print('  题目按来源：%s' % json.dumps(result['questions_by_source'], ensure_ascii=False))
    print('  PDB：%d 个条目，EC 七大类覆盖 %d 类，分辨率 ≤2 Å 的 %d / %d'
          % (result['rcsb_pdb']['distinct_entries'], result['rcsb_pdb']['ec_classes_covered'],
             result['rcsb_pdb']['resolution']['at_or_below_2A'], result['rcsb_pdb']['resolution']['known']))
    print('  COD：%d 个 CIF，%d / %d 个空间群'
          % (result['cod']['cif_files'], result['cod']['space_groups_used'], result['cod']['space_groups_possible']))
    print('  QM7-X：%d 个分子，重原子数 %s，重元素组合 %s'
          % (result['qm7x']['distinct_molecules'], json.dumps(result['qm7x']['by_heavy_atom_count']),
             json.dumps(result['qm7x']['by_heavy_elements'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
