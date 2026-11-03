"""A1: fetch the structures named in templates/a1-download-plan.json and register them for enumeration.

  python tools/fetch_a1.py --kind cod          # COD CIFs  -> inputs/cod, docs/assets/materials, registry 'crystals'
  python tools/fetch_a1.py --kind pdb          # PDB chains -> inputs/pdb, docs/assets/bio,  registry 'structures'
  python tools/fetch_a1.py --kind cod --dry-run

Raw downloads are kept under inputs/ (not in Git) and the published copy is the same bytes; both checksums are
written to a sources file next to the assets, together with the licence wording the database publishes itself
(tools/license_note.py). Entries already registered are skipped, so the tool can be re-run.

The plan's large assemblies (12+ chains, the 10-100 nm pixels) are NOT handled here: they need the reduction that
tools/build_assembly_assets.py does per structure (deposited operators, chain centroids), which is a second pass.
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import license_note  # noqa: E402

PLAN = ROOT / 'templates/a1-download-plan.json'
REGISTRY = ROOT / 'templates/structures.json'
DATE = '2026-11-02'
WHERE = {
    'cod': dict(raw=ROOT / 'inputs/cod', published=ROOT / 'docs/assets/materials', section='crystals',
                record=ROOT / 'docs/assets/materials/sources-a1-2026-11-02.json', statement='cod-home',
                licence='COD: public domain (CC0)'),
    'pdb': dict(raw=ROOT / 'inputs/pdb', published=ROOT / 'docs/assets/bio', section='structures',
                record=ROOT / 'docs/assets/bio/sources-a1-2026-11-02.json', statement='rcsb-usage-policy',
                licence='wwPDB (CC0)'),
}
# A chain count above this needs the assembly reduction, not a raw chain; those rows wait for the second pass.
ASSEMBLY_CHAINS = 10
NUCLEIC = ('dna', 'rna', 'nucleic', 'oligonucleotide', 'duplex', 'holliday', 'junction', 'decamer', 'dodecamer')


def fetch(url, tries=4, timeout=90):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            if attempt == tries - 1:
                raise
            time.sleep(4)


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'), object_pairs_hook=OrderedDict)


def rows_of(plan, kind):
    """Every entry of the plan for one database, with the pixel it was chosen for."""
    for target in plan['targets']:
        if target['database'] != kind:
            continue
        for entry in target['entries']:
            yield target, entry


def pdb_kind(entry, coordinates=None):
    # Classify the chain we actually register, rather than a title such as
    # HOLLIDAY JUNCTION BINDING PROTEIN (1HJP), which is a protein.
    if coordinates is not None:
        names = set()
        for line in coordinates.splitlines():
            if line.startswith('ENDMDL'):
                break
            if line.startswith('ATOM  ') and len(line) > 21 and line[21] == 'A' and line[16] in ' A':
                names.add(line[12:16].strip())
        if 'CA' in names:
            return 'protein'
        if names & {'P', "C1'"}:
            return 'nucleic'
    text = (entry.get('title') or '').lower()
    return 'nucleic' if any(word in text for word in NUCLEIC) else 'protein'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=sorted(WHERE), required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    where = WHERE[args.kind]
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    data = registry()
    known = {str(item.get('cod') or item.get('pdb') or '').upper() for item in data[where['section']]}
    known |= {str(item.get('pdb') or '').upper() for item in data['assemblies']}

    where['raw'].mkdir(parents=True, exist_ok=True)
    added, record, skipped = [], OrderedDict(), []
    for target, entry in rows_of(plan, args.kind):
        ident = entry['id'].upper()
        if ident in known:
            skipped.append((ident, '已登记'))
            continue
        if args.kind == 'pdb' and (entry.get('chains') or 0) > ASSEMBLY_CHAINS:
            skipped.append((ident, '%d 条链，要走组装体约简（第二批）' % entry['chains']))
            continue
        name = '%s.%s' % (entry['id'], 'cif' if args.kind == 'cod' else 'pdb')
        raw_path = where['raw'] / name
        if args.dry_run:
            print('%-8s %-9s %s' % (ident, target['pixel'], entry['url']))
            continue
        if not raw_path.exists():
            try:
                raw_path.write_bytes(fetch(entry['url']))
            except urllib.error.HTTPError as exc:
                skipped.append((ident, 'HTTP %s' % exc.code))
                continue
        blob = raw_path.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        (where['published'] / name).write_bytes(blob)
        asset = 'assets/%s/%s' % ('materials' if args.kind == 'cod' else 'bio', name)
        if args.kind == 'cod':
            label = entry.get('name') or entry['formula']
            data['crystals'].append(OrderedDict(cod=entry['id'], asset=asset,
                                                name='%s (%s, COD %s)' % (label, entry['formula'], entry['id'])))
        else:
            data['structures'].append(OrderedDict(
                pdb=entry['id'], asset=asset, chain='A', kind=pdb_kind(entry, blob.decode('utf-8')),
                context='%s (%s, %s)' % (entry['title'], entry['method'] or 'experimental',
                                         ('%.2f Å' % entry['resolution_A']) if entry.get('resolution_A') else '分辨率未记录'),
                source=entry['page'], license=where['licence']))
        record[name] = OrderedDict(id=entry['id'], pixel=target['pixel'], subdomain=target['subdomain'],
                                   downloaded=DATE, url=entry['url'], bytes=len(blob), sha256=digest,
                                   asset_sha256=digest, why=target['why'])
        if args.kind == 'cod':
            record[name].update(formula=entry['formula'], cell_volume_A3=entry['cell_volume_A3'],
                                a=entry['a'], b=entry['b'], c=entry['c'], spacegroup=entry['spacegroup'])
        else:
            record[name].update(title=entry['title'], method=entry['method'], resolution_A=entry.get('resolution_A'),
                                chains=entry.get('chains'), atoms=entry.get('atoms'))
        added.append(ident)
        print('%-8s %-9s %7d bytes  %s' % (ident, target['pixel'], len(blob), raw_path.relative_to(ROOT).as_posix()))

    if args.dry_run:
        return
    if added:
        REGISTRY.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
        existing = json.loads(where['record'].read_text(encoding='utf-8'),
                              object_pairs_hook=OrderedDict) if where['record'].exists() else OrderedDict()
        files = existing.get('files', OrderedDict())
        files.update(record)
        where['record'].write_bytes((json.dumps(OrderedDict(
            kind='a1_downloads', batch='A1', downloaded=DATE, database=args.kind, license=where['licence'],
            license_statement=license_note.statement(where['statement']),
            note='按 templates/a1-download-plan.json 点名下载（docs/data/subdomain-map.json 的空像素）。'
                 '原始下载在 inputs/%s（不进 Git），发布副本逐字节相同，两处哈希相同。' % args.kind,
            plan='templates/a1-download-plan.json', files=files), ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    print('\n新增 %d 个，跳过 %d 个' % (len(added), len(skipped)))
    for ident, why in skipped:
        print('  跳过 %-8s %s' % (ident, why))


if __name__ == '__main__':
    main()
