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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not args.write and not args.dry_run:
        parser.error('要么 --dry-run，要么 --write')

    amap = read(MAP)
    manifest = {item['id']: item for item in read(MANIFEST)['items']}
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
        domain = amap['families'][family]['domain']
        prefix = '%sN%s' % (DOMAIN_LETTER[domain], ABILITY_LETTER[FAMILIES[family]['ability']])
        highest[prefix] += 1
        label = names.get(family) or family
        added.append(OrderedDict(instance=instance, action='new',
                                 catalog_id='%s%03d' % (prefix, highest[prefix]),
                                 title='%s · %s（四选一）' % (structure_of(spec), label)))

    print('要新增 %d 条映射' % len(added))
    for entry in added[:8]:
        print('  %-40s -> %-8s %s' % (entry['instance'], entry['catalog_id'], entry['title']))
    if len(added) > 8:
        print('  …')
    by_prefix = Counter(re.match(r'^([A-Z]{3})', e['catalog_id']).group(1) for e in added)
    print('按系列:', dict(sorted(by_prefix.items())))

    if args.write and (added or stale):
        amap['instances'].extend(added)
        amap['version'] = '0.13.0'
        MAP.write_bytes((json.dumps(amap, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
        print('已写入 %s（现在 %d 条）' % (MAP.relative_to(ROOT).as_posix(), len(amap['instances'])))


if __name__ == '__main__':
    main()
