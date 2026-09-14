import json
import shutil
from pathlib import Path

def validate_config(config):
    for key in ("max_questions", "max_output_tokens", "max_bundle_chars"):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError("scope: positive integer required for "+key)

def initialize(b, root, bundle_path, run):
    bundle=b.read(bundle_path); b.bundle_check(bundle)
    c=b.read(Path(__file__).with_name('settings.json'))
    b.validate(c, b.read(Path(__file__).with_name("schema.json")))
    validate_config(c)
    if len(json.dumps(bundle,ensure_ascii=False))>c['max_bundle_chars']: raise ValueError('bundle too large; narrow material explicitly, no silent truncation')
    run=Path(run)
    if run.exists(): raise ValueError('run path already exists; use a new path')
    run.mkdir(parents=True)
    b.write(run/'bundle.json',bundle); b.write(run/'config.json',c)
    b.write(run/'schemas.json',b.SCHEMAS)
    shutil.copytree(root/'prompts',run/'prompts')
    shutil.copyfile(Path(b.__file__),run/'builder_snapshot.py')
    b.write(run/'manifest.json',{'created':b.now(),'version':c['version'],'hashes':b.snapshot(run)})
