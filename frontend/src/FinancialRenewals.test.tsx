import {render,screen,fireEvent,within} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
// Bank correction evidence from Nov 6 remains reproducible after future renewals.
vi.mock('./public-data/financial-renewals.json',async()=>({default:(await import('./test-fixtures/financial-renewals-20261106.json')).default}));
import ProductExplorer,{readPreparedDecision} from './ProductExplorer';
import RegionalPrograms from './RegionalPrograms';
import DataFreshness from './DataFreshness';
import {verifiedBasicRate} from './RecommendationShelf';
import {financialProducts,productRecheck,financialFreshness,discontinuedRechecks} from './financial-snapshots';
import original from './public-data/product-expanded.json';

beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-07T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('Financial profile must remain local');}));});
afterEach(()=>vi.useRealTimers());
const byId=(id:string,day='2026-11-07')=>financialProducts(day).find(p=>p.product_id===id)!;

it('keeps independently rechecked products usable after the old shared expiry',()=>{
 expect(original.valid_until).toBe('2026-11-06');
 expect(readPreparedDecision(byId('KAKAO-FREE-SAVINGS'),300000,12,'2026-11-07')).toBe('FIT');
 expect(verifiedBasicRate('KAKAO-FREE-SAVINGS',12,'2026-11-07')?.base_rate_percent).toBe('3.85');
 expect(financialFreshness('2026-11-07').expired).toBe(false);
 expect(readPreparedDecision(byId('KAKAO-FREE-SAVINGS'),300000,12,'2026-11-14')).toBe('STALE');
 expect(verifiedBasicRate('KAKAO-FREE-SAVINGS',12,'2026-11-14')).toBeNull();
});

it('preserves old snapshots while exposing corrected basic and conditional rates only after recheck',()=>{
 expect(byId('PEPPER-TERM-DEPOSIT','2026-11-03').sources.every(s=>s.reviewed_on<='2026-11-03')).toBe(true);
 const current=verifiedBasicRate('PEPPER-TERM-DEPOSIT',12,'2026-11-07')!;
 expect(current.base_rate_percent).toBe('3.80');expect(current.max_total_rate_percent).toBe('3.95');
 expect(verifiedBasicRate('NOV3-SB-BULIM-DEPOSIT',12,'2026-11-07')?.base_rate_percent).toBe('4.00');
 expect(byId('NOV3-SB-BULIM-LONG-DEPOSIT').rates.find(r=>r.min_months===12)?.base_rate_percent).toBe('4.10');
 expect(verifiedBasicRate('NOV3-SB-BULIM-LONG-DEPOSIT',12,'2026-11-07')).toBeNull();
 expect(byId('PEPPER-TERM-DEPOSIT').eligibility).toBe('UNKNOWN');
 expect(byId('PEPPER-TERM-DEPOSIT').calculation).toBeNull();
});

it('never revives held products, failed-fetch products or untouched expired products',()=>{
 expect(productRecheck('IBKSB-REGULAR-SAVING','2026-11-07')?.status).toBe('UNCONFIRMED');
 expect(readPreparedDecision(byId('IBKSB-REGULAR-SAVING'),300000,12,'2026-11-07')).toBe('REVIEW');
 expect(verifiedBasicRate('IBKSB-REGULAR-SAVING',12,'2026-11-07')).toBeNull();
 const untouched=financialProducts('2026-11-07').find(p=>!productRecheck(p.product_id,'2026-11-07'))!;
 expect(readPreparedDecision(untouched,300000,12,'2026-11-07')).toBe('STALE');
 expect(financialProducts('2026-11-07').some(p=>p.product_id==='NOV3-KB-SALARY')).toBe(false);
 expect(discontinuedRechecks('2026-11-07')[0].already_excluded_from_current_326).toBe(true);
});

it('clearly separates renewed information, rate coverage and unverified history',()=>{
 render(<DataFreshness scope="products"/>);
 const note=screen.getByRole('complementary',{name:'금융상품 자료 확인 안내'});
 expect(note).toHaveTextContent('자료 확인 2026-11-06');
 expect(note).toHaveTextContent('화면 기준 2026-11-07');
 expect(note).toHaveTextContent('기본금리 근거');expect(note).toHaveTextContent('이번 재확인 전 자료');
 expect(note).not.toHaveClass('needs-review');
 fireEvent.click(screen.getByText('판매 종료로 제외된 상품 확인'));
 expect(screen.getByRole('link',{name:'은행 공식 종료 공지 ↗'})).toHaveAttribute('href',expect.stringContaining('articleId=141870'));
});

it('offers the same verified recommendation order in both actual entry flows after expiry',()=>{
 const view=render(<ProductExplorer/>);
 fireEvent.change(screen.getByLabelText('매월 저축할 금액'),{target:{value:'300000'}});
 fireEvent.click(screen.getByRole('button',{name:'추천 상품 보기'}));
 const ids=Array.from(document.querySelectorAll('[data-recommended-id]'),p=>p.getAttribute('data-recommended-id'));
 expect(ids).toHaveLength(3);
 expect(ids.every(id=>productRecheck(id!,'2026-11-07')?.status==='CURRENT')).toBe(true);
 const values=ids.map(id=>Number(verifiedBasicRate(id!,12,'2026-11-07')!.base_rate_percent));
 expect(values).toEqual([...values].sort((a,b)=>b-a));
 view.unmount();render(<RegionalPrograms browse={false}/>);
 fireEvent.click(screen.getByRole('button',{name:'사업 비교하기 (0/3)'}));const dialog=screen.getByRole('dialog');const d=within(dialog);
 fireEvent.click(d.getByRole('button',{name:'적금·예금 찾기'}));
 fireEvent.change(d.getByLabelText('월 납입액 (원)'),{target:{value:'300000'}});
 expect(Array.from(dialog.querySelectorAll('[data-product-id]')).slice(0,3).map(p=>p.getAttribute('data-product-id'))).toEqual(ids);
 expect(fetch).not.toHaveBeenCalled();expect(localStorage.length).toBe(0);
});
