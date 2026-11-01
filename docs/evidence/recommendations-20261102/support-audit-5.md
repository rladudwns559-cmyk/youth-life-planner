# 5차 전국 지원서비스 확장 검증 기록

확인일:2026-11-02. 기존1~4차JSON은수정하지않고별도10개카드로동결했습니다. Program/Rule기존모델각10개검증통과. production변경0.

|사업|신청근거/상태|공식자료|
|---|---|---|
|문화누리카드 · 2026 신규·재충전|WINDOW / OPEN_OFFICIAL_APPLICATION_GUIDANCE|[공식 자료](https://m.mnuri.kr/card/cardMain/cardIssue_step00.do)|
|자립준비청년 보호종료 자립수당|CONTINUOUS / OPEN_OFFICIAL_APPLICATION_GUIDANCE|[공식 자료](https://www.gov.kr/portal/service/serviceInfo/508000000565)|
|고용보험 미적용자 출산급여|CONTINUOUS / OPEN_OFFICIAL_APPLICATION_GUIDANCE|[공식 자료](https://www.gov.kr/portal/service/serviceInfo/149200000153)|
|전기·가스·난방·TV 요금감면 일괄신청|CONTINUOUS / OPEN_OFFICIAL_APPLICATION_GUIDANCE|[공식 자료](https://www.gov.kr/portal/service/serviceInfo/174100000049)|
|근로·자녀장려금 · 2025년 귀속 기한 후 신청|WINDOW / OPEN_OFFICIAL_APPLICATION_GUIDANCE|[공식 자료](https://j.nts.go.kr/nts/na/ntt/selectNttInfo.do?bbsId=1028&mi=2201&nttSn=1354474)|
|모두의카드(K-패스) 대중교통비 환급|CONTINUOUS / OPEN_OFFICIAL_APPLICATION_GUIDANCE|[공식 자료](https://www.korea-pass.kr/info/intro.do)|
|주거급여 · 임차료·집수리·청년 분리지급 확인|UNKNOWN / APPLICATION_GUIDANCE_VERIFIED|[공식 자료](https://www.lh.or.kr/menu.es?mid=a10401050100)|
|저소득 여성청소년 생리용품 바우처|UNKNOWN / APPLICATION_GUIDANCE_VERIFIED|[공식 자료](https://www.incheon.go.kr/welfare/WE020405)|
|에너지바우처 · 2026 냉난방비 지원|WINDOW / OPEN_OFFICIAL_APPLICATION_GUIDANCE|[공식 자료](https://www.energyv.or.kr/info/apl_info.do)|
|취업똑똑 온라인 취업상담|CONTINUOUS / OPEN_OFFICIAL_APPLICATION_GUIDANCE|[공식 자료](https://www.workplus.go.kr/survey.do)|

## 모집 및 신청 진입의 구분

- 공식 현재 발급/가입/상담 시작 화면을 직접 읽은 것: 문화누리카드(약관·본인인증 이전), 모두의카드(가입조건·카드등록/본인인증 이전), 취업똑똑(상담안내·다음버튼).
- 명확한2026모집일정+공식온라인신청절차를 확인한 것: 에너지바우처6/15~12/31, 근로·자녀장려금2025귀속기한후6/2~12/1. 근로장려금은 국세청2026년공고가정부24의반복정기일정보다우선한다.
- 개별사건/자격발생후신청하는공식상시서비스: 자립수당(상시·보호종료이력), 미적용출산급여(출산후1년), 요금감면일괄신청(자격/고객번호검증). 공개정부24공통템플릿의회원/비회원버튼만을실제접수완료증거로사용하지않았다. 공식상세의신청경로와기관별안내를같이확인했다.
- 주거급여·여성청소년생리용품은현행2026공식기준과복지로온라인신청안내/서비스연결을확인했지만지정접수창내부까지읽을수없었다. **intake_mode UNKNOWN / APPLICATION_GUIDANCE_VERIFIED**로두어현재모집확정정렬에올리지않는다. 전국시군구동일마감일을임의생성하지않았다.
- 미적용출산급여는 공식work24전체메뉴onclick의민원경로를확인했지만GET405였다. 공고/안내는검증했으며로그인이후양식·접수완료는검증하지않았다.
- 요금감면일괄신청은공식실제신청링크에서로그인으로리다이렉트되며도구URL안전검증에서중단됐다. 로그인·개인정보제출·대행신청으로이어가지않았다.

## 범위와 자격 판정

10개중상당수는청년전용이아닌전국생활지원이다. 청년도가구·소득·수급·개인사건요건에따라검토할수있는서비스로설명했다. 모두의카드는현행공식명칭을읽고기존K-패스명칭을함께적었다. 청년우대34세를사업전체상한나이로적용하지않으며일반참여19세이상만비교한다.

현재월소득으로2025귀속총소득·가구재산·공식수급자격·과거고용·출산일·학생신분·보호이력을추론하지않는다. 개인입력에서확인할수없는특화요건은모두UNKNOWN이다. 불필요한성별·건강·출산·가족관계·계좌정보를우리서비스에서새로수집하지않는다.

자격확정0건,지원금실제Cashflow반영0원,DRAFT/CONDITION_SLICE유지. 금융상품만기계산이나LLM·핵심정책엔진·Coverage·Historical·release변경없음. 전체회귀는이조사에서는실행하지않음.

## 제외한 전국 후보

- 희망저축계좌I/II: 공식지자체현행안내에서6·9·11월등추가모집잠정중단을확인했다. 도봉구일정표에11월예정이있더라도개시확정으로추정하지않았다.
- 해외취업정착지원금: 월드잡공식공지목록에2026.8.31사업종료·후속조치공지가있어연중/12월말까지접수라고추정하지않았다.
- 청년문화예술패스: 공식신청버튼은있지만지역별마감이달라전국모집중으로추가하지않았다. 지역별잔여/예산확인필요.
- 농식품바우처:2026년청년포함가구확대와12/11마감공식보도자료는확인했지만공식신청포털이400RequestBlocked여서이번의실제신청창확인범위에서제외했다.
- 청년국가기술자격응시료:2026지원안내는있지만개별시험원서접수창과예산종료여부를현재확인하지못해추가하지않았다.
- 생계급여:공식2026기준은확인했으나이번지시의현재온라인신청확인범위에서정부24가주민센터방문만명시해제외했다.

## 로컬 증거

`v5-kpass*.html/.txt`, `v5-mnuri.html/.txt`, `v5-work24.html/.txt`, `v5-workcounsel.html/.txt`, `v5-govcare.html/.txt`, `v5-govfee.html/.txt`, `v5-energyapply/energybenefit.html/.txt`, `v5-housing.html/.txt`, `v5-sanitary.html/.txt`.

웹도구상502/내용없음인페이지중모두의카드는직접requests응답200과공식현재본문을확인했다. 반대로농식품바우처400,복지로신청내부읽기불가를정상신청화면확인으로바꾸지않았다. 실제모든문의·신청전송0건,유료사용0건.

## 동결 SHA256

ccd52d34258e7ab0195766e3b7006464a0dcfd51f9e21829afe32e07e043dcc7
