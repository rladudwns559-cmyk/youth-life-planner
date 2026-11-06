"""Compile explicitly reviewed official evidence, never auto-approve fetched HTML."""
import argparse
import json
from datetime import date
from pathlib import Path

from backend.finance.discovery import load_catalog
from backend.finance.renewal import compile_renewals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--reviews', type=Path, required=True)
    parser.add_argument('--batch', type=Path, action='append', required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    reviews = {e['product_id']: e for e in read(args.reviews)['entries']}
    result = compile_renewals(load_catalog(args.catalog), reviews, [read(p) for p in args.batch], date.fromisoformat(args.as_of))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
    print(json.dumps(result['counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
