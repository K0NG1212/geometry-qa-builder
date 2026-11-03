"""A1: name the structures to download, pixel by pixel, from the databases themselves.

The bank has 336 questions in 44 of the 74 meaningful pixels of the subdomain map; 30 meaningful pixels hold nothing and
seven hold one or two. Those gaps cannot be enumerated away -- a zeolite question needs a zeolite -- so the only lever is
more source structures (A1). This tool turns each empty or thin pixel into a concrete download list by asking COD and RCSB
for real entries: no identifier here is written from memory.

Columns of the grid need different kinds of structure, because a question is filed by the scale its reasoning lives at:
  * 0.1-1 nm     an ordinary unit cell, a bond, a coordination shell   -> COD cells, small PDB chains
  * 1-10 nm      a large cell (zeolite, MOF, polymer, layered c axis)  -> COD large cells, small proteins, DNA
  * 10-100 nm    an assembly                                           -> PDB capsids, machines, cages
  * 100-1000 nm  a model built from a paper's numbers                  -> papers, not downloads (tier C)

python tools/plan_a1.py              # query and write templates/a1-download-plan.json
python tools/plan_a1.py --offline    # re-render the summary from the file already written
"""
import argparse
import hashlib
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'templates/a1-download-plan.json'
MAP = ROOT / 'docs/data/subdomain-map.json'
COD = 'https://www.crystallography.net/cod/result?%s&format=json'
RCSB = 'https://search.rcsb.org/rcsbsearch/v2/query?json=%s'
ENTRY = 'https://data.rcsb.org/rest/v1/core/entry/%s'
ELEMENT = re.compile(r'([A-Z][a-z]?)[\d.]*')

# Every pixel that holds nothing or almost nothing, with what it needs and what can consume it.
TARGETS = [
    # ---- 0.1-1 nm: ordinary cells and bonds -------------------------------------------------------------------
    dict(pixel='P2 0.1-1', name='磁性', want=4, db='cod', formulas=['Fe3 O4', 'Cr2 O3', 'Mn O', 'Ni O', 'Co O'],
         why='磁性这一格一道题都没有；磁性氧化物的晶胞与配位壳层是最直接的几何量',
         families=['coordination_shell', 'first_diffraction_peak', 'kinematic_extinction']),
    dict(pixel='M7 0.1-1', name='表面与界面', want=4, db='cod', formulas=['O2 Ti', 'Mg O', 'Al2 O3', 'O3 Sr Ti'],
         why='表面与界面整个一级分类都是空的；先用常见表面材料的体相晶胞把 0.1-1 nm 撑起来',
         families=['coordination_shell', 'first_diffraction_peak', 'named_bond_distance']),
    dict(pixel='B5 0.1-1', name='毒素', want=4, db='pdb', text='snake venom neurotoxin', resolution=1.8, chains=1,
         why='毒素这一格是空的，而毒素正是「结构 → 性质」最有故事的一类',
         families=['backbone_torsion', 'secondary_structure', 'disulfide_design', 'named_bond_distance']),
    dict(pixel='B7 0.1-1', name='核酸与核蛋白', want=4, db='pdb', text='B-DNA dodecamer oligonucleotide crystal',
         resolution=1.8, chains=2,
         why='核酸只有 1EHZ / 355D / 1BNA 三个，核酸与核蛋白 0.1-1 nm 是空的',
         families=['backbone_torsion', 'named_bond_distance', 'named_bond_angle']),

    # ---- 1-10 nm: large cells, small proteins, DNA -------------------------------------------------------------
    dict(pixel='C5 1-10', name='反应与催化', want=5, db='cod', text='zeolite', elements=['Si', 'O', 'Al'],
         min_volume=2500,
         why='反应与催化 1-10 nm 是空的；沸石骨架的孔径与笼径正好落在这一档',
         families=['coordination_shell', 'first_diffraction_peak', 'scattering_q_design', 'diffraction_design']),
    dict(pixel='C6 1-10', name='高分子化学', want=4, db='cod', texts=['isotactic', 'syndiotactic', 'nylon', 'polyester'],
         elements=['C', 'H'], only_elements=['C', 'H', 'N', 'O', 'F'], min_max_edge=10,
         why='高分子化学三格全空；链周期与晶胞是最小可用的几何量',
         families=['named_bond_distance', 'named_bond_angle', 'first_diffraction_peak', 'extent_choice_v2']),
    dict(pixel='C3 1-10', name='无机与配位化学', want=4, db='cod', text='metal-organic framework',
         elements=['C', 'O'], min_volume=5000,
         why='无机与配位化学 1-10 nm 只有 1 道；MOF 的大晶胞与金属配位壳层同时能出感知与推断题',
         families=['coordination_shell', 'scattering_q_design', 'first_diffraction_peak']),
    dict(pixel='P1 1-10', name='超导', want=4, db='cod',
         formulas=['Ba2 Cu3 O7 Y', 'Bi2 Ca Cu2 O8 Sr2', 'Nb3 Sn', 'B2 Mg', 'Fe Se'],
         why='超导 1-10 nm 与 10-100 nm 都空着；BSCCO 这类层状超导体的 c 轴本身就是 3 nm 量级',
         families=['first_diffraction_peak', 'kinematic_extinction', 'coordination_shell']),
    dict(pixel='P3 1-10', name='二维材料与莫尔物理', want=4, db='cod', formulas=['Mo S2', 'C', 'B N', 'Se2 W'],
         why='二维材料 0.1-1 nm 只有 1 道、1-10 nm 是空的；层间距与超胞周期是现成的几何量',
         families=['first_diffraction_peak', 'kinematic_extinction', 'named_bond_distance']),
    dict(pixel='M1 1-10', name='金属与合金', want=4, db='cod', text='intermetallic', elements=['Al'], min_volume=1500,
         why='金属与合金 1-10 nm 是空的；金属间化合物的大晶胞落在这一档',
         families=['coordination_shell', 'first_diffraction_peak', 'kinematic_extinction']),
    dict(pixel='M2 1-10', name='陶瓷与氧化物', want=4, db='cod',
         formulas=['Al14 Ca12 O33', 'Al5 O12 Y3', 'Mg2 O4 Si', 'Al2 Mg O4'], min_volume=280,
         why='这一格枚举估计已有 13 道产能却一道没选上；大晶胞氧化物能把它直接填起来',
         families=['coordination_shell', 'first_diffraction_peak', 'scattering_q_design']),
    dict(pixel='M3 1-10', name='半导体', want=4, db='cod', formulas=['Cd Se', 'Ga N', 'In P', 'Cs I3 Pb', 'Cd Te'],
         why='这一格枚举估计有 7 道产能也没选上；补几个半导体晶胞顺便覆盖卤化物钙钛矿子领域',
         families=['first_diffraction_peak', 'kinematic_extinction', 'coordination_shell']),
    dict(pixel='M5 1-10', name='有机与高分子材料', want=4, db='cod', formulas=['C22 H14', 'C42 H28', 'C14 H10', 'C18 H12'],
         min_volume=400,
         why='有机与高分子材料 1-10 nm 只有 1 道；并五苯、红荧烯这类有机半导体晶体的分子长轴正好 1-2 nm',
         families=['named_bond_distance', 'extent_choice_v2', 'first_diffraction_peak']),
    dict(pixel='M8 1-10', name='生物与仿生材料', want=4, db='cod',
         formulas=['Ca5 H O13 P3', 'C Ca O3', 'Ca O4 S', 'Ca H2 O6 S'],
         why='生物与仿生材料 1-10 / 10-100 两格都空；羟基磷灰石与碳酸钙是生物矿物的标准体系',
         families=['coordination_shell', 'first_diffraction_peak', 'named_bond_distance']),
    dict(pixel='P5 1-10', name='原子与分子物理', want=3, db='cod', formulas=['C60', 'C70'], texts=['fullerene'],
         elements=['C'], only_elements=['C'], min_max_edge=10,
         why='原子与分子物理 1-10 nm 只有 2 道；富勒烯团簇的笼径与转动常数都能出题',
         families=['extent_choice_v2', 'rotational_line', 'isotopologue_design']),
    dict(pixel='C7 1-10', name='化学生物学与 DNA 纳米技术', want=4, db='pdb', text='Holliday junction four-way DNA',
         resolution=3.0,
         why='DNA 纳米技术 1-10 nm 是空的，而我们已有 7ARQ 这种 origami，中间这一档缺一个台阶',
         families=['backbone_torsion', 'extent_choice_v2', 'named_bond_distance']),
    dict(pixel='B4 1-10', name='膜蛋白', want=4, db='pdb', text='membrane transporter alpha-helical', resolution=2.2,
         chains=1,
         why='膜蛋白 0.1-1 与 1-10 各只有 1 道；跨膜螺旋的几何是现成的推断题材料',
         families=['secondary_structure', 'backbone_torsion', 'fret_design', 'fret_efficiency']),
    dict(pixel='B8 1-10', name='大分子机器', want=4, db='pdb', text='chaperonin', resolution=3.5, min_chains=7,
         why='大分子机器这一格是空的，而它正是「几何 → 功能」最直观的一类',
         families=['assembly_extent', 'assembly_rg', 'secondary_structure', 'scattering_q_design']),

    # ---- 10-100 nm: assemblies ---------------------------------------------------------------------------------
    dict(pixel='M6 10-100', name='纳米材料与组装', want=4, db='pdb', text='protein nanocage', resolution=4.5,
         min_chains=12,
         why='纳米材料与组装 1-10 与 100-1000 两格空着、10-100 也薄；人工蛋白笼是现成的组装体',
         families=['assembly_extent', 'assembly_rg', 'capsid_architecture', 'guinier_intensity']),
    dict(pixel='P4 10-100', name='纳米与介观物理', want=3, db='pdb', text='encapsulin', resolution=4.5, min_chains=12,
         why='纳米与介观物理 10-100 nm 是空的；壳状蛋白的腔体直径接上量子点那一档',
         families=['assembly_extent', 'assembly_rg', 'capsid_architecture']),
    dict(pixel='B8 10-100', name='大分子机器（组装体）', want=3, db='pdb', text='flagellar filament', resolution=4.5,
         min_chains=11,
         why='给大分子机器补一个 10-100 nm 的台阶，和 1-10 nm 的那批成对',
         families=['assembly_extent', 'assembly_rg', 'scattering_q_design']),

    # ---- what downloads cannot fix: tier C pixels need a paper ---------------------------------------------------
    dict(pixel='C8 10-100', name='液晶与胶体化学', want=0, db='paper',
         why='液晶 100-1000 nm 已有 10 道（胆甾相），10-100 nm 要另找一篇短螺距或胶体晶体的论文',
         families=['cholesteric_geometry', 'cholesteric_optics', 'opal_bragg']),
    dict(pixel='C6 10-100 / C6 100-1000', name='高分子化学', want=0, db='paper',
         why='片晶厚度（10-100 nm）与球晶（100-1000 nm）只能按论文数值建模',
         families=['superlattice_metric', 'guinier_intensity']),
    dict(pixel='C7 100-1000', name='化学生物学与 DNA 纳米技术', want=0, db='paper',
         why='DNA origami 的微米级阵列要按论文的晶格常数建模',
         families=['superlattice_saxs', 'superlattice_metric']),
    dict(pixel='P2 1-10 / P2 100-1000', name='磁性', want=0, db='paper',
         why='斯格明子晶格与磁畴周期是 100-1000 nm，只能按论文实测周期建模（已有 muhlbauer 可用）',
         families=['vortex_geometry', 'vortex_design', 'vortex_inference']),
    dict(pixel='P7 1-10 / P7 10-100 / P7 100-1000', name='软物质与生物物理', want=0, db='paper',
         why='软物质整个一级分类都是空的：胶体堆积、聚合物链统计、膜与囊泡三条都要论文参数模型',
         families=['guinier_intensity', 'debye_intensity', 'opal_geometry']),
    dict(pixel='P1 10-100', name='超导', want=0, db='paper',
         why='超导 10-100 nm 是相干长度与穿透深度的尺度，按论文实测值建模（已有 cottet / schaefermeier）',
         families=['vortex_geometry', 'vortex_inference']),
    dict(pixel='M5 10-100 / M8 10-100 / M6 100-1000 / M7 1-10', name='材料其余空格', want=0, db='paper',
         why='聚合物晶片、生物矿物的介观结构、纳米粒子超晶格、界面重构，都是论文参数模型的活',
         families=['superlattice_saxs', 'superlattice_shell', 'opal_geometry']),
]


CACHE = ROOT / 'inputs/a1-query-cache'


def get(url, timeout=60, tries=4):
    """A database query, cached on disk. An empty body means no hits; COD truncates or drops a big response now and then."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / (hashlib.sha256(url.encode('utf-8')).hexdigest()[:24] + '.json')
    if cached.exists():
        return json.loads(cached.read_text(encoding='utf-8'))
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                body = response.read().decode('utf-8').strip()
            result = json.loads(body) if body else []
            cached.write_text(json.dumps(result), encoding='utf-8')
            return result
        except (urllib.error.URLError, ConnectionError, TimeoutError, json.JSONDecodeError,
                http.client.IncompleteRead, OSError) as exc:
            if attempt == tries - 1:
                print('  查询失败（%s），这一项记为 0 条：%s' % (type(exc).__name__, url[:90]))
                return []
            time.sleep(4)


def elements_of(formula):
    return set(ELEMENT.findall((formula or '').replace('-', ' ')))


def long_enough(row, target):
    """A question is filed by the scale its reasoning lives at, so for 1-10 nm what matters is the longest cell edge."""
    if target.get('min_volume') and float(row['vol']) < target['min_volume']:
        return False
    if target.get('min_max_edge'):
        return max(float(row['a']), float(row['b']), float(row['c'])) >= target['min_max_edge']
    return True


def cod_row(row, formula_fallback=''):
    return dict(id=row['file'], formula=(row.get('formula') or formula_fallback).strip(' -'),
                cell_volume_A3=float(row['vol']), a=row['a'], b=row['b'], c=row['c'],
                spacegroup=(row.get('sg') or '').strip(),
                name=(row.get('mineral') or row.get('commonname') or row.get('chemname') or '').strip(),
                url='https://www.crystallography.net/cod/%s.cif' % row['file'],
                license='COD: public domain (CC0)')


def cod_entries(target):
    """Real COD entries for one pixel: exact formulas when they are known, else a keyword plus an element filter."""
    out, seen = [], set()
    for formula in target.get('formulas', []):
        rows = [r for r in get(COD % urllib.parse.urlencode(dict(formula=formula)))
                if r.get('a') and r.get('b') and r.get('c') and r.get('vol')]
        rows = [r for r in rows if long_enough(r, target)]
        rows.sort(key=lambda r: -float(r['vol']))
        for row in rows:                                   # one entry per formula keeps the chemistry spread out
            if row['file'] not in seen:
                seen.add(row['file'])
                out.append(cod_row(row, formula))
                break
    keywords = target.get('texts') or ([target['text']] if target.get('text') else [])
    wanted = set(target.get('elements', []))
    allowed = set(target['only_elements']) if target.get('only_elements') else None
    shortlists = []
    for keyword in keywords:
        rows = [r for r in get(COD % urllib.parse.urlencode(dict(text=keyword)))
                if r.get('a') and r.get('b') and r.get('c') and r.get('vol')]
        shortlist, formulas = [], set()
        for row in sorted(rows, key=lambda r: -float(r['vol'])):
            have = elements_of(row.get('formula'))
            if not wanted <= have or (allowed is not None and not have <= allowed):
                continue
            if not long_enough(row, target):
                continue
            key = (row.get('formula') or '').strip()
            if key in formulas:                 # one entry per composition, or four hits become four polymorphs
                continue
            formulas.add(key)
            shortlist.append(dict(cod_row(row), keyword=keyword))
        shortlists.append(shortlist)
    picked_formulas = set()
    for depth in range(max((len(s) for s in shortlists), default=0)):
        for shortlist in shortlists:            # round robin, so several keywords stay represented
            if len(out) >= target['want']:
                break
            if depth >= len(shortlist):
                continue
            entry = shortlist[depth]
            if entry['id'] in seen or entry['formula'] in picked_formulas:
                continue
            seen.add(entry['id'])
            picked_formulas.add(entry['formula'])
            out.append(entry)
    return out[:target['want']]


def pdb_entries(target):
    nodes = [dict(type='terminal', service='full_text', parameters=dict(value=target['text']))]
    if target.get('resolution'):
        nodes.append(dict(type='terminal', service='text', parameters=dict(
            attribute='rcsb_entry_info.resolution_combined', operator='less', value=target['resolution'])))
    if target.get('chains'):
        nodes.append(dict(type='terminal', service='text', parameters=dict(
            attribute='rcsb_entry_info.deposited_polymer_entity_instance_count', operator='equals',
            value=target['chains'])))
    if target.get('min_chains'):
        nodes.append(dict(type='terminal', service='text', parameters=dict(
            attribute='rcsb_entry_info.deposited_polymer_entity_instance_count', operator='greater_or_equal',
            value=target['min_chains'])))
    query = dict(query=dict(type='group', logical_operator='and', nodes=nodes), return_type='entry',
                 request_options=dict(paginate=dict(start=0, rows=max(target['want'] * 3, 10)),
                                      results_content_type=['experimental']))
    hits = get(RCSB % urllib.parse.quote(json.dumps(query)))
    out = []
    for hit in (hits.get('result_set', []) if isinstance(hits, dict) else []):
        entry = get(ENTRY % hit['identifier'])
        info = entry.get('rcsb_entry_info', {})
        out.append(dict(id=hit['identifier'], title=(entry.get('struct', {}).get('title') or '').strip(),
                        method=(info.get('experimental_method') or '').strip(),
                        resolution_A=(info.get('resolution_combined') or [None])[0],
                        chains=info.get('deposited_polymer_entity_instance_count'),
                        atoms=info.get('deposited_atom_count'),
                        url='https://files.rcsb.org/download/%s.pdb' % hit['identifier'],
                        page='https://www.rcsb.org/structure/%s' % hit['identifier'],
                        license='wwPDB (CC0)'))
        if len(out) == target['want']:
            break
    return out


def build():
    pixels = {p['l1'] + ' ' + p['scale']: p for p in json.loads(MAP.read_text(encoding='utf-8'))['pixels']
              if p['meaningful']}
    plan, totals = [], dict(cod=0, pdb=0, paper=0)
    for target in TARGETS:
        row = dict(pixel=target['pixel'], subdomain=target['name'], database=target['db'], wanted=target['want'],
                   why=target['why'], families=target['families'])
        key = ' '.join(target['pixel'].split(' ')[:2])
        if key in pixels:
            row['questions_now'] = pixels[key]['questions']
            row['enumerated_estimate'] = pixels[key]['enumerated_estimate']
        if target['db'] == 'cod':
            row['entries'] = cod_entries(target)
        elif target['db'] == 'pdb':
            row['entries'] = pdb_entries(target)
        else:
            row['entries'] = []
            row['note'] = '要论文，不是下载：按论文实测数值建模（tier C）'
        totals[target['db']] += len(row['entries'])
        plan.append(row)
        print('%-40s %-6s %d/%d' % (target['pixel'], target['db'], len(row['entries']), target['want']))
    return dict(kind='a1_download_plan', version='0.1.0', date='2026-11-02', status='provisional',
                note='按 docs/data/subdomain-map.json 的空像素点名。条目由 COD 与 RCSB 的检索接口返回，没有一个是凭记忆写的；'
                     'COD CIF 约 7 KB 一个，PDB 结构约 200 KB 一个（docs/assets/bio 现有 14 个共 2.8 MB）。'
                     '100-1000 nm 的空格下载解决不了，要论文参数模型，单列在 database=paper 的行里。',
                totals=totals, pixels_meaningful=len(pixels),
                pixels_empty=sum(1 for p in pixels.values() if p['questions'] == 0), targets=plan)


def summary(plan):
    print('\n| 像素 | 子领域 | 库 | 现有题 | 要下 | 条目 |')
    print('|---|---|---|---|---|---|')
    for row in plan['targets']:
        ids = ', '.join(e['id'] for e in row['entries']) or '（要论文）'
        print('| %s | %s | %s | %s | %d | %s |' % (row['pixel'], row['subdomain'], row['database'],
                                                  row.get('questions_now', '—'), row['wanted'], ids))
    print('\nCOD %(cod)d + PDB %(pdb)d 个结构' % plan['totals'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='只重新渲染已写好的计划')
    args = parser.parse_args()
    if args.offline:
        summary(json.loads(OUT.read_text(encoding='utf-8')))
    else:
        result = build()
        OUT.write_bytes((json.dumps(result, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
        summary(result)
        print('\n写入', OUT.relative_to(ROOT).as_posix())
