"""Replay handwritten synthetic fixtures; no model call and no scientific sample."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pipeline as p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    p.init(ROOT/'examples/synthetic.bundle.json', args.run, ROOT/'examples/v02/asset-units.json')
    for module in p.MODULES:
        request = p.packet(args.run)
        path = ROOT/'examples/v02/construction.json' if module == 'construction' else ROOT/f'examples/fixture-results/{module}.json'
        p.accept(args.run, path, 'handwritten-fixture', request['context_hash'], fixture=True)
    p.export(args.run)
    print('Synthetic replay complete (zero model calls): '+str(Path(args.run).resolve()))


if __name__ == '__main__':
    main()
