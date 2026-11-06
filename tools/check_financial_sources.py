"""Bounded public-source change detection. Never renews or edits product facts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import ssl
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler

from backend.finance.discovery import HOSTS, Product, load_catalog, pairs

MAX_BYTES=6*1024*1024


def official_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):
        raise ValueError('UNAPPROVED_OFFICIAL_URL')
    return url


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def inspect(url):
    official_url(url)
    try:
        opener=build_opener(OfficialRedirect(),HTTPSHandler(context=ssl.create_default_context()))
        request=Request(url,headers={'User-Agent':'AI-X official financial source verification','Accept':'text/html,application/pdf'})
        with opener.open(request,timeout=12) as response:
            raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise ValueError('SOURCE_TOO_LARGE')
            return {'url':url,'status':response.status,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'result':'FETCHED_REVIEW_REQUIRED'}
    except Exception as error:
        return {'url':url,'status':error.code if isinstance(error,HTTPError) else None,'result':'FETCH_FAILED_NOT_DISCONTINUED','error_type':type(error).__name__}


def main():
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--renewals',type=Path);p.add_argument('--previous',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.resolve() in {x.resolve() for x in [a.catalog,a.renewals,a.previous] if x}:raise ValueError('INPUT_OVERWRITE_FORBIDDEN')
    catalog=load_catalog(a.catalog);products=list(catalog.products)
    if a.renewals:
        data=json.loads(a.renewals.read_text(encoding='utf-8'),object_pairs_hook=pairs)
        products.extend(Product.model_validate(r['product']) for r in data['records'].values())
    urls=sorted({official_url(s.url) for product in products for s in product.sources})
    if len(urls)>500:raise ValueError('SOURCE_CHECK_BATCH_TOO_LARGE')
    previous={}
    if a.previous:previous={r['url']:r for r in json.loads(a.previous.read_text(encoding='utf-8'))['sources']}
    with ThreadPoolExecutor(max_workers=3) as executor:rows=list(executor.map(inspect,urls))
    for row in rows:
        old=previous.get(row['url'],{})
        row['comparison']='CHANGED_REVIEW_REQUIRED' if row.get('sha256') and old.get('sha256') and row['sha256']!=old['sha256'] else 'UNCHANGED_NOT_RENEWED' if row.get('sha256') and row.get('sha256')==old.get('sha256') else 'NO_PREVIOUS_COMPARISON'
    result={'checked_at':datetime.now(timezone(timedelta(hours=9))).isoformat(),'sources':rows,'facts_modified':False,'expiry_extended':False,'discontinuation_inferred_from_fetch_failure':False}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'sources':len(rows),'fetched':sum(r['result']=='FETCHED_REVIEW_REQUIRED' for r in rows),'failed':sum(r['result']=='FETCH_FAILED_NOT_DISCONTINUED' for r in rows),'changed':sum(r['comparison']=='CHANGED_REVIEW_REQUIRED' for r in rows),'facts_modified':False}))


if __name__=='__main__':main()
