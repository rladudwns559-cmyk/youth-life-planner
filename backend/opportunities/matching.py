"""Deterministic discovery checks; no complete eligibility or support-money approval."""
from datetime import date,datetime,timedelta,timezone
import hashlib,json
from pydantic import field_validator
from .catalog import Strict,Province,Catalog,Program,kst_time,iso_date
from backend.policy_engine.models import UserProfile,Policy,PolicyRule,Field,Operator,EvaluationContext
from backend.policy_engine.evaluator import evaluate_policy
from backend.policy_engine.birth_evaluator import evaluate_birth_date_rule
from backend.policy_engine.specialized_rules.birth_date import BirthDateRule
from backend.policy_engine.facts.birth import BirthFact,BirthSource

class Supplement(Strict):
    province:Province|None=None
    birth_date:str|None=None
    owns_home:bool|None=None
    @field_validator('birth_date')
    @classmethod
    def birth(cls,v):return iso_date(v) if v is not None else None

STATUS_LABEL={'OPEN':'모집 중','UPCOMING':'모집 예정','CLOSED':'신청 마감','NO_INTAKE':'올해 신규모집 없음','UNKNOWN':'일정 확인 필요','REVIEW_REQUIRED':'최신 공고 재확인 필요'}
ALIASES={'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','광주광역시':'광주','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종','경기도':'경기','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남','전북특별자치도':'전북','전라북도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주','안산시':'경기','안산':'경기','수원시':'경기'}

def province_for(value):
    if value is None:return None
    text=value.strip()
    from .catalog import REGIONS
    if text in REGIONS:return text
    if text in ALIASES:return ALIASES[text]
    first=text.split()[0]
    if first in REGIONS:return first
    return ALIASES.get(first)

def program_revision(program:Program):
    # Verification timestamps/HTML hashes and page navigation are not substantive policy changes.
    payload=program.model_dump(mode='json',exclude={'source_ids','data_status','coverage'})
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def intake(program:Program,catalog:Catalog,as_of:datetime):
    if as_of.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
    as_of=as_of.astimezone(timezone(timedelta(hours=9)))
    sources={s.source_id:s for s in catalog.sources}
    days=[(as_of.date()-date.fromisoformat(sources[s].verified_on)).days for s in program.source_ids]
    fresh=all(0<=age<=catalog.review_after_days for age in days)
    if program.schedule_kind=='NO_INTAKE':status='NO_INTAKE'
    elif program.schedule_kind=='UNKNOWN':status='UNKNOWN'
    else:
        window=next(w for w in program.windows if w.kind=='APPLICATION')
        if as_of<kst_time(window.starts_at):status='UPCOMING'
        elif as_of>=kst_time(window.ends_at_exclusive):status='CLOSED'
        else:status='OPEN'
    if not fresh and status in ('OPEN','UPCOMING','UNKNOWN'):status='REVIEW_REQUIRED'
    phases=[w.label for w in program.windows if w.kind!='APPLICATION' and kst_time(w.starts_at)<=as_of<kst_time(w.ends_at_exclusive)]
    return dict(status=status,label=STATUS_LABEL[status],fresh=fresh,phase=' · '.join(phases) or None,
                application=next((w.model_dump(mode='json') for w in program.windows if w.kind=='APPLICATION'),None),
                note=program.schedule_note)

def _atomic(program,field,operator,value,observed,as_of):
    rule=PolicyRule(program.program_id+'-'+field.value,field,operator,value,evidence_refs=program.source_ids)
    policy=Policy(program.program_id,program.title+' 기초 검토',program.edition,rule,False,False,allow_real_data=True)
    profile=UserProfile(**{field.value:observed})
    return evaluate_policy(profile,policy,EvaluationContext(as_of.date(),'asset-discovery-v1')).overall_status.value

def _check(key,label,status,note):return dict(key=key,label=label,status=status,note=note)

def assess(program:Program,catalog:Catalog,profile,extra:Supplement,capacity:int|None,as_of:datetime,goal_months:int|None=None):
    state=intake(program,catalog,as_of)
    sources={s.source_id:s for s in catalog.sources}
    base=dict(program=program.model_dump(mode='json'),sources=[sources[s].model_dump(mode='json') for s in program.source_ids],
              intake=state,notification_key=f'{program.program_id}:{program.edition}',revision=program_revision(program),
              calculation=None,benefit_applied_krw=0,eligibility_scope='PRELIMINARY_DISCOVERY_ONLY')
    if profile is None:return base|dict(assessment=None,bucket='CATALOG',reasons=[])
    region=extra.province or province_for(profile.region)
    checks=[]
    region_status='PASS' if not program.regions else _atomic(program,Field.REGION,Operator.IN,program.regions,region,as_of)
    checks.append(_check('region','현재 관심·거주 지역',region_status,
        '전국 대상 사업입니다.' if not program.regions else '현재 지역을 기준으로 한 목록 필터입니다. 공고 기준일 주민등록·거주기간은 별도 확인합니다.'))
    birth=extra.birth_date
    age_status='UNKNOWN'
    if program.age_basis=='EXPLICIT_BIRTH_RANGE':
        rule=BirthDateRule(program.program_id+'-birth',date.fromisoformat(program.birth_from),date.fromisoformat(program.birth_to),program.source_ids)
        result=evaluate_birth_date_rule(rule,BirthFact(date.fromisoformat(birth),BirthSource.SELF_REPORTED) if birth else None)
        age_status=result.status.value
        if age_status=='FAIL' and program.military_exception and birth<program.birth_from:age_status='UNKNOWN'
    elif program.age_basis=='CURRENT':
        age=profile.age
        if birth:
            birthday=date.fromisoformat(birth);now=as_of.date()
            age=now.year-birthday.year-((now.month,now.day)<(birthday.month,birthday.day))
        lower=_atomic(program,Field.AGE,Operator.GTE,program.age_min,age,as_of)
        upper=_atomic(program,Field.AGE,Operator.LTE,program.age_max,age,as_of)
        age_status='FAIL' if 'FAIL' in (lower,upper) else 'UNKNOWN' if 'UNKNOWN' in (lower,upper) else 'PASS'
        if upper=='FAIL' and program.military_exception:age_status='UNKNOWN'
    checks.append(_check('age','공식 연령 기준',age_status,program.age_note))
    if program.requires_work:
        status=_atomic(program,Field.EMPLOYMENT_STATUS,Operator.EQ,'employed',profile.employment_status,as_of)
        # Current unemployment does not prove absence of earnings/leave/qualifying past employment.
        checks.append(_check('work','현재 근로 정보',status if status=='PASS' else 'UNKNOWN','현재 취업 입력만 참고합니다. 공고 기준일 소득·근로시간·사업·휴직·재직기간은 추가 확인합니다.'))
    if program.requires_unhoused:
        status='UNKNOWN' if extra.owns_home is None else 'FAIL' if extra.owns_home else 'PASS'
        checks.append(_check('home','본인 무주택',status,'본인 주택 소유 여부의 자가 입력입니다. 공식 무주택 확인과 기존 청약계좌 여부는 별도입니다.'))
    min_pay,max_pay=program.monthly_minimum,program.monthly_maximum
    if capacity==0:budget='FAIL'
    elif min_pay is None:budget='UNKNOWN'
    else:budget='PASS' if capacity is not None and capacity>=min_pay else 'FAIL'
    allocation=None
    if budget=='PASS':
        allocation=min(capacity,max_pay) if max_pay is not None else min_pay
        if program.payment_step:allocation-=allocation%program.payment_step
    budget_check=_check('budget','월 납입 여력',budget,
        '현재 저축 여력과 최소 납입액을 비교합니다. 월 한도보다 많은 여력은 이 상품에 모두 납입하지 않습니다.')
    # Remaining conditions are mandatory UNKNOWN. A discovery slice can never become full PASS.
    remaining=[_check(f'confirmation-{i}','추가 확인','UNKNOWN',text) for i,text in enumerate(program.remaining_checks)]
    failed=any(c['status']=='FAIL' for c in checks)
    overall='FAIL' if failed else 'UNKNOWN'
    if failed:bucket='NOT_MATCHED'
    elif budget=='FAIL':bucket='BUDGET_SHORTFALL'
    elif state['status']=='OPEN':bucket='CURRENT_CANDIDATE'
    else:bucket='WATCHLIST'
    reasons=[]
    if region_status=='PASS':reasons.append('전국 대상이라 지역 제한 없이 살펴볼 수 있어요.' if not program.regions else '입력한 현재 지역과 사업 대상 지역이 맞아요.')
    if age_status=='PASS':reasons.append('입력한 정보가 확인한 연령 범위에 들어가요.')
    if budget=='PASS':reasons.append(f'최소 월 {min_pay:,}원 납입을 현재 저축 여력으로 검토할 수 있어요.')
    if state['status']!='OPEN':reasons.append('현재 신규 신청 후보와 구분해 다음 모집·공식 일정 확인용으로 보여드려요.')
    return base|dict(bucket=bucket,reasons=reasons,assessment=dict(status=overall,display_status='현재 조건과 맞지 않음' if failed else '추가 확인 필요',
        checks=checks,remaining_checks=remaining,budget=budget_check,allocation_krw=allocation,
        unallocated_capacity_krw=capacity-allocation if allocation is not None else None,
        goal_matches=None if goal_months is None or not program.term_months else goal_months in program.term_months,
        income_note=program.income_note))

def discover(catalog:Catalog,as_of:datetime,profile=None,extra:Supplement|None=None,capacity:int|None=None,goal_months:int|None=None):
    if type(as_of) is not datetime or as_of.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
    as_of=as_of.astimezone(timezone(timedelta(hours=9)))
    extra=extra or Supplement()
    if extra.birth_date:
        birth=date.fromisoformat(extra.birth_date)
        if birth>as_of.date() or as_of.date().year-birth.year>120:raise ValueError('INVALID_BIRTH_CONTEXT')
    if profile is not None and (type(capacity) is not int or capacity<0):raise ValueError('CAPACITY_REQUIRED')
    rows=[assess(p,catalog,profile,extra,capacity,as_of,goal_months) for p in catalog.programs]
    priority={'CURRENT_CANDIDATE':0,'WATCHLIST':1,'BUDGET_SHORTFALL':2,'NOT_MATCHED':3,'CATALOG':0}
    status_order={'OPEN':0,'UPCOMING':1,'UNKNOWN':2,'REVIEW_REQUIRED':3,'CLOSED':4,'NO_INTAKE':5}
    rows.sort(key=lambda r:(priority[r['bucket']],status_order[r['intake']['status']],r['program']['title']))
    notes=[]
    if profile is not None and extra.birth_date and profile.age is not None:
        b=date.fromisoformat(extra.birth_date);d=as_of.date()
        if profile.age!=d.year-b.year-((d.month,d.day)<(b.month,b.day)):notes.append('현재 만 나이와 생년월일이 다릅니다. 생년월일 기준으로 연령을 검토했습니다.')
    return dict(schema_version='asset-discovery-response-v1',dataset_version=catalog.dataset_version,evaluated_at=as_of.isoformat(),
        review_after_days=catalog.review_after_days,source_mode='VERIFIED_SNAPSHOT',program_count=len(rows),
        counts={key:sum(r['intake']['status']==key for r in rows) for key in STATUS_LABEL},
        recommendation_counts={key:sum(r['bucket']==key for r in rows) for key in priority},
        personalized=profile is not None,province=extra.province or province_for(profile.region) if profile else None,
        monthly_capacity=capacity if profile is not None else None,programs=rows,input_notes=notes,
        policy_benefit_applied_krw=0,actual_product_calculation_count=0,
        notifications=dict(change_contract='asset-program-events-v1',delivery_enabled=False,subscriptions_stored=False),
        disclaimer='공식 공고를 바탕으로 한 기초 추천입니다. 모든 자격조건을 확인한 결과가 아니며 가입·선정·지원금 수령을 확정하지 않습니다. 생활비 소득을 공식 소득기준으로 환산하지 않습니다.')
