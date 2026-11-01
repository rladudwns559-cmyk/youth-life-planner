"""Official discovery snapshots. This is not an approved full eligibility dataset."""
import json
from datetime import date,datetime,timedelta
from pathlib import Path
from typing import Annotated,Literal
from urllib.parse import urlsplit
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator

CATALOG_PATH=Path(__file__).resolve().parents[2]/'data/asset-programs/catalog-20261030.json'
REGIONS=('서울','부산','대구','인천','광주','대전','울산','세종','경기','강원','충북','충남','전북','전남','경북','경남','제주')
Province=Literal['서울','부산','대구','인천','광주','대전','울산','세종','경기','강원','충북','충남','전북','전남','경북','경남','제주']
Text=Annotated[str,Field(strict=True,min_length=1,max_length=2400)]
Money=Annotated[int,Field(strict=True,ge=0,le=1_000_000_000_000)]
HOSTS={'www.korea.kr','m.korea.kr','www.bokjiro.go.kr','account.gfgf.kr','www.gg.go.kr','news.seoul.go.kr','www.seoul.go.kr','young.busan.go.kr','youth.incheon.go.kr','www.modadream.kr','daejeonyouthportal.kr','www.daejeonyouthportal.kr','double.jb2030.or.kr','www.jeonju.go.kr','obank.kbstar.com'}

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True)

def iso_date(value):
    if type(value) is not str or len(value)!=10 or date.fromisoformat(value).isoformat()!=value:raise ValueError('INVALID_ISO_DATE')
    return value

def kst_time(value):
    parsed=datetime.fromisoformat(value)
    if parsed.utcoffset()!=timedelta(hours=9):raise ValueError('KST_OFFSET_REQUIRED')
    return parsed

def official_url(value):
    p=urlsplit(value)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443) or not p.path:raise ValueError('OFFICIAL_SOURCE_REQUIRED')
    return value

class Source(Strict):
    source_id:Text
    url:Text
    title:Text
    published_on:str|None
    verified_on:str
    locator:Text
    capture_sha256:Annotated[str,Field(pattern=r'^[0-9a-f]{64}$')]
    _url=field_validator('url')(official_url)
    _verified=field_validator('verified_on')(iso_date)
    @field_validator('published_on')
    @classmethod
    def published(cls,v):return iso_date(v) if v is not None else None
    @model_validator(mode='after')
    def chronological(self):
        if self.published_on and self.published_on>self.verified_on:raise ValueError('FUTURE_SOURCE')
        return self

class Window(Strict):
    kind:Literal['APPLICATION','SCREENING','ACCOUNT_OPENING']
    label:Text
    starts_at:Text
    ends_at_exclusive:Text
    time_note:Text
    @model_validator(mode='after')
    def chronological(self):
        if kst_time(self.starts_at)>=kst_time(self.ends_at_exclusive):raise ValueError('INVALID_WINDOW')
        return self

class Program(Strict):
    program_id:Text
    edition:Text
    title:Text
    authority:Text
    category:Literal['NATIONAL_SAVINGS','LOCAL_ASSET_BUILDING','HOUSING_SAVINGS']
    regions:tuple[Province,...]
    source_ids:tuple[Text,...]
    schedule_kind:Literal['WINDOW','CONTINUOUS','NO_INTAKE','UNKNOWN']
    windows:tuple[Window,...]
    schedule_note:Text
    age_min:Annotated[int,Field(strict=True,ge=0,le=120)]|None
    age_max:Annotated[int,Field(strict=True,ge=0,le=120)]|None
    age_basis:Literal['CURRENT','EXPLICIT_BIRTH_RANGE','OFFICIAL_REFERENCE_REQUIRED']
    birth_from:str|None
    birth_to:str|None
    military_exception:bool
    age_note:Text
    requires_work:bool
    requires_unhoused:bool
    monthly_minimum:Money|None
    monthly_maximum:Money|None
    payment_step:Annotated[int,Field(strict=True,ge=1)]|None
    term_months:tuple[Annotated[int,Field(strict=True,ge=1,le=120)],...]
    contribution_note:Text
    benefit_summary:Text
    income_note:Text
    remaining_checks:tuple[Text,...]
    data_status:Literal['DRAFT']='DRAFT'
    coverage:Literal['CONDITION_SLICE']='CONDITION_SLICE'
    @model_validator(mode='after')
    def coherent(self):
        if not self.source_ids or len(set(self.source_ids))!=len(self.source_ids):raise ValueError('INVALID_SOURCE_REFS')
        if len(set(self.regions))!=len(self.regions) or len(set(self.term_months))!=len(self.term_months):raise ValueError('DUPLICATES')
        if not self.remaining_checks:raise ValueError('DISCOVERY_MUST_NOT_CLAIM_FULL_COVERAGE')
        if (self.birth_from is None)!=(self.birth_to is None):raise ValueError('INCOMPLETE_BIRTH_RANGE')
        if self.birth_from is not None:
            iso_date(self.birth_from);iso_date(self.birth_to)
            if self.birth_from>self.birth_to:raise ValueError('INVALID_BIRTH_RANGE')
        if self.age_basis=='EXPLICIT_BIRTH_RANGE' and self.birth_from is None:raise ValueError('BIRTH_RANGE_REQUIRED')
        if self.age_basis=='CURRENT' and (self.age_min is None or self.age_max is None):raise ValueError('AGE_REQUIRED')
        if self.age_min is not None and self.age_max is not None and self.age_min>self.age_max:raise ValueError('INVALID_AGE')
        if self.monthly_minimum is not None and self.monthly_maximum is not None and self.monthly_minimum>self.monthly_maximum:raise ValueError('INVALID_CONTRIBUTION')
        applications=[w for w in self.windows if w.kind=='APPLICATION']
        if self.schedule_kind in ('WINDOW','CONTINUOUS') and len(applications)!=1:raise ValueError('ONE_APPLICATION_WINDOW_REQUIRED')
        if self.schedule_kind in ('NO_INTAKE','UNKNOWN') and applications:raise ValueError('UNCONFIRMED_WINDOW_FORBIDDEN')
        return self

class Catalog(Strict):
    schema_version:Literal['asset-discovery-v1']
    dataset_version:Text
    review_after_days:Annotated[int,Field(strict=True,ge=1,le=30)]
    sources:tuple[Source,...]
    programs:tuple[Program,...]
    @model_validator(mode='after')
    def references(self):
        ids={s.source_id for s in self.sources}
        if not ids or len(ids)!=len(self.sources) or not self.programs:raise ValueError('INVALID_CATALOG')
        if len({p.program_id for p in self.programs})!=len(self.programs):raise ValueError('DUPLICATE_PROGRAM')
        if any(not set(p.source_ids)<=ids for p in self.programs):raise ValueError('MISSING_SOURCE')
        return self

def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('DUPLICATE_JSON_KEY')
        result[key]=value
    return result

class CatalogError(ValueError):pass

def load_catalog(path:Path=CATALOG_PATH):
    try:
        raw=json.loads(path.read_bytes(),object_pairs_hook=_unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NON_FINITE')))
        return Catalog.model_validate_json(json.dumps(raw,ensure_ascii=False))
    except (OSError,ValueError,TypeError) as error:raise CatalogError('ASSET_CATALOG_INVALID') from error
