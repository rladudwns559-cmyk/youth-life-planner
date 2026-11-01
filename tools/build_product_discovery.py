"""Compile audited, dated public comparison tables. Does not fetch or re-date sources."""
import argparse,json,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.finance.discovery import load_catalog,compile_tables

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--as-of',required=True);parser.add_argument('--output',type=Path,default=ROOT/'frontend/src/public-data/product-discovery.json');args=parser.parse_args()
    catalog=load_catalog();as_of=date.fromisoformat(args.as_of)
    # A rebuild cannot silently renew the reviewed_on evidence date.
    result=compile_tables(catalog,as_of)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps(dict(products=len(catalog.products),institutions=len({p.institution for p in catalog.products}),bytes=args.output.stat().st_size,valid_until=result['valid_until'],automatic_refresh=False)))

if __name__=='__main__':main()
