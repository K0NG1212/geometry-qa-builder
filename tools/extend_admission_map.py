"""Give every newly published instance a catalog id, so tools/admit_family_instances.py can admit the batch.

The admission map must cover every instance of the published run exactly once (admit_family_instances checks it).
Writing several hundred entries by hand is not sensible, so this assigns each new instance the next free id of its
<domain><N><ability> series, the same scheme the bank already uses (BNP/BNI/BND, CNP/..., MNP/..., QNP/...), and a
title made of the structure it asks about and the family's Chinese name from templates/registry.json.

  python tools/extend_admission_map.py --dry-run
  python tools/extend_admission_map.py --write

Every entry is action "new": these are enumerated instances of reviewed families, not rebuilds of legacy records.
Admission still only takes instances that passed the independent checker, and still only as provisional.

It also forgets an instance the manifest no longer holds. A later selection round shifts target answer positions
within a family, so tools/stabilize_manifest.py may drop an instance that an earlier round had already mapped;
admit_family_instances would then refuse the whole batch ("Instance did not pass the independent checker").
"""
import argparse
import copy
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from task_families import FAMILIES  # noqa: E402

MAP = ROOT / 'templates/admission-map.json'
MANIFEST = ROOT / 'templates/family-manifest.json'
WORKBENCH = ROOT / 'docs/data/family-workbench.json'
CHECK = ROOT / 'docs/data/independent-check.json'
CATALOG = ROOT / 'docs/data/catalog.json'
REGISTRY = ROOT / 'templates/registry.json'
STRUCTURES = ROOT / 'templates/structures.json'
DOMAIN_LETTER = dict(biology='B', chemistry='C', materials='M', quantum='Q', physics='Q')
ABILITY_LETTER = dict(perception='P', inference='I', design='D')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=OrderedDict)


def structure_of(spec):
    """The thing the question asks about, for the title."""
    for key in ('pdb', 'cod', 'molecule', 'assembly'):
        if spec.get(key):
            return str(spec[key])
    asset = spec.get('asset') or ''
    return Path(asset).stem or spec['id']


# These families mix input datasets; provenance follows the registered asset. Stereo families deliberately keep
# their own chemistry classification, so a QM7-X registry label cannot override their scientific classification.
MIXED_MOLECULE_FAMILIES = {'named_bond_angle', 'named_bond_distance', 'rotational_line',
                           'isotopologue_design', 'extent_choice_v2'}
ASSEMBLY_FAMILIES = {'assembly_extent', 'assembly_rg', 'scattering_q_design', 'guinier_intensity'}
SAMPL9_COORDINATES = ('SAMPL9 challenge contributors (samplchallenges/SAMPL9) · CC BY 4.0；'
                     '主体或客体结构由 PDB 转为 XYZ，保留提供构象的原子顺序与坐标；'
                     '结构与实测表属非软件材料，MIT 仅覆盖上游代码。')
SAMPL9_BINDING = ('SAMPL9 challenge contributors (samplchallenges/SAMPL9) · CC BY 4.0；'
                 'WP6 主客体结构与 Isaacs 课题组 ITC 实测表，见 '
                 'docs/assets/families/hostguest/WP6-binding.json；MIT 仅覆盖上游代码。')


def metadata_overrides(spec, structures):
    """Known source-specific admission metadata; no scientific spec or answer is changed."""
    family = spec['family']
    if family in MIXED_MOLECULE_FAMILIES and spec.get('molecule'):
        row = next((r for r in structures.get('molecules', [])
                    if r['molecule'] == spec['molecule'] and r['asset'] == spec['asset']), None)
        if row:
            source = row.get('source', '').lower()
            if 'sampl9' in source:
                return dict(domain=row['domain'], paper='sampl9', attribution=SAMPL9_COORDINATES)
            if 'qm7-x' in source or 'qm7x' in source:
                return dict(domain=row['domain'], paper='qm7x',
                            attribution='QM7-X (Hoja et al., Sci. Data 2021) · CC BY 4.0；提供的几何坐标原样。')
    if family in ASSEMBLY_FAMILIES:
        row = next((r for r in structures.get('assemblies', []) if r['asset'] == spec['asset']), None)
        if row:
            metadata = dict(domain=row['domain'], paper='pdb-dna-origami' if row['pdb'] == '7ARQ' else 'pdb-bio-nm',
                            attribution='RCSB PDB (wwPDB, CC0)；按 docs/assets/families/assemblies/sources.json 约简；'
                                        + row['scope'])
            if 'deposited' in Path(row['asset']).name:
                metadata['sizeDefinition'] = '输入：全部提供的约简点集最大间距；推理：题目指定点集的最大间距。'
                metadata['learningObjective'] = {
                    'assembly_extent': '在给定的沉积模型约简点集中测定最大点对间距，区分它与包围盒跨度或半径。',
                    'assembly_rg': '在给定的沉积模型约简点集中计算等权回转半径，区分它与半径及单轴离散度。',
                    'scattering_q_design': '为给定的等权沉积模型点集选择使取向平均散射强度首次降至目标的测量 q。',
                    'guinier_intensity': '由给定的等权沉积模型点集求回转半径，并在 Guinier 适用范围内推断归一化散射强度。',
                }[family]
            return metadata
    if family in {'fret_efficiency', 'fret_design'} and spec.get('pdb'):
        row = next((r for r in structures.get('structures', [])
                    if r['pdb'] == spec['pdb'] and r['asset'] == spec['asset'] and r['kind'] == 'nucleic'), None)
        if row:
            return dict(domain='chemistry', paper='pdb-bio-nm',
                        attribution='RCSB PDB (wwPDB, CC0)；核酸链 ATOM 记录原样摘录，指定原子作为虚拟 FRET 点探针；'
                                    'R0 为题设参数，不代表真实染料或实验 FRET 数据。')
    return {}


def repair_metadata(amap, manifest, structures):
    """Return a corrected copy and changed keys, preserving published IDs and hand-written scientific overrides.

    Only the known inherited-source omissions are repaired. Other existing entries are left alone; fresh entries
    receive metadata_overrides before their domain prefix is assigned in main().
    """
    amap, changed = copy.deepcopy(amap), []
    for family in ('binding_evidence_choice', 'binding_design_choice'):
        row = amap['families'].get(family)
        if row and 'MIT' in row.get('attribution', '') and row['attribution'] != SAMPL9_BINDING:
            row['attribution'] = SAMPL9_BINDING
            changed.append('family:' + family)
    for entry in amap['instances']:
        instance = entry['instance']
        spec = manifest.get(instance)
        before = dict(entry)
        if spec and ((instance.startswith('EN-SAMPL9-') and spec['family'] in MIXED_MOLECULE_FAMILIES)
                     or (instance.startswith('EN-7ARQ-') and spec['family'] in ASSEMBLY_FAMILIES)):
            for key, value in metadata_overrides(spec, structures).items():
                entry.setdefault(key, value)
        if instance == 'FA-DIST-WP6-C20O22' and 'MIT' in entry.get('attribution', ''):
            entry['attribution'] = SAMPL9_COORDINATES
        if entry != before:
            changed.append(instance)
    return amap, changed



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not args.write and not args.dry_run:
        parser.error('要么 --dry-run，要么 --write')

    amap = read(MAP)
    manifest = {item['id']: item for item in read(MANIFEST)['items']}
    structures = read(STRUCTURES)
    amap, corrected = repair_metadata(amap, manifest, structures)
    if corrected:
        print('来源元数据修正 %d 项（保留已有目录号与科学字段覆盖）' % len(corrected))
    workbench = read(WORKBENCH)
    passed = {row['id'] for row in read(CHECK)['results'] if row.get('status') == 'pass'} if CHECK.exists() else None
    names = {t['id']: t.get('name') for t in read(REGISTRY)['templates']}
    published = {packet['id'] for packet in workbench['student_packets']}
    stale = [entry for entry in amap['instances']
             if entry['instance'] not in manifest and entry['instance'] not in published]
    if stale:
        print('清单和本次运行都没有、要从映射里去掉的 %d 条：' % len(stale))
        for entry in stale[:8]:
            print('  %-40s %s' % (entry['instance'], entry['catalog_id']))
        amap['instances'] = [entry for entry in amap['instances'] if entry not in stale]
    mapped = {entry['instance'] for entry in amap['instances']}

    used = {entry['catalog_id'] for entry in amap['instances']}
    used |= {q['id'] for q in read(CATALOG)['questions']}
    highest = Counter()
    for cid in used:
        m = re.match(r'^([A-Z]{3})(\d+)$', cid)
        if m:
            highest[m.group(1)] = max(highest[m.group(1)], int(m.group(2)))

    fresh = [packet['id'] for packet in workbench['student_packets'] if packet['id'] not in mapped]
    print('已发布 %d 道，其中 %d 道还没有目录号' % (len(published), len(fresh)))
    if passed is not None:
        skipped = [i for i in fresh if i not in passed]
        fresh = [i for i in fresh if i in passed]
        if skipped:
            print('独立检查没过、不给目录号的 %d 道' % len(skipped))

    added = []
    for instance in fresh:
        spec = manifest.get(instance)
        if spec is None:
            print('  清单里找不到 %s，跳过' % instance)
            continue
        family = spec['family']
        metadata = metadata_overrides(spec, structures)
        domain = metadata.get('domain', amap['families'][family]['domain'])
        prefix = '%sN%s' % (DOMAIN_LETTER[domain], ABILITY_LETTER[FAMILIES[family]['ability']])
        highest[prefix] += 1
        label = names.get(family) or family
        added.append(OrderedDict(instance=instance, action='new',
                                 catalog_id='%s%03d' % (prefix, highest[prefix]),
                                 title='%s · %s（四选一）' % (structure_of(spec), label), **metadata))

    print('要新增 %d 条映射' % len(added))
    for entry in added[:8]:
        print('  %-40s -> %-8s %s' % (entry['instance'], entry['catalog_id'], entry['title']))
    if len(added) > 8:
        print('  …')
    by_prefix = Counter(re.match(r'^([A-Z]{3})', e['catalog_id']).group(1) for e in added)
    print('按系列:', dict(sorted(by_prefix.items())))

    if args.write and (added or stale or corrected):
        amap['instances'].extend(added)
        amap['version'] = '0.14.0'
        MAP.write_bytes((json.dumps(amap, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
        print('已写入 %s（现在 %d 条）' % (MAP.relative_to(ROOT).as_posix(), len(amap['instances'])))


if __name__ == '__main__':
    main()
