# 저축은행 추가20개 공식 검증 — 2026-11-03

동결29개를수정하지않고신규20개/3개회사(대명6·남양7·금화7)를추가분리했다. 기존256+동결29=285개와ID/기관·상품명중복0.20개Product/Source strict검증통과.금리표100행,명시추천제외7개.전체20개를추천가능20개라고보고하지않는다.

## 실제 비교가능·불확실성

대명더드림정기적금은매월고정금액납입,월1만원~500만원,12~36개월이명시된다. 기본금리는12~23개월2.95%,24~35개월3.00%,36개월3.05%.기존엔진으로9999원BUDGET/1만원FIT/500만원FIT/500만원+1PARTIAL/11개월TERM/36개월FIT/37개월TERM을검사했다.별도pytest가아닌7개직접경계확인이고production변경은없다.

대명나머지·남양현재상세의최소금액은확인했으나상한미명시를무제한으로바꾸지않았다.남양rnum1옛안내의'제한없음'문구와5천만원예금보호등낡은표시를최신rnum18~20에차용하지않고최신개별상세조건만사용했다.

금화정기적금원문의'원금과이자를합산한계약금액1만원이상'을월부금1만원으로변환하지않았다.minimum=null,상한UNKNOWN,비교보류. e-행복더드림은월상한100만원은명시되지만월최소미명시이므로minimum=null/보류.

대명자유적립은가입1만원~5천만원,2회차부터월중합계가가입한도의10%이하이고입금마감은만기1개월전응당일이다.가입총액5천만원을매월납입한도로표시하지않고CUSTOM_DATE/다중한도설명/비교보류로남겼다.남양·금화자유적립도월정액추천과구분한다.

## 중복을 줄인 집계

단리/복리선택지는1카드로통합했다.대명E플러스예금의신규/인터넷/스마트6개페이지는1카드, E플러스적금의3개경로도1카드다.개인/법인의경로별대상차이는설명에유지했다.남양은공식명칭이구별된정기/e/비대면상품유형을각각안내하되지급방식만다른단리복리는통합했다.

## 공식 자료·날짜·충돌

모든채택상품은직접HTTPS HTTP200으로본문확인했고원문을tmp/expand3/savingsbanks2에보존했다.주요원문SHA256은JSON evidence_files,추가단리/복리·채널본문은sources에함께연결했다.

남양예금/자유적립기본금리원문기준2026-10-26,정기적금은2026-07-13이다.대명/금화본문에금리시행일이명확하지않아basis_date=null이다.11월3일확인일을시행일로바꾸지않았다.

대명E플러스예금은상품개요12개월인데표에6개월금리도있어확인가능한12개월만기록하고6개월취급차이는추가확인으로남겼다.대명자유적립12개월직접본문은3.65%였으며검색색인의옛4.10%를대체근거로쓰지않았다.기본명목금리와복리연평균수익률을구분했다.

JT친애는정상HTTPS요청연결종료로제외했고우회하지않았다.은행개인로그인/신청/계좌개설/문의전송/유료API사용0.미확인최신가입상태를확정하지않는다.

| 금융회사 | 상품·유형 | 공식근거 |
|---|---|---|
| 대명저축은행 | 정기예금 · 단리/복리 | [공식](https://www.daemyungbank.co.kr/ProdList_001.act?rnum=19) |
| 대명저축은행 | E-플러스 정기예금 · 단리/복리 | [공식](https://www.daemyungbank.co.kr/ProdList_001.act?rnum=23) |
| 대명저축은행 | 정기적금 | [공식](https://www.daemyungbank.co.kr/ProdList_001.act?rnum=29) |
| 대명저축은행 | E-플러스 정기적금 | [공식](https://www.daemyungbank.co.kr/ProdList_001.act?rnum=30) |
| 대명저축은행 | 더드림정기적금 | [공식](https://www.daemyungbank.co.kr/ProdList_001.act?rnum=44) |
| 대명저축은행 | 자유적립식예금 | [공식](https://www.daemyungbank.co.kr/ProdList_001.act?rnum=45) |
| 남양저축은행 | 정기예금 · 단리/복리 | [공식](https://www.nybank.co.kr/ProdList_001.act?rnum=15) |
| 남양저축은행 | e-정기예금 · 단리/복리 | [공식](https://www.nybank.co.kr/ProdList_001.act?rnum=16) |
| 남양저축은행 | 비대면 정기예금 · 단리/복리 | [공식](https://www.nybank.co.kr/ProdList_001.act?rnum=17) |
| 남양저축은행 | 정기적금 | [공식](https://www.nybank.co.kr/ProdList_001.act?rnum=18) |
| 남양저축은행 | e-정기적금 | [공식](https://www.nybank.co.kr/ProdList_001.act?rnum=19) |
| 남양저축은행 | 비대면 정기적금 | [공식](https://www.nybank.co.kr/ProdList_001.act?rnum=20) |
| 남양저축은행 | 자유적립예금 | [공식](https://www.nybank.co.kr/ProdList_001.act?rnum=21) |
| 금화저축은행 | 정기예금 · 단리/복리 | [공식](https://www.kuemhwabank.co.kr/ProdList_001.act?rnum=21) |
| 금화저축은행 | 정기예금 · 인터넷 단리/복리 | [공식](https://www.kuemhwabank.co.kr/ProdList_001.act?rnum=23) |
| 금화저축은행 | 정기적금 | [공식](https://www.kuemhwabank.co.kr/ProdList_001.act?rnum=25) |
| 금화저축은행 | 정기적금 · 인터넷 | [공식](https://www.kuemhwabank.co.kr/ProdList_001.act?rnum=27) |
| 금화저축은행 | 자유적립적금 | [공식](https://www.kuemhwabank.co.kr/ProdList_001.act?rnum=26) |
| 금화저축은행 | 자유적립적금 · 인터넷 | [공식](https://www.kuemhwabank.co.kr/ProdList_001.act?rnum=28) |
| 금화저축은행 | e-행복더드림 정기적금 | [공식](https://www.kuemhwabank.co.kr/ProdList_001.act?rnum=29) |

최종통합·전체회귀·실제UI추천정렬·배포는상위작업에서검증한다.본단계는공식추가자료와독립경계검사만완료했다.
