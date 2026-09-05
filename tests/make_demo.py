"""Create explicitly synthetic demo files; never calls a model or network."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import builder
from test_builder import fixtures

if __name__=='__main__':
    root=builder.ROOT/'examples'
    bundle,stages=fixtures()
    builder.write(root/'synthetic.bundle.json',bundle)
    for stage,data in stages.items(): builder.write(root/'fixture-results'/f'{stage}.json',data)
    run=root/'synthetic-demo-run'
    builder.init(root/'synthetic.bundle.json',run)
    for stage in builder.STAGES:
        builder.packet(run)
        builder.accept(run,stages[stage],'none-handwritten-fixture','test_fixture')
    builder.report(run)
    for key,schema in builder.SCHEMAS.items(): builder.write(builder.ROOT/'schemas'/f'{key}.json',schema)
    print('Synthetic fixture demo created; no GPT-6 request was made.')
