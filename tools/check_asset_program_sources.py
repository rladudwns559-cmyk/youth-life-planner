"""Read registered official sources and report candidates for manual review.
Does not rewrite the catalog, infer rules, schedule a job, or send notifications.
"""
import argparse,json,sys,hashlib,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.opportunities.catalog import load_catalog,CATALOG_PATH

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):return None

def check_sources(catalog,source_id=None):
    if source_id is not None and source_id not in {s.source_id for s in catalog.sources}:raise ValueError('UNKNOWN_SOURCE_ID')
    rows=[]
    opener=urllib.request.build_opener(NoRedirect)
    for source in catalog.sources:
        if source_id is not None and source.source_id!=source_id:continue
        row=dict(source_id=source.source_id,url=source.url)
        try:
            request=urllib.request.Request(source.url,headers={'User-Agent':'AI-X-official-source-check/1.0'})
            with opener.open(request,timeout=10) as response:
                content=response.read(2_000_001)
                if len(content)>2_000_000:raise ValueError('SOURCE_SIZE_LIMIT')
                sha=hashlib.sha256(content).hexdigest()
                row.update(http_status=response.status,bytes=len(content),sha256=sha,
                    result='UNCHANGED_BYTES' if sha==source.capture_sha256 else 'CONTENT_CHANGED_REVIEW_REQUIRED')
        except Exception as error:row.update(result='FETCH_FAILED_REVIEW_REQUIRED',error_type=type(error).__name__)
        rows.append(row)
    return dict(schema_version='asset-source-check-v1',checked_at=datetime.now(timezone(timedelta(hours=9))).isoformat(),
        automatic_policy_update=False,notifications_sent=0,catalog_verified_dates_updated=False,sources=rows,
        note='HTML byte differences may reflect navigation or counters. Manual review of substantive conditions is required before publishing or emitting a policy-change event.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-id')
    parser.add_argument('--output',type=Path)
    options=parser.parse_args()
    result=check_sources(load_catalog(),options.source_id)
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if options.output:
        target=options.output.resolve()
        if target==CATALOG_PATH.resolve() or CATALOG_PATH.parent.resolve() in target.parents:raise ValueError('CATALOG_OVERWRITE_FORBIDDEN')
        with target.open('x',encoding='utf-8') as stream:stream.write(text)
    else:print(text)

