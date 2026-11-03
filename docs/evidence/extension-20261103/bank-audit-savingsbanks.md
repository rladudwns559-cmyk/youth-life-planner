# 추가 저축은행 공식 상품 검증 — 2026-11-03

기존256개 상품과 비교해 신규29개·5개 금융회사(SNT/인성/DH/HB/유니온)를 확인했다. 전체29개 Product/Source strict 모델 검증 통과,기존ID/기관·상품명 중복0. 공식 원문은각 상품 source URL에서HTTPS로직접 HTTP200을 확인하고 비공개 tmp에보존했다.상품별원문SHA256은 bank-additions-savingsbanks.json의 evidence_files에기록했다.

신규29개는가입유형카드수이며모두추천가능하다는뜻이아니다. 같은상품의단리/복리나동일페이지의 e/스마트명칭을묶었다. DH비대면예금은 rnum18·19를1개로통합했다.유니온같은원상품의온라인가입우대도별도상품수로늘리지않았다.

## 실제 추천·보류 구분

- HB 정기적금/비대면정기적금: 월1만원~100만원·12~36개월이원문에서명확하다. 기본금리표는확인된12/24/36개월만기록(중간기간금리추정없음). 기본12개월 각각3.50/3.70%, 원문 기준2026-01-01. 만원미만BUDGET·100만원FIT·100만원+1PARTIAL을기존엔진으로검사했다.
- SNT 비대면정기예금:10만원~3억원,3~24개월,만19세이상내국인개인.12개월명목3.74%(2026-09-07)와복리연평균3.80%를구별했다.
- 유니온 정기예금:10만원이상제한없음이명시되어상한UNLIMITED.12개월일반기본3.80%,온라인가입3.90%안내는우대로만설명한다.
- SNT정기적금2개는원문의'가입금액제한없음/계약금액1만원이상'에서계약금액을최소월부금으로변환하지않았다.minimum=null,비교보류.자유적립예금은계약금액을납입금합계라고정의하므로이를정기적금의월최소로대체하지않았다.
- 인성정기적금은가입금액제한없음으로상한제한없음은기록하되,최소월부금은미명시이므로보류한다. e적금과DH적금의상한미명시는UNKNOWN.
- 인성·DH·SNT·유니온자유적립은개별납입일과실예치기간/월복리계약이필요하여기존월정액추천에서보류한다.자유적립'예금'은거치식DEPOSIT로분류하지않고SAVINGS/CUSTOM_DATE로안내한다.
- 인성·HB·유니온회전예금은총36개월과6/12개월회전주기금리를구별한다.회전금리를36개월고정금리로순위매기지않는다.14개명시recommendation_exclusions,전체107개공식기간별금리행이며등록수/금리행수/추천수는서로다르다.

## 자료 충돌과 확인일

인성정기예금12~17개월은공식직접HTTP본문3.90%이며검색색인의옛3.80%를그대로채택하지않았다. e정기예금12~17개월은직접본문3.80%로구분했다. 날짜없는인성/DH/유니온게시금리는basis_date=null이고검토일2026-11-03으로기록했다. 심의번호의유효기간을금리시행일로변환하지않았다. SNT실제시행일과HB명시기준일만basis_date에사용했다.

## 미추가·접근 실패

- 대신저축은행:실제HTTPS인증오류.인증우회/검증해제하지않고이번JSON에추가하지않았다.
- 상상인:연결종료,상상인플러스:HTTP412.검색색인만으로최신직접본문검증완료를선언하지않고추가하지않았다.
- 키움:공식홈에서잘못된요청차단응답.보안우회없음·추가없음.
- NH:공식홈이JS렌더링셸이라상품상세확인완료로취급하지않았다.
- 파킹/보통예금/대출은이번범위에추가하지않았다.은행별로그인·계좌개설·문의·신청·다운로드설치·유료API실행0.

## 실제 검증

29개모델검증·기존256개대조·원문파일SHA256·eligibility=UNKNOWN/calculation=null전체보존. 기존엔진을읽기전용으로불러22개독립경계확인을실행했다(별도pytest추가/전체회귀실행아님). 결과는savingsbanks-boundary-checks.json. 원본production파일은수정하지않았으며허용도메인5개를추가해야하는필요사항만반환한다.

| 금융회사 | 상품·유형 | 근거 | 대표12개월금액검사 |
|---|---|---|---|
| 인성저축은행 | 정기예금 · 단리/복리 | [공식](https://www.insungsavingsbank.co.kr/ProdList_001.act?rnum=28) | MISSING |
| 인성저축은행 | e-정기예금 · 단리/복리 | [공식](https://www.insungsavingsbank.co.kr/ProdList_001.act?rnum=29) | MISSING |
| 인성저축은행 | 정기적금 | [공식](https://www.insungsavingsbank.co.kr/ProdList_001.act?rnum=30) | MISSING |
| 인성저축은행 | e-정기적금 | [공식](https://www.insungsavingsbank.co.kr/ProdList_001.act?rnum=31) | MISSING |
| 인성저축은행 | 자유적립예금 | [공식](https://www.insungsavingsbank.co.kr/ProdList_001.act?rnum=32) | SCHEDULE |
| 인성저축은행 | 회전정기예금 · 단리/복리 | [공식](https://www.insungsavingsbank.co.kr/ProdList_001.act?rnum=39) | TERM |
| 인성저축은행 | e-회전정기예금 · 단리/복리 | [공식](https://www.insungsavingsbank.co.kr/ProdList_001.act?rnum=40) | TERM |
| DH저축은행 | 정기예금 · 단리/복리 | [공식](https://www.dhsavingsbank.co.kr/ProdList_001.act?rnum=17) | MISSING |
| DH저축은행 | 정기예금 · 비대면 단리/복리 | [공식](https://www.dhsavingsbank.co.kr/ProdList_001.act?rnum=18) | MISSING |
| DH저축은행 | 정기적금 | [공식](https://www.dhsavingsbank.co.kr/ProdList_001.act?rnum=20) | MISSING |
| DH저축은행 | 정기적금 · 비대면 | [공식](https://www.dhsavingsbank.co.kr/ProdList_001.act?rnum=21) | MISSING |
| DH저축은행 | 자유적립예금 | [공식](https://www.dhsavingsbank.co.kr/ProdList_001.act?rnum=23) | SCHEDULE |
| SNT저축은행 | 정기예금 · 단리/복리 | [공식](https://hisntm.com/kor/sub01_02_02.html) | MISSING |
| SNT저축은행 | 정기예금 · 비대면 단리/복리 | [공식](https://hisntm.com/kor/sub01_02_08.html) | FIT |
| SNT저축은행 | 정기적금 | [공식](https://hisntm.com/kor/sub01_02_04.html) | MISSING |
| SNT저축은행 | 정기적금 · 비대면 | [공식](https://hisntm.com/kor/sub01_02_09.html) | MISSING |
| SNT저축은행 | 자유적립예금 | [공식](https://hisntm.com/kor/sub01_02_05.html) | SCHEDULE |
| HB저축은행 | 정기적금 | [공식](https://hbsb.co.kr/deposit/fixed-deposit) | FIT |
| HB저축은행 | 비대면 정기적금 | [공식](https://hbsb.co.kr/deposit/online-fixed-deposit) | FIT |
| HB저축은행 | 정기예금 · 단리/복리 | [공식](https://hbsb.co.kr/deposit/time-deposit) | MISSING |
| HB저축은행 | 비대면 정기예금 · e/스마트 단리·복리 | [공식](https://hbsb.co.kr/deposit/online-time-deposit) | MISSING |
| HB저축은행 | 회전정기예금 · 단리/복리 | [공식](https://hbsb.co.kr/deposit/renewable-time-deposit) | TERM |
| HB저축은행 | 6개월 회전정기예금 · 단리/복리 | [공식](https://hbsb.co.kr/deposit/6-month-renewable-time-deposit) | TERM |
| HB저축은행 | 비대면 회전정기예금 · e/스마트 단리·복리 | [공식](https://hbsb.co.kr/deposit/online-renewable-time-deposit) | TERM |
| HB저축은행 | 비대면6개월 회전정기예금 · e/스마트 단리·복리 | [공식](https://hbsb.co.kr/deposit/online-6-month-renewable-time-deposit) | TERM |
| 유니온저축은행 | 정기예금 · 단리/복리 | [공식](https://www.kusb.co.kr/contents/deposit/surplus.html) | FIT |
| 유니온저축은행 | 정기적금 | [공식](https://www.kusb.co.kr/contents/deposit/largeSum.html) | MISSING |
| 유니온저축은행 | 자유적립예금 | [공식](https://www.kusb.co.kr/contents/deposit/freeSurplus.html) | SCHEDULE |
| 유니온저축은행 | 회전식 정기예금 · 단리/복리 | [공식](https://www.kusb.co.kr/contents/deposit/rotationSurplus.html) | TERM |

전체국내상품전수확인·실제가입보장·실제만기계산완료를주장하지않는다.최종통합·추천정렬·회귀·배포는상위작업에서별도검증한다.
