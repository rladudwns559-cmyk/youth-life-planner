import {render,screen,fireEvent} from '@testing-library/react';
import {it,expect,vi,afterEach} from 'vitest';
import current from './public-data/financial-renewals.json';
import {financialFreshness,financialProducts,productRecheck,renewedDecision} from './financial-snapshots';
import {verifiedBasicRate} from './RecommendationShelf';
import ProductExplorer from './ProductExplorer';
afterEach(()=>vi.useRealTimers());

it('routes every actual current record without silently reviving a hold',()=>{
 const asOf=current.built_on;
 for(const [id,r] of Object.entries(current.records)){
  if(r.status!=='CURRENT'){
   expect(renewedDecision(id,300000,12,asOf)).toBe('REVIEW');
   expect(verifiedBasicRate(id,12,asOf)).toBeNull();
  }else{
   expect(productRecheck(id,asOf)?.checked_on).toBe(r.checked_on);
   expect(financialProducts(asOf).find(p=>p.product_id===id)?.sources).toEqual(r.product.sources);
  }
 }
 expect(financialFreshness(asOf).checked).toBe(Object.keys(current.records).length);
});

it('expires the actual current records after their own last deadline',()=>{
 const last=Object.values(current.records).filter(r=>r.status==='CURRENT').map(r=>r.valid_until!).sort().at(-1)!;
 const d=new Date(last+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+1);const after=d.toISOString().slice(0,10);
 expect(financialFreshness(after).active).toBe(0);
 for(const id of Object.keys(current.records))expect(verifiedBasicRate(id,12,after)).toBeNull();
});

it('renders the actual current artifact and recommends only live rechecked records',()=>{
 vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date(current.built_on+'T03:00:00Z'));
 render(<ProductExplorer/>);
 fireEvent.change(screen.getByLabelText('매월 저축할 금액'),{target:{value:'300000'}});
 fireEvent.click(screen.getByRole('button',{name:'추천 상품 보기'}));
 const cards=Array.from(document.querySelectorAll('[data-recommended-id]'));
 for(const c of cards){
  const id=c.getAttribute('data-recommended-id')!;
  expect(productRecheck(id,current.built_on)?.status).toBe('CURRENT');
  expect(verifiedBasicRate(id,12,current.built_on)).not.toBeNull();
 }
 const viable=financialProducts(current.built_on).filter(p=>p.kind==='SAVINGS'&&['FIT','PARTIAL'].includes(renewedDecision(p.product_id,300000,12,current.built_on)??'')&&verifiedBasicRate(p.product_id,12,current.built_on));
 expect(cards.length).toBe(Math.min(3,viable.length));
});
