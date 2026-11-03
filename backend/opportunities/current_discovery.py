"""Current public discovery snapshot. Historical snapshots and policy cores stay intact."""
from datetime import date,timedelta
import json
from backend.opportunities.personal_discovery import load_inputs,compile_personal,read_json,Rule,Rules
from backend.opportunities.regional_discovery import Catalog,Program,Source,ROOT,recruitment

PATH=ROOT/'data/support-programs/recruitment-evidence-20261101.json'
# Residence is not the only route into these programs (workplace, school, living area).
ALTERNATIVE_REGION={
 'JB-GUNSAN-YOUTH-INTERVIEW-FEE-2026','JB-GUNSAN-JOB-SUCCESS-GIFT-2026',
 'SEOUL-YONGSAN-YOUTH-LIFE-COOKIE-2026','SEOUL-YANGCHEON-LEATHER-WORKSHOP-2026-11',
 'BUSAN-SAHA-WEBNOVEL-ACADEMY-2026-11','BUSAN-HAEUNDAE-AI-MARKETING-2026-R2',
 'BUSAN-JINGU-SINGLE-LIFE-CLASS-2026-11','BUSAN-JINGU-MOCK-INTERVIEW-2026-11',
}

def load_municipal_batches():
    batches = [read_json(ROOT / 'data/support-programs' / filename) for filename in (
        'municipal-gap-20261101.json', 'municipal-open-gap-20261101.json', 'municipal-intakes-20261101.json', 'verified-intakes-next-20261101.json', 'verified-intakes-gap95-20261101.json', 'verified-intakes-gap73-20261101.json', 'recommendation-intakes-20261102.json', 'verified-expansion-20261103.json', 'verified-extension-20261103.json')]
    return {
        'programs': [record for batch in batches for record in batch['programs']],
        'rules': [rule for batch in batches for rule in batch['rules']],
        'intake_verification': {key: value for batch in batches for key, value in batch['intake_verification'].items()},
        'alternative_region_ids': [key for batch in batches for key in batch['alternative_region_ids']],
    }


def current_inputs():
    catalog,rules=load_inputs()
    research=read_json(PATH)
    display=read_json(ROOT/'data/support-programs/recruitment-display-20261101.json')
    records={p.program_id:p.model_dump(mode='json') for p in catalog.programs}
    evidence=dict(research['intake_verification'])
    for p in research['programs']:
        if p['program_id'] in records:raise ValueError('DUPLICATE_CURRENT_PROGRAM')
        records[p['program_id']]=Program.model_validate({**p,**display.get(p['program_id'],{})}).model_dump(mode='json')
    expansion=read_json(ROOT/'data/support-programs/nationwide-notices-20261101.json')
    municipal=load_municipal_batches()
    for row in [*expansion['programs'],*municipal['programs']]:
        item=Program.model_validate(row)
        if item.program_id in records:
            raise ValueError('DUPLICATE_NATIONWIDE_NOTICE')
        records[item.program_id]=item.model_dump(mode='json')
    evidence.update(expansion['intake_verification'])
    evidence.update(municipal['intake_verification'])
    for u in research['existing_updates']:
        p=records[u['program_id']]
        source=dict(url=u['url'],title='후속 공식 모집 상태 확인',basis_date=u.get('basis_date'),verified_on=u['verified_on'],evidence='OFFICIAL_INDEXED_PAGE' if 'JINJU' in u['program_id'] else 'OFFICIAL_NOTICE',locator=u['evidence_excerpt'])
        p['sources'].insert(0,source)
        p['schedule_note']=u['evidence_excerpt']+' · 최신 공식 안내를 확인하세요.'
        if u['status']=='NO_INTAKE_FOR_2026_SECOND_ROUND':p['intake_mode']='NO_INTAKE'
        elif u['status']=='HOLD_FOR_EXPLICIT_CLOSURE_SIGNAL':p['intake_mode']='CLOSED'
        elif u['status']=='OPEN_OFFICIAL_HOME_APPLICATION_LABEL':
            evidence[p['program_id']]={**u,'explicit_status':'OPEN_OFFICIAL_LABEL','budget_uncertainty':'공식 메인 접수중 표시 확인. 잔여예산·최종 접수는 별도 확인.'}
    for pid in ALTERNATIVE_REGION:
        p=records[pid]
        p['required_checks'].insert(0,'거주지 외 직장·학교·활동지역 등 대상 경로 확인')
        p['schedule_note']+=' 거주지 외 직장·학교·활동 지역을 인정하는지 공식 참여 조건을 확인하세요.'
    # The official notice provides an exact birth-date interval; other new
    # programs remain UNKNOWN until their exceptions and reference dates resolve.
    starter=records['SEOUL-LIFE-PLANNING-STARTER-2026']
    rules=Rules.model_validate({**rules.model_dump(mode='json'),'rules':[
      *[r.model_dump(mode='json') for r in rules.rules],
      dict(program_id=starter['program_id'],sources=starter['sources'],
           age=dict(kind='BIRTH_RANGE',birth_start='2002-01-01',birth_end='2008-12-31',note='공식 2026 스타터코스 공고의 2002.1.1~2008.12.31 출생 범위와 비교합니다. 생일이 필요한 경계는 추가 확인입니다.'),
           employment_note='취업 상태 제한을 확정하지 않았습니다. 공고의 선정 기준을 확인하세요.',
           rent_note='월세 거주 필수 조건을 확인하지 않았습니다.')
    ]})
    seocho=records['METRO-SEOCHO-EXAM-Q4-2026']
    rule=Rule.model_validate(dict(program_id=seocho['program_id'],sources=seocho['sources'],
        age=dict(kind='BIRTH_RANGE',birth_start='1986-01-01',birth_end='2007-12-31',older_exception=True,note=seocho['age_note']),
        unemployed='PASS',employment_note='미취업 대상이며 단기근로 등 예외는 공고에서 확인하세요.',
        rent_note='월세 거주 필수 여부는 확인되지 않았습니다.'))
    additional_rules=[rule,*[Rule.model_validate(item) for item in municipal['rules']]]
    for pid,age_fields in (
        ('IC-JEMULPO-MOVE-2026',dict(kind='BIRTH_RANGE',birth_start='1986-01-01',birth_end='2007-12-31')),
        ('GW-WONJU-AI-INTERVIEW-2026',dict(kind='CURRENT',minimum=18,maximum=39)),
    ):
        notice=records[pid]
        additional_rules.append(Rule.model_validate(dict(
            program_id=pid,sources=notice['sources'],age={**age_fields,'note':notice['age_note']},
            employment_note='현재 고용 상태만으로 사업의 추가 자격을 확정할 수 없습니다.',
            rent_note='월세 거주 여부만으로 공고의 주거 조건을 확정할 수 없습니다.')))
    rules=Rules.model_validate({**rules.model_dump(mode='json'),'rules':[*rules.rules,*additional_rules]})
    from urllib.parse import urlsplit
    data=catalog.model_dump(mode='json')
    data['programs']=list(records.values())
    data['official_hosts']=sorted(set(data['official_hosts'])|{urlsplit(s['url']).hostname for p in data['programs'] for s in p['sources']})
    # This is a local, reviewed repository snapshot, not an arbitrary user upload.
    return Catalog.model_validate(data),rules,evidence

def current_intake(p,as_of,evidence,review_days=7):
    base=recruitment(p,as_of,review_days)
    if base in ('CLOSED','NO_INTAKE','UPCOMING','REVIEW_REQUIRED'):return base
    e=evidence.get(p.program_id)
    if e and e['explicit_status'].startswith('OPEN_OFFICIAL_LABEL'):
        age=(as_of-date.fromisoformat(e['verified_on'])).days
        if 0<=age<=review_days:
            # On the deadline day the exact hour / remaining seats need rechecking.
            if p.ends_on==as_of.isoformat():return 'WINDOW_GUIDANCE'
            return 'VERIFIED_OPEN'
    return base

def compile_current():
    catalog,rules,evidence=current_inputs()
    public=compile_personal(catalog,rules)
    built=date.fromisoformat(catalog.built_on)
    public['schedules']={(built+timedelta(days=i)).isoformat():[current_intake(p,built+timedelta(days=i),evidence,catalog.review_after_days) for p in catalog.programs] for i in range(366)}
    expansion=read_json(ROOT/'data/support-programs/nationwide-notices-20261101.json')
    municipal=load_municipal_batches()
    alternative=ALTERNATIVE_REGION.union(expansion['alternative_region_ids'],municipal['alternative_region_ids'])
    for values in public['regions'].values():
        for i,p in enumerate(catalog.programs):
            if p.program_id in alternative and values[i]=='FAIL':values[i]='UNKNOWN'
    public['recruitment_evidence']=evidence
    public['scope_note']='지원사업·교육 프로그램·모집 회차 안내. 동일 정책의 다른 분기는 별도 공고이며 새로운 정책 종류가 아닙니다.'
    return public

def index_daily_rows(daily):
    """Keep one copy of each distinct row while preserving each date's lookup."""
    pool, indexes, calendar = [], {}, {}
    for day, row in daily.items():
        key = tuple(row)
        if key not in indexes:
            indexes[key] = len(pool)
            pool.append(row)
        calendar[day] = indexes[key]
    return calendar, pool


def compact_calendar(public):
    result = dict(public)
    result['calendar'], result['schedule_pool'] = index_daily_rows(result.pop('schedules'))
    personal = dict(result['personal'])
    personal['age_calendar'], personal['age_vectors'] = index_daily_rows(personal.pop('age_days'))
    result['personal'] = personal
    return result


if __name__=='__main__':
    out=ROOT/'frontend/src/public-data/current-support.json'
    value=compile_current()
    out.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    compact=out.with_name('current-support-web.json')
    compact.write_text(json.dumps(compact_calendar(value),ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps(dict(programs=len(value['programs']),open=value['schedules'][value['built_on']].count('VERIFIED_OPEN')),ensure_ascii=False))
