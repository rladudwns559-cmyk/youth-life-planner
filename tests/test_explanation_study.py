"""집계용 합성 응답만 사용. 사람 평가 실적을 만들지 않는다."""
import copy
import csv
import json
from pathlib import Path
import pytest
from tools.explanation_study import (StudyError,allocations,analyze,validate,answers,read_csv,
    PARTICIPANT_FIELDS,RESPONSE_FIELDS,load_sessions,main)

ROOT=Path(__file__).resolve().parents[1]
KEY_PATH=ROOT/'docs/experiments/m3_8f/private/study_key.json'

@pytest.fixture
def key():
    return json.loads(KEY_PATH.read_text(encoding='utf-8'))

def fixtures(key,kind='synthetic',people=2):
    participants=[];rows=[]
    for slot in range(1,people+1):
        pid=f'SYN{slot:03}' if kind=='synthetic' else f'P{slot:02}'
        participants.append(dict(data_kind=kind,participant_id=pid,allocation_slot=str(slot),consented='true',
            session_status='completed',preference='X',added_value='same_information',preference_comment=''))
        for assignment in key['allocations']:
            if assignment['allocation_slot']!=slot:continue
            task=next(t for t in key['tasks'] if t['task_id']==assignment['task_id'])
            row={field:'' for field in RESPONSE_FIELDS}
            row.update(data_kind=kind,participant_id=pid,task_id=task['task_id'],order=str(assignment['order']),
                task_status='submitted',elapsed_ms='1000' if assignment['condition']=='A' else '2000',interrupted='false',
                ease='3' if assignment['condition']=='A' else '4',trust='4',usefulness='3')
            for q in task['questions']:row[q['id']]='|'.join(q['correct'])
            if assignment['condition']=='A':row['q1']='DK'
            rows.append(row)
    return participants,rows

def test_ready_tasks_source_and_common_content(key):
    assert len(key['tasks'])==8
    assert len({t['case_id'] for t in key['tasks']})==8
    assert [t['case_id'] for t in key['tasks']]==['EX01','EX02','EX04','EX07','EX09','EX11','EX12','FU01']
    assert key['ready']==all(t['variants']['B'] is not None for t in key['tasks'])
    for t in key['tasks']:
        assert len(t['questions'])==4
        a,b=t['variants']['A'],t['variants']['B']
        if b:
            assert a['changed_facts']==b['changed_facts']
            assert a['unknown_information']==b['unknown_information']
            assert a['next_actions']==b['next_actions']
            assert [dict(p,text='') for p in a['policy_explanations']]==[dict(p,text='') for p in b['policy_explanations']]
        assert all(q['provenance'] for q in t['questions'])

def test_independent_ground_truth_known_boundaries(key):
    expected=[('T01','0','PASS'),('T02','0','FAIL'),('T03','0','UNKNOWN'),('T04','300000','UNKNOWN'),
              ('T05','-100000','UNKNOWN'),('T06','200000','UNKNOWN'),('T07','-900000','UNKNOWN'),('T08','200000','FAIL')]
    for tid,money,state in expected:
        t=next(t for t in key['tasks'] if t['task_id']==tid)
        assert t['questions'][0]['correct']==[money]
        assert t['questions'][1]['correct']==[state]
    assert key['tasks'][2]['questions'][3]['correct']==['employment_status','household_income']
    assert len(key['tasks'][7]['facts']['changed_input_fields'])==3

@pytest.mark.parametrize('slot',range(1,21))
def test_each_planned_person_sees_each_task_once_four_per_condition(key,slot):
    rows=[r for r in key['allocations'] if r['allocation_slot']==slot]
    assert len({r['task_id'] for r in rows})==8
    assert sorted(r['order'] for r in rows)==list(range(1,9))
    assert sum(r['condition']=='A' for r in rows)==4
    assert sum(r['condition']=='B' for r in rows)==4

@pytest.mark.parametrize('task_id',[f'T{i:02}' for i in range(1,9)])
def test_task_condition_balance(key,task_id):
    rows=[r for r in key['allocations'] if r['task_id']==task_id]
    assert sum(r['condition']=='A' for r in rows)==10
    assert sum(r['condition']=='B' for r in rows)==10

@pytest.mark.parametrize('position',range(1,9))
def test_position_condition_balance(key,position):
    rows=[r for r in key['allocations'] if r['order']==position]
    assert sum(r['condition']=='A' for r in rows)==10
    assert sum(r['condition']=='B' for r in rows)==10
    assert len({r['task_id'] for r in rows})==8

def test_pair_opposite_conditions_identical_order(key):
    for slot in range(1,21,2):
        left=[r for r in key['allocations'] if r['allocation_slot']==slot]
        right=[r for r in key['allocations'] if r['allocation_slot']==slot+1]
        assert [(r['task_id'],r['order']) for r in left]==[(r['task_id'],r['order']) for r in right]
        assert all(a['condition']!=b['condition'] for a,b in zip(left,right))

def test_locked_allocations_reproducible(key):
    assert key['allocations']==allocations([t['task_id'] for t in key['tasks']])

def test_empty_real_is_unmeasured(key):
    result=analyze(key,[],[],'real')
    assert result['actual_participants']==result['real_response_rows']==0
    for c in result['conditions'].values():
        assert c['accuracy_assigned'] is None and c['completion_rate'] is None
        assert c['time_mean_seconds'] is None and c['ratings']['ease']['mean'] is None
        assert all(v is None for v in c['observed_wrong_by_category'].values())
    assert result['serious_model_contradictions'] is None

def test_known_synthetic_scores_times_and_pair_difference(key):
    p,r=fixtures(key,people=5);out=analyze(key,p,r,'synthetic')
    assert out['actual_participants']==0 and out['synthetic_participants']==5
    assert out['conditions']['A']['accuracy_assigned']==.75
    assert out['conditions']['B']['accuracy_assigned']==1
    assert out['participant_paired_accuracy_delta_B_minus_A']==.25
    assert out['conditions']['A']['completion_rate']==out['conditions']['B']['completion_rate']==1
    assert out['conditions']['A']['time_mean_seconds']==1
    assert out['conditions']['B']['time_mean_seconds']==2
    assert out['conditions']['A']['ratings']['ease']['mean']==3
    assert out['conditions']['B']['ratings']['ease']['mean']==4
    assert out['conditions']['A']['dont_know_items']==20
    assert out['conditions']['A']['observed_wrong_by_category']['money']==0 # q3 of deficit task remains an observed money item
    assert out['added_value']['counts']['same_information']==5
    assert out['preference']['counts']['A']==3 and out['preference']['counts']['B']==2

def test_blank_preserved_missing_time_and_rating_not_zero(key):
    p,r=fixtures(key,people=1);p[0].update(session_status='started',preference='',added_value='')
    r=r[:1];r[0].update(q1='',ease='',elapsed_ms='',task_status='partial')
    before=copy.deepcopy(r);out=analyze(key,p,r,'synthetic')
    assert r==before
    c=out['conditions']['A'];assert c['assigned_items']==16 and c['missing_items']==13
    assert c['accuracy_assigned']==3/16 and c['accuracy_observed']==1
    assert c['completion_rate']==0 and c['time_mean_seconds'] is None and c['ratings']['ease']['mean'] is None

def test_no_rows_started_person_has_zero_assigned_score_but_no_observed_score(key):
    p,_=fixtures(key,people=1);p[0].update(session_status='started',preference='',added_value='')
    out=analyze(key,p,[],'synthetic')
    assert out['conditions']['A']['accuracy_assigned']==0
    assert out['conditions']['A']['accuracy_observed'] is None

def test_withdrawal_excludes_without_destroying_raw(key):
    p,r=fixtures(key,people=2);p[0].update(session_status='withdrawn',preference='',added_value='')
    out=analyze(key,p,r,'synthetic')
    assert out['withdrawn_records']==1 and out['synthetic_participants']==1 and out['response_rows']==8
    assert len(r)==16

def test_multiselect_exact_and_confirmations_omitted(key):
    p,r=fixtures(key,people=1);row=next(x for x in r if x['task_id']=='T03');row['q4']='household_income'
    out=analyze(key,p,r,'synthetic');assert out['conditions']['A']['confirmation_omissions']==1
    assert out['conditions']['A']['observed_wrong_by_category']['confirmation']==1

def test_interruption_excluded_only_secondary_time_view(key):
    p,r=fixtures(key,people=1)
    for row in r:row['interrupted']='true'
    out=analyze(key,p,r,'synthetic')
    assert out['conditions']['A']['time_n']==4 and out['conditions']['A']['uninterrupted_time_n']==0
    assert out['conditions']['A']['accuracy_assigned']==.75

@pytest.mark.parametrize('field,value',[('data_kind','real'),('participant_id','김영준'),('participant_id','P01'),
    ('allocation_slot','0'),('allocation_slot','21'),('consented','false'),('session_status','fake'),('preference','AI'),('added_value','great')])
def test_invalid_person_rejected(key,field,value):
    p,r=fixtures(key);p[0][field]=value
    with pytest.raises(StudyError):analyze(key,p,r,'synthetic')

@pytest.mark.parametrize('field,value',[('data_kind','real'),('participant_id','SYN999'),('task_id','T99'),('order','8'),
    ('elapsed_ms','NaN'),('elapsed_ms','-1'),('elapsed_ms','Infinity'),('ease','0'),('ease','6'),('trust','1.5'),
    ('interrupted','yes'),('task_status','unknown'),('q1','made_up'),('q1','0|DK'),('q4','NONE|household_income'),
    ('q4','household_income|household_income')])
def test_invalid_response_rejected(key,field,value):
    p,r=fixtures(key);r[0][field]=value
    with pytest.raises(StudyError):analyze(key,p,r,'synthetic')

def test_duplicate_people_and_slots_and_trials_rejected(key):
    p,r=fixtures(key)
    with pytest.raises(StudyError):analyze(key,p+[p[0]],r,'synthetic')
    p[1]['allocation_slot']='1'
    with pytest.raises(StudyError):analyze(key,p,r,'synthetic')
    p,r=fixtures(key)
    with pytest.raises(StudyError):analyze(key,p,r+[r[0]],'synthetic')

def test_completed_requires_eight_rows_and_preference_after_primary(key):
    p,r=fixtures(key)
    with pytest.raises(StudyError):analyze(key,p,r[:-1],'synthetic')
    p[0]['session_status']='started'
    with pytest.raises(StudyError):analyze(key,p,r,'synthetic')

def test_bad_csv_header_or_short_row_rejected(tmp_path):
    path=tmp_path/'bad.csv';path.write_text('name\nAlice\n',encoding='utf-8')
    with pytest.raises(StudyError):read_csv(path,PARTICIPANT_FIELDS)
    path.write_text(','.join(PARTICIPANT_FIELDS)+'\nreal,P01\n',encoding='utf-8')
    with pytest.raises(StudyError):read_csv(path,PARTICIPANT_FIELDS)

def test_public_session_blinding_and_questions(key):
    if not key['ready']:
        assert not list((KEY_PATH.parent.parent/'participant/sessions').glob('P*.json'));return
    for path in (KEY_PATH.parent.parent/'participant/sessions').glob('P*.json'):
        d=json.loads(path.read_text(encoding='utf-8'))
        assert len(d['tasks'])==8 and 'correct' not in path.read_text(encoding='utf-8')
        assert all('variants' not in t and 'source' not in t and 'condition' not in t for t in d['tasks'])
        for task in d['tasks']:
            original=next(t for t in key['tasks'] if t['task_id']==task['task_id'])
            assert task['questions']==[{k:v for k,v in q.items() if k not in ('correct','provenance','category')} for q in original['questions']]

def test_cli_real_empty_and_synthetic_namespace_separated(key,tmp_path):
    key['ready']=True # CLI fixture only; actual source stays unchanged
    keyfile=tmp_path/'key.json';keyfile.write_text(json.dumps(key),encoding='utf-8')
    sessions=tmp_path/'sessions';sessions.mkdir()
    out=tmp_path/'result'
    main(['--key',str(keyfile),'--kind','real','--sessions',str(sessions),'--output',str(out)])
    result=json.loads((out/'summary_real.json').read_text(encoding='utf-8'))
    assert result['actual_participants']==0 and not (out/'summary_synthetic.json').exists()
    with pytest.raises(StudyError):main(['--key',str(keyfile),'--kind','real','--sessions',str(sessions),'--output',str(out)])

def test_no_automatic_real_complete_or_ai_superiority(key):
    p,r=fixtures(key,'real',5);out=analyze(key,p,r,'real')
    assert out['verdict']=='M3_EXPLANATION_HUMAN_EVALUATION_PARTIAL'
    assert out['ai_added_value_conclusion']=='EXPLORATORY_REVIEW_REQUIRED'
    assert out['serious_model_contradictions'] is None
