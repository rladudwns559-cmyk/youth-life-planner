"""Import a manually obtained, dated bank-republished FSS table, offline only.

Not a live FSS client. No network, credentials, inference or eligibility calls.
Unknown columns, periods and monetary/rate syntax fail closed.
"""
import argparse,hashlib,json,re
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

SOURCE_URL='https://blog.kbanknow.com/rate-compare/savings-rate-comparison-261023/'
HEADERS=['순서','금융회사','금융권','상품명','기간','적립','유형','기본금리','우대금리']
class Table(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.tables=0;self.active=False;self.in_cell=False;self.parts=[];self.row=[];self.rows=[];self.cell_tag=None
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.tables+=1;self.active=True
        if not self.active:return
        if tag=='tr':self.row=[]
        if tag in ('td','th'):self.in_cell=True;self.parts=[];self.cell_tag=tag
    def handle_data(self,data):
        if self.active and self.in_cell:self.parts.append(data)
    def handle_endtag(self,tag):
        if not self.active:return
        if tag in ('td','th') and self.in_cell:
            self.row.append(re.sub(r'\s+',' ',''.join(self.parts)).strip());self.in_cell=False
        if tag=='tr' and self.row:self.rows.append(self.row);self.row=[]
        if tag=='table':self.active=False

def parse_disclosure(raw:bytes,reviewed_on:str,basis_date:str='2026-10-23'):
    reviewed=date.fromisoformat(reviewed_on);basis=date.fromisoformat(basis_date)
    if basis>reviewed:raise ValueError('FUTURE_DISCLOSURE')
    text=raw.decode('utf-8-sig',errors='strict')
    if basis.isoformat() not in text and basis.strftime('%Y.%m.%d') not in text:raise ValueError('BASIS_DATE_NOT_IN_SOURCE')
    table=Table();table.feed(text);table.close()
    if table.tables!=1 or not table.rows or table.rows[0]!=HEADERS:raise ValueError('UNRECOGNIZED_DISCLOSURE_TABLE')
    groups={};row_ids=[]
    for v in table.rows[1:]:
        if len(v)!=9 or not v[0].isdigit() or v[2] not in ('1금융권','2금융권') or v[4]!='12개월' or v[5] not in ('정액적립식','자유적립식') or v[6] not in ('단리','복리'):raise ValueError('UNRECOGNIZED_DISCLOSURE_ROW')
        if not v[1] or not v[3]:raise ValueError('MISSING_DISCLOSURE_IDENTITY')
        for rate in v[7:9]:
            if not re.fullmatch(r'\d{1,3}(?:\.\d+)?%',rate) or not Decimal(0)<=Decimal(rate[:-1])<=Decimal(100):raise ValueError('INVALID_DISCLOSURE_RATE')
        row_id=int(v[0]);row_ids.append(row_id);key=(v[1],v[3])
        group=groups.setdefault(key,dict(product_id='DISC-'+hashlib.sha256('|'.join(key).encode()).hexdigest()[:16],institution=v[1],product_name=v[3],sector='BANK' if v[2]=='1금융권' else 'SAVINGS_BANK',options=[],row_numbers=[],current_sale_verified=False,eligibility='UNKNOWN',monthly_limit=None))
        if group['sector']!=('BANK' if v[2]=='1금융권' else 'SAVINGS_BANK'):raise ValueError('CONFLICTING_SECTOR')
        option=dict(months=12,method=v[5],interest_type=v[6],base_rate_percent=v[7][:-1],source_preferential_rate_percent=v[8][:-1])
        if option not in group['options']:group['options'].append(option)
        group['row_numbers'].append(row_id)
    if not row_ids or row_ids!=list(range(1,len(row_ids)+1)):raise ValueError('INCOMPLETE_OR_DUPLICATE_ROWS')
    return dict(schema_version='official-republished-disclosure-v1',reviewed_on=reviewed_on,basis_date=basis_date,source_url=SOURCE_URL,source_title='케이뱅크 공식 블로그의 금융감독원 API 공시 재게재',source_level='BANK_REPUBLISHED_FSS_DISCLOSURE',source_sha256=hashlib.sha256(raw).hexdigest(),raw_rows=len(row_ids),unique_products=len(groups),institutions=len({k[0] for k in groups}),coverage_note='2026-10-23 기준 12개월 적금 공시 참고 목록입니다. 납입한도·가입대상·현재 판매 여부는 개별 은행에서 검증되지 않았습니다. 개인 조건 비교 및 금리 순위에 사용하지 않습니다.',products=list(groups.values()))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--reviewed-on',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=parse_disclosure(args.input.read_bytes(),args.reviewed_on)
    args.output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('raw_rows','unique_products','institutions','source_sha256')}))
if __name__=='__main__':main()
