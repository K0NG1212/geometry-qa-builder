"""Select the 160-question prototype (10 per domain x reasoning-scale cell) from the active catalog.

  python tools/select_prototype.py            # -> docs/data/prototype-selection.json

The rule lives in templates/prototype-selection-rule.json and is a proposal pending the professor. Selection is
deterministic: independently checked questions first, abilities balanced towards 3/3/3, then questions outside the
pending-decision groups, review-unit and source diversity, and finally SHA-256(seed|id). Unselected active questions
become reserve; nothing in the catalog is changed.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import review_system as rs  # noqa: E402

DOMAINS = ('chemistry', 'biology', 'materials', 'quantum')
CELLS = ('0.1-1', '1-10', '10-100', '100-1000')
TIER = {'family': 0, 'family-version': 0, 'legacy': 1}
TIER_LABEL = {0: '经独立检查（题型族实例或旧题的四选一版本）', 1: '旧模板题'}


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def pending(item, rule):
    for key, g in rule['pending_decision'].items():
        if item['unit'] in g['families'] or any((item['instance'] or '').startswith(p) for p in g['instance_prefixes']):
            return key
    return None


def candidates(catalog, rule):
    out = []
    for it in rs.instances(catalog):
        out.append(dict(it, tier=TIER[it['form']], pending=pending(it, rule)))
    return out


def pick(cands, rule, chosen):
    """Greedy balanced pick within one tier; chosen is extended in place."""
    order = rule['abilities']
    count = {a: sum(c['ability'] == a for c in chosen) for a in order}
    units, sources = {}, {}
    for c in chosen:
        units[c['unit']] = units.get(c['unit'], 0) + 1
        sources[c['source']] = sources.get(c['source'], 0) + 1
    left = list(cands)
    while len(chosen) < rule['per_cell'] and left:
        avail = {c['ability'] for c in left}
        a = min(avail, key=lambda x: (count[x], order.index(x)))
        c = min((c for c in left if c['ability'] == a),
                key=lambda c: (c['pending'] is not None, units.get(c['unit'], 0), sources.get(c['source'], 0), rs.rank_key(rule['seed'], c['id'])))
        left.remove(c)
        chosen.append(c)
        count[a] += 1
        units[c['unit']] = units.get(c['unit'], 0) + 1
        sources[c['source']] = sources.get(c['source'], 0) + 1
    return chosen


def short(c):
    return {k: c[k] for k in ('id', 'ability', 'form', 'unit', 'instance', 'source', 'pending')}


def select(catalog, rule):
    by_cell = {}
    for c in candidates(catalog, rule):
        by_cell.setdefault(c['cell'], []).append(c)
    cells = []
    for d in DOMAINS:
        for b in CELLS:
            key = '%s %s' % (d, b)
            members = sorted(by_cell.get(key, []), key=lambda c: c['id'])
            ok = [c for c in members if c['l0']]
            chosen = []
            for tier in (0, 1):
                pick([c for c in ok if c['tier'] == tier], rule, chosen)
            ids = {c['id'] for c in chosen}
            tier0 = sum(c['tier'] == 0 for c in ok)
            notes = ['可用 %d 道，其中经独立检查 %d 道' % (len(ok), tier0)]
            legacy = [c['id'] for c in chosen if c['tier'] == 1]
            if legacy:
                notes.append('经独立检查的题不足 %d 道，用旧模板题补 %d 道：%s' % (rule['per_cell'], len(legacy), '、'.join(legacy)))
            gaps = [a for a in rule['abilities'] if not any(c['ability'] == a for c in chosen)]
            if gaps:
                notes.append('缺少能力：' + '、'.join(gaps))
            if len(chosen) < rule['per_cell']:
                notes.append('不足 %d 道' % rule['per_cell'])
            cells.append(dict(cell=key, domain=d, bin=b, available=len(members), eligible=len(ok),
                              abilities={a: sum(c['ability'] == a for c in chosen) for a in rule['abilities']},
                              selected=[short(c) for c in sorted(chosen, key=lambda c: (rule['abilities'].index(c['ability']), c['id']))],
                              reserve=[dict(short(c), reason='未通过 L0' if not c['l0'] else '本格已满 %d 道' % rule['per_cell'])
                                       for c in members if c['id'] not in ids],
                              rationale='；'.join(notes)))
    return cells


def build(catalog=None, rule=None):
    catalog = catalog or read('docs/data/catalog.json')
    rule = rule or read('templates/prototype-selection-rule.json')
    cells = select(catalog, rule)
    sel = [s for c in cells for s in c['selected']]
    res = [s for c in cells for s in c['reserve']]
    stray = sorted(c['id'] for c in candidates(catalog, rule) if c['cell'].split(' ')[1] == 'out-of-range')
    summary = dict(selected=len(sel), reserve=len(res), out_of_range=stray,
                   abilities={a: sum(s['ability'] == a for s in sel) for a in rule['abilities']},
                   forms={f: sum(s['form'] == f for s in sel) for f in TIER},
                   review_units=len({s['unit'] for s in sel}),
                   family_units=len({s['unit'] for s in sel if s['form'] != 'legacy'}),
                   legacy_units=len({s['unit'] for s in sel if s['form'] == 'legacy'}),
                   pending_decision={k: sum(s['pending'] == k for s in sel) for k in rule['pending_decision']},
                   full_cells=sum(len(c['selected']) == rule['per_cell'] for c in cells))
    return dict(kind='prototype_selection', rule_version=rule['version'], status=rule['status'], status_note=rule['status_note'],
                seed=rule['seed'], steps=rule['steps'],
                pending_labels={k: v['label'] for k, v in rule['pending_decision'].items()},
                summary=summary, cells=cells, selected_ids=sorted(s['id'] for s in sel))


def load_selected():
    path = ROOT / 'docs/data/prototype-selection.json'
    return set(json.loads(path.read_text(encoding='utf-8'))['selected_ids']) if path.exists() else None


if __name__ == '__main__':
    out = build()
    (ROOT / 'docs/data/prototype-selection.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(out['summary'], ensure_ascii=False))
    for c in out['cells']:
        print(c['cell'], c['abilities'], c['rationale'])
