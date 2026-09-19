"""Export public module docs/code from an explicit allowlist; never include run data."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    modules = []
    for path in sorted((ROOT/'builder_modules').glob('m[0-6]_*')):
        entry = json.loads((path/'module.json').read_text(encoding='utf-8'))
        entry['files'] = []
        for name in ('README.md', 'module.py', 'prompt.md', 'schema.json', 'settings.json', 'retrieval.md', 'prototype-policy.json', 'coverage.py'):
            file = path/name
            if file.exists():
                entry['files'].append({'name': name, 'path': file.relative_to(ROOT).as_posix(),
                    'content': file.read_text(encoding='utf-8'),
                    'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
        modules.append(entry)
    if [m['id'] for m in modules] != [f'M{i}' for i in range(7)]:
        raise ValueError('Expected exactly seven module definitions')
    return {'version': '0.4.0', 'modules': modules,
        'note': '实现文件的静态展示，不会在浏览器执行 Python 或调用模型。科学质量尚待真实材料评测。'}


if __name__ == '__main__':
    path = ROOT/'docs/data/builder-modules.json'
    path.write_text(json.dumps(build(), ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('Exported 7 public module definitions to '+path.name)
