from datetime import date, timedelta
from itertools import product
import json
import pytest
from pydantic import ValidationError
from backend.opportunities.personal_discovery import (
    Profile, AgeRule, Rule, Rules, age_match, possible_births,
    personal_conditions, summarize, compile_personal, load_inputs, ROOT,
)

DAY=date(2026,11,1)
@pytest.fixture(scope='module')
def inputs():return load_inputs()
@pytest.fixture(scope='module')
def rules(inputs):return {r.program_id:r for r in inputs[1].rules}

@pytest.mark.parametrize('age,expected',[(17,'FAIL'),(18,'UNKNOWN'),(19,'PASS'),(25,'PASS'),(34,'PASS'),(35,'UNKNOWN'),(36,'FAIL')])
def test_current_age_never_substitutes_for_official_birth_range(rules,age,expected):
    assert age_match(rules['KR-YOUTH-RENT-2026'].age,age,DAY)==expected

@pytest.mark.parametrize('age,expected',[(23,'FAIL'),(24,'UNKNOWN'),(25,'UNKNOWN'),(26,'FAIL')])
def test_q3_exact_birth_window_requires_birthday_at_boundary(rules,age,expected):
    assert age_match(rules['ANSAN-YOUTH-BASIC-INCOME-2026-Q3'].age,age,DAY)==expected

@pytest.mark.parametrize('age,expected',[(18,'FAIL'),(19,'PASS'),(34,'PASS'),(35,'UNKNOWN'),(40,'UNKNOWN')])
def test_military_exception_not_inferred_or_excluded(rules,age,expected):
    assert age_match(rules['KR-YOUTH-HOUSING'].age,age,DAY)==expected

def test_conflicting_age_statements_and_unknown_reference_stay_unknown(rules):
    for pid in ('ANSAN-YOUTH-EXAM-FEE-2026','ANSAN-INTERVIEW-SUIT-2026','KR-YOUTH-TOMORROW'):
        for age in (18,25,39,40):assert age_match(rules[pid].age,age,DAY)=='UNKNOWN'

def test_leap_year_birth_interval_is_sound():
    assert possible_births(21,date(2025,2,28))==(date(2003,3,1),date(2004,2,28))
    assert possible_births(21,date(2025,3,1))==(date(2003,3,2),date(2004,3,1))
    assert possible_births(20,date(2024,2,29))==(date(2003,3,1),date(2004,2,29))

def test_age_comparison_sound_against_independent_day_by_day_births(rules):
    rule=rules['KR-YOUTH-RENT-2026'].age
    for age in (18,19,25,35,36):
        low,high=possible_births(age,DAY)
        answers=[]
        for i in range((high-low).days+1):
            dob=low+timedelta(days=i)
            assert DAY.year-dob.year-((DAY.month,DAY.day)<(dob.month,dob.day))==age
            answers.append(date(1991,1,1)<=dob<=date(2007,12,31))
        expected='PASS' if all(answers) else 'FAIL' if not any(answers) else 'UNKNOWN'
        assert age_match(rule,age,DAY)==expected

@pytest.mark.parametrize('employment',['employed','unemployed','self_employed'])
def test_exam_and_prior_year_income_do_not_use_current_employment_as_proof(rules,employment):
    for pid in ('ANSAN-YOUTH-EXAM-FEE-2026','KR-YOUTH-FUTURE','KR-YOUTH-TOMORROW'):
        assert personal_conditions(rules[pid],Profile(employment=employment),DAY)['employment']=='UNKNOWN'

def test_unemployed_changes_worker_candidate_not_final_eligibility(rules):
    rule=rules['GG-YOUTH-WELFARE-POINTS-2026']
    assert personal_conditions(rule,Profile(employment='employed'),DAY)['employment']=='PASS'
    assert personal_conditions(rule,Profile(employment='unemployed'),DAY)['employment']=='FAIL'
    assert personal_conditions(rule,Profile(employment='self_employed'),DAY)['employment']=='UNKNOWN'
    assert summarize(('PASS','PASS','FAIL','UNKNOWN'))['eligibility']=='UNKNOWN'

def test_part_time_exception_and_current_employment_not_required(rules):
    assert personal_conditions(rules['SEOUL-YOUTH-ALLOWANCE-2026'],Profile(employment='employed'),DAY)['employment']=='UNKNOWN'
    assert personal_conditions(rules['SEOUL-YOUTH-ALLOWANCE-2026'],Profile(employment='unemployed'),DAY)['employment']=='PASS'
    for e in ('employed','unemployed','self_employed'):
        assert personal_conditions(rules['KR-YOUTH-HOUSING'],Profile(employment=e),DAY)['employment']=='PASS'

def test_rent_no_does_not_remove_jeonse_moving_support(rules):
    assert personal_conditions(rules['KR-YOUTH-RENT-2026'],Profile(rent='no'),DAY)['rent']=='FAIL'
    assert personal_conditions(rules['KR-YOUTH-RENT-2026'],Profile(rent='yes'),DAY)['rent']=='PASS'
    assert personal_conditions(rules['ANSAN-YOUTH-MOVE-FEE-2026'],Profile(rent='no'),DAY)['rent']=='UNKNOWN'

def test_missing_input_and_unstructured_program_never_pass(rules):
    assert set(personal_conditions(rules['KR-YOUTH-RENT-2026'],Profile(),DAY).values())=={'UNKNOWN'}
    assert set(personal_conditions(None,Profile(age=25,employment='employed',rent='yes'),DAY).values())=={'UNKNOWN'}

@pytest.mark.parametrize('data',[{'age':True},{'age':'25'},{'age':25.5},{'age':-1},{'age':121},{'employment':'student'},{'rent':True},{'income':1000000}])
def test_invalid_or_unrequested_profile_fields_rejected(data):
    with pytest.raises(ValidationError):Profile(**data)

@pytest.mark.parametrize('data',[
    {'kind':'BIRTH_RANGE','birth_start':'2000-01-01'},
    {'kind':'BIRTH_RANGE','birth_start':'2000-01-02','birth_end':'2000-01-01'},
    {'kind':'CURRENT','minimum':30,'maximum':20},
    {'kind':'CURRENT','minimum':19,'maximum':39,'birth_start':'2000-01-01'},
    {'kind':'UNKNOWN','minimum':19},
])
def test_ambiguous_rules_are_rejected(data):
    with pytest.raises(ValidationError):AgeRule(note='synthetic validation',**data)

def test_duplicated_rules_rejected(inputs):
    d=inputs[1].model_dump(mode='json');d['rules'].append(d['rules'][0])
    with pytest.raises(ValidationError):Rules.model_validate(d)

def test_new_catalog_retains_original_38_and_adds_only_three_reviewed_programs(inputs):
    original=json.loads((ROOT/'data/support-programs/regional-20261101.json').read_text(encoding='utf-8'))
    catalog,_=inputs
    assert len(catalog.programs)==41
    assert [p.model_dump(mode='json') for p in catalog.programs[:38]]==__import__('backend.opportunities.regional_discovery',fromlist=['load_catalog']).load_catalog().model_dump(mode='json')['programs']
    assert catalog.programs[38].program_id=='SEOUL-YOUTH-CULTURE-PASS-2026'
    assert all(p.eligibility=='UNKNOWN' and p.benefit_applied_krw==0 for p in catalog.programs)
    assert all(p.program_id!='GG-ANSEONG-YOUTH-INTERVIEW-SUIT-2026' for p in catalog.programs)

def test_public_table_reproducibility_and_cross_input_examples(inputs):
    public=compile_personal(*inputs)
    saved=json.loads((ROOT/'frontend/src/public-data/personal-programs.json').read_text(encoding='utf-8'))
    assert public==saved
    assert len(public['personal']['age_days'])==366
    c,rs=inputs;rules={r.program_id:r for r in rs.rules}
    decode={'P':'PASS','F':'FAIL','U':'UNKNOWN'}
    for day in (DAY,date(2027,1,1),date(2027,3,1),date(2027,11,1)):
        for i,p in enumerate(c.programs):
            r=rules.get(p.program_id)
            for age in (0,18,19,24,25,34,35,39,40,120):
                idx=public['personal']['age_days'][day.isoformat()][i]
                assert decode[public['personal']['age_pool'][idx][age]]==age_match(r.age if r else None,age,day)
    for combo in product(('PASS','FAIL','UNKNOWN'),repeat=4):
        result=public['personal']['combinations']['|'.join(combo)]
        assert result['eligibility']=='UNKNOWN' and result['benefit_applied_krw']==0
        assert result['candidate_status']==('DIFFERENT' if 'FAIL' in combo else 'REVIEW')
    # A year's age arithmetic must never extend the one-week recruitment evidence.
    assert public['valid_until']=='2026-11-08'
    assert '2026-11-09' not in public['schedules']
