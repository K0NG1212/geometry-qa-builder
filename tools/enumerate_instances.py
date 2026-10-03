"""Enumerate candidate instances, build a deterministic sample and check it independently.

  python tools/enumerate_instances.py --out runs/enum-v01 [--sample 40] [--families fret_design,...]

1. enumerators.propose lists every candidate spec per family and structure (templates/structures.json);
   candidates already in templates/family-manifest.json are left out.
2. A deterministic sample (SHA-256 order, at most --sample per family and structure) goes into
   <out>/manifest.json and is generated with family_engine.run (the family decides admissibility). Slow families
   (SLOW below) are sampled at most twice per structure.
3. verify_all re-checks every generated instance with the independent checkers.
4. A capacity summary (no answers) is written to <out>/capacity.json and docs/data/enumeration-capacity.json:
   proposals, sampled, accepted by the family, rejection reasons, checker agreement and an estimate
   of admissible instances (proposals x acceptance rate in the sample).

Nothing is admitted to the catalog: batch production starts only after the family passes L1/L2 review.
Answer positions are counted per family with the production tolerance max(4, 15% of instances).
Exit status 1 if any independent check fails or any family's answer positions are out of balance.
"""
import argparse
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import enumerators  # noqa: E402
import family_engine  # noqa: E402
import verify_all  # noqa: E402
from task_families import kit  # noqa: E402


def existing_signatures():
    manifest = json.loads((ROOT / 'templates/family-manifest.json').read_text(encoding='utf-8'))
    return {enumerators.signature(spec) for spec in manifest['items']}


# Families whose instances take minutes each (exact Debye sums inside a root search) get a smaller fixed sample.
SLOW = {'scattering_q_design': 2}


def sample(proposals, per_structure, seed):
    chosen = []
    for family, specs in proposals.items():
        by_structure = {}
        for spec in specs:
            by_structure.setdefault(enumerators.structure_of(spec), []).append(spec)
        for pdb, group in sorted(by_structure.items()):
            group.sort(key=lambda s: kit.digest(seed, s['id']))
            chosen += group[:min(per_structure, SLOW.get(family, per_structure))]
    return chosen


def reason_kind(text):
    """Short bucket for a rejection message (the full text stays in the run)."""
    return text.split(':')[0].split(' (')[0][:80]


def run(out, per_structure=40, seed='geobench-enum-v1', families=None, date=None):
    out = Path(out)
    if out.exists():
        raise SystemExit('Output exists; use a new directory under runs/')
    seen = existing_signatures()
    proposals = {f: [s for s in specs if enumerators.signature(s) not in seen]
                 for f, specs in enumerators.propose(ROOT, families).items()}
    picked = sample(proposals, per_structure, seed)
    out.mkdir(parents=True)
    manifest = dict(kind='enumerated_sample', version='0.1.0', seed=seed, items=picked)
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    report = family_engine.run(out / 'manifest.json', out / 'run', seed)
    check = verify_all.verify(*verify_all.load(run=out / 'run'))
    (out / 'independent-check.json').write_text(json.dumps(check, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    failed = {f['id']: f['reason'] for f in report['failures']}
    checked = {r['id']: r['status'] for r in check['results']}
    keys = json.loads((out / 'run/private-answers.json').read_text(encoding='utf-8'))
    positions = {}
    for k in keys:
        positions.setdefault(k['family'], Counter())[k['correct_label']] += 1
    balance = {}
    for family, c in positions.items():
        n = sum(c.values())
        limit = max(4, 0.15 * n)                               # same tolerance as the production batches
        worst = max(abs(c.get(l, 0) - n / 4) for l in kit.LABELS)
        balance[family] = dict(counts={l: c.get(l, 0) for l in kit.LABELS}, max_deviation=round(worst, 1), tolerance=round(limit, 1),
                               ok=worst <= limit)
    rows = []
    for family, specs in proposals.items():
        for pdb in sorted({enumerators.structure_of(s) for s in specs}):
            ids = [s['id'] for s in picked if s['family'] == family and enumerators.structure_of(s) == pdb]
            built = [i for i in ids if i not in failed]
            n = sum(enumerators.structure_of(s) == pdb for s in specs)
            rows.append(dict(family=family, structure=pdb, proposals=n, sampled=len(ids), accepted=len(built),
                             rejected=dict(Counter(reason_kind(failed[i]) for i in ids if i in failed)),
                             checker_pass=sum(checked.get(i) == 'pass' for i in built),
                             checker_fail=sum(checked.get(i) not in (None, 'pass') for i in built),
                             estimated_admissible=round(n * len(built) / len(ids)) if ids else 0))
    totals = dict(proposals=sum(r['proposals'] for r in rows), sampled=len(picked), accepted=report['passed'],
                  checker_pass=check['passed'], checker_checked=check['checked'],
                  estimated_admissible=sum(r['estimated_admissible'] for r in rows),
                  positions=report['correct_position_counts'])
    totals['position_balance_ok'] = all(b['ok'] for b in balance.values())
    summary = dict(kind='enumeration_capacity', date=date or datetime.date.today().isoformat(), seed=seed, sample_per_structure=per_structure,
                   run=out.name, structures=[s['pdb'] for s in enumerators.load_structures(ROOT)] + ['COD ' + c['cod'] for c in enumerators.load_crystals(ROOT)], totals=totals, rows=rows, position_balance=balance, model_calls=0,
                   note='Capacity probe only: nothing is admitted to the catalog. Estimates scale the acceptance rate of the sample to all '
                        'proposals of the same family and structure.')
    for path in (out / 'capacity.json', ROOT / 'docs/data/enumeration-capacity.json'):
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    return summary, check


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', required=True)
    p.add_argument('--sample', type=int, default=40)
    p.add_argument('--seed', default='geobench-enum-v1')
    p.add_argument('--families')
    p.add_argument('--date')
    a = p.parse_args()
    summary, check = run(a.out, a.sample, a.seed, a.families.split(',') if a.families else None, a.date)
    print(json.dumps(summary['totals'], ensure_ascii=False))
    for r in summary['rows']:
        print(r['family'], r['structure'], r['proposals'], r['sampled'], r['accepted'], r['checker_pass'], r['rejected'])
    for f, b in summary['position_balance'].items():
        print('positions', f, b['counts'], 'ok' if b['ok'] else 'IMBALANCED')
    if check['failed']:
        print('INDEPENDENT CHECK FAILURES:', json.dumps(check['failed'][:20], ensure_ascii=False))
    sys.exit(0 if check['passed'] == check['checked'] and summary['totals']['position_balance_ok'] else 1)
