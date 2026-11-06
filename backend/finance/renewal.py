"""Versioned official rechecks. Existing decision/rate engines remain unchanged."""
from copy import deepcopy
from datetime import date

from backend.finance.discovery import Catalog, Product, Source, compile_tables
from backend.finance.recommendation import compile_recommendations


def compile_renewals(catalog: Catalog, reviews: dict, batches: list[dict], as_of: date) -> dict:
    original = {p.product_id: p for p in catalog.products}
    products = dict(original)
    rate_reviews = deepcopy(reviews)
    records = {}
    # Old input batches are immutable; select each product's latest dated review.
    latest = {}
    seen = set()
    for batch in batches:
        checked = date.fromisoformat(batch['checked_on'])
        for key in ('updates', 'holds'):
            for entry in batch.get(key, []):
                pid = entry['product']['product_id'] if key == 'updates' else entry['product_id']
                marker = (pid, checked)
                if marker in seen:
                    raise ValueError('DUPLICATE_SAME_DAY_RECHECK')
                seen.add(marker)
                if pid not in latest or checked > latest[pid][0]:
                    latest[pid] = (checked, key, entry)
    selected = {}
    for checked, key, entry in latest.values():
        selected.setdefault(checked, {'checked_on': checked.isoformat(), 'updates': [], 'holds': []})[key].append(entry)
    for batch in sorted(selected.values(), key=lambda b: b['checked_on']):
        checked = date.fromisoformat(batch['checked_on'])
        if checked > as_of:
            raise ValueError('FUTURE_RECHECK')
        for entry in batch.get('updates', []):
            product = Product.model_validate(entry['product'])
            pid = product.product_id
            if pid not in original or pid in records:
                raise ValueError('UNKNOWN_OR_DUPLICATE_RECHECK')
            if product.institution != original[pid].institution or product.kind != original[pid].kind:
                raise ValueError('RECHECK_IDENTITY_CHANGE')
            if entry['sale_status'] != 'CURRENT':
                raise ValueError('CURRENT_RECHECK_REQUIRED')
            if not entry.get('evidence_note', '').strip():
                raise ValueError('SALE_EVIDENCE_REQUIRED')
            if any(s.reviewed_on != checked.isoformat() or s.mode not in ('OFFICIAL_PAGE', 'OFFICIAL_DOCUMENT') for s in product.sources):
                raise ValueError('FRESH_DIRECT_SOURCE_REQUIRED')
            if not any(s.mode == 'OFFICIAL_PAGE' for s in product.sources):
                raise ValueError('CURRENT_SALE_PAGE_REQUIRED')
            review = entry.get('review')
            rate_reviews.pop(pid, None)
            if review:
                if review.get('product_id') != pid:
                    raise ValueError('RATE_RECHECK_ID_MISMATCH')
                sources = [Source.model_validate(s) for s in review.get('sources', [])]
                if not sources or any(s.reviewed_on != checked.isoformat() or s.mode not in ('OFFICIAL_PAGE', 'OFFICIAL_DOCUMENT') for s in sources):
                    raise ValueError('FRESH_RATE_SOURCE_REQUIRED')
                rate_reviews[pid] = deepcopy(review)
            one = Catalog.model_validate({**catalog.model_dump(mode='json'), 'reviewed_on': checked.isoformat(), 'products': [product.model_dump(mode='json')]})
            compiled = compile_tables(one, checked)
            records[pid] = dict(status='CURRENT', checked_on=checked.isoformat(), valid_until=compiled['valid_until'],
                                product=product.model_dump(mode='json'), compiled=compiled,
                                reason=entry['evidence_note'], rate_hold_reason=review.get('excluded_reason') if review else '현재 기본금리는 추가 확인이 필요합니다.', change_notes=entry.get('change_notes', []))
            products[pid] = product
        for entry in batch.get('holds', []):
            pid = entry['product_id']
            if pid not in original or pid in records:
                raise ValueError('UNKNOWN_OR_DUPLICATE_RECHECK')
            if entry['sale_status'] not in ('UNCONFIRMED', 'DISCONTINUED') or not entry.get('reason', '').strip():
                raise ValueError('HOLD_REASON_REQUIRED')
            sources = [Source.model_validate(s) for s in entry.get('sources', [])]
            if any(s.reviewed_on != checked.isoformat() for s in sources):
                raise ValueError('HOLD_SOURCE_DATE_MISMATCH')
            if entry['sale_status'] == 'DISCONTINUED' and not sources:
                raise ValueError('OFFICIAL_DISCONTINUATION_EVIDENCE_REQUIRED')
            # Old terms remain historical; a failed fetch never renews their dates.
            raw = original[pid].model_dump(mode='json')
            raw.update(reference_only=True, reference_reason=entry['reason'])
            product = Product.model_validate(raw)
            products[pid] = product
            rate_reviews.pop(pid, None)
            records[pid] = dict(status=entry['sale_status'], checked_on=checked.isoformat(), valid_until=None,
                                product=raw, compiled=None, reason=entry['reason'],
                                status_sources=[s.model_dump(mode='json') for s in sources], change_notes=[])
    combined = Catalog.model_validate({**catalog.model_dump(mode='json'), 'reviewed_on': as_of.isoformat(), 'products': [products[p.product_id].model_dump(mode='json') for p in catalog.products]})
    ranking = compile_recommendations(combined, rate_reviews, as_of)
    current = [r for r in records.values() if r['status'] == 'CURRENT']
    return dict(schema_version='official-financial-renewals-v1', built_on=as_of.isoformat(),
                review_after_days=catalog.review_after_days, records=records, recommendations=ranking,
                counts=dict(total=len(original), renewed=len(current), held=len(records)-len(current),
                            not_rechecked=len(original)-len(records),
                            rate_verified=sum(pid in ranking['rate_by_product'] for pid,r in records.items() if r['status']=='CURRENT')),
                actual_product_calculation_count=0, policy_benefit_applied_krw=0, automatic_refresh=False)
