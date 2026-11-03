"""Prune the manifest until a full run would report no new failures, rebuilding only the families that moved.

Why this exists: family_engine gives each instance a target answer position from its index within its family in
manifest order (family_engine.py:60), and a spec with strict_rank is refused when that position is unreachable with
plausible distractors (task_families/kit.py require_rank). So dropping one instance shifts every later instance of the
same family by one position and can refuse a different one -- tools/prune_manifest.py alone does not converge.

Rebuilding all 872 instances to find out costs ~28 minutes. Only a family that lost an instance can change, so this
rebuilds one family at a time until nothing new fails, which took 6 rounds and 98 seconds on 2026-11-03.

  python tools/stabilize_manifest.py --dirty rotational_line,guinier_intensity --dry-run
  python tools/stabilize_manifest.py --dirty rotational_line,guinier_intensity --write --batch stabilize-2026-11-03

Run it after tools/prune_manifest.py, with --dirty set to the families whose instances that prune removed.
"""
import argparse
import json
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import family_engine                                                            # noqa: E402
from task_families import kit                                                   # noqa: E402

MANIFEST = ROOT / 'templates/family-manifest.json'
RECORD = ROOT / 'templates/pruned-instances.json'
POLICY = ROOT / 'builder_modules/m0_scope/prototype-policy.json'
_BINS = json.loads(POLICY.read_text(encoding='utf-8'))['scale_bins_nm']
WINDOW = (_BINS[0][0], _BINS[-1][1])
SEED = 'geobench-family-v1'
KEEP = {'FA-CONF-7063-max_dipole'}
ROUNDS = 12


def target_positions(items):
    """The target answer position family_engine would hand each instance, for this manifest order."""
    counters, out = Counter(), {}
    for spec in items:
        offset = kit.digest(SEED, spec['family'], 'offset')[0] % 4
        out[spec['id']] = 1 + (offset + counters[spec['family']]) % 4
        counters[spec['family']] += 1
    return out


def refusal(spec, target):
    """Why this instance cannot be published at this target position, or None."""
    try:
        _, built = family_engine.build_instance(dict(spec, target_position=target), SEED)
    except (ValueError, KeyError) as error:
        return str(error)
    scale = built['scales']['reasoning_nm']
    if not WINDOW[0] <= scale <= WINDOW[1]:
        return '推理尺度 %.4f nm 落在申报窗口 %s 之外' % (scale, WINDOW)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dirty', required=True, help='逗号分隔的族名：刚被剪过、目标答案位置会移位的那些')
    parser.add_argument('--batch', default='stabilize', help='写进 pruned-instances.json 的批次名')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not args.write and not args.dry_run:
        parser.error('要么 --dry-run，要么 --write')

    dirty = {x.strip() for x in args.dirty.split(',') if x.strip()}
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'), object_pairs_hook=OrderedDict)
    before, dropped = len(manifest['items']), OrderedDict()
    for round_number in range(1, ROUNDS + 1):
        target = target_positions(manifest['items'])
        todo = [s for s in manifest['items'] if s['family'] in dirty]
        print('\n第 %d 轮：复算 %d 条（族 %s）' % (round_number, len(todo), ', '.join(sorted(dirty))), flush=True)
        t0, failures = time.time(), OrderedDict()
        for spec in todo:
            reason = refusal(spec, target[spec['id']])
            if reason and spec['id'] not in KEEP:
                failures[spec['id']] = reason
                print('  拿掉 %-40s %s' % (spec['id'], reason), flush=True)
        print('  用时 %.0f 秒，新失败 %d 条' % (time.time() - t0, len(failures)), flush=True)
        if not failures:
            print('\n清单已稳定：%d 条（本次共拿掉 %d 条）' % (len(manifest['items']), len(dropped)), flush=True)
            break
        dropped.update(failures)
        dirty = {s['family'] for s in manifest['items'] if s['id'] in failures}
        manifest['items'] = [s for s in manifest['items'] if s['id'] not in failures]
        if args.write:
            MANIFEST.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    else:
        raise SystemExit('%d 轮还没稳定，说明某个族一直在互相顶掉，需要人看' % ROUNDS)

    if args.write and dropped:
        record = json.loads(RECORD.read_text(encoding='utf-8'), object_pairs_hook=OrderedDict)
        record['batches'][args.batch] = OrderedDict(
            note='按族逐轮复算：拿掉一条会改同族后面几条的目标答案位置，strict_rank 的那些因此可能换一条被拒。',
            manifest_before=before, manifest_after=len(manifest['items']), pruned=len(dropped),
            reasons=OrderedDict(Counter(dropped.values()).most_common()), ids=OrderedDict(sorted(dropped.items())))
        RECORD.write_bytes((json.dumps(record, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
        print('清单 %d → %d 条；原因记在 %s' % (before, len(manifest['items']), RECORD.relative_to(ROOT).as_posix()), flush=True)


if __name__ == '__main__':
    main()
