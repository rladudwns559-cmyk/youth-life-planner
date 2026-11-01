"""Overlay source verification only. Never auto-edit financial/eligibility rules."""
import os,sys
from datetime import datetime,timedelta
from .runtime import get_monitor,DEFAULT_STATE

def states():
    if 'pytest' in sys.modules and not os.environ.get('ASSET_ALERTS_STATE_DIR'):return {}
    if not (DEFAULT_STATE/'state.sqlite3').exists() and not os.environ.get('ASSET_ALERTS_STATE_DIR'):return {}
    return get_monitor().verified_sources()

def current_catalog(catalog):
    observed=states();sources=[]
    for source in catalog.sources:
        row=observed.get(source.source_id,{})
        # A matching complete referenced content fingerprint renews the source;
        # 200 responses and unrelated list pages alone do not.
        verified=row.get('last_success_at','')[:10]
        if row.get('reference_verified') and verified>=source.verified_on:
            source=source.model_copy(update={'verified_on':verified})
        sources.append(source)
    return catalog.model_copy(update={'sources':tuple(sources)})

def live_response(result):
    observed=states()
    for row in result['programs']:
        altered=any(observed.get(s['source_id'],{}).get('status')=='CHANGED_REVIEW_REQUIRED' for s in row['sources'])
        if altered:
            row['intake']['fresh']=False
            row['intake']['note']+=' 공식 원문 변경이 감지되어 기존 조건은 재검토가 필요합니다. 새 모집 공고는 알림 영역에서 별도로 확인하세요.'
            if row['intake']['status'] in ('OPEN','UPCOMING'):
                row['intake']['status']='REVIEW_REQUIRED';row['intake']['label']='최신 공고 재확인 필요'
                if row['bucket']=='CURRENT_CANDIDATE':row['bucket']='WATCHLIST'
    result['counts']={k:sum(r['intake']['status']==k for r in result['programs']) for k in result['counts']}
    result['recommendation_counts']={k:sum(r['bucket']==k for r in result['programs']) for k in result['recommendation_counts']}
    result['notifications']={'change_contract':'asset-program-events-v1','delivery_enabled':True,'subscriptions_stored':True}
    return result
