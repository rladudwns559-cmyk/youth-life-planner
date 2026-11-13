import {useState} from 'react';
import GroupedInput from './GroupedInput';
import {type CashflowResult} from './cashflow';
import {assumeSupport,MAX_MONTHS} from './support-assumption';
import {routeLinks} from './portal-routing';

const won=(n:number)=>`${n.toLocaleString('ko-KR')}원`;
const signed=(n:number)=>`${n>0?'+':n<0?'−':''}${Math.abs(n).toLocaleString('ko-KR')}원`;
const quick=[100000,200000,300000];

/** Lays an assumed monthly support next to the real result. Never changes the result itself. */
export default function SupportAssumption({result}:{result:CashflowResult}){
  const [amount,setAmount]=useState(''),[months,setMonths]=useState('12');
  const amountOk=/^\d+$/.test(amount.trim())&&Number(amount)>0&&Number(amount)<=100_000_000;
  const monthsOk=/^\d+$/.test(months.trim())&&Number(months)>=1&&Number(months)<=MAX_MONTHS;
  const a=amountOk&&monthsOk?assumeSupport(result,Number(amount),Number(months)):null;
  const coversDeficit=a&&a.disposable_now<0?Math.min(a.monthly_support,-a.disposable_now):0;
  return <section className="budget-support" aria-labelledby="support-assume-heading">
    <h3 id="support-assume-heading">지원을 받는다고 가정하면?</h3>
    <p className="budget-hint">공고에 적힌 지원 금액을 넣으면, <b>받는다면</b> 매달 남는 돈이 얼마나 달라지는지 지금 결과 옆에 보여 드려요. 선정이 확정된 금액이 아니라서 위 계산 결과와 상품 추천에는 넣지 않아요.</p>
    <div className="budget-support-inputs">
      <div className="budget-field"><label htmlFor="assume-amount">매달 받는 지원금 (가정)</label>
        <div className="discovery-unit"><GroupedInput id="assume-amount" inputMode="numeric" autoComplete="off" placeholder="예: 200,000" value={amount} onChange={e=>setAmount(e.target.value)} aria-invalid={amount!==''&&!amountOk} aria-describedby="assume-amount-hint"/><span>원</span></div>
        <p className="budget-hint" id="assume-amount-hint">{amount!==''&&!amountOk?'1원~1억 원 사이의 원 단위 정수로 넣어 주세요.':'월세 지원·청년수당처럼 매달 받는 금액'}</p></div>
      <div className="budget-field"><label htmlFor="assume-months">받는 기간</label>
        <div className="discovery-unit"><GroupedInput id="assume-months" inputMode="numeric" autoComplete="off" value={months} onChange={e=>setMonths(e.target.value)} aria-invalid={!monthsOk} aria-describedby="assume-months-hint"/><span>개월</span></div>
        <p className="budget-hint" id="assume-months-hint">{monthsOk?'공고의 지원 기간(예: 12개월)':`1~${MAX_MONTHS}개월로 넣어 주세요.`}</p></div>
    </div>
    <div className="budget-presets" role="group" aria-label="지원금 빠른 입력">{quick.map(v=><button type="button" key={v} aria-pressed={amount===String(v)} onClick={()=>setAmount(String(v))}>월 {v/10000}만원</button>)}</div>
    {a&&<div className="budget-support-result" role="status">
      <table><caption className="sr-only">지금과 지원을 받는다고 가정했을 때 비교</caption>
        <thead><tr><th scope="col">항목</th><th scope="col">지금</th><th scope="col">받는다면 (가정)</th><th scope="col">차이</th></tr></thead>
        <tbody>
          <tr><th scope="row">한 달 여유자금</th><td>{signed(a.disposable_now)}</td><td>{signed(a.disposable_assumed)}</td><td className={a.disposable_assumed>a.disposable_now?'up':'same'}>{signed(a.disposable_assumed-a.disposable_now)}</td></tr>
          <tr><th scope="row">저축에 쓸 수 있는 금액</th><td>{won(a.savable_now)}</td><td>{won(a.savable_assumed)}</td><td className={a.monthly_gain>0?'up':'same'}>{a.monthly_gain===0?'변화 없음':signed(a.monthly_gain)}</td></tr>
        </tbody></table>
      <p className="budget-support-total">{a.monthly_gain>0
        ?<>{a.months}개월 동안 받으면 저축 여력이 <b>총 {won(a.total_gain)}</b> 늘어나요. (가정)</>
        :<>이 금액으로는 저축에 쓸 수 있는 금액이 늘지 않아요.</>}</p>
      {coversDeficit>0&&<p className="budget-hint">지원금 중 매달 {won(coversDeficit)}은 지금 부족한 생활비를 메우는 데 쓰여요.</p>}
      {a.capped&&<p className="budget-hint">정한 저축 상한 {won(result.user_savings_capacity!)} 때문에 지원금 일부는 저축 여력에 더하지 않았어요.</p>}
      <p className="budget-note">가정한 결과예요. 실제 지원 여부·금액·기간은 공고와 선정 결과에 따라 달라지고, 지원이 끝나면 위의 원래 결과로 돌아가요.</p>
    </div>}
    <a className="budget-secondary" href={routeLinks.programs}>받을 수 있는 지원 찾기 <span aria-hidden="true">→</span></a>
  </section>;
}
