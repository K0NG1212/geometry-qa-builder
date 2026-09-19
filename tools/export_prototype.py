"""Rebuild the public 16-cell prototype index from policy and catalog."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from builder_modules.m0_scope.coverage import summarize
if __name__=='__main__':
    read=lambda p:json.loads(p.read_text(encoding='utf8'))
    policy=read(ROOT/'builder_modules/m0_scope/prototype-policy.json')
    result=summarize(read(ROOT/'docs/data/catalog.json'),policy)
    for name,data in [('prototype-policy.json',policy),('prototype-progress.json',result)]:
        (ROOT/'docs/data'/name).write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print('Prototype screened:',result['screened_total'],'/',result['target_total'])
