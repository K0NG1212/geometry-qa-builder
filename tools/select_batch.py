"""The step RUNBOOK section 4.2 lists as missing: pick instances for production under the diversity caps.

tools/enumerate_instances.py only measures capacity and tools/batch_plan.py only measures the gap; neither puts an
instance into templates/family-manifest.json. This does, and it is the only way the bank grows by breadth rather
than by asking one structure many times.

  python tools/select_batch.py --dry-run           # what would be added, per family and per source
  python tools/select_batch.py --write             # append the chosen specs to templates/family-manifest.json

The caps come from templates/batch-selection-rule.json and act together, counting what the manifest already holds:
  * max_per_family_source  4   one structure answers at most four questions of the same family
  * max_per_source         8   one structure answers at most eight questions in all
  * max_per_family        60   one family holds at most sixty questions
Order is deterministic (SHA-256 of the signature) and the pass is greedy with the scarcest first: a structure with
no questions yet is served before one that already has some, and within a structure the families it has never been
used for come first. Nothing is admitted to the catalog here -- that is still family_engine, verify_all and
tools/admit_family_instances.py.
"""
import argparse
import json
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import enumerators  # noqa: E402
from task_families import kit  # noqa: E402

MANIFEST = ROOT / 'templates/family-manifest.json'
RULE = ROOT / 'templates/batch-selection-rule.json'
RECORD = ROOT / 'templates/batch-selection-2026-11-02.json'
# Enumerated per residue pair, so O(n^2) in chain length: 3W4T alone (446 residues) takes minutes, and the two
# caps (60 per family, 4 per family and source) let these two contribute a few dozen questions at most. Left out
# unless asked for, because the no-argument run is the one someone tries first and it does not come back.
SLOW_FAMILIES = ('fret_efficiency', 'fret_design')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=OrderedDict)


def source_of(spec):
    """The structure a spec asks about: the key the per-source caps count."""
    return (spec.get('assembly') or spec.get('pdb') or spec.get('cod') or spec.get('molecule')
            or spec.get('asset') or spec.get('id'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--families', help='只选这些族（逗号分隔）')
    parser.add_argument('--include-slow', action='store_true',
                        help='连 %s 一起枚举（按残基对展开，蛋白一大就要几分钟一族）' % '、'.join(SLOW_FAMILIES))
    parser.add_argument('--limit', type=int, default=0, help='最多选这么多道（0 表示不限）')
    args = parser.parse_args()
    if not args.write and not args.dry_run:
        parser.error('要么 --dry-run，要么 --write')

    caps = read(RULE)['global']
    per_family_source = read(RULE)['tiers']['A']['max_per_family_source']
    max_per_source, max_per_family = caps['max_per_source'], caps['max_per_family']

    manifest = read(MANIFEST)
    held_family = Counter(item.get('family') for item in manifest['items'])
    held_source = Counter(source_of(item) for item in manifest['items'])
    held_pair = Counter((item.get('family'), source_of(item)) for item in manifest['items'])
    signatures = {enumerators.signature(item) for item in manifest['items']}
    taken_ids = {item['id'] for item in manifest['items']}

    if args.families:
        families = args.families.split(',')
    elif args.include_slow:
        families = None
    else:
        families = [f for f in enumerators.ENUMERATORS if f not in SLOW_FAMILIES]
    print('枚举提案中…（结构多了之后这一步要几分钟）%s'
          % ('' if families is None else '；本次枚举 %d 个族' % len(families)))
    proposals = enumerators.propose(ROOT, families)
    fresh = []
    for family, specs in proposals.items():
        for spec in specs:
            signature = enumerators.signature(spec)
            if signature in signatures or spec['id'] in taken_ids:
                continue
            fresh.append((family, source_of(spec), signature, spec))
    print('去掉清单里已有的之后，候选 %d 道（%d 个族）' % (len(fresh), len({f for f, _, _, _ in fresh})))

    # scarcest first: a structure with no questions, then a family this structure has never answered, then by hash
    fresh.sort(key=lambda row: (held_source[row[1]], held_pair[(row[0], row[1])], held_family[row[0]],
                                kit.digest('select-2026-11-02', row[2])))
    chosen, blocked = [], Counter()
    for family, source, signature, spec in fresh:
        if args.limit and len(chosen) >= args.limit:
            break
        if held_pair[(family, source)] >= per_family_source:
            blocked['族×来源上限 %d' % per_family_source] += 1
            continue
        if held_source[source] >= max_per_source:
            blocked['来源上限 %d' % max_per_source] += 1
            continue
        if held_family[family] >= max_per_family:
            blocked['族上限 %d' % max_per_family] += 1
            continue
        if signature in signatures:
            blocked['与已选重复'] += 1
            continue
        held_pair[(family, source)] += 1
        held_source[source] += 1
        held_family[family] += 1
        signatures.add(signature)
        chosen.append(spec)

    print('\n选中 %d 道' % len(chosen))
    by_family = Counter(spec['family'] for spec in chosen)
    for family, count in sorted(by_family.items(), key=lambda x: -x[1]):
        print('  %-30s +%-4d (清单里将有 %d)' % (family, count, held_family[family]))
    print('\n被上限挡下的：')
    for why, count in blocked.most_common():
        print('  %-20s %d' % (why, count))
    sources = Counter(source_of(spec) for spec in chosen)
    print('\n涉及 %d 个来源，单个来源最多 +%d 道' % (len(sources), max(sources.values()) if sources else 0))

    if args.write and chosen:
        manifest['items'].extend(chosen)
        MANIFEST.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
        RECORD.write_bytes((json.dumps(OrderedDict(
            kind='batch_selection', date='2026-11-02', rule='templates/batch-selection-rule.json',
            rule_version=read(RULE)['version'], caps=OrderedDict(
                max_per_family_source=per_family_source, max_per_source=max_per_source, max_per_family=max_per_family),
            note='tools/select_batch.py 选出的批次：按稀缺优先（没题的结构先上）、确定性顺序；'
                 '选中只是进清单，是否成题由 family_engine 判定，入库另走 admit。',
            candidates=len(fresh), chosen=len(chosen), blocked=OrderedDict(blocked.most_common()),
            by_family=OrderedDict(sorted(by_family.items())),
            ids=[spec['id'] for spec in chosen]), ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
        print('\n已写入 %s（清单现在 %d 条）和 %s' % (MANIFEST.relative_to(ROOT).as_posix(), len(manifest['items']),
                                             RECORD.relative_to(ROOT).as_posix()))


if __name__ == '__main__':
    main()
