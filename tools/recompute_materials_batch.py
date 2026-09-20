"""Recompute six materials-cell QA from three COD CIFs; standard library only.
Limited reader for these cubic, fully occupied CIF entries; NOT a general CIF parser.
Usage: python tools/recompute_materials_batch.py CIF_DIRECTORY --out metrics.json
"""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal,localcontext
import re,shlex,itertools,math,cmath,json,argparse

def expression(text,point):
 text=text.replace(' ','');parts=re.findall(r'[+-]?[^+-]+',text)
 if ''.join(parts)!=text:raise ValueError('Unsupported symmetry expression')
 value=F(0)
 for term in parts:
  sign=-1 if term.startswith('-') else 1;t=term.lstrip('+-')
  if t in 'xyz' and len(t)==1:v=point['xyz'.index(t)]
  elif re.fullmatch(r'\d+(?:/\d+)?',t):v=F(t)
  else:raise ValueError('Unsupported symmetry term: '+term)
  value+=sign*v
 return value%1

def read_cubic(path):
 lines=path.read_text(encoding='utf8').splitlines()
 def scalar(tag):
  vals=[shlex.split(l)[1] for l in lines if l.startswith(tag+' ')];assert len(vals)==1;return F(vals[0])
 a,b,c=[scalar('_cell_length_'+v) for v in 'abc'];assert a==b==c
 assert all(scalar('_cell_angle_'+v)==90 for v in ['alpha','beta','gamma'])
 idx=lines.index('_space_group_symop_operation_xyz')+1;ops=[]
 while idx<len(lines) and not lines[idx].startswith(('loop_','_')):
  if lines[idx].strip():ops.append(lines[idx].strip().strip("'\""))
  idx+=1
 idx=lines.index('_atom_site_fract_z')+1;sites=[]
 while idx<len(lines) and not lines[idx].startswith(('loop_','_')):
  if lines[idx].strip():
   t=shlex.split(lines[idx]);assert len(t)==4 and re.fullmatch('[A-Z][a-z]?',t[0]);sites.append((t[0],tuple(map(F,t[1:]))))
  idx+=1
 rows=[]
 for symbol,p in sites:
  xyz=sorted({tuple(expression(e,p) for e in op.split(',')) for op in ops})
  for f in xyz:rows.append({'element':symbol,'fractional':[float(v) for v in f],'fractional_exact':[str(v) for v in f],'xyz_A':[float(a*v) for v in f]})
 assert len(rows)==8
 return dict(a_A=float(a),cell_diagonal_nm=math.sqrt(3)*float(a)/10,rows=rows,symmetry_operation_count=len(ops))

def neighbors(crystal,element):
 a=crystal['a_A'];rows=crystal['rows'];origin=next(r for r in rows if r['element']==element and r['fractional']==[0,0,0]);pts=[]
 for j,r in enumerate(rows):
  for t in itertools.product([-1,0,1],repeat=3):
   v=[a*(f+n) for f,n in zip(r['fractional'],t)];d=math.sqrt(sum(x*x for x in v))
   if d>1e-8:pts.append(dict(row=j+1,translation=list(t),element=r['element'],vector_A=v,distance_A=d))
 pts.sort(key=lambda p:p['distance_A']);first=[x for x in pts if abs(x['distance_A']-pts[0]['distance_A'])<1e-8]
 angles=[]
 for u,v in itertools.combinations(first,2):
  dot=sum(x*y for x,y in zip(u['vector_A'],v['vector_A']));angles.append(math.degrees(math.acos(max(-1,min(1,dot/u['distance_A']/v['distance_A'])))))
 like=[x for x in pts if x['element']==element];same=[x for x in like if abs(x['distance_A']-like[0]['distance_A'])<1e-8]
 return dict(distance_A=pts[0]['distance_A'],coordination=len(first),neighbors=first,angles_deg=angles,same_species_distance_A=like[0]['distance_A'],same_species_count=len(same),cluster_span_nm=max(math.dist(u['vector_A'],v['vector_A']) for u,v in itertools.combinations(first,2))/10)

def structure_factor(crystal,hkl,weights):
 z=sum(weights[r['element']]*cmath.exp(2j*math.pi*sum(h*x for h,x in zip(hkl,r['fractional']))) for r in crystal['rows'])
 # Exact roots of unity for quarter-grid coordinates; no numerical phase cancellation error.
 roots=[(1,0),(0,1),(-1,0),(0,-1)];real=imag=0
 for r in crystal['rows']:
  phase=sum(h*F(x) for h,x in zip(hkl,r['fractional_exact']))%1;k=phase*4;assert k.denominator==1;rr,ii=roots[int(k)];real+=weights[r['element']]*rr;imag+=weights[r['element']]*ii
 assert abs(z-complex(real,imag))<1e-10
 return dict(real=real,imaginary=imag,amplitude=math.hypot(real,imag),intensity=real*real+imag*imag)

def calculate(directory):
 out={name:read_cubic(directory/(cod+'.cif')) for name,cod in [('silicon','9008565'),('diamond','9008564'),('halite','9008678')]}
 out['silicon']['coordination_shell']=neighbors(out['silicon'],'Si');out['halite']['coordination_shell']=neighbors(out['halite'],'Na')
 for name in ['silicon','diamond']:
  a=out[name]['a_A'];out[name]['d111_nm']=a/math.sqrt(3)/10;out[name]['d220_nm']=a/math.sqrt(8)/10
  out[name]['two_theta111_deg']=2*math.degrees(math.asin(1.5406/(2*a/math.sqrt(3))))
 out['silicon']['factors']={''.join(map(str,h)):structure_factor(out['silicon'],h,{'Si':1}) for h in [(1,1,1),(2,0,0),(2,2,0)]}
 out['halite']['factors']={''.join(map(str,h)):structure_factor(out['halite'],h,{'Na':11,'Cl':17}) for h in [(1,1,1),(2,0,0)]}
 out['halite']['equal_factors']={''.join(map(str,h)):structure_factor(out['halite'],h,{'Na':1,'Cl':1}) for h in [(1,1,1),(2,0,0)]}
 with localcontext() as ctx:
  ctx.prec=40
  sa=Decimal(str(out['silicon']['a_A']));na=Decimal(str(out['halite']['a_A']));check={'silicon_nearest_A':float(sa*Decimal(3).sqrt()/4),'halite_unlike_A':float(na/2),'halite_like_A':float(na/Decimal(2).sqrt())}
  assert abs(check['silicon_nearest_A']-out['silicon']['coordination_shell']['distance_A'])<1e-12
  assert abs(check['halite_unlike_A']-out['halite']['coordination_shell']['distance_A'])<1e-12
  assert abs(check['halite_like_A']-out['halite']['coordination_shell']['same_species_distance_A'])<1e-12
 out['checks']={'exact_root_structure_factors':True,'decimal_closed_form_distances':check,'cell_counts':{name:len(out[name]['rows']) for name in ['silicon','diamond','halite']}}
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=calculate(a.directory);a.out.write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps({n:{k:v for k,v in r[n].items() if k not in ['rows','coordination_shell']} for n in ['silicon','diamond','halite']},indent=2))
