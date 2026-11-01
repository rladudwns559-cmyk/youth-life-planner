"""Evidence-bound candidate discovery; never full eligibility or benefit approval.

Only Python computes comparisons. Public clients select precomputed, dated rows.
Current coarse work/housing facts describe relevance, not historical facts.
"""
from datetime import date, timedelta
from itertools import product
from pathlib import Path
import json
from typing import Literal
from pydantic import Field, field_validator, model_validator
from backend.opportunities.regional_discovery import Strict, Source, Catalog, load_catalog, compile_public, iso, ROOT

Status = Literal['PASS', 'FAIL', 'UNKNOWN']
Employment = Literal['employed', 'unemployed', 'self_employed', 'unknown']
STATES = ('PASS', 'FAIL', 'UNKNOWN')
EMPLOYMENTS = ('employed', 'unemployed', 'self_employed', 'unknown')
CODES = {'PASS': 'P', 'FAIL': 'F', 'UNKNOWN': 'U'}
RULE_PATH = ROOT / 'data/support-programs/personal-rules-20261101.json'
EXTRA_PATH = ROOT / 'data/support-programs/additional-20261101.json'


class Profile(Strict):
    age: int | None = Field(default=None, ge=0, le=120)
    employment: Employment = 'unknown'
    rent: Literal['yes', 'no', 'unknown'] = 'unknown'


class AgeRule(Strict):
    kind: Literal['UNKNOWN', 'BIRTH_RANGE', 'CURRENT'] = 'UNKNOWN'
    birth_start: str | None = None
    birth_end: str | None = None
    minimum: int | None = Field(default=None, ge=0, le=120)
    maximum: int | None = Field(default=None, ge=0, le=120)
    older_exception: bool = False
    note: str

    @field_validator('birth_start', 'birth_end')
    @classmethod
    def dates(cls, v):
        return None if v is None else iso(v)

    @model_validator(mode='after')
    def coherent(self):
        if not self.note.strip():
            raise ValueError('AGE_NOTE_REQUIRED')
        if self.kind == 'BIRTH_RANGE':
            if not self.birth_start or not self.birth_end or self.birth_start > self.birth_end:
                raise ValueError('BIRTH_RANGE_REQUIRED')
            if self.minimum is not None or self.maximum is not None:
                raise ValueError('AMBIGUOUS_AGE_BASIS')
        elif self.birth_start is not None or self.birth_end is not None:
            raise ValueError('UNUSED_BIRTH_RANGE')
        if self.kind == 'CURRENT':
            if self.minimum is None or self.maximum is None or self.minimum > self.maximum:
                raise ValueError('CURRENT_AGE_RANGE_REQUIRED')
        elif self.minimum is not None or self.maximum is not None:
            raise ValueError('UNUSED_AGE_RANGE')
        return self


class Rule(Strict):
    program_id: str
    sources: list[Source]
    age: AgeRule
    employed: Status = 'UNKNOWN'
    unemployed: Status = 'UNKNOWN'
    self_employed: Status = 'UNKNOWN'
    employment_note: str
    rent_required: bool = False
    rent_note: str

    @model_validator(mode='after')
    def evidence(self):
        if not self.program_id.strip() or not self.sources or not self.employment_note.strip() or not self.rent_note.strip():
            raise ValueError('RULE_EVIDENCE_REQUIRED')
        if any(s.evidence == 'OFFICIAL_INDEXED_PAGE' for s in self.sources):
            raise ValueError('DIRECT_EVIDENCE_REQUIRED_FOR_MATCHING')
        return self


class Rules(Strict):
    schema_version: Literal['personal-discovery-rules-v1']
    built_on: str
    rules: list[Rule]
    _date = field_validator('built_on')(iso)

    @model_validator(mode='after')
    def unique(self):
        if len({r.program_id for r in self.rules}) != len(self.rules):
            raise ValueError('DUPLICATE_RULE')
        return self


def read_json(path):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError('DUPLICATE_KEY')
            out[k] = v
        return out
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def load_inputs():
    original = load_catalog().model_dump(mode='json')
    extra = Catalog.model_validate(read_json(EXTRA_PATH))
    original['programs'].extend(p.model_dump(mode='json') for p in extra.programs)
    original['official_hosts'] = sorted(set(original['official_hosts'] + extra.official_hosts))
    catalog = Catalog.model_validate(original)
    rules = Rules.model_validate(read_json(RULE_PATH))
    ids = {p.program_id for p in catalog.programs}
    if not {r.program_id for r in rules.rules} <= ids:
        raise ValueError('RULE_PROGRAM_NOT_FOUND')
    from urllib.parse import urlsplit
    allowed = set(catalog.official_hosts)
    if any(urlsplit(s.url).hostname not in allowed for r in rules.rules for s in r.sources):
        raise ValueError('UNAPPROVED_RULE_SOURCE_HOST')
    return catalog, rules


def shift_year(day, years):
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        # Gregorian Feb 29; normal age convention considers that birthday Mar 1
        # in a non-leap year. The +one-day lower bound preserves this convention.
        return day.replace(year=day.year + years, day=28)


def possible_births(age, as_of):
    Profile(age=age)
    if age is None or type(as_of) is not date:
        raise ValueError('AGE_AND_DATE_REQUIRED')
    return shift_year(as_of, -age-1) + timedelta(days=1), shift_year(as_of, -age)


def age_match(rule, age, as_of):
    Profile(age=age)
    if type(as_of) is not date:
        raise ValueError('DATE_REQUIRED')
    if rule is None or age is None or rule.kind == 'UNKNOWN':
        return 'UNKNOWN'
    if rule.kind == 'CURRENT':
        if rule.minimum <= age <= rule.maximum:
            return 'PASS'
        return 'UNKNOWN' if age > rule.maximum and rule.older_exception else 'FAIL'
    low, high = possible_births(age, as_of)
    start, end = date.fromisoformat(rule.birth_start), date.fromisoformat(rule.birth_end)
    if low >= start and high <= end:
        return 'PASS'
    if low > end:
        return 'FAIL'
    if high < start:
        return 'UNKNOWN' if rule.older_exception else 'FAIL'
    return 'UNKNOWN'


def personal_conditions(rule, profile, as_of):
    if type(profile) is not Profile:
        raise ValueError('VALIDATED_PROFILE_REQUIRED')
    employment = 'UNKNOWN' if rule is None or profile.employment == 'unknown' else getattr(rule, profile.employment)
    rent = 'UNKNOWN' if rule is None or not rule.rent_required or profile.rent == 'unknown' else ('PASS' if profile.rent == 'yes' else 'FAIL')
    return dict(age=age_match(rule.age if rule else None, profile.age, as_of), employment=employment, rent=rent)


def summarize(statuses):
    if len(statuses) != 4 or any(s not in STATES for s in statuses):
        raise ValueError('FOUR_VALID_CONDITIONS_REQUIRED')
    return dict(candidate_status='DIFFERENT' if 'FAIL' in statuses else 'REVIEW', matched_count=statuses.count('PASS'),
                eligibility='UNKNOWN', benefit_applied_krw=0)


def compile_personal(catalog, rules):
    public = compile_public(catalog)
    by_id = {r.program_id: r for r in rules.rules}
    # One year of dated age lookups, interned into a small shared pool. This is
    # date computation coverage, NOT a fresh official-source check or new intake.
    built = date.fromisoformat(rules.built_on)
    pool, pool_ids, days = [], {}, {}
    for offset in range(366):
        day = built + timedelta(days=offset)
        indices = []
        for p in catalog.programs:
            r = by_id.get(p.program_id)
            row = ''.join(CODES[age_match(r.age if r else None, age, day)] for age in range(121))
            if row not in pool_ids:
                pool_ids[row] = len(pool)
                pool.append(row)
            indices.append(pool_ids[row])
        days[day.isoformat()] = indices
    public['personal'] = dict(
        schema_version='personal-discovery-public-v1', built_on=rules.built_on,
        age_valid_until=(built + timedelta(days=365)).isoformat(), age_pool=pool, age_days=days,
        employment={e: [personal_conditions(by_id.get(p.program_id), Profile(employment=e), built)['employment'] for p in catalog.programs] for e in EMPLOYMENTS},
        rent={v: [personal_conditions(by_id.get(p.program_id), Profile(rent=v), built)['rent'] for p in catalog.programs] for v in ('yes', 'no', 'unknown')},
        combinations={'|'.join(v): summarize(v) for v in product(STATES, repeat=4)},
        rules=[by_id[p.program_id].model_dump(mode='json') if p.program_id in by_id else None for p in catalog.programs],
    )
    return public


if __name__ == '__main__':
    c, r = load_inputs()
    out = ROOT / 'frontend/src/public-data/personal-programs.json'
    out.write_text(json.dumps(compile_personal(c, r), ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
    print(json.dumps(dict(programs=len(c.programs), structured_programs=len(r.rules), bytes=out.stat().st_size)))
