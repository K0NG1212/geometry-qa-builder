"""Sub-domain "pixel map" for the draft taxonomy (templates/subdomain-draft.json; status draft, pending the advisor).

  python tools/subdomain_map.py      # -> docs/data/subdomain-map.json

Every active catalog question is assigned to one sub-domain (by the object it asks about, not the measurement
technique) and to its reasoning-scale cell; the enumeration capacity (docs/data/enumeration-capacity.json) is assigned
the same way. A pixel is a sub-domain x scale pair; only the scales listed for a sub-domain are meaningful. Read-only
with respect to questions and rules: it changes no catalog entry and no batch rule.
"""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCALES = ['0.1-1', '1-10', '10-100', '100-1000']
TAXONOMY = 'templates/subdomain-draft.json'
OUT = 'docs/data/subdomain-map.json'


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def scale_of(nm):
    for hi, s in ((1, '0.1-1'), (10, '1-10'), (100, '10-100')):
        if nm < hi:
            return s
    return '100-1000'


class Assigner:
    def __init__(self, tax):
        g, f = tax['structure_groups'], tax['family_groups']
        self.capsids, self.machines, self.nucleic = set(g['capsids']), set(g['machines']), set(g['nucleic_acids'])
        self.mof, self.hosts = set(g['mof_cod']), set(g['sampl9_hosts'])
        self.engineering, self.spectro = set(f['protein_engineering']), set(f['spectroscopy'])
        self.papers = tax['paper_routes']

    def biology(self, structure, family):
        if structure in self.capsids:
            return 'B4'
        if structure in self.machines:
            return 'B5'
        if structure in self.nucleic:
            return 'B3'
        return 'B2' if family in self.engineering else 'B1'

    def question(self, q):
        d, paper, family = q['domain'], q.get('paper'), q.get('family', '')
        if d == 'biology':
            text = ' '.join(str(q.get(k, '')) for k in ('title', 'source', 'question'))
            ids = set(re.findall(r'\b([0-9][A-Z0-9]{3})\b', text))
            structure = next((i for i in sorted(ids) if i in self.capsids | self.machines | self.nucleic), None)
            if structure is None and ('DNA' in q['title'] or 'tRNA' in q['title']):
                structure = next(iter(sorted(self.nucleic)))
            return self.biology(structure, family)
        if d == 'chemistry':
            if family in self.spectro:
                return 'C1'
            return self.papers['chemistry'].get(paper, 'C1')
        if d == 'materials':
            if re.search(r'MOF-5|SALEM|ZIF-8', q['title']):          # MOF crystals recorded under the COD crystal source
                return 'M2'
            return self.papers['materials'][paper]
        if family in self.spectro:
            return 'Q2'
        return self.papers['quantum'].get(paper, 'Q1')

    def capacity(self, row, domain):
        s, family = row['structure'], row['family']
        base = s[:-2] if s.endswith('-T') else s
        if domain == 'biology':
            return self.biology(base, family)
        if domain == 'materials':
            return 'M2' if s in self.mof else 'M1'
        if domain == 'chemistry':
            if base == '7ARQ':
                return self.papers['chemistry']['pdb-dna-origami']
            return 'C3' if s in self.hosts else 'C1'
        return 'Q2' if family in self.spectro else 'Q1'


def build():
    tax = read(TAXONOMY)
    assign = Assigner(tax)
    meaningful = {s['id']: s['scales'] for s in tax['subdomains']}
    pixels = {(s['id'], sc): dict(subdomain=s['id'], domain=s['domain'], name=s['name'], scale=sc,
                                  meaningful=sc in s['scales'], questions=0, abilities=collections.Counter(), ids=[],
                                  enumerated_estimate=0.0)
              for s in tax['subdomains'] for sc in SCALES}
    active = [q for q in read('docs/data/catalog.json')['questions'] if q['lifecycle'] == 'active']
    outside = []
    for q in active:
        key = (assign.question(q), scale_of(q['reasoningSizeNm']))
        p = pixels[key]
        p['questions'] += 1
        p['abilities'][q['ability']] += 1
        p['ids'].append(q['id'])
        if not p['meaningful']:
            outside.append(q['id'])
    for r in read('docs/data/enumeration-capacity.json')['rows']:
        total = sum(r['cells'].values()) or 1
        for cell, n in r['cells'].items():
            domain, sc = cell.split(' ', 1)
            if sc in SCALES:
                pixels[(assign.capacity(r, domain), sc)]['enumerated_estimate'] += r['estimated_admissible'] * n / total
    rows = []
    for p in pixels.values():
        rows.append(dict(p, abilities={k: p['abilities'].get(k, 0) for k in ('perception', 'inference', 'design')},
                         enumerated_estimate=round(p['enumerated_estimate'])))
    good = [r for r in rows if r['meaningful']]
    empty_subdomains = [s['id'] for s in tax['subdomains'] if not any(r['questions'] for r in rows if r['subdomain'] == s['id'])]
    summary = dict(subdomains=len(tax['subdomains']), meaningful_pixels=len(good),
                   pixels_with_questions=sum(1 for r in good if r['questions']),
                   empty_meaningful_pixels=sum(1 for r in good if not r['questions']),
                   pixels_with_enumerator=sum(1 for r in good if r['enumerated_estimate']),
                   empty_subdomains=empty_subdomains, active_questions=len(active),
                   questions_outside_meaningful_pixels=outside,
                   planning_total=tax['planning_total'], mean_target_per_pixel=round(tax['planning_total'] / len(good)))
    return dict(kind='subdomain_pixel_map', taxonomy_version=tax['version'], taxonomy_status=tax['status'],
                note='Draft taxonomy pending the advisor; assignment is automatic (by source, structure and family) and '
                     'individual questions may need manual reassignment.', summary=summary, pixels=rows)


if __name__ == '__main__':
    result = build()
    (ROOT / OUT).write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result['summary'], ensure_ascii=False))
    sys.exit(1 if result['summary']['questions_outside_meaningful_pixels'] else 0)
