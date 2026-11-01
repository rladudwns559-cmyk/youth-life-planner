import {fireEvent,render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,describe,it,expect,vi} from 'vitest';
import DisclosureDirectory from './DisclosureDirectory';
import data from './public-data/disclosure-directory.json';
beforeEach(()=>{vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('No profile or source requests');}));});
describe('dated official-republished disclosure directory',()=>{
 it('distinguishes source rows from products and personal comparisons',()=>{
  render(<DisclosureDirectory/>);expect(screen.getByText(/97개 금융회사 · 상품명 기준 299개 · 원문 416개 공시 행/)).toBeVisible();expect(screen.getAllByTestId('disclosure-product')).toHaveLength(20);expect(screen.getByText(/두 목록의 수를 합산하지 않습니다/)).toBeVisible();expect(document.querySelector('.code-fit,.code-partial')).not.toBeInTheDocument();expect(fetch).not.toHaveBeenCalled();
 });
 it('groups the same product variants and retains dated source names',async()=>{
  render(<DisclosureDirectory/>);fireEvent.change(screen.getByLabelText('공시 상품 검색'),{target:{value:'BNK저축은행'}});expect(screen.getAllByTestId('disclosure-product')).toHaveLength(1);
  const c=within(screen.getAllByTestId('disclosure-product')[0]);await userEvent.click(c.getByText('12개월 공시 금리·적립 방식 참고'));expect(c.getAllByRole('row')).toHaveLength(3);expect(c.getByRole('columnheader',{name:'원문 우대금리'})).toBeVisible();expect(c.getByRole('link',{name:/공시 재게재 원문에서 확인/})).toHaveAttribute('href',data.source_url);
 });
 it('filters institution and sector, resets incompatible institution, and paginates',async()=>{
  render(<DisclosureDirectory/>);await userEvent.click(screen.getByRole('button',{name:'공시 다음'}));expect(screen.getByText('2 / 15 페이지')).toBeVisible();await userEvent.selectOptions(screen.getByLabelText('공시 금융회사'),'BNK저축은행');expect(screen.getAllByTestId('disclosure-product')).toHaveLength(1);
  await userEvent.selectOptions(screen.getByLabelText('금융권'),'BANK');expect(screen.getByLabelText('공시 금융회사')).toHaveValue('ALL');expect(screen.getAllByTestId('disclosure-product').every(c=>c.textContent!.includes(' · 은행 · '))).toBe(true);
 });
 it('reports empty results honestly and restores the directory',async()=>{
  render(<DisclosureDirectory/>);fireEvent.change(screen.getByLabelText('공시 상품 검색'),{target:{value:'해당없음123'}});expect(screen.queryAllByTestId('disclosure-product')).toHaveLength(0);expect(screen.getByText(/이 공시 목록 밖에도 상품/)).toBeVisible();await userEvent.click(screen.getByRole('button',{name:'공시 검색 초기화'}));expect(screen.getAllByTestId('disclosure-product')).toHaveLength(20);
 });
});
