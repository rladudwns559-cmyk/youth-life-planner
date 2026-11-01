"""저장된 실제 모델 증거와 기존 Python 엔진에서 M3.8F 고정 실험 자료 생성. 모델 호출 없음."""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
from backend.explanation.facts import build_facts,deterministic_document
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from tools.evaluate_explanation_scenarios import cases
from tools.explanation_study import allocations,PARTICIPANT_FIELDS,RESPONSE_FIELDS,analyze,table

ROOT=Path(__file__).resolve().parents[1]
SELECTED=['EX01','EX02','EX04','EX07','EX09','EX11','EX12','FU01']
TITLES=['입력 유지','취업 상태 변경','취업 정보 미입력','월소득 증가','월세 증가','저축 투입 상한 증가','월소득 감소와 적자','소득·월세·취업 동시 변경']
REASONS=['PASS 유지와 수급 확정 오해','PASS에서 FAIL로 변경된 조건','UNKNOWN 유지와 누락 취업/가구 정보',
         '개인 월소득과 정책 가구소득 분리','월세 변화의 예산 효과','여유자금과 저축 상한 구분','음수 여유자금과 저축0',
         '세 입력 동시 변경의 복합 결과; 사용자 승인 신규 자료']

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def question(qid,text,choices,correct,category,multiple=False,rotation=0,provenance=''):
    options=[dict(value=str(v),label=label) for v,label in choices]
    options=options[rotation%len(options):]+options[:rotation%len(options)]
    options.append(dict(value='DK',label='모르겠다'))
    return dict(id=qid,text=text,choices=options,correct=[str(v) for v in correct],category=category,
                multiple=multiple,provenance=provenance)

def questions(index,facts):
    money={m['field']:m for m in facts['money_facts']};policies={p['policy_id']:p for p in facts['policy_facts']}
    if index==6:
        amount=money['disposable_after_policy']['after'];text='변경 후 월 여유자금은 얼마인가요?';proof='money_facts.disposable_after_policy.after'
    elif index==5:
        amount=money['savable_amount']['delta'];text='저축 투입 가능액은 얼마나 변했나요?';proof='money_facts.savable_amount.delta'
    else:
        amount=money['disposable_after_policy']['delta'];text='월 여유자금은 얼마나 변했나요?';proof='money_facts.disposable_after_policy.delta'
    values=list(dict.fromkeys([amount,0,100000,-100000,300000,-900000]))[:4]
    if amount not in values:values[0]=amount
    q1=question('q1',text,[(v,f'{v:+,}원' if v else '0원 / 변화 없음') for v in values],[amount],'money',rotation=index,provenance=proof)
    target='SAMPLE-002' if index in (1,2,7) else 'SAMPLE-001' if index==0 else 'SAMPLE-003'
    q2=question('q2',f'변경 후 {target}의 표시 상태는 무엇인가요?',
        [('PASS','이용 가능성 높음 (PASS)'),('FAIL','현재 조건과 맞지 않음 (FAIL)'),('UNKNOWN','추가 확인 필요 (UNKNOWN)')],
        [policies[target]['after_status']],'policy',rotation=index,provenance=f'policy_facts.{target}.after_status')
    if index==1:
        rule=next(r for r in policies['SAMPLE-002']['rules'] if r['after_status']=='FAIL')
        q3=question('q3','SAMPLE-002의 결과가 바뀐 직접 조건은?',
            [('employment_status','미취업에서 취업으로 변경'),('monthly_rent','월세 변경'),('household_income','가구소득이 확인됨')],
            [rule['field']],'reason',rotation=index,provenance='SAMPLE-002.rules: FAIL + input_changed')
    elif index==2:
        q3=question('q3','취업 상태를 입력하지 않은 SAMPLE-002를 어떻게 해석해야 하나요?',
            [('pending','판단할 정보가 없어 추가 확인한다'),('pass','미입력은 조건 충족이다'),('fail','미입력은 조건 불충족이다')],
            ['pending'],'unknown',rotation=index,provenance='SAMPLE-002.rules UNKNOWN/MISSING_FIELD')
    elif index==3:
        q3=question('q3','개인 월소득이 늘었는데 SAMPLE-003이 UNKNOWN인 이유는?',
            [('separate','정책 가구소득 정보가 여전히 없으며 개인 월소득과 다르다'),('met','개인 월소득으로 가구소득 기준을 충족했다'),('rejected','소득 증가만으로 탈락했다')],
            ['separate'],'unknown',rotation=index,provenance='SAMPLE-003.household_income MISSING_FIELD + assumptions')
    elif index==4:
        assert facts['changed_input_fields']==['monthly_rent']
        q3=question('q3','여유자금 감소를 만든 입력 변화는?',
            [('rent','월세 증가'),('income','월소득 감소'),('benefit','지원금 삭감')],['rent'],'reason',rotation=index,provenance='changed_input_fields/monthly_rent')
    elif index==5:
        assert money['disposable_after_policy']['delta']==0
        q3=question('q3','저축 투입 가능액 증가를 어떻게 해석해야 하나요?',
            [('cap','여유자금은 그대로이며 사용자가 설정한 저축 상한이 증가했다'),('income','월소득이 증가했다'),('benefit','실제 지원금이 추가됐다')],
            ['cap'],'reason',rotation=index,provenance='user_savings_capacity delta + disposable delta0')
    elif index==6:
        assert money['disposable_after_policy']['after']<0 and money['savable_amount']['after']==0
        q3=question('q3','적자일 때 저축 투입 가능액0은 무엇을 뜻하나요?',
            [('deficit','여유자금 적자는 남고 저축 투입 가능액만0으로 제한된다'),('balanced','지출과 소득이 같아졌다'),('support','실제 정책 지원금으로 적자가 해소됐다')],
            ['deficit'],'money',rotation=index,provenance='disposable_after_policy<0, savable_amount0')
    else:
        assert facts['benefit_applied_krw']==0
        q3=question('q3','이 합성 결과의 PASS만으로 실제 지원금 수령이 확정되나요?',
            [('no','아니요. 실제 자격·수령 확정이 아니며 지원금 반영도0원이다'),('yes','예. PASS면 실제로 지급된다'),('unknown_is_pass','UNKNOWN도 PASS로 처리할 수 있다')],
            ['no'],'certainty',rotation=index,provenance='synthetic/test_only/benefit_applied_krw0 + disclaimer')
    missing=sorted({field for u in facts['unknown_information'] for field in u['after_missing_fields']})
    assert missing
    q4=question('q4','변경 후 UNKNOWN 조건을 판단하려면 어떤 누락 정보를 더 확인해야 하나요? 모두 선택하세요.',
        [('household_income','정책 기준의 가구소득'),('employment_status','취업 상태'),('account_number','계좌번호'),('NONE','추가 확인 정보 없음')],
        missing,'confirmation',multiple=True,rotation=index,provenance='unknown_information[].after_missing_fields 합집합')
    return [q1,q2,q3,q4]

def build(evidence_path,combined_path,destination):
    evidence=json.loads(evidence_path.read_text(encoding='utf-8'));combined=json.loads(combined_path.read_text(encoding='utf-8'))
    rows={r['case_id']:r for r in evidence['actual_fixed30']['results']}
    assert len(combined['results'])==1
    rows['FU01']=combined['results'][0]
    inputs={c['case_id']:c for c in cases()};inputs['FU01']=combined['case']
    tasks=[]
    for i,cid in enumerate(SELECTED):
        row=rows[cid];case=inputs[cid]
        comparison=compare_scenarios(ComparisonInput(before=case['before'],after=case['after']))
        facts=build_facts(comparison);canonical=deterministic_document(comparison,facts)
        assert comparison.model_dump()==row['python_confirmed_result']
        assert canonical.model_dump()==row['deterministic_document']
        assert facts.model_dump()==row['api_result']['facts']
        a=canonical.model_dump();b=row['api_result']['document'] if row['api_result']['ai_success'] else None
        if b:
            assert row['exact_candidate_match'] and row['existing_validator_passed']
            assert a['changed_facts']==b['changed_facts'] and a['unknown_information']==b['unknown_information'] and a['next_actions']==b['next_actions']
            assert [dict(p,text='') for p in a['policy_explanations']]==[dict(p,text='') for p in b['policy_explanations']]
        source=evidence_path if cid!='FU01' else combined_path
        tasks.append(dict(task_id=f'T{i+1:02}',case_id=cid,title=TITLES[i],selection_reason=REASONS[i],
            input=copy.deepcopy({k:case[k] for k in ('before','after')}),facts=facts.model_dump(),
            disclaimer=row['api_result']['disclaimer'],variants=dict(A=a,B=b),questions=questions(i,facts.model_dump()),
            source=dict(file=source.name,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                source_milestone='M3.8E' if cid!='FU01' else 'M3.8F',actual_model_accepted=b is not None)))
    plan=allocations([t['task_id'] for t in tasks]);ready=all(t['variants']['B'] for t in tasks)
    key=dict(version='m38f-study-v1',locked_date='2026-10-26',ready=ready,actual_participants=0,
        tasks=tasks,allocations=plan,targets=dict(accuracy=.8,ease=4,serious_contradictions=0),
        verdict='M3_EXPLANATION_EVALUATION_READY_PARTICIPANTS_PENDING' if ready else 'M3_EXPLANATION_EVALUATION_REVISION_REQUIRED')
    write_json(destination/'private/study_key.json',key)
    with (destination/'private/allocations.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(plan[0]));writer.writeheader();writer.writerows(plan)
    for filename,fields in [('participants.csv',PARTICIPANT_FIELDS),('responses.csv',RESPONSE_FIELDS)]:
        path=destination/'templates'/filename;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('w',encoding='utf-8-sig',newline='') as stream:csv.writer(stream).writerow(fields)
    def public_task(t,variant):
        assert t['variants'][variant] is not None
        return dict(task_id=t['task_id'],title=t['title'],input=t['input'],facts=t['facts'],
            disclaimer=t['disclaimer'],document=t['variants'][variant],
            questions=[{k:v for k,v in q.items() if k not in ('correct','provenance','category')} for q in t['questions']])
    if ready:
        for slot in range(1,21):
            assigned=[r for r in plan if r['allocation_slot']==slot]
            ordered=[dict(order=r['order'],**public_task(next(t for t in tasks if t['task_id']==r['task_id']),r['condition'])) for r in assigned]
            x=assigned[0]['preference_X'];other='B' if x=='A' else 'A';t=tasks[-1]
            session=dict(version=key['version'],data_kind='real',participant_id=f'P{slot:02}',allocation_slot=slot,
                tasks=ordered,preference=dict(task_id='T08',X=public_task(t,x),Y=public_task(t,other)))
            write_json(destination/f'participant/sessions/P{slot:02}.json',session)
    qa_tasks=[dict(order=i+1,**public_task(t,'A' if i%2==0 else 'B')) for i,t in enumerate(tasks) if t['variants']['B'] is not None]
    qa=dict(version=key['version'],data_kind='synthetic',participant_id='SYN001',allocation_slot=1,
        ready=ready,preview_only=True,tasks=qa_tasks,preference=None,
        note='도구 조작 확인용 합성 미리보기. 실제 사람 평가/모델 재실행 아님. 복합 과제 B 미확보 시 해당 과제 제외.')
    write_json(destination/'participant/sessions/QA_SYN001.json',qa)
    output=analyze(key,[],[],'real');output['verdict']=key['verdict']
    write_json(destination/'results/initial_summary_real.json',output)
    (destination/'results/initial_summary_real.md').write_text(table(output),encoding='utf-8')
    return key

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--combined',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True);args=parser.parse_args()
    result=build(args.evidence,args.combined,args.destination)
    print(json.dumps(dict(tasks=len(result['tasks']),ready=result['ready'],slots=20,actual_participants=0,verdict=result['verdict']),ensure_ascii=False))
