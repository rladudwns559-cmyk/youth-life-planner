"""M3.8F 전용 오프라인 채점. 모델 호출·제품 코드 변경·사람 응답 생성 없음."""
import argparse
import csv
import json
import math
from pathlib import Path
import re
import statistics

PARTICIPANT_FIELDS = ['data_kind','participant_id','allocation_slot','consented','session_status',
                      'preference','added_value','preference_comment']
RESPONSE_FIELDS = ['data_kind','participant_id','task_id','order','task_status','elapsed_ms','interrupted',
                   'q1','q2','q3','q4','ease','trust','usefulness','comment']
KINDS = {'real': r'P\d{2,3}', 'synthetic': r'SYN\d{3}'}
PREFERENCES = {'','X','Y','tie','neither'}
VALUES = {'','X','Y','same_information','neither_clear','not_sure'}

class StudyError(ValueError):
    pass

def ensure(ok, message):
    if not ok:
        raise StudyError(message)

def allocations(task_ids, slots=20):
    ensure(len(task_ids)==8 and len(set(task_ids))==8, 'Eight distinct tasks required')
    result=[]
    for slot in range(1,slots+1):
        shift=((slot-1)//2)%8
        ordered=task_ids[shift:]+task_ids[:shift]
        for position, task in enumerate(ordered,1):
            result.append(dict(allocation_slot=slot,order=position,task_id=task,
                condition='A' if (task_ids.index(task)+(slot-1)%2)%2==0 else 'B',
                preference_X='A' if slot%2 else 'B'))
    return result

def read_csv(path, fields):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        ensure(reader.fieldnames==fields, f'CSV header mismatch: {path}')
        rows=list(reader)
        ensure(all(None not in r and all(v is not None for v in r.values()) for r in rows),'Malformed CSV row')
        return rows

def boolean(value, label):
    ensure(value in ('true','false'), f'{label}: expected true/false')
    return value=='true'

def integer(value, label, minimum=0, maximum=None, optional=False):
    if optional and value=='':
        return None
    ensure(isinstance(value,str) and re.fullmatch(r'\d+',value) is not None, f'{label}: invalid integer')
    n=int(value)
    ensure(n>=minimum and (maximum is None or n<=maximum), f'{label}: out of range')
    return n

def answers(value, question):
    if value=='':
        return None
    parts=value.split('|')
    ensure(len(parts)==len(set(parts)), 'Duplicate answer choice')
    allowed={c['value'] for c in question['choices']}
    ensure(set(parts)<=allowed, 'Unknown answer choice')
    ensure(question['multiple'] or len(parts)==1,'Multiple answers to single-choice question')
    ensure(not ({'DK','NONE'} & set(parts)) or len(parts)==1,'Exclusive answer mixed with others')
    return set(parts)

def average(values):
    return statistics.mean(values) if values else None

def validate(key, participants, responses, kind):
    ensure(kind in KINDS, 'Unknown data kind')
    tasks={t['task_id']:t for t in key['tasks']}
    ensure(len(tasks)==8,'Task key mismatch')
    plan={(r['allocation_slot'],r['task_id']):r for r in key['allocations']}
    persons={}; slots=set()
    for raw in participants:
        ensure(set(raw)==set(PARTICIPANT_FIELDS), 'Participant columns mismatch')
        p=raw.copy(); pid=p['participant_id']
        ensure(p['data_kind']==kind and re.fullmatch(KINDS[kind],pid) is not None,'Data kind / anonymous ID mismatch')
        ensure(pid not in persons,'Duplicate participant ID')
        slot=integer(p['allocation_slot'],'allocation_slot',1,20)
        ensure(slot not in slots,'Duplicate allocation slot');slots.add(slot)
        p['allocation_slot']=slot;p['consented']=boolean(p['consented'],'consented')
        ensure(p['session_status'] in ('started','completed','withdrawn'),'Invalid session status')
        ensure(p['consented'] or p['session_status']=='withdrawn','No consent')
        ensure(p['preference'] in PREFERENCES and p['added_value'] in VALUES,'Invalid preference')
        persons[pid]=p
    seen=set(); clean=[]
    for raw in responses:
        ensure(set(raw)==set(RESPONSE_FIELDS),'Response columns mismatch')
        r=raw.copy();pid=r['participant_id'];tid=r['task_id']
        ensure(r['data_kind']==kind,'Mixed real/synthetic rows')
        ensure(pid in persons and tid in tasks,'Unknown participant or task')
        ensure((pid,tid) not in seen,'Duplicate participant/task response');seen.add((pid,tid))
        assignment=plan[(persons[pid]['allocation_slot'],tid)]
        ensure(integer(r['order'],'order',1,8)==assignment['order'],'Order does not match locked allocation')
        ensure(r['task_status'] in ('submitted','partial'),'Invalid task status')
        r.update(condition=assignment['condition'],order=assignment['order'],
            elapsed_ms=integer(r['elapsed_ms'],'elapsed_ms',0,optional=True),
            interrupted=boolean(r['interrupted'],'interrupted'))
        r['answers']={q['id']:answers(r[q['id']],q) for q in tasks[tid]['questions']}
        for field in ('ease','trust','usefulness'):
            r[field]=integer(r[field],field,1,5,optional=True)
        clean.append(r)
    for pid,p in persons.items():
        rows=[r for r in clean if r['participant_id']==pid]
        if p['session_status']=='completed':
            ensure(len(rows)==8 and all(r['task_status']=='submitted' for r in rows),'Completed session missing submitted tasks')
        if p['preference'] or p['added_value']:
            ensure(p['session_status']=='completed','Preference must follow completed primary tasks')
    return tasks,persons,clean

def analyze(key, participants, responses, kind='real'):
    tasks,persons,rows=validate(key,participants,responses,kind)
    included={pid:p for pid,p in persons.items() if p['consented'] and p['session_status']!='withdrawn'}
    rows=[r for r in rows if r['participant_id'] in included]
    scored=[]
    for r in rows:
        items=[]
        for q in tasks[r['task_id']]['questions']:
            answer=r['answers'][q['id']];correct=set(q['correct'])
            observed=answer is not None;dk=answer=={'DK'}
            items.append(dict(question=q['id'],category=q['category'],observed=observed,dont_know=dk,
                correct=None if not observed else answer==correct,
                observed_wrong=observed and not dk and answer!=correct,
                missing_confirmations=len(correct-answer) if observed and not dk and q['category']=='confirmation' else None))
        scored.append(dict(participant_id=r['participant_id'],task_id=r['task_id'],condition=r['condition'],
            complete=r['task_status']=='submitted' and all(i['observed'] for i in items),
            elapsed_ms=r['elapsed_ms'],interrupted=r['interrupted'],
            **{f:r[f] for f in ('ease','trust','usefulness')},items=items))
    def condition_result(condition):
        chosen=[r for r in scored if r['condition']==condition];items=[i for r in chosen for i in r['items']]
        n=len(included);denominator=n*16
        correct=sum(i['correct'] is True for i in items);observed=sum(i['observed'] for i in items)
        per_person=[sum(i['correct'] is True for r in chosen if r['participant_id']==pid for i in r['items'])/16 for pid in included]
        times=[r['elapsed_ms']/1000 for r in chosen if r['elapsed_ms'] is not None]
        uninterrupted=[r['elapsed_ms']/1000 for r in chosen if r['elapsed_ms'] is not None and not r['interrupted']]
        return dict(assigned_tasks=n*4,recorded_tasks=len(chosen),answered_items=observed,assigned_items=denominator,
            correct_items=correct if n else None,missing_items=denominator-observed if n else None,
            dont_know_items=sum(i['dont_know'] for i in items) if n else None,
            accuracy_assigned=average(per_person),accuracy_observed=correct/observed if observed else None,
            completed_tasks=sum(r['complete'] for r in chosen) if n else None,
            completion_rate=sum(r['complete'] for r in chosen)/(n*4) if n else None,
            time_n=len(times),time_mean_seconds=average(times),time_median_seconds=statistics.median(times) if times else None,
            uninterrupted_time_n=len(uninterrupted),uninterrupted_time_mean_seconds=average(uninterrupted),
            ratings={f:dict(n=len(v),mean=average(v)) for f in ('ease','trust','usefulness')
                     for v in [[r[f] for r in chosen if r[f] is not None]]},
            observed_wrong_by_category={cat:sum(i['observed_wrong'] for i in items if i['category']==cat)
                                       if any(i['observed'] and not i['dont_know'] for i in items if i['category']==cat) else None
                                       for cat in ('money','policy','unknown','confirmation','reason','certainty')},
            confirmation_omissions=sum(i['missing_confirmations'] or 0 for i in items)
                if any(i['missing_confirmations'] is not None for i in items) else None)
    conditions={c:condition_result(c) for c in ('A','B')}
    paired=[]
    for pid in included:
        score={c:sum(i['correct'] is True for r in scored if r['participant_id']==pid and r['condition']==c for i in r['items'])/16 for c in ('A','B')}
        paired.append(score['B']-score['A'])
    preferences=[];values=[]
    for pid,p in included.items():
        x=next(r['preference_X'] for r in key['allocations'] if r['allocation_slot']==p['allocation_slot'])
        convert=lambda v: x if v=='X' else ('B' if x=='A' else 'A') if v=='Y' else v
        if p['preference']:preferences.append(convert(p['preference']))
        if p['added_value']:values.append(convert(p['added_value']))
    n=len(included)
    return dict(milestone='M3.8F',data_kind=kind,synthetic_analysis_only=kind=='synthetic',
        actual_participants=n if kind=='real' else 0,synthetic_participants=n if kind=='synthetic' else 0,
        enrolled_records=len(persons),withdrawn_records=sum(p['session_status']=='withdrawn' for p in persons.values()),
        real_response_rows=len(rows) if kind=='real' else 0,response_rows=len(rows),conditions=conditions,
        participant_paired_accuracy_delta_B_minus_A=average(paired),
        preference=dict(n=len(preferences),counts={v:preferences.count(v) for v in ('A','B','tie','neither')}),
        added_value=dict(n=len(values),counts={v:values.count(v) for v in ('A','B','same_information','neither_clear','not_sure')}),
        serious_model_contradictions=None,serious_contradiction_review='NOT_PERFORMED',
        ai_added_value_conclusion='NOT_EVALUATED' if not n else 'EXPLORATORY_REVIEW_REQUIRED',
        verdict='SYNTHETIC_ANALYSIS_TEST_ONLY' if kind=='synthetic' else
            'M3_EXPLANATION_EVALUATION_READY_PARTICIPANTS_PENDING' if not n else 'M3_EXPLANATION_HUMAN_EVALUATION_PARTIAL',
        note='결측 원자료는 유지. assigned 정답률만 미응답 비득점 처리. DK는 별도 집계. 사람 단위 탐색 비교이며 우수성 자동 판정 없음.')

def load_sessions(directory):
    participants=[];responses=[]
    for path in sorted(Path(directory).glob('*.json')):
        d=json.loads(path.read_text(encoding='utf-8'))
        ensure(set(d)=={'participant','responses'},'Invalid session export')
        participants.append(d['participant']);responses.extend(d['responses'])
    return participants,responses

def table(result):
    def show(v):
        return '미측정' if v is None else f'{v:.3f}' if isinstance(v,float) else str(v)
    lines=['# M3.8F 집계 결과',f"\n자료 구분: **{result['data_kind']}**. 실제 참가자 {result['actual_participants']}명 / 실제 응답 {result['real_response_rows']}건.",
           '\n| 지표 | A 정형 | B 후보 선택 |','|---|---:|---:|']
    for label,field in [('할당 정답률','accuracy_assigned'),('관측 응답 정답률','accuracy_observed'),('완료율','completion_rate'),('평균 시간(초)','time_mean_seconds')]:
        lines.append('| '+label+' | '+' | '.join(show(result['conditions'][c][field]) for c in ('A','B'))+' |')
    for field,label in [('ease','이해 용이성'),('trust','신뢰감'),('usefulness','유용성')]:
        lines.append('| '+label+' | '+' | '.join(show(result['conditions'][c]['ratings'][field]['mean']) for c in ('A','B'))+' |')
    lines+=['',f"최종 상태: `{result['verdict']}`",'','목표 80%·4/5·중대한 모순0은 달성 실적이 아니다. 모델 모순은 별도 근거 검토가 필요하다.']
    return '\n'.join(lines)+'\n'

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key',type=Path,required=True)
    parser.add_argument('--kind',choices=KINDS,required=True)
    parser.add_argument('--participants',type=Path);parser.add_argument('--responses',type=Path)
    parser.add_argument('--sessions',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    ensure(bool(args.sessions)!=bool(args.participants and args.responses),'Use CSV pair or session directory')
    people,rows=load_sessions(args.sessions) if args.sessions else (read_csv(args.participants,PARTICIPANT_FIELDS),read_csv(args.responses,RESPONSE_FIELDS))
    key=json.loads(args.key.read_text(encoding='utf-8'));ensure(key['ready'],'Study stimuli not ready')
    result=analyze(key,people,rows,args.kind);args.output.mkdir(parents=True,exist_ok=True)
    target=args.output/f'summary_{args.kind}'
    ensure(not target.with_suffix('.json').exists(),'Refuse to overwrite previous analysis; use a new directory')
    target.with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    target.with_suffix('.md').write_text(table(result),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('data_kind','actual_participants','real_response_rows','verdict')},ensure_ascii=False))

if __name__=='__main__':
    main()
