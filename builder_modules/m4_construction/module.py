import copy
import math
from pathlib import Path

def construct(b, plan, bundle, previous, units):
    """Trusted distance/angle calculators; never execute generated code."""
    b.validate(plan, b.read(Path(__file__).with_name('schema.json')))
    sources = b.bundle_check(bundle)
    unit_map = b.unique(units['assets'], 'source_id')
    output = copy.deepcopy(plan)
    for q in output['items']:
        answer = q.pop('answer_text')
        v = q['verifier']
        if v:
            if answer is not None:
                raise ValueError('construction: numeric answer must come from code; answer_text must be null')
            asset = unit_map.get(v['source_id'])
            if not asset or asset['unit'] != 'angstrom':
                raise ValueError('construction: coordinate units unresolved for '+v['source_id'])
            q['answer_numeric'] = 0.0
            actual = geometry(b, q, sources)['computed']
            q['answer_numeric'] = actual
            q['reference_answer'] = f"{actual:.10g} {q['units']}"
        else:
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError('construction: evidence-based text answer missing')
            q['answer_numeric'] = None
            q['reference_answer'] = answer
    return output

def geometry(b, q, sources):
    v = q['verifier']
    pts = b.parse_xyz(sources[v['source_id']]['text'])
    idx = v['atom_indices']
    count = 2 if v['kind']=='xyz_distance' else 3
    tol = v['tolerance']
    max_tol = .001 if count==2 else .1
    if len(idx)!=count or len(set(idx))!=count or any(i<1 or i>len(pts) for i in idx):
        raise ValueError('invalid atom indices')
    if not 0<tol<=max_tol: raise ValueError('invalid tolerance')
    if q['units']!=('angstrom' if count==2 else 'degree'): raise ValueError('invalid units')
    p = [pts[i-1] for i in idx]
    if count==2: actual = math.dist(*p)
    else:
        u = [a-b for a,b in zip(p[0],p[1])]
        v2 = [a-b for a,b in zip(p[2],p[1])]
        den = math.sqrt(sum(x*x for x in u)*sum(x*x for x in v2))
        if den == 0: raise ValueError('undefined angle')
        actual = math.degrees(math.acos(max(-1,min(1,sum(a*b for a,b in zip(u,v2))/den))))
    return {'kind': v['kind'], 'computed': actual, 'claimed': q['answer_numeric'],
            'passed': abs(actual-q['answer_numeric'])<=tol}
