"""Sub-domain "pixel map" for the draft taxonomy (templates/subdomain-draft.json; status draft, pending the advisor).

  python tools/subdomain_map.py      # -> docs/data/subdomain-map.json

The draft (v0.2.0) is a two-level discipline tree: domain -> level-1 sub-domain -> leaf. Every active catalog question
is assigned to one leaf by the object it asks about (structure, substance), not the measurement technique; the leaf
fixes its level-1 sub-domain and its domain (so with "quantum" renamed "physics", molecular electronic-structure
questions move to chemistry). The enumeration capacity is assigned the same way. Two granularities are reported:
pixels = level-1 x reasoning scale (only the scales listed for the level-1 sub-domain are meaningful), and leaves.
Read-only with respect to questions and rules: it changes no catalog entry and no batch rule.
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
PDB_ID = re.compile(r'\b([0-9][A-Z0-9]{3})\b')


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def scale_of(nm):
    for hi, s in ((1, '0.1-1'), (10, '1-10'), (100, '10-100')):
        if nm < hi:
            return s
    return '100-1000'


class Tree:
    def __init__(self, tax):
        self.tax = tax
        self.leaf, self.level1, self.domain_of = {}, {}, {}
        for d in tax['domains']:
            for one in d['l1']:
                self.level1[one['id']] = dict(one, domain=d['id'])
                for leaf in one['leaves']:
                    self.leaf[leaf['id']] = dict(leaf, l1=one['id'], domain=d['id'])
        a = tax['assignment']
        self.pdb, self.cod, self.family, self.paper = a['pdb'], a['cod'], a['family'], a['paper']
        self.cod_names, self.hosts = a['cod_names'], set(a['sampl9_hosts'])

    def _named_crystal(self, text):
        low = text.lower()
        for key in sorted(self.cod_names, key=lambda k: (self.cod_names[k] != 'M4a', -len(k))):   # MOF names first
            if key.lower() in low:
                return self.cod_names[key]
        return None

    def question(self, q):
        """Leaf id for a catalog question; raises KeyError if no rule applies."""
        text = ' '.join(str(q.get(k, '')) for k in ('title', 'source', 'question', 'answer'))
        family, paper = q.get('family', ''), q.get('paper')
        if q['domain'] in ('biology', 'chemistry'):
            hit = next((self.pdb[i] for i in PDB_ID.findall(q['title'] + ' ' + str(q.get('source', ''))) if i in self.pdb), None)
            if hit:
                return hit
        if q['domain'] == 'biology':
            if 'DNA' in q['title']:
                return self.pdb['1BNA']
            hit = next((self.pdb[i] for i in PDB_ID.findall(text) if i in self.pdb), None)
            if hit:
                return hit
            raise KeyError('No structure rule for ' + q['id'])
        if paper == 'sampl9':
            return self.family.get(family, 'C4a') if family in self.family and self.family[family] != 'C1a' else 'C4a'
        if paper in self.paper:
            return self.paper[paper]
        if q['domain'] == 'materials':
            hit = self._named_crystal(text)
            if hit:
                return hit
            return 'M2a'          # multi-crystal diffraction design questions: the candidate sets are simple ionic crystals
        return self.family[family]

    def capacity(self, row):
        s, family = row['structure'], row['family']
        base = s[:-2] if s.endswith('-T') else s
        if base in self.pdb:
            return self.pdb[base]
        if base in self.cod:
            return self.cod[base]
        if base in self.hosts:
            return 'C4a'
        return self.family[family]


def build():
    tax = read(TAXONOMY)
    tree = Tree(tax)
    empty = lambda: dict(questions=0, abilities=collections.Counter(), ids=[], enumerated_estimate=0.0)
    pixels = {(l1, sc): dict(empty(), l1=l1, domain=v['domain'], name=v['name'], scale=sc, meaningful=sc in v['scales'])
              for l1, v in tree.level1.items() for sc in SCALES}
    leaves = {k: dict(empty(), leaf=k, l1=v['l1'], domain=v['domain'], name=v['name']) for k, v in tree.leaf.items()}
    active = [q for q in read('docs/data/catalog.json')['questions'] if q['lifecycle'] == 'active']
    outside, moved = [], collections.Counter()
    for q in active:
        leaf = tree.question(q)
        l1, sc = tree.leaf[leaf]['l1'], scale_of(q['reasoningSizeNm'])
        for p in (pixels[(l1, sc)], leaves[leaf]):
            p['questions'] += 1
            p['abilities'][q['ability']] += 1
            p['ids'].append(q['id'])
        if not pixels[(l1, sc)]['meaningful']:
            outside.append(q['id'])
        new = tree.leaf[leaf]['domain']
        if {'quantum': 'physics'}.get(q['domain'], q['domain']) != new:
            moved['%s -> %s' % (q['domain'], new)] += 1
    for r in read('docs/data/enumeration-capacity.json')['rows']:
        leaf = tree.capacity(r)
        total = sum(r['cells'].values()) or 1
        for cell, n in r['cells'].items():
            sc = cell.split(' ', 1)[1]
            if sc in SCALES:
                share = r['estimated_admissible'] * n / total
                pixels[(tree.leaf[leaf]['l1'], sc)]['enumerated_estimate'] += share
                leaves[leaf]['enumerated_estimate'] += share
    finish = lambda p: dict(p, abilities={k: p['abilities'].get(k, 0) for k in ('perception', 'inference', 'design')},
                            enumerated_estimate=round(p['enumerated_estimate']))
    pix, lv = [finish(p) for p in pixels.values()], [finish(p) for p in leaves.values()]
    good = [p for p in pix if p['meaningful']]
    summary = dict(level1=len(tree.level1), leaves=len(tree.leaf), meaningful_pixels=len(good),
                   pixels_with_questions=sum(1 for p in good if p['questions']),
                   empty_meaningful_pixels=sum(1 for p in good if not p['questions']),
                   pixels_with_enumerator=sum(1 for p in good if p['enumerated_estimate']),
                   leaves_with_questions=sum(1 for p in lv if p['questions']),
                   empty_level1=[k for k in tree.level1 if not any(p['questions'] for p in lv if p['l1'] == k)],
                   domain_changes=dict(moved), active_questions=len(active),
                   questions_outside_meaningful_pixels=outside, planning_total=tax['planning_total'],
                   mean_target_per_pixel=round(tax['planning_total'] / len(good)))
    return dict(kind='subdomain_pixel_map', taxonomy_version=tax['version'], taxonomy_status=tax['status'],
                note='Draft taxonomy pending the advisor; assignment is automatic (by structure, source and family) and '
                     'individual questions may need manual reassignment.', summary=summary, pixels=pix, leaves=lv)


if __name__ == '__main__':
    result = build()
    (ROOT / OUT).write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result['summary'], ensure_ascii=False))
    sys.exit(1 if result['summary']['questions_outside_meaningful_pixels'] else 0)
