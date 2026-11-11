"""Assign validated 2026-11-07 A1 source IDs to the draft taxonomy's scientific leaves."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / 'templates/subdomain-draft.json'
PLANS = (ROOT / 'templates/a1-download-plan.json',
         ROOT / 'templates/a1-download-plan-assembly-2026-11-07.json')

PIXEL_LEAF = {
    'B8 1-10': 'B8a', 'B8 10-100': 'B8e', 'M1 1-10': 'M1b',
    'P1 1-10': 'P1b', 'P2 0.1-1': 'P2a', 'M7 0.1-1': 'M7a',
    'B5 0.1-1': 'B5b', 'B7 0.1-1': 'B7a', 'C5 1-10': 'C5a',
    'C6 1-10': 'C6a', 'C3 1-10': 'C3b', 'P3 1-10': 'P3a',
    'M2 1-10': 'M2c', 'M3 1-10': 'M3a', 'M5 1-10': 'M5a',
    'M8 1-10': 'M8a', 'P5 1-10': 'P5c', 'C7 1-10': 'C7a',
    'B4 1-10': 'B4b', 'M6 10-100': 'M6a', 'P4 10-100': 'P4a',
}
EXCEPTIONS = {
    # Ion channels and aquaporins rather than carrier transporters.
    '3HD6': 'B4a', '5I32': 'B4a', '2W2E': 'B4a', '3B9Y': 'B4a',
    '6QZI': 'B4a', '3C02': 'B4a',
    # Halide perovskite instead of a binary semiconductor.
    '4127358': 'M3b',
}


def main():
    taxonomy = json.loads(TAXONOMY.read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'templates/structures.json').read_text(encoding='utf-8'))
    valid = {
        'cod': {str(p['cod']).upper() for p in registry['crystals']},
        'pdb': {p['pdb'].upper() for section in ('structures', 'assemblies') for p in registry[section]},
    }
    leaves = {leaf['id'] for domain in taxonomy['domains'] for one in domain['l1'] for leaf in one['leaves']}
    assigned = {'cod': {}, 'pdb': {}}
    for path in PLANS:
        plan = json.loads(path.read_text(encoding='utf-8'))
        for target in plan['targets']:
            kind = target['database']
            if kind not in assigned:
                continue
            leaf = PIXEL_LEAF[target['pixel']]
            for entry in target['entries']:
                ident = entry['id'].upper()
                if ident not in valid[kind]:
                    continue
                chosen = EXCEPTIONS.get(ident, leaf)
                if chosen not in leaves:
                    raise ValueError('Unknown taxonomy leaf: ' + chosen)
                previous = assigned[kind].setdefault(ident, chosen)
                if previous != chosen:
                    raise ValueError('Conflicting A1 assignments for ' + ident)
    if sum(map(len, assigned.values())) != 75:
        raise ValueError('Expected the 75 validated source IDs; got %d' % sum(map(len, assigned.values())))
    for kind, rows in assigned.items():
        for ident, leaf in rows.items():
            old = taxonomy['assignment'][kind].get(ident)
            if old and old != leaf:
                raise ValueError('Existing assignment conflicts for %s: %s / %s' % (ident, old, leaf))
            taxonomy['assignment'][kind][ident] = leaf
    TAXONOMY.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('Assigned %d COD and %d PDB source IDs' % (len(assigned['cod']), len(assigned['pdb'])))


if __name__ == '__main__':
    main()
