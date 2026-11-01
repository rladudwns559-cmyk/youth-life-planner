"""Pure recommendation ordering from verified basic rates. No maturity arithmetic."""
from datetime import date,timedelta
from decimal import Decimal,InvalidOperation
from backend.finance.discovery import Product,Source,Catalog,decision

def select_rate(product:Product,months:int,entry:dict|None,as_of:date,review_days=7):
    if not entry or entry.get('excluded_reason') or product.reference_only or product.comparison_hold_reason:return None
    if product.schedule not in ('MONTHLY','LUMP_SUM'):return None
    if product.min_months is None or product.max_months is None or not product.min_months<=months<=product.max_months or product.allowed_months is not None and months not in product.allowed_months:return None
    try:
        sources=[Source.model_validate(s) for s in entry['sources']]
        if not sources or any(s.mode not in ('OFFICIAL_PAGE','OFFICIAL_DOCUMENT') or not 0<=(as_of-date.fromisoformat(s.reviewed_on)).days<=review_days for s in sources):return None
        candidates=[]
        for row in entry['rates']:
            lo,hi=row['min_months'],row['max_months']
            if type(lo)is not int or type(hi)is not int or not 1<=lo<=hi<=120:raise ValueError('INVALID_RATE_PERIOD')
            if not lo<=months<=hi:continue
            base=Decimal(str(row['base_rate_percent']))
            top=None if row.get('max_total_rate_percent') is None else Decimal(str(row['max_total_rate_percent']))
            if not base.is_finite() or not 0<=base<=100 or top is not None and (not top.is_finite() or not base<=top<=100):raise ValueError('INVALID_RATE')
            if not row['evidence_locator'].strip():raise ValueError('RATE_EVIDENCE_REQUIRED')
            candidates.append((base,top,row['evidence_locator']))
        if not candidates:return None
        if len({(x[0],x[1]) for x in candidates})!=1:return None
        base,top,locator=candidates[0]
        return dict(base_rate_percent=str(base),max_total_rate_percent=None if top is None else str(top),evidence_locator=locator,sources=[s.model_dump(mode='json') for s in sources])
    except (KeyError,TypeError,ValueError,InvalidOperation):
        return None

def rank_products(catalog:Catalog,reviews:dict,kind:str,amount:int|None,months:int,as_of:date):
    if kind not in ('SAVINGS','DEPOSIT'):raise ValueError('INVALID_KIND')
    if amount is not None and (type(amount)is not int or not 0<=amount<=1_000_000_000_000):raise ValueError('INVALID_AMOUNT')
    if type(months)is not int or not 1<=months<=120:raise ValueError('INVALID_MONTHS')
    ranked=[]
    for p in catalog.products:
        if p.kind!=kind:continue
        code=decision(p,amount,months,as_of,catalog.review_after_days)
        rate=select_rate(p,months,reviews.get(p.product_id),as_of,catalog.review_after_days)
        allocation=amount if code=='FIT' else p.maximum if code=='PARTIAL' else None
        ranked.append(dict(product_id=p.product_id,code=code,rate=rate,allocation=allocation,
            unallocated=None if allocation is None or amount is None else amount-allocation,
            eligibility='UNKNOWN',calculation=None))
    order={'FIT':0,'PARTIAL':1,'INPUT':2,'SCHEDULE':3,'TERM':4,'BUDGET':5,'MISSING':6,'REVIEW':7,'STALE':8}
    ranked.sort(key=lambda r:(order[r['code']],r['rate'] is None,-Decimal(r['rate']['base_rate_percent']) if r['rate'] else Decimal(0),r['product_id']))
    return ranked

def compile_recommendations(catalog:Catalog,reviews:dict,as_of:date):
    unknown=set(reviews)-{p.product_id for p in catalog.products}
    if unknown:raise ValueError('UNKNOWN_RATE_PRODUCT')
    products={};orders={};pool=[];seen={}
    for months in range(1,121):
        for p in catalog.products:
            rate=select_rate(p,months,reviews.get(p.product_id),as_of,catalog.review_after_days)
            if rate:products.setdefault(p.product_id,{})[str(months)]=rate
        for kind in ('SAVINGS','DEPOSIT'):
            ps=[p for p in catalog.products if p.kind==kind]
            ps.sort(key=lambda p:(str(months) not in products.get(p.product_id,{}),-Decimal(products[p.product_id][str(months)]['base_rate_percent']) if str(months) in products.get(p.product_id,{}) else Decimal(0),p.product_id))
            ids=[p.product_id for p in ps];key=tuple(ids)
            if key not in seen:seen[key]=len(pool);pool.append(ids)
            orders.setdefault(kind,{})[str(months)]=seen[key]
    dates=[date.fromisoformat(s['reviewed_on']) for e in reviews.values() for s in e.get('sources',[])]
    return dict(schema_version='basic-rate-recommendations-v1',built_on=as_of.isoformat(),
        valid_until=min([date.fromisoformat(catalog.reviewed_on)+timedelta(days=catalog.review_after_days),*[d+timedelta(days=catalog.review_after_days) for d in dates]]).isoformat(),
        method='FULL_BUDGET_THEN_VERIFIED_BASIC_ANNUAL_RATE',rate_by_product=products,order_calendar=orders,order_pool=pool,
        eligibility='UNKNOWN',actual_product_calculation_count=0,policy_benefit_applied_krw=0,
        disclosure='입력 예산 전액 납입 가능성을 먼저 보고, 같은 상품 종류·기간에서 확인된 기본 연이율이 높은 순으로 제안합니다. 최고금리 우대는 반영하지 않으며 만기이자순·가입 가능 확정 결과가 아닙니다.')

