"""Regional discovery only. No complete eligibility approval or financial arithmetic."""
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlsplit
import json
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field as F,field_validator,model_validator
from backend.opportunities.catalog import REGIONS
from backend.policy_engine.models import UserProfile,Policy,PolicyRule,Field,Operator,EvaluationContext
from backend.policy_engine.evaluator import evaluate_policy

ROOT=Path(__file__).resolve().parents[2]
PATH=ROOT/'data/support-programs/regional-20261101.json'

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True)

def iso(v):
    if type(v) is not str or date.fromisoformat(v).isoformat()!=v:raise ValueError('INVALID_DATE')
    return v

class Source(Strict):
    url:str
    title:str
    basis_date:str|None
    verified_on:str
    evidence:Literal['OFFICIAL_PAGE','OFFICIAL_NOTICE','OFFICIAL_INDEXED_PAGE','PREVIOUS_VERIFIED_SNAPSHOT']
    locator:str
    @field_validator('url')
    @classmethod
    def safe_url(cls,v):
        u=urlsplit(v)
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):raise ValueError('UNSAFE_SOURCE')
        return v
    _date=field_validator('verified_on')(iso)
    @field_validator('basis_date')
    @classmethod
    def basis(cls,v):return None if v is None else iso(v)
    @model_validator(mode='after')
    def chronological(self):
        if self.basis_date and self.basis_date>self.verified_on:raise ValueError('FUTURE_SOURCE')
        if not self.title.strip() or not self.locator.strip():raise ValueError('SOURCE_LOCATION_REQUIRED')
        return self

class Program(Strict):
    program_id:str
    title:str
    authority:str
    edition:str
    category:Literal['HOUSING','EMPLOYMENT','EDUCATION','LIVING','CULTURE','ASSET']
    provinces:list[str]
    city:str|None
    benefit_summary:str
    age_note:str
    income_note:str
    required_checks:list[str]
    schedule_note:str
    starts_on:str|None
    ends_on:str|None
    intake_mode:Literal['WINDOW','CONTINUOUS','UNKNOWN','CLOSED','NO_INTAKE']
    sources:list[Source]
    aliases:list[str]=[]
    data_status:Literal['DRAFT']='DRAFT'
    coverage:Literal['CONDITION_SLICE']='CONDITION_SLICE'
    eligibility:Literal['UNKNOWN']='UNKNOWN'
    benefit_applied_krw:Literal[0]=0
    @field_validator('starts_on','ends_on')
    @classmethod
    def dates(cls,v):return None if v is None else iso(v)
    @model_validator(mode='after')
    def valid(self):
        if not self.program_id.strip() or not self.title.strip() or not self.sources or not self.required_checks:raise ValueError('REQUIRED_EVIDENCE')
        if len(set(self.provinces))!=len(self.provinces) or not set(self.provinces)<=set(REGIONS):raise ValueError('INVALID_PROVINCE')
        if self.city is not None and (not self.city.strip() or len(self.provinces)!=1):raise ValueError('CITY_REQUIRES_ONE_PROVINCE')
        if self.intake_mode=='WINDOW' and (not self.starts_on or not self.ends_on):raise ValueError('WINDOW_REQUIRED')
        if self.starts_on and self.ends_on and self.starts_on>self.ends_on:raise ValueError('INVALID_WINDOW')
        return self

class Catalog(Strict):
    schema_version:Literal['regional-discovery-v1']
    built_on:str
    review_after_days:int=7
    programs:list[Program]
    official_hosts:list[str]
    _date=field_validator('built_on')(iso)
    @model_validator(mode='after')
    def valid(self):
        if not self.programs or len({p.program_id for p in self.programs})!=len(self.programs):raise ValueError('DUPLICATE_PROGRAM')
        if type(self.review_after_days) is not int or not 1<=self.review_after_days<=30:raise ValueError('INVALID_REVIEW_WINDOW')
        hosts={urlsplit(s.url).hostname for p in self.programs for s in p.sources}
        if not hosts<=set(self.official_hosts):raise ValueError('UNAPPROVED_HOST')
        return self

def load_catalog(path=PATH):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('DUPLICATE_KEY')
            d[k]=v
        return d
    return Catalog.model_validate(json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique))

def atomic(pid,actual,expected,as_of,refs):
    rule=PolicyRule(pid+'-discovery-region',Field.REGION,Operator.IN,tuple(expected),evidence_refs=refs)
    policy=Policy(pid,'현재 관심 지역 목록 비교','regional-discovery-v1',rule,False,False,allow_real_data=True)
    return evaluate_policy(UserProfile(region=actual),policy,EvaluationContext(as_of,'regional-discovery-v1')).overall_status.value

def region_match(p,province,city,as_of):
    if province is not None and province not in REGIONS:raise ValueError('INVALID_PROVINCE')
    if city is not None and province is None:raise ValueError('CITY_REQUIRES_PROVINCE')
    if not p.provinces:return 'PASS'
    refs=tuple(s.url for s in p.sources)
    province_result=atomic(p.program_id,province,p.provinces,as_of,refs)
    if province_result=='FAIL' or p.city is None:return province_result
    city_result=atomic(p.program_id+'-city',city,[p.city],as_of,refs)
    return 'FAIL' if 'FAIL' in (province_result,city_result) else 'UNKNOWN' if 'UNKNOWN' in (province_result,city_result) else 'PASS'

def recruitment(p,as_of,review_days=7):
    # Negative/terminal official notices dominate old advertised annual dates.
    if p.intake_mode in ('CLOSED','NO_INTAKE'):return p.intake_mode
    if p.ends_on and as_of>date.fromisoformat(p.ends_on):return 'CLOSED'
    fresh=all(0<=(as_of-date.fromisoformat(s.verified_on)).days<=review_days for s in p.sources)
    if not fresh:return 'REVIEW_REQUIRED'
    if p.intake_mode=='UNKNOWN':return 'UNKNOWN'
    if p.starts_on and as_of<date.fromisoformat(p.starts_on):return 'UPCOMING'
    if p.intake_mode=='CONTINUOUS':return 'CONTINUOUS_GUIDANCE'
    return 'WINDOW_GUIDANCE'

def evaluate(p,province,city,as_of,review_days=7):
    region=region_match(p,province,city,as_of)
    return dict(region=region,overall='FAIL' if region=='FAIL' else 'UNKNOWN',recruitment=recruitment(p,as_of,review_days),benefit_applied_krw=0)

def compile_public(c):
    built=date.fromisoformat(c.built_on)
    city_map={r:sorted({p.city for p in c.programs if r in p.provinces and p.city}) for r in REGIONS}
    keys={'*':(None,None)}
    for r in REGIONS:
        keys[r]=(r,None)
        for city in city_map[r]+['__OTHER__']:keys[r+'|'+city]=(r,city)
    return dict(schema_version='regional-public-v1',built_on=c.built_on,valid_until=(built+timedelta(days=c.review_after_days)).isoformat(),provinces=list(REGIONS),cities=city_map,
        programs=[p.model_dump(mode='json') for p in c.programs],
        regions={k:[region_match(p,*v,built) for p in c.programs] for k,v in keys.items()},
        schedules={(built+timedelta(days=i)).isoformat():[recruitment(p,built+timedelta(days=i),c.review_after_days) for p in c.programs] for i in range(c.review_after_days+1)})
