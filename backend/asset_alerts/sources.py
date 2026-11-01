"""Bounded public-source adapters. Never generate eligibility rules from a page."""
import hashlib,json,re,copy
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit,urljoin
import httpx
from bs4 import BeautifulSoup

KST=timezone(timedelta(hours=9))
MAX_BYTES=2_000_000
def stamp():return datetime.now(KST).isoformat()
def sha(value):return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()
def normalized(text):return re.sub(r'\s+',' ',text).strip()
def compact(text):return re.sub(r'\s+','',text).lower()

def validate_url(url,hosts):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in hosts or p.port not in (None,443) or p.username or p.password or p.fragment:raise ValueError('UNTRUSTED_SOURCE_URL')
    return url

def fetch(url,hosts):
    validate_url(url,hosts)
    with httpx.Client(timeout=10,follow_redirects=False,trust_env=False) as client:
        with client.stream('GET',url,headers={'User-Agent':'AI-X-Youth-Asset-Discovery/1.0 (public notices; 6-hour checks)'}) as response:
            response.raise_for_status()
            if response.status_code!=200:raise ValueError('SOURCE_NOT_OK')
            body=bytearray()
            for block in response.iter_bytes():
                body.extend(block)
                if len(body)>MAX_BYTES:raise ValueError('SOURCE_TOO_LARGE')
            media=response.headers.get('content-type','').lower()
            if bytes(body[:4])==b'%PDF':media='application/pdf'
            if 'pdf' not in media and 'html' not in media:raise ValueError('SOURCE_FORMAT_CHANGED')
            return bytes(body),media

def content(body,selector=None):
    if body[:4]==b'%PDF':return sha(body),'',None
    soup=BeautifulSoup(body,'html.parser')
    if selector:
        nodes=[]
        for part in selector.split(','):
            selected=soup.select(part.strip())
            if len(selected)!=1:raise ValueError('SOURCE_LAYOUT_CHANGED')
            nodes.append(selected[0])
        node=soup.new_tag('section')
        for selected in nodes:node.append(copy.deepcopy(selected))
    else:node=soup.body
    if node is None:raise ValueError('SOURCE_LAYOUT_CHANGED')
    for hidden in node.select('script,style,noscript,nav,header,footer'):hidden.decompose()
    text=node.get_text('\n',strip=True)
    if len(text)<30:raise ValueError('SOURCE_CONTENT_EMPTY')
    # Images/attachments may contain material terms, even if visible text is unchanged.
    assets=sorted((e.get('src') or e.get('href') or '') for e in node.select('img[src],a[href]'))
    return sha(normalized(text)+'\n'+json.dumps(assets,ensure_ascii=False)),text,soup

def identify(title,programs):
    t=compact(title)
    matches=[p for p in programs if any(compact(a) in t for a in [p['title'],*p.get('aliases',[])])]
    return matches[0] if len(matches)==1 else None

def links(body,url,programs,hosts):
    soup=BeautifulSoup(body,'html.parser');result={}
    for a in soup.select('a[href]'):
        title=normalized(a.get('title') or a.get_text(' ',strip=True))
        if not identify(title,programs) and not ('청년' in title and any(w in title for w in ['적금','통장','자산형성'])):continue
        if not any(w in title for w in ['모집','신청','접수']):continue
        if any(w in title for w in ['수기','교육','후기','실적','선정 결과','선정결과','최종선정','서류심사','계좌개설','대출']):continue
        href=a.get('href','')
        if not href or href.startswith(('#','javascript:')):continue
        target=urljoin(url,href).split('#')[0]
        try:validate_url(target,hosts)
        except ValueError:continue
        if target==url or any(x in target for x in ['download','login','logout','delete','remove']):continue
        if len(target)>1200:continue
        result[target]=title[:240]
    return list(result.items())[:12]

# Only explicitly labelled application periods. Narrative dates, birthdays,
# selection/education/account-opening dates are deliberately not inferred.
RANGE=re.compile(r'(?:(?P<y>20\d{2})\s*[.년/-]\s*)?(?P<m>\d{1,2})\s*[.월/-]\s*(?P<d>\d{1,2})\s*(?:[.일])?\s*(?:\([월화수목금토일]\))?\s*(?:(?P<h>\d{1,2}):(?P<min>\d{2})\s*)?(?:부터\s*)?[~～∼–—]\s*(?:(?P<ey>20\d{2})\s*[.년/-]\s*)?(?:(?P<em>\d{1,2})\s*[.월/-]\s*)?(?P<ed>\d{1,2})\s*(?:[.일])?\s*(?:\([월화수목금토일]\))?\s*(?:(?P<eh>\d{1,2}):(?P<emin>\d{2}))?')

def parse_notice(body,url,title,programs,now,selector=None):
    if any(t in title for t in ['미운영','모집 안','모집 종료','모집종료','모집 마감','모집마감','선정결과','계좌개설','교육','수기','대출','취소','연기','잠정']):return None
    fingerprint,text,soup=content(body,selector)
    if soup is None:return None # PDF/OCR-only schedules require review.
    if not ('청년' in title and any(t in title for t in ['적금','통장','자산형성'])):return None
    if not any(t in title for t in ['모집','신청','접수','가입']) and not identify(title,programs):return None
    windows=[]
    for label in re.finditer(r'(?:온라인\s*)?(?:신청|접수|모집)\s*기간\s*[:：]?',text):
        segment=normalized(text[label.end():label.end()+210])
        match=RANGE.search(segment)
        if not match or match.start()>35:continue
        if any(t in segment[:match.end()+10] for t in ['예정','변경 전','변경전','오전','오후','추후']):continue
        g=match.groupdict();years=re.findall(r'20\d{2}',title)
        year=int(g['y']) if g['y'] else int(years[0]) if len(set(years))==1 else None
        if year is None:continue
        try:
            start=datetime(year,int(g['m']),int(g['d']),int(g['h'] or 0),int(g['min'] or 0),tzinfo=KST)
            end=datetime(int(g['ey'] or year),int(g['em'] or g['m']),int(g['ed']),tzinfo=KST)
            hour=int(g['eh'] or 0);minute=int(g['emin'] or 0)
            if hour==24 and minute==0:end+=timedelta(days=1)
            elif hour<24:end=end.replace(hour=hour,minute=minute)
            else:continue
            if g['eh'] is None:end+=timedelta(days=1)
        except ValueError:continue
        if not start<end or end-start>timedelta(days=366) or start<now-timedelta(days=400) or start>now+timedelta(days=366):continue
        windows.append((start,end,g['eh'] is None,g['h'] is None,segment[:match.end()]))
    unique={(a.isoformat(),b.isoformat()):(a,b,c,d,e) for a,b,c,d,e in windows}
    if len(unique)!=1:return None
    start,end,date_only,start_date_only,quote=next(iter(unique.values()))
    program=identify(title,programs)
    # Unknown programs are discovered as notices only; no financial/eligibility rules.
    regions=program['regions'] if program else []
    scope='NATIONAL' if program and not regions else 'REGIONAL' if regions else 'UNCONFIRMED'
    if not program:
        aliases={'서울':['서울시','서울특별시'],'경기':['경기도'],'부산':['부산시','부산광역시'],'인천':['인천시','인천광역시'],'경남':['경남','경상남도'],'대전':['대전시','대전광역시'],'전북':['전북','전북특별자치도']}
        regions=[k for k,values in aliases.items() if any(v in title for v in values)]
        if len(regions)==1:scope='REGIONAL'
        else:regions=[]
    pid=program['program_id'] if program else 'DISCOVERED-'+sha(url)[:16]
    key=sha(pid+'|'+start.isoformat()+'|'+end.isoformat())
    return dict(notice_id=key,program_id=pid,title=title[:240],url=url,regions=regions,scope=scope,
        starts_at=start.isoformat(),ends_at_exclusive=end.isoformat(),date_only=date_only,start_date_only=start_date_only,
        schedule_evidence=quote,verified_at=now.isoformat(),content_sha256=fingerprint,
        eligibility_status='UNKNOWN',financial_calculation_available=False,
        note='공식 공고에서 자동 확인한 신청 일정입니다. 소득·재산·선발 등 가입조건은 별도 확인해야 합니다.'+(' 종료 날짜만 공개되어 당일 마감시각은 공식 채널 확인이 필요합니다.' if date_only else ''))

def notice_status(row,now):
    if row.get('invalidated'):return 'REVIEW_REQUIRED'
    if now>=datetime.fromisoformat(row['ends_at_exclusive']):return 'CLOSED'
    verified=datetime.fromisoformat(row['verified_at'])
    if now-verified>timedelta(days=7):return 'REVIEW_REQUIRED'
    if now<datetime.fromisoformat(row['starts_at']):return 'UPCOMING'
    return 'OPEN'
