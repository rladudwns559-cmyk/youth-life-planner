"""모델/Provider 없이 후보 의미·정확 일치·서버 원본 불변을 검증한다."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from itertools import product
import copy
import json
from pathlib import Path
import socket
import unicodedata
import warnings

import pytest

from backend.explanation import narrative_catalog as catalog, narrative_contract as v1, service as legacy
from backend.explanation.contracts import ExplanationFacts, ExplanationDocument
from backend.explanation.facts import build_facts, deterministic_document
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from tools.evaluate_explanation_scenarios import cases

ROOT = Path(__file__).resolve().parents[1]
HISTORY = json.loads((ROOT/'docs/evidence/m3_8b_actual_evaluation.json').read_text(encoding='utf-8'))['actual_fixed30']['results']


def bundle(case=None, count=3):
    case = case or cases()[0]
    comparison = compare_scenarios(ComparisonInput(before=case['before'], after=case['after']))
    obj = build_facts(comparison).model_dump()
    obj['policy_facts'] = obj['policy_facts'][:count]
    ids = {p['policy_id'] for p in obj['policy_facts']}
    for key in ('unknown_information', 'next_actions'):obj[key] = [r for r in obj[key] if r['policy_id'] in ids]
    facts = ExplanationFacts.model_validate(obj)
    return facts, deterministic_document(comparison, facts)


def edited(facts, document, edit):
    obj=facts.model_dump();edit(obj);facts=ExplanationFacts.model_validate(obj)
    doc=document.model_dump()
    doc.update(changed_facts=obj['money_facts'],policy_explanations=obj['policy_facts'],unknown_information=obj['unknown_information'],next_actions=obj['next_actions'])
    return facts,ExplanationDocument.model_validate(doc)


def selection(prepared, variant=0):
    return dict(summary=prepared.summary_options[variant],policy_texts={p.slot:p.texts[variant] for p in prepared.policy_options})


def wire(obj):return json.dumps(obj,ensure_ascii=False)


def unchanged(actual, expected):
    assert actual.changed_facts==expected.changed_facts
    assert actual.unknown_information==expected.unknown_information
    assert actual.next_actions==expected.next_actions
    assert [p.model_dump(exclude={'text'}) for p in actual.policy_explanations]==[p.model_dump(exclude={'text'}) for p in expected.policy_explanations]


@pytest.mark.parametrize('case',cases(),ids=lambda c:c['case_id'])
def test_fixed30_every_candidate_combination_preserves_python_and_request_sources(case):
    facts,doc=bundle(case);before=(facts.model_dump_json(),doc.model_dump_json())
    prepared=catalog.prepare_catalog(facts,doc)
    sets=(prepared.summary_options,)+tuple(p.texts for p in prepared.policy_options)
    for combo in product(*sets):
        obj=dict(summary=combo[0],policy_texts={p.slot:t for p,t in zip(prepared.policy_options,combo[1:],strict=True)})
        result=catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(obj),prepared))
        unchanged(result,doc)
        assert result.summary==obj['summary']
        assert [p.text for p in result.policy_explanations]==list(obj['policy_texts'].values())
    result=catalog.evaluate_synthetic_catalog(facts,doc,wire(selection(prepared)))
    assert not result.fallback and result.validation_passed
    assert result.explanation_source=='validated_test_double' and not result.ai_executed and not result.ai_success
    assert before==(facts.model_dump_json(),doc.model_dump_json())


@pytest.mark.parametrize('row',HISTORY,ids=lambda r:r['case_id'])
def test_real_m38b_outputs_replayed_offline_are_not_accepted_by_new_catalog(row):
    case=next(c for c in cases() if c['case_id']==row['case_id']);facts,doc=bundle(case)
    result=catalog.evaluate_synthetic_catalog(facts,doc,row['actual_model_output'])
    assert result.fallback and result.document==doc and not result.ai_executed
    if row['wire_validation']=='PASS':
        assert result.diagnostic_code=='TEXT_NOT_IN_REQUEST_CATALOG'
        assert result.fallback_reason=='UNSUPPORTED_NARRATIVE'
    else:assert result.diagnostic_code=='FORBIDDEN_NARRATIVE'


@pytest.mark.parametrize('case_id,family,fragment',[('EX01','S5','입력'),('EX02','S4','취업상태'),('EX06','S4','취업상태'),
 ('EX07','S2','월소득은 늘었'),('EX08','S2','월소득은 줄었'),('EX09','S2','월세는 늘었'),
 ('EX10','S2','월세는 줄었고, 월 여유자금은 늘었어요.'),('EX11','S1','저축 상한'),('EX12','S2','월 여유자금은 줄었'),
 ('EX13','S4','만 나이'),('EX14','S4','거주 지역'),('EX15','S4','재학 상태'),('EX16','S1','저축 상한'),('EX17','S1','저축 상한')])
def test_summary_known_inputs_have_correct_scope_and_direction(case_id,family,fragment):
    facts,doc=bundle(next(c for c in cases() if c['case_id']==case_id));prepared=catalog.prepare_catalog(facts,doc)
    assert prepared.summary_family==family and fragment in prepared.summary_options[0]
    if case_id=='EX10':assert all('소득' not in s and '수입' not in s for s in prepared.summary_options)
    if case_id=='EX07':assert all('정책' not in s for s in prepared.summary_options)


@pytest.mark.parametrize('before,after',product((None,0,300000),repeat=2))
def test_cap_none_zero_positive_are_distinct_without_invented_numeric_comparison(before,after):
    case=copy.deepcopy(cases()[0]);case['before']['user_savings_capacity']=before;case['after']['user_savings_capacity']=after
    facts,doc=bundle(case);prepared=catalog.prepare_catalog(facts,doc)
    assert prepared.summary_family==('S1' if before!=after else 'S5')
    assert all('늘' not in t and '줄' not in t for t in prepared.summary_options)
    cap=next(m for m in facts.money_facts if m.field=='user_savings_capacity')
    assert cap.delta is None if before is None or after is None else cap.delta==after-before


@pytest.mark.parametrize('field,after,phrase',[('monthly_fixed_expenses',250000,'고정지출은 늘었'),('other_monthly_expenses',100000,'기타지출은 줄었')])
def test_named_expense_does_not_turn_into_income(field,after,phrase):
    case=copy.deepcopy(cases()[0]);case['after'][field]=after
    facts,doc=bundle(case);prepared=catalog.prepare_catalog(facts,doc)
    assert phrase in prepared.summary_options[0]
    assert all('소득' not in s for s in prepared.summary_options)


def test_multiple_budget_changes_and_input_label_priority():
    case=copy.deepcopy(cases()[0]);case['after'].update(monthly_income=1800000,monthly_rent=550000)
    facts,doc=bundle(case);prepared=catalog.prepare_catalog(facts,doc)
    assert prepared.summary_family=='S3' and '여러 항목' in prepared.summary_options[0]
    case=copy.deepcopy(cases()[0]);case['after'].update(age=None,region=None,employment_status=None)
    facts,doc=bundle(case);prepared=catalog.prepare_catalog(facts,doc)
    assert prepared.summary_family=='S4' and all(s.startswith('만 나이') for s in prepared.summary_options)


@pytest.mark.parametrize('income',[0,100000,1000000])
def test_deficit_and_zero_keep_original_numbers(income):
    case=copy.deepcopy(cases()[0]);case['after']['monthly_income']=income
    facts,doc=bundle(case);prepared=catalog.prepare_catalog(facts,doc)
    result=catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(selection(prepared)),prepared))
    unchanged(result,doc)
    assert next(m.after for m in result.changed_facts if m.field=='disposable_after_policy')==income-1000000


@pytest.mark.parametrize('before,after',product(('PASS','FAIL','UNKNOWN'),repeat=2))
def test_all_nine_policy_pairs_keep_aggregate_state_and_unknown_scope(before,after):
    facts,doc=bundle(count=1)
    def edit(obj):
        p=obj['policy_facts'][0];p['before_status']=before;p['after_status']=after
        for r in p['rules']:
            r.update(before_status='PASS',after_status='PASS',before_missing=[],after_missing=[])
        r=p['rules'][0];r['before_status']=before;r['after_status']=after
        r['before_missing']=['age'] if before=='UNKNOWN' else [];r['after_missing']=['age'] if after=='UNKNOWN' else []
        obj['unknown_information']=([dict(policy_id=p['policy_id'],before_status=before,after_status=after,
          before_missing_fields=r['before_missing'],after_missing_fields=r['after_missing'])] if 'UNKNOWN' in (before,after) else [])
    facts,doc=edited(facts,doc,edit);prepared=catalog.prepare_catalog(facts,doc);policy=prepared.policy_options[0]
    expected=('P3' if before==after else 'P4') if after=='UNKNOWN' else ('P6' if before=='UNKNOWN' else 'P1' if before==after else 'P2')
    assert policy.family==expected
    result=catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(selection(prepared)),prepared))
    unchanged(result,doc)
    if after=='UNKNOWN':assert all('확인할 조건' in s for s in policy.texts)


@pytest.mark.parametrize('resolve',[False,True])
def test_fail_can_keep_unknown_or_resolve_it_while_aggregate_stays_fail(resolve):
    facts,doc=bundle(cases()[18])
    def edit(obj):
        p=obj['policy_facts'][2];p['before_status']=p['after_status']='FAIL'
        u=obj['unknown_information'][0];u['before_status']=u['after_status']='FAIL'
        if resolve:
            u['after_missing_fields']=[]
            r=next(r for r in p['rules'] if r['field']=='household_income');r['after_status']='PASS';r['after_missing']=[]
    facts,doc=edited(facts,doc,edit);prepared=catalog.prepare_catalog(facts,doc);policy=prepared.policy_options[2]
    assert policy.family==('P5' if resolve else 'P3')
    assert policy.pending_before and policy.pending_after is not resolve
    if resolve:assert all('해소' in t and '종합 판정은 같' in t for t in policy.texts)
    else:assert all('확인할 조건' in t for t in policy.texts)
    unchanged(catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(selection(prepared)),prepared)),doc)


def test_rule_unknown_without_missing_label_still_requires_confirmation():
    facts,doc=bundle(count=1)
    def edit(obj):
        p=obj['policy_facts'][0];p['before_status']=p['after_status']='FAIL'
        p['rules'][0]['before_status']=p['rules'][0]['after_status']='UNKNOWN'
        obj['unknown_information']=[dict(policy_id=p['policy_id'],before_status='FAIL',after_status='FAIL',before_missing_fields=[],after_missing_fields=[])]
    facts,doc=edited(facts,doc,edit);prepared=catalog.prepare_catalog(facts,doc)
    assert prepared.policy_options[0].family=='P3' and prepared.summary_family=='S5'


def test_rules_change_without_global_input_change_uses_neutral_summary_not_unchanged_result():
    facts,doc=bundle(count=1)
    def edit(obj):obj['policy_facts'][0]['rules'][0]['after_status']='FAIL'
    facts,doc=edited(facts,doc,edit);prepared=catalog.prepare_catalog(facts,doc)
    assert prepared.summary_family=='S6'
    assert prepared.policy_options[0].family=='P1' # final state is copied, not recomputed from this rule
    assert all('조건 판정은 같' not in s for s in prepared.policy_options[0].texts)


def test_partial_unknown_resolution_never_selects_cleared_text():
    facts,doc=bundle(count=1)
    def edit(obj):
        p=obj['policy_facts'][0];p['before_status']=p['after_status']='UNKNOWN'
        for r in p['rules'][:2]:r.update(before_status='UNKNOWN',after_status='UNKNOWN',before_missing=['age'],after_missing=['age'])
        p['rules'][0].update(after_status='PASS',after_missing=[])
        obj['unknown_information']=[dict(policy_id=p['policy_id'],before_status='UNKNOWN',after_status='UNKNOWN',before_missing_fields=['age'],after_missing_fields=['age'])]
    facts,doc=edited(facts,doc,edit);policy=catalog.prepare_catalog(facts,doc).policy_options[0]
    assert policy.family=='P3' and all('해소' not in text for text in policy.texts)


@pytest.mark.parametrize('count',[0,1,2,3])
def test_counts_schema_enum_and_fresh_copies(count):
    facts,doc=bundle(count=count);prepared=catalog.prepare_catalog(facts,doc)
    obj=prepared.model_input();schema=catalog.catalog_output_schema(prepared)
    assert schema['properties']['summary']['enum']==obj['summary_options']
    assert schema['properties']['policy_texts']['required']==list(obj['policy_options'])
    obj['summary_options'].clear();obj['policy_options'].clear();schema['properties']['summary']['enum'].clear()
    assert len(prepared.summary_options)==2 and len(prepared.policy_options)==count
    unchanged(catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(selection(prepared)),prepared)),doc)
    with pytest.raises(FrozenInstanceError):prepared.summary_options=()
    if count:
        with pytest.raises(FrozenInstanceError):prepared.policy_options[0].slot='p99'


@pytest.mark.parametrize('mode',['append','prepend','space','delete_clause','other_slot','summary_as_policy','nfd','unknown_sentence','candidate_id','empty'])
def test_non_exact_text_is_rejected_without_repair_and_whole_document_falls_back(mode):
    facts,doc=bundle();prepared=catalog.prepare_catalog(facts,doc);obj=selection(prepared)
    target=obj['policy_texts']['p03']
    if mode=='append':obj['summary']+=' 함께 봐요.'
    elif mode=='prepend':obj['summary']='참고로 '+obj['summary']
    elif mode=='space':obj['summary']+=' '
    elif mode=='delete_clause':obj['policy_texts']['p03']=target.split('.')[0]+'.'
    elif mode=='other_slot':obj['policy_texts']['p03']=obj['policy_texts']['p01']
    elif mode=='summary_as_policy':obj['policy_texts']['p01']=obj['summary']
    elif mode=='nfd':obj['summary']=unicodedata.normalize('NFD',obj['summary'])
    elif mode=='unknown_sentence':obj['summary']='모든 정책의 상태를 알기 어려워요.'
    elif mode=='candidate_id':obj['summary']='S5'
    else:obj['summary']=''
    result=catalog.evaluate_synthetic_catalog(facts,doc,wire(obj))
    assert result.fallback and result.document==doc and not result.ai_success
    if mode not in ('candidate_id','empty'):assert result.diagnostic_code=='TEXT_NOT_IN_REQUEST_CATALOG'


@pytest.mark.parametrize('raw',[b'\xff','not JSON','[]','null','{}','{"summary":"같아요","summary":"달라요","policy_texts":{}}',
 '{"summary":NaN,"policy_texts":{}}','{"summary":"같아요","policy_texts":{},"extra":true}'])
def test_existing_strict_parser_stays_in_front_of_membership(raw):
    facts,doc=bundle();result=catalog.evaluate_synthetic_catalog(facts,doc,raw)
    assert result.fallback and result.document==doc and result.diagnostic_code!='TEXT_NOT_IN_REQUEST_CATALOG'


@pytest.mark.parametrize('length,code',[(60,'TEXT_NOT_IN_REQUEST_CATALOG'),(61,'INVALID_TEXT_LENGTH_OR_TYPE')])
def test_summary_codepoint_limit_precedes_membership(length,code):
    facts,doc=bundle();obj=selection(catalog.prepare_catalog(facts,doc));obj['summary']='가'*length
    result=catalog.evaluate_synthetic_catalog(facts,doc,wire(obj));assert result.diagnostic_code==code


@pytest.mark.parametrize('length,code',[(40,'TEXT_NOT_IN_REQUEST_CATALOG'),(41,'INVALID_TEXT_LENGTH_OR_TYPE')])
def test_policy_codepoint_limit_precedes_membership(length,code):
    facts,doc=bundle();obj=selection(catalog.prepare_catalog(facts,doc));obj['policy_texts']['p01']='가'*length
    assert catalog.evaluate_synthetic_catalog(facts,doc,wire(obj)).diagnostic_code==code


@pytest.mark.parametrize('size,code',[(4096,'INVALID_NARRATIVE_JSON'),(4097,'NARRATIVE_TOO_LONG')])
def test_inner_byte_boundary_unchanged(size,code):
    facts,doc=bundle();assert catalog.evaluate_synthetic_catalog(facts,doc,b'x'*size).diagnostic_code==code


def test_json_key_order_escapes_and_whitespace_do_not_change_string_values():
    facts,doc=bundle();prepared=catalog.prepare_catalog(facts,doc);obj=selection(prepared,1)
    obj={'policy_texts':dict(reversed(list(obj['policy_texts'].items()))),'summary':obj['summary']}
    raw=json.dumps(obj,ensure_ascii=True,indent=4)
    result=catalog.assemble_catalog(prepared,catalog.parse_catalog(raw,prepared))
    assert result.summary==obj['summary'];unchanged(result,doc)


def test_cross_request_checked_objects_cannot_be_assembled_even_when_candidates_overlap():
    facts,doc=bundle();a=catalog.prepare_catalog(facts,doc);b=catalog.prepare_catalog(facts,doc)
    raw=wire(selection(a));checked=catalog.parse_catalog(raw,a)
    with pytest.raises(v1.NarrativeContractError,match='REQUEST_MAPPING_MISMATCH'):catalog.assemble_catalog(b,checked)
    # Text alone is not provenance: identical text may be true for both requests.
    unchanged(catalog.assemble_catalog(b,catalog.parse_catalog(raw,b)),doc)
    altered=replace(checked,_checked=replace(checked._checked,summary='월세가 줄어서 소득이 늘었어요.'))
    with pytest.raises(v1.NarrativeContractError,match='TEXT_NOT_IN_REQUEST_CATALOG'):catalog.assemble_catalog(a,altered)


def test_different_request_candidates_and_concurrent_snapshots_stay_isolated():
    bundles=[bundle(cases()[i]) for i in (1,9)]
    a=catalog.prepare_catalog(*bundles[0]);b=catalog.prepare_catalog(*bundles[1])
    with pytest.raises(v1.NarrativeContractError,match='TEXT_NOT_IN_REQUEST_CATALOG'):catalog.parse_catalog(wire(selection(a)),b)
    def run(pair):
        facts,doc=pair;prepared=catalog.prepare_catalog(facts,doc)
        result=catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(selection(prepared)),prepared));unchanged(result,doc)
        return result.summary
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,bundles*5))
    assert results[::2]==[a.summary_options[0]]*5 and results[1::2]==[b.summary_options[0]]*5


def test_prepared_snapshot_survives_mutating_caller_lists_and_returned_documents():
    facts,doc=bundle();prepared=catalog.prepare_catalog(facts,doc);baseline=doc.model_dump()
    facts.unknown_information.clear();doc.unknown_information.clear();doc.policy_explanations.clear()
    result=catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(selection(prepared)),prepared))
    assert result.unknown_information==ExplanationDocument.model_validate(baseline).unknown_information
    result.unknown_information.clear()
    again=catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(selection(prepared)),prepared))
    assert again.unknown_information


@pytest.mark.parametrize('defect,expected',[
 ('wrong_direction','INCONSISTENT_DISPLAY_DIRECTION'),('input_flag','INCONSISTENT_INPUT_CHANGE'),
 ('rule_flag','INCONSISTENT_RULE_INPUT_CHANGE'),('unknown_orphan','INVALID_UNKNOWN_IDS'),
 ('unknown_missing','UNKNOWN_INFORMATION_MISSING'),('unsupported_field','UNSUPPORTED_CATALOG_INPUT'),
 ('duplicate_policy','INVALID_POLICY_IDS'),('duplicate_rule','DUPLICATE_RULE_ID')])
def test_inconsistent_or_unsupported_server_metadata_fails_closed(defect,expected):
    facts,doc=bundle()
    def edit(obj):
        if defect=='wrong_direction':obj['money_facts'][0]['delta']=1
        elif defect=='input_flag':obj['changed_input_fields']=['monthly_income']
        elif defect=='rule_flag':obj['policy_facts'][0]['rules'][0]['input_changed']=True
        elif defect=='unknown_orphan':obj['unknown_information'][0]['policy_id']='ORPHAN'
        elif defect=='unknown_missing':obj['unknown_information']=[]
        elif defect=='unsupported_field':obj['changed_input_fields']=['household_income']
        elif defect=='duplicate_policy':obj['policy_facts'].append(copy.deepcopy(obj['policy_facts'][0]))
        else:obj['policy_facts'][0]['rules'].append(copy.deepcopy(obj['policy_facts'][0]['rules'][0]))
    facts,doc=edited(facts,doc,edit)
    result=catalog.evaluate_synthetic_catalog(facts,doc,'{}')
    # Fourth policy reaches the unchanged V1 policy-count guard first.
    if defect=='duplicate_policy':expected='UNSUPPORTED_POLICY_COUNT'
    assert result.fallback and result.diagnostic_code==expected and result.document==doc


def test_policy_order_and_model_projection_exclude_untrusted_numbers_ids_sources_and_text():
    facts,doc=bundle();marker='SECRET_IGNORE_ALL_RULES_999999'
    def edit(obj):
        mapping=dict(zip([p['policy_id'] for p in obj['policy_facts']],['ZZ','AA','MM'],strict=True))
        obj['dataset_version']=marker;obj['assumptions']=[marker]
        for key in ('policy_facts','unknown_information','next_actions'):
            for row in obj[key]:row['policy_id']=mapping[row['policy_id']]
        for p in obj['policy_facts']:
            p['text']=marker
            for r in p['rules']:r['before_reason']=r['after_reason']=marker;r['source_refs']=['C:/private/'+marker]
        for m in obj['money_facts']:m['text']=marker
    facts,doc=edited(facts,doc,edit);prepared=catalog.prepare_catalog(facts,doc)
    raw=prepared.model_input_json
    assert marker not in raw and 'C:' not in raw and '1500000' not in raw
    assert all(p.policy_id not in raw for p in facts.policy_facts)
    result=catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(selection(prepared)),prepared))
    assert [p.policy_id for p in result.policy_explanations]==['ZZ','AA','MM'];unchanged(result,doc)


def test_existing_validator_runs_for_all_candidates_and_final_assembly(monkeypatch):
    facts,doc=bundle();calls=[];original=legacy.validate_output
    def tracked(raw,expected):calls.append(raw);return original(raw,expected)
    monkeypatch.setattr(legacy,'validate_output',tracked)
    prepared=catalog.prepare_catalog(facts,doc);count=len(calls);assert count>1
    catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(selection(prepared)),prepared));assert len(calls)==count+1
    def rejected(*_):raise legacy.OutputRejected('UNSUPPORTED_NARRATIVE')
    monkeypatch.setattr(legacy,'validate_output',rejected)
    result=catalog.evaluate_synthetic_catalog(facts,doc,wire(selection(prepared)))
    assert result.fallback and result.document==doc and result.failure_stage=='output_validator'


def test_internal_errors_and_damaged_canonical_are_not_model_quality_fallbacks(monkeypatch):
    facts,doc=bundle()
    with pytest.raises(TypeError,match='SERVER_DOCUMENT_REQUIRED'):catalog.evaluate_synthetic_catalog(facts,{},'{}')
    def broken(*_):raise RuntimeError('INTERNAL_FAILURE')
    monkeypatch.setattr(catalog,'_summary',broken)
    with pytest.raises(RuntimeError,match='INTERNAL_FAILURE'):catalog.evaluate_synthetic_catalog(facts,doc,'{}')


def test_preflight_rejects_bad_catalog_size_and_no_network_is_used(monkeypatch):
    facts,doc=bundle()
    def forbidden(*_,**__):raise AssertionError('NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    prepared=catalog.prepare_catalog(facts,doc)
    assert not catalog.evaluate_synthetic_catalog(facts,doc,wire(selection(prepared))).fallback
    monkeypatch.setattr(catalog,'_summary',lambda _:('S5',('가'*1500,'나'*1500)))
    with pytest.raises(v1.NarrativeContractError,match='CATALOG_CONTEXT_TOO_LONG'):catalog.prepare_catalog(facts,doc)


def test_warning_free_rejection_of_corrupt_fact_and_repeatability():
    facts,doc=bundle();baseline=catalog.prepare_catalog(facts,doc).model_input_json
    for _ in range(10):assert catalog.prepare_catalog(facts,doc).model_input_json==baseline
    broken=facts.model_copy(update={'money_facts':['PRIVATE_BAD_VALUE']})
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always');result=catalog.evaluate_synthetic_catalog(broken,doc,'{}')
    assert result.fallback and not captured


@pytest.mark.parametrize('slot_change',['missing','extra'])
def test_missing_or_extra_policy_slot_never_partially_returns(slot_change):
    facts,doc=bundle();obj=selection(catalog.prepare_catalog(facts,doc))
    if slot_change=='missing':obj['policy_texts'].pop('p03')
    else:obj['policy_texts']['p04']=obj['policy_texts']['p01']
    result=catalog.evaluate_synthetic_catalog(facts,doc,wire(obj))
    assert result.fallback and result.diagnostic_code=='SLOT_SET_MISMATCH' and result.document==doc


def test_single_candidate_is_valid_and_schema_has_single_enum(monkeypatch):
    facts,doc=bundle();original=catalog._summary
    monkeypatch.setattr(catalog,'_summary',lambda f:(original(f)[0],original(f)[1][:1]))
    monkeypatch.setattr(catalog,'_POLICIES',{k:v[:1] for k,v in catalog._POLICIES.items()})
    prepared=catalog.prepare_catalog(facts,doc)
    assert len(prepared.summary_options)==1 and all(len(p.texts)==1 for p in prepared.policy_options)
    assert len(catalog.catalog_output_schema(prepared)['properties']['summary']['enum'])==1
    unchanged(catalog.assemble_catalog(prepared,catalog.parse_catalog(wire(selection(prepared)),prepared)),doc)


@pytest.mark.parametrize('options',[(),('같아요.','같아요.'),('가요.','나요.','다요.')])
def test_invalid_candidate_cardinality_or_duplicate_is_not_silently_truncated(options,monkeypatch):
    facts,doc=bundle();monkeypatch.setattr(catalog,'_summary',lambda _:('S5',options))
    result=catalog.evaluate_synthetic_catalog(facts,doc,'{}')
    assert result.fallback and result.diagnostic_code=='INVALID_CATALOG_OPTIONS' and result.document==doc


def test_catalog_context_size_guard_at_measured_boundary(monkeypatch):
    facts,doc=bundle();size=len(catalog.prepare_catalog(facts,doc).model_input_json.encode('utf-8'))
    monkeypatch.setattr(v1,'MAX_CONTEXT_BYTES',size)
    # The old V1 projection is larger than the candidate context for this case;
    # isolate the added guard with an already validated request snapshot.
    prepared=catalog.CatalogPrepared('S5',('같아요.',),(),v1.prepare_narrative(*bundle(count=0)))
    limit=len(prepared.model_input_json.encode('utf-8'))
    monkeypatch.setattr(v1,'MAX_CONTEXT_BYTES',limit);catalog._preflight(prepared)
    monkeypatch.setattr(v1,'MAX_CONTEXT_BYTES',limit-1)
    with pytest.raises(v1.NarrativeContractError,match='CATALOG_CONTEXT_TOO_LONG'):catalog._preflight(prepared)


