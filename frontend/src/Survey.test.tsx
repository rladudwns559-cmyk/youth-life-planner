import {render,screen,fireEvent,within} from '@testing-library/react';
import {it,expect,describe} from 'vitest';
import Survey from './Survey';
import {SURVEY_QUESTIONS,prefilledFormUrl,missingAnswers} from './survey-config';
import {resolveRoute,routeLinks} from './portal-routing';

const form={formUrl:'https://docs.google.com/forms/d/e/1FAIpQLSexample_ID-123/viewform',entries:Object.fromEntries(SURVEY_QUESTIONS.map((q,i)=>[q.id,'entry.'+(1000+i)]))};
const full=Object.fromEntries(SURVEY_QUESTIONS.map(q=>[q.id,q.type==='scale'?'4':q.options[1]]));

describe('prefilled Google Form link',()=>{
  it('maps every answer to its entry and encodes Korean text',()=>{
    const url=new URL(prefilledFormUrl(full,form)!);
    expect(url.origin+url.pathname).toBe(form.formUrl);
    expect(url.searchParams.get('usp')).toBe('pp_url');
    for(const q of SURVEY_QUESTIONS)expect(url.searchParams.get(form.entries[q.id])).toBe(full[q.id]);
  });
  it('refuses an unconnected form, a non-Google URL, a missing entry or an answer outside the options',()=>{
    expect(prefilledFormUrl(full,{formUrl:'',entries:{}})).toBeNull();
    expect(prefilledFormUrl(full,{...form,formUrl:'https://example.com/forms/d/e/x/viewform'})).toBeNull();
    expect(prefilledFormUrl(full,{...form,entries:{...form.entries,age:'name'}})).toBeNull();
    expect(prefilledFormUrl({...full,age:'홍길동 010-0000-0000'},form)).toBeNull();
    expect(prefilledFormUrl({...full,before:'7'},form)).toBeNull();
  });
  it('lists unanswered questions',()=>{
    expect(missingAnswers({})).toHaveLength(SURVEY_QUESTIONS.length);
    expect(missingAnswers(full)).toEqual([]);
  });
});

it('keeps submission closed until a form is connected',()=>{
  render(<Survey form={{formUrl:'',entries:{}}}/>);
  expect(screen.getByText(/구글 폼을 연결하는 중/)).toBeVisible();
  expect(screen.getByRole('button',{name:'구글 폼 연결 전 · 제출 불가'})).toHaveAttribute('aria-disabled','true');
  expect(screen.queryByRole('link',{name:/구글 폼에서 확인하고 제출하기/})).toBeNull();
});

it('asks for missing answers, then opens the prefilled form in a new tab',()=>{
  render(<Survey form={form}/>);
  fireEvent.click(screen.getByRole('button',{name:'구글 폼에서 확인하고 제출하기'}));
  expect(screen.getByText(`답하지 않은 문항이 ${SURVEY_QUESTIONS.length}개 있어요.`)).toBeVisible();
  expect(screen.getAllByText('이 문항에 답해 주세요.')).toHaveLength(SURVEY_QUESTIONS.length);
  for(const q of SURVEY_QUESTIONS){
    const group=screen.getByRole('group',{name:new RegExp(q.text.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))});
    fireEvent.click(within(group).getAllByRole('radio')[q.type==='scale'?3:1]);
  }
  const link=screen.getByRole('link',{name:/구글 폼에서 확인하고 제출하기/});
  expect(link).toHaveAttribute('target','_blank');
  expect(link).toHaveAttribute('rel','noopener noreferrer');
  expect(link.getAttribute('href')).toBe(prefilledFormUrl(full,form));
  expect(screen.queryByText('이 문항에 답해 주세요.')).toBeNull();
});

it('has its own route',()=>{
  expect(resolveRoute('#/survey')).toBe('survey');
  expect(routeLinks.survey).toBe('#/survey');
});
