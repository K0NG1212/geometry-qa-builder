"""A1: drop the downloaded structures the readers cannot use, before anything is enumerated from them.

A search hit is not a usable structure. Several COD entries carry partial occupancy or an element the cell reader
does not know, and a PDB hit may have no chain A or too few residues to ask anything about. This pass tries each
newly registered A1 structure with the same reader the enumerators use, removes the failures from
templates/structures.json and from docs/assets, and records every rejection with its reason in the A1 sources file,
so the count in the plan and the count in the registry never drift apart silently.

python tools/validate_a1.py [--dry-run]
"""
import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from task_families.cell import read_cif  # noqa: E402
from task_families.local_geometry import read_pdb_residues  # noqa: E402

REGISTRY = ROOT / 'templates/structures.json'
RECORDS = {'cod': ROOT / 'docs/assets/materials/sources-a1-2026-11-02.json',
           'pdb': ROOT / 'docs/assets/bio/sources-a1-2026-11-02.json'}
# A protein needs a stretch long enough to ask about secondary structure; a DNA or RNA duplex of 8 base pairs is a
# whole structure in its own right, so nucleic acids get the lower bar.
MIN_RESIDUES = dict(protein=12, nucleic=8)


def check_crystal(asset):
    cell, atoms = read_cif(ROOT / 'docs' / asset)[:2]
    if len(atoms) < 2:
        raise ValueError('只有 %d 个原子，问不出几何量' % len(atoms))
    return '%d 原子' % len(atoms)


def check_structure(asset, chain, kind='protein'):
    text = (ROOT / 'docs' / asset).read_text(encoding='utf-8')
    residues, order, altloc = read_pdb_residues(text, chain)
    usable = [n for n in order if n not in altloc]
    names = {atom for n in usable for atom in residues[n]['atoms']}
    expected = {'CA'} if kind == 'protein' else {'P', "C1'"}
    if not names & expected:
        raise ValueError('链 %s 的原子记录与登记类型 %s 不符（缺少 %s）' %
                         (chain, kind, '/'.join(sorted(expected))))
    least = MIN_RESIDUES[kind]
    if len(usable) < least:
        raise ValueError('链 %s 只有 %d 个可用残基（少于 %d）' % (chain, len(usable), least))
    return '链 %s，%d 个可用残基（%s）' % (chain, len(usable), kind)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    data = json.loads(REGISTRY.read_text(encoding='utf-8'), object_pairs_hook=OrderedDict)
    rejected = {'cod': OrderedDict(), 'pdb': OrderedDict()}
    kept = {'cod': 0, 'pdb': 0}

    for kind, section, key in (('cod', 'crystals', 'cod'), ('pdb', 'structures', 'pdb')):
        record_path = RECORDS[kind]
        if not record_path.exists():
            continue
        record = json.loads(record_path.read_text(encoding='utf-8'), object_pairs_hook=OrderedDict)
        mine = {entry['id'].upper() for entry in record['files'].values()}
        survivors = []
        for item in data[section]:
            ident = str(item[key]).upper()
            if ident not in mine:
                survivors.append(item)
                continue
            try:
                detail = (check_crystal(item['asset']) if kind == 'cod'
                          else check_structure(item['asset'], item['chain'], item.get('kind', 'protein')))
            except Exception as exc:                      # a reader refusing the file is the answer we are after
                rejected[kind][ident] = '%s: %s' % (type(exc).__name__, str(exc).strip()[:120])
                print('%-8s 丢弃  %s' % (ident, rejected[kind][ident]))
                continue
            kept[kind] += 1
            print('%-8s 可用  %s' % (ident, detail))
            survivors.append(item)
            for name in list(record.get('rejected', {})):      # a bar that moved can let an earlier reject back in
                if record['rejected'][name]['id'].upper() == ident:
                    record['files'][name] = OrderedDict(
                        (k, v) for k, v in record['rejected'].pop(name).items() if k != 'rejected_because')
        if args.dry_run:
            continue
        data[section] = survivors
        names = {entry['id'].upper(): name for name, entry in record['files'].items()}
        for ident, why in rejected[kind].items():
            name = names[ident]
            record.setdefault('rejected', OrderedDict())[name] = OrderedDict(
                dict(record['files'].pop(name)), rejected_because=why)
            asset = ROOT / 'docs/assets' / ('materials' if kind == 'cod' else 'bio') / name
            if asset.exists():
                asset.unlink()
        record['note'] = record['note'] + ' 读不进来的条目（部分占据、未知元素、链太短）已由 tools/validate_a1.py 移出注册表，' \
                                         '原因记在 rejected 里；原始下载仍留在 inputs/，不再发布。'
        record_path.write_bytes((json.dumps(record, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))

    if not args.dry_run:
        REGISTRY.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    print('\n可用 COD %d + PDB %d；丢弃 COD %d + PDB %d' %
          (kept['cod'], kept['pdb'], len(rejected['cod']), len(rejected['pdb'])))
    print('注册表现在：crystals %d, structures %d, molecules %d, assemblies %d' %
          tuple(len(data[s]) for s in ('crystals', 'structures', 'molecules', 'assemblies')))


if __name__ == '__main__':
    main()
