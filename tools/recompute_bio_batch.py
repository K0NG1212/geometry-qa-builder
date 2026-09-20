"""Recompute the biological nm-scale batch from original PDB files (standard library).
This is a supplemental answer calculator, not a registered generic semantic grader.
Usage: python tools/recompute_bio_batch.py PATH_TO_PDB_DIRECTORY --out metrics.json
"""
import argparse,json,math,itertools
from pathlib import Path
from decimal import Decimal,localcontext

def atoms(path,name,chains):
 rows=[]
 for line in path.read_text().splitlines():
  if line.startswith('ENDMDL'):break
  if not line.startswith('ATOM  ') or line[12:16].strip()!=name or line[21] not in chains:continue
  if line[16].strip() or line[26].strip():raise ValueError('Alternate location/insertion code requires explicit handling')
  rows.append(dict(chain=line[21],residue=int(line[22:26]),resname=line[17:20].strip(),atom=name,serial=int(line[6:11]),xyz=[float(line[a:b]) for a,b in [(30,38),(38,46),(46,54)]]))
 assert len({(a['chain'],a['residue']) for a in rows})==len(rows)
 return rows

def distance(a,b):return math.dist(a,b)
def metrics(rows):
 xyz=[a['xyz'] for a in rows];n=len(xyz);center=[sum(p[k] for p in xyz)/n for k in range(3)]
 rg2=sum(math.dist(p,center)**2 for p in xyz)/n
 maximum,i,j=max((distance(xyz[i],xyz[j]),i,j) for i in range(n) for j in range(i+1,n))
 with localcontext() as ctx:
  ctx.prec=40
  dxyz=[[Decimal(str(v)) for v in p] for p in xyz]
  pair_sum=sum(sum((a-b)**2 for a,b in zip(p,q)) for p,q in itertools.combinations(dxyz,2))
  independent_rg=float((pair_sum/Decimal(n*n)).sqrt())
  independent_max=float(max(sum((a-b)**2 for a,b in zip(p,q)) for p,q in itertools.combinations(dxyz,2)).sqrt())
 assert abs(independent_rg-math.sqrt(rg2))<1e-10 and abs(independent_max-maximum)<1e-10
 return dict(count=n,rows=rows,centroid_A=center,rg_A=math.sqrt(rg2),diameter_A=maximum,diameter_pair=[i+1,j+1],end_to_end_A=distance(xyz[0],xyz[-1]),independent_rg_A=independent_rg,independent_diameter_A=independent_max)

def calculate(directory):
 out={}
 for code,n in [('1UBQ',76),('1CRN',46)]:
  rows=atoms(directory/(code+'.pdb'),'CA',{'A'});assert len(rows)==n and [r['residue'] for r in rows]==list(range(1,n+1));out[code]=metrics(rows)
 rows=atoms(directory/'1BNA.pdb',"C1'",{'A','B'});assert len(rows)==24
 lookup={(a['chain'],a['residue']):a for a in rows};centers=[]
 for i in range(1,13):
  a,b=lookup['A',i],lookup['B',25-i];assert {a['resname'],b['resname']} in [{'DA','DT'},{'DC','DG'}]
  centers.append([(v+w)/2 for v,w in zip(a['xyz'],b['xyz'])])
 out['1BNA']=metrics(rows);L=sum(distance(a,b) for a,b in zip(centers,centers[1:]));r=distance(centers[0],centers[-1]);out['dna']=dict(midpoints_A=centers,marker_path_A=L,chord_A=r,straightness=r/L,fret_R0_nm=3.5,fret_chord=1/(1+(r/35)**6),fret_incorrect_contour=1/(1+(L/35)**6))
 with localcontext() as ctx:
  ctx.prec=40
  c=[[Decimal(str(v)) for v in p] for p in centers]
  d=lambda a,b:sum((v-w)**2 for v,w in zip(a,b)).sqrt()
  rd=d(c[0],c[-1]);ld=sum(d(a,b) for a,b in zip(c,c[1:]));ef=Decimal(1)/(1+(rd/Decimal(35))**6)
  assert abs(float(rd)-r)<1e-10 and abs(float(ld)-L)<1e-10 and abs(float(ef)-out['dna']['fret_chord'])<1e-12
  out['dna']['decimal_check']={'chord_A':float(rd),'marker_path_A':float(ld),'efficiency':float(ef),'passed':True}
 out['guinier']={}
 for code in ['1UBQ','1CRN']:
  rg=out[code]['rg_A']/10;out['guinier'][code]={str(q):{'qRg':q*rg,'within_task_limit':q*rg<1.1,'normalized_intensity':math.exp(-(q*rg)**2/3) if q*rg<1.1 else None} for q in [0.5,1.0]}
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();result=calculate(a.directory);a.out.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:{a:b for a,b in v.items() if a!='rows'} for k,v in result.items()},indent=2))
