"""GeoBench v0.4: file-based, subscription-session pipeline. No API calls."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
if (ROOT / 'builder_snapshot.py').exists():
    spec = importlib.util.spec_from_file_location('frozen_core', ROOT / 'builder_snapshot.py')
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
else:
    import builder as b

PLAN_ITEM = copy.deepcopy(b.SCHEMAS['qa']['properties']['items']['items'])
for field in ('answer_numeric', 'reference_answer'):
    del PLAN_ITEM['properties'][field]
    PLAN_ITEM['required'].remove(field)
PLAN_ITEM['properties']['answer_text'] = b.nullable(b.S)
PLAN_ITEM['required'].append('answer_text')
PLAN = b.obj(items=b.arr(PLAN_ITEM), exclusions=b.SS)
UNITS = b.obj(assets=b.arr(b.obj(source_id=b.S, unit=b.enum('angstrom', 'unknown'),
    source_refs=b.arr(b.REF), checked_by=b.S, notes=b.S)))
MODULES = ('evidence', 'tasks', 'construction', 'review')

from builder_modules.m0_scope import module as scope
from builder_modules.m1_materials import module as materials
from builder_modules.m2_evidence import module as evidence
from builder_modules.m3_tasks import module as tasks
from builder_modules.m4_construction import module as construction
from builder_modules.m5_quality import module as quality
from builder_modules.m6_export import module as exporting

MODULE_PATHS = {'evidence': 'm2_evidence', 'tasks': 'm3_tasks', 'construction': 'm4_construction', 'review': 'm5_quality'}



def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol_hashes(run):
    paths = [run/'pipeline_snapshot.py', run/'asset-units.json', run/'protocol.json']
    paths += sorted((run/'modules').rglob('*'))
    paths += [p for p in sorted((run/'builder_modules').rglob('*')) if '__pycache__' not in p.parts and p.suffix != '.pyc']
    return {p.relative_to(run).as_posix(): file_hash(p) for p in paths if p.is_file()}


def check_units(units, bundle):
    return materials.check_units(b, units, bundle)


def init(bundle, run, units=None):
    bundle_data = b.read(bundle)
    unit_data = b.read(units) if units else {'assets': []}
    check_units(unit_data, bundle_data)
    scope.initialize(b, ROOT, bundle, run)
    run = Path(run)
    b.write(run/'asset-units.json', unit_data)
    b.write(run/'protocol.json', {'version': '0.4.0', 'executor': 'codex_session',
        'requested_model': 'gpt-6-astra', 'api_required': False,
        'numeric_answers': 'program_computed', 'independent_review': False})
    shutil.copyfile(Path(__file__), run/'pipeline_snapshot.py')
    shutil.copytree(ROOT/'modules', run/'modules')
    shutil.copytree(ROOT/'builder_modules', run/'builder_modules', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    b.write(run/'protocol-manifest.json', {'created': b.now(), 'hashes': protocol_hashes(run)})


def state(run):
    run = Path(run)
    manifest = b.read(run/'protocol-manifest.json')
    if manifest['hashes'] != protocol_hashes(run):
        raise ValueError('module snapshot changed; create a new run')
    if file_hash(__file__) != manifest['hashes']['pipeline_snapshot.py']:
        raise ValueError('pipeline changed; use run/pipeline_snapshot.py')
    current_modules = {p.relative_to(ROOT).as_posix(): file_hash(p)
        for p in (ROOT/'builder_modules').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    frozen_modules = {k: v for k, v in manifest['hashes'].items() if k.startswith('builder_modules/')}
    if current_modules != frozen_modules:
        raise ValueError('module implementation changed; use run/pipeline_snapshot.py or create a new run')
    result = b.state(run)
    check_units(b.read(run/'asset-units.json'), result[1])
    # A later accepted stage must never silently survive removal of its parent.
    for stage in b.STAGES[len(result[3]):]:
        if (run/(stage+'.json')).exists():
            raise ValueError('orphan stage: '+stage)
    if 'qa' in result[3]:
        receipt = b.read(run/'construction-receipt.json')
        if receipt['plan_hash'] != b.digest(receipt['plan']):
            raise ValueError('construction plan changed')
        regenerated = construct(receipt['plan'], result[1], result[3], b.read(run/'asset-units.json'))
        if b.digest(regenerated) != b.digest(result[3]['qa']):
            raise ValueError('construction result mismatch')
    return result


def status(run):
    run, bundle, config, previous, manifest = state(run)
    attempts = sorted((run/'attempts-v02').glob('*.json'))
    return {'version': '0.4.0', 'paper_id': bundle['paper_id'],
        'completed': list(MODULES[:len(previous)]),
        'next': MODULES[len(previous)] if len(previous) < 4 else 'export',
        'accepted_candidates': len(previous.get('qa', {}).get('items', [])),
        'failed_attempts': len(attempts),
        'last_failure': b.read(attempts[-1])['error'] if attempts else None,
        'benchmark_ready': False}


def packet(run):
    run, bundle, config, previous, manifest = state(run)
    if len(previous) == 4:
        return None
    stage = b.STAGES[len(previous)]
    module = MODULES[len(previous)]
    instructions = (run/'prompts/common.md').read_text(encoding='utf-8')
    instructions += '\n' + (run/'builder_modules'/MODULE_PATHS[module]/'prompt.md').read_text(encoding='utf-8')
    result = {'module': module, 'execution_mode': 'codex_session',
        'requested_model': 'gpt-6-astra', 'instructions': instructions,
        'input': {'bundle': bundle, 'previous': previous,
                  'asset_units': b.read(run/'asset-units.json'), 'max_questions': config['max_questions'],
                  'prototype_policy': b.read(run/'builder_modules/m0_scope/prototype-policy.json')},
        'output_schema': b.read(run/'builder_modules'/MODULE_PATHS[module]/'schema.json'),
        'context_hash': b.digest({'core': manifest['hashes'], 'previous': previous,
                                  'protocol': protocol_hashes(run)})}
    b.write(run/f'{module}.packet.json', result)
    return result


def construct(plan, bundle, previous, units):
    return construction.construct(b, plan, bundle, previous, units)


def accept(run, result_path, model, context_hash, fixture=False):
    lock = Path(run)/'.accept.lock'
    try:
        with lock.open('x', encoding='utf-8') as handle:
            handle.write(b.now())
    except FileExistsError:
        raise ValueError('another import is active; inspect .accept.lock if the prior process crashed') from None
    try:
        return _accept(run, result_path, model, context_hash, fixture)
    finally:
        lock.unlink(missing_ok=True)


def _accept(run, result_path, model, context_hash, fixture=False):
    run = Path(run)
    module = 'unknown'
    data = None
    raw = None
    try:
        request = packet(run)
        if request is None:
            raise ValueError('all stages complete; fork to revise')
        module = request['module']
        if context_hash != request['context_hash']:
            raise ValueError('stale packet context; read the current packet')
        if not model.strip():
            raise ValueError('reported model is required; use unknown if unavailable')
        raw = Path(result_path).read_text(encoding='utf-8-sig')
        data = json.loads(raw)
        run, bundle, config, previous, manifest = state(run)
        output = construct(data, bundle, previous, b.read(run/'asset-units.json')) if module == 'construction' else data
        stage = b.STAGES[len(previous)]
        validator = {'evidence': evidence, 'tasks': tasks, 'review': quality}.get(stage)
        if validator:
            validator.validate(b, output, bundle, previous, config)
        b.semantic(stage, output, bundle, previous, config)
        if fixture and not bundle['synthetic']:
            raise ValueError('fixture mode requires a synthetic bundle')
        if module == 'construction':
            b.write(run/'construction-receipt.json', {'plan': data, 'plan_hash': b.digest(data),
                'executor': 'trusted_python_geometry_or_evidence_text', 'reported_model': model})
        b.accept(run, output, model, 'test_fixture' if fixture else 'codex_session')
        return status(run)
    except (ValueError, KeyError, OSError, IndexError) as error:
        if (run/'protocol-manifest.json').exists():
            import datetime
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')
            b.write(run/'attempts-v02'/f'{stamp}.json', {'module': module,
                'error': str(error), 'data': data, 'result_file': str(result_path),
                'raw_result': raw if data is None else None,
                'time': b.now(), 'context_hash': context_hash})
        raise


def export(run):
    run, bundle, config, previous, manifest = state(run)
    return exporting.export(b, run, bundle, previous, status(run))


def fork(run, target, before):
    run, bundle, config, previous, manifest = state(run)
    target = Path(target)
    if target.resolve().is_relative_to(run.resolve()):
        raise ValueError('fork target must be outside the source run')
    if target.exists():
        raise ValueError('fork target already exists')
    index = MODULES.index(before)
    if index > len(previous):
        raise ValueError('cannot fork beyond completed prefix')
    shutil.copytree(run, target)
    # Only fixed generated files in the newly created copy are removed.
    names = [s+'.json' for s in b.STAGES[index:]]
    names += [s+'.packet.json' for s in MODULES]
    names += ['report.json', 'report.md', 'candidates.csv', 'model-inputs.json',
              'private-answers.json', 'quality-report.json']
    if index <= 2:
        names.append('construction-receipt.json')
    for name in names:
        (target/name).unlink(missing_ok=True)
    b.write(target/'fork-origin.json', {'parent': str(run.resolve()), 'before': before,
        'time': b.now(), 'inherited_failure_records': True})
    return status(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--paper-id', required=True); p.add_argument('--title', required=True); p.add_argument('--url', required=True)
    p.add_argument('--source', action='append', default=[]); p.add_argument('--xyz', action='append', default=[])
    p.add_argument('--out', required=True); p.add_argument('--synthetic', action='store_true')
    p = sub.add_parser('init')
    p.add_argument('--bundle', required=True); p.add_argument('--units'); p.add_argument('--run', required=True)
    for command in ('next', 'status', 'accept', 'export', 'fork'):
        p = sub.add_parser(command); p.add_argument('--run', required=True)
        if command == 'accept':
            p.add_argument('--result', required=True); p.add_argument('--model', required=True)
            p.add_argument('--context', required=True); p.add_argument('--fixture', action='store_true')
        if command == 'fork':
            p.add_argument('--target', required=True); p.add_argument('--before', choices=MODULES, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            materials.prepare(b, args); result = {'bundle': args.out}
        elif args.command == 'init':
            init(args.bundle, args.run, args.units); result = status(args.run)
        elif args.command == 'next':
            request = packet(args.run)
            result = {'packet': str(Path(args.run)/(request['module']+'.packet.json')),
                      'context': request['context_hash']} if request else status(args.run)
        elif args.command == 'accept':
            result = accept(args.run, args.result, args.model, args.context, args.fixture)
        elif args.command == 'export': result = export(args.run)
        elif args.command == 'fork': result = fork(args.run, args.target, args.before)
        else: result = status(args.run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, IndexError) as error:
        print('Stopped: '+str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
