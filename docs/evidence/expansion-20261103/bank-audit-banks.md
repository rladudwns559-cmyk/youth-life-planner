# 2026-11-03 은행상품 추가 조사 최종 감사

## 동결 결과

- 1차19개 + 2차6개 + 3차3개 = 신규28개 상품·가입유형 카드. 기존153개 및 신규배치 간 ID/동일은행 정규화 상품명 중복0건. Product/Source28개 strict 검증 통과.
- 실제 만기 계산0개, 개인별 가입 확정0건. 가입/신청/동의/계좌/유료 API 실행없음. production 코드와 기존153개 원본은 수정하지 않았다.
- 등록28개가28개 모두 일반 TOP 추천 가능하다는 의미는 아니다. 상한/최저/금리/특수자격/납입일정 미확인 및 상품의 제한을 유지한다.

## 기관·상품별 공식 근거

| ID | 기관·상품 | 금액·기간 근거 | 금리 근거 | 공식 URL |
|---|---|---|---|---|
| NOV3-IBK-SME | IBK기업은행 IBK중기근로자우대적금 | 월 납입액 10,000원 이상 ~ 1,000,000원 이하 / 12개월 | 12~12개월 기본2.50% | [공식](https://mybank.ibk.co.kr/uib/jsp/guest/ntr/ntr70/ntr7010/PNTR701000_i2.jsp?grcd=21&lncd=01&pdcd=0122&tmcd=121) |
| NOV3-IBK-LOVE | IBK기업은행 IBK사랑나눔적금 | 월 납입액 1,000원 이상 ~ 500,000원 이하 / 12개월 | 12~12개월 기본4.40% | [공식](https://mybank.ibk.co.kr/uib/jsp/guest/ntr/ntr70/ntr7010/PNTR701000_i2.jsp?grcd=21&lncd=01&pdcd=0095&tmcd=121) |
| NOV3-IBK-PARENTS | IBK기업은행 IBK부모급여우대적금 | 월 납입액 10,000원 이상 ~ 500,000원 이하 / 12개월 | 12~12개월 기본2.50% | [공식](https://mybank.ibk.co.kr/uib/jsp/guest/ntr/ntr70/ntr7010/PNTR701000_i2.jsp?grcd=21&lncd=01&pdcd=0124&tmcd=121) |
| NOV3-IBK-LIFE | IBK기업은행 IBK생활금융적금 | 월 납입액 1,000원 이상 ~ 100,000원 이하 / 12개월 | 12~12개월 기본3.10% | [공식](https://mybank.ibk.co.kr/uib/jsp/guest/ntr/ntr70/ntr7010/PNTR701000_i2.jsp?grcd=21&lncd=01&pdcd=0116&tmcd=121) |
| NOV3-IBK-MARKET | IBK기업은행 실세금리정기예금 | 예치금액 5,000,000원 이상 · 상한 미확인 / 1~36개월 | 36~36개월 기본2.25% | [공식](https://mybank.ibk.co.kr/uib/jsp/guest/ntr/ntr70/ntr7010/PNTR701000_i2.jsp?grcd=21&lncd=01&pdcd=0003&tmcd=131) |
| NOV3-IBK-INNOVATION | IBK기업은행 IBK혁신창업기업응원통장 · 정기예금 기본형 | 예치금액 1,000,000원 이상 ~ 10,000,000,000원 이하 / 12~36개월 | 36~36개월 기본2.25% | [공식](https://mybank.ibk.co.kr/uib/jsp/guest/ntr/ntr70/ntr7010/PNTR701000_i2.jsp?grcd=21&lncd=01&pdcd=0140&tmcd=131) |
| NOV3-IBK-MORE | IBK기업은행 IBK더굴리기통장 · 정기예금 | 예치금액 1,000,000원 이상 · 상한 미확인 / 6~36개월 | 12~12개월 기본3.53% | [공식](https://mybank.ibk.co.kr/uib/jsp/guest/ntr/ntr70/ntr7010/PNTR701000_i2.jsp?grcd=21&lncd=01&pdcd=0130&tmcd=131) |
| NOV3-IBK-ROLL | IBK기업은행 IBK굴리기통장 · 정기예금 | 예치금액 1,000,000원 이상 ~ 500,000,000원 이하 / 1~12개월 | 현재 금리 추가 확인 | [공식](https://mybank.ibk.co.kr/uib/jsp/guest/ntr/ntr70/ntr7010/PNTR701000_i2.jsp?MENU_DIV=GNB&grcd=21&lncd=01&p_code=01211310142%2A%2A%2A%2A%2A%2A%2A%2A%2A%2A%2A&pdcd=0142&tmcd=131) |
| NOV3-WOORI-SAMSUNG | 우리은행 삼성월렛머니 우리 적금 | 월 납입액 최저금액 추가 확인 ~ 300,000원 이하 / 6~12개월 (지정 기간만 가입) | 6~6개월 기본2.75%; 12~12개월 기본2.75% | [공식](https://spot.wooribank.com/pot/Dream?PRD_CD=P010002576&cc=c007095%3Ac009166%3Bc012263%3Ac012399&withyou=PODEP0019) |
| NOV3-WOORI-WON | 우리은행 WON 적금 | 월 납입액 최저금액 추가 확인 ~ 500,000원 이하 / 12개월 | 12~12개월 기본3.20% | [공식](https://spot.wooribank.com/pot/Dream?PRD_CD=P010002353&cc=c007095%3Ac009166%3Bc012263%3Ac012399&withyou=PODEP0019) |
| NOV3-WOORI-SUPER | 우리은행 우리 SUPER주거래 적금 | 월 납입액 최저금액 추가 확인 ~ 500,000원 이하 / 12~36개월 (지정 기간만 가입) | 12~12개월 기본2.45%; 24~24개월 기본2.40%; 36~36개월 기본2.40% | [공식](https://spot.wooribank.com/pot/Dream?PRD_CD=P010000109&cc=c007095%3Ac009166%3Bc012263%3Ac012399&withyou=PODEP0019) |
| NOV3-KJ-DIGITAL | 광주은행 쏠쏠한MY디지털적금 · 정액적립식 | 월 납입액 10,000원 이상 ~ 1,000,000원 이하 / 12~24개월 (지정 기간만 가입) | 12~12개월 기본2.60% | [공식](https://www.kjbank.com/ib20/mnu/FPMDPTR030100?INBN_GDS_NO=DEP20220225001) |
| NOV3-HANA-369 | 하나은행 3·6·9 정기예금 | 온라인1만원 이상, 영업점300만원 이상. 최고가입한도 제한없음 / 12개월 | 현재 금리 추가 확인 | [공식](https://www.kebhana.com/cont/mall/mall08/mall0801/mall080101/1419598_115126.jsp) |
| NOV3-HANA-FIXED | 하나은행 고단위 플러스 · 금리확정형 | 예치금액 10,000원 이상 · 상한 미확인 / 1~60개월 | 현재 금리 추가 확인 | [공식](https://www.kebhana.com/cont/mall/mall08/mall0801/mall080101/1419600_115126.jsp) |
| NOV3-HANA-LINKED | 하나은행 고단위 플러스 · 금리연동형 | 예치금액 10,000원 이상 · 상한 미확인 / 12~60개월 (지정 기간만 가입) | 현재 금리 추가 확인 | [공식](https://www.kebhana.com/cont/mall/mall08/mall0801/mall080101/1419601_115126.jsp) |
| NOV3-HANA-MISO | 하나은행 하나 미소드림 적금 | 월 납입액 10,000원 이상 ~ 200,000원 이하 / 12~60개월 (지정 기간만 가입) | 현재 금리 추가 확인 | [공식](https://www.kebhana.com/cont/mall/mall08/mall0801/mall080102/1419754_115157.jsp) |
| NOV3-IM-BONUS | iM뱅크 내가만든 보너스적금 | 월 납입액 10,000원 이상 ~ 200,000원 이하 / 6~12개월 (지정 기간만 가입) | 현재 금리 추가 확인 | [공식](https://www.imbank.co.kr/upload/newbbs/FNM001/202503041927299504877857.pdf) |
| NOV3-IM-DEPOSIT | iM뱅크 IM예금 | 예치금액 1,000,000원 이상 ~ 50,000,000원 이하 / 12~36개월 | 현재 금리 추가 확인 | [공식](https://www.imbank.co.kr/cms/fnm/deposit/product/03/1220451_2391.html) |
| NOV3-IM-DOKDO | iM뱅크 독도예금 | 예치금액 1,000,000원 이상 · 상한 미확인 / 12~36개월 | 현재 금리 추가 확인 | [공식](https://www.imbank.co.kr/cms/fnm/deposit/product/03/1199451_2391.html) |
| NOV3-KB-MERCHANT | KB국민은행 KB가맹점우대적금 | 월 납입액 10,000원 이상 ~ 10,000,000원 이하 / 6~36개월 | 6~11개월 기본1.95%; 12~23개월 기본2.25%; 24~35개월 기본2.60%; 36~36개월 기본3.00% | [공식](https://obank.kbstar.com/quics?cc=b061761%3Ab061770&isNew=N&page=C020702&prcode=DP01000500) |
| NOV3-WOORI-NPAY | 우리은행 Npay 우리 적금 | 월 납입액 최저금액 추가 확인 ~ 300,000원 이하 / 6개월 | 6~6개월 기본4.50% | [공식](https://spot.wooribank.com/pot/Dream?PRD_CD=P010002570&PRD_YN=Y&cc=c007095%3Ac009166%3Bc012263%3Ac012399&withyou=PODEP0021) |
| NOV3-WOORI-SUPERFREE | 우리은행 우리 SUPER주거래 자유적금 | 월 납입액 최저금액 추가 확인 ~ 500,000원 이하 / 12~36개월 (지정 기간만 가입) | 12~12개월 기본2.45%; 24~24개월 기본2.40%; 36~36개월 기본2.40% | [공식](https://spot.wooribank.com/pot/Dream?PRD_CD=P010000110&PRD_YN=Y&cc=c007095%3Ac009166%3Bc012263%3Ac012399&withyou=PODEP0021) |
| NOV3-WOORI-HOPE | 우리은행 우리희망드림적금 | 월 납입액 최저금액 추가 확인 ~ 200,000원 이하 / 12개월 | 현재 금리 추가 확인 | [공식](https://spot.wooribank.com/pot/Dream?PRD_CD=P010000136&PRD_YN=Y&cc=c007095%3Ac009166%3Bc012263%3Ac012399&withyou=PODEP0021) |
| NOV3-WOORI-MISO | 우리은행 우리미소드림적금 | 월 납입액 10,000원 이상 ~ 200,000원 이하 / 12~60개월 (지정 기간만 가입) | 현재 금리 추가 확인 | [공식](https://spot.wooribank.com/pot/Dream?PRD_CD=P010000016&PRD_YN=Y&cc=c007095%3Ac009166%3Bc012263%3Ac012399&withyou=PODEP0021) |
| NOV3-WOORI-BOSS | 우리은행 우리 사장님 성장 적금 | 월 납입액 최저금액 추가 확인 ~ 1,000,000원 이하 / 12개월 | 현재 금리 추가 확인 | [공식](https://spot.wooribank.com/pot/Dream?PRD_CD=P010002588&PRD_YN=Y&cc=c007095%3Ac009166%3Bc012263%3Ac012399&withyou=PODEP0021) |
| NOV3-KB-STANDARD-DEPOSIT | KB국민은행 일반정기예금 | 최저100,000원 이상·최고한도 없음(원단위) / 1~60개월 | 1~2개월 기본1.65%; 3~5개월 기본2.00%; 6~11개월 기본2.25%; 12~23개월 기본2.50%; 24~35개월 기본2.35%; 36~36개월 기본2.45% | [공식](https://obank.kbstar.com/quics?cc=b061761%3Ab061770&isNew=N&page=C020702&prcode=DP01000014) |
| NOV3-KB-SUPER-FIXED | KB국민은행 국민수퍼정기예금(개인) · 고정금리형 | 예치금액 1,000,000원 이상 · 상한 미확인 / 1~36개월 | 1~2개월 기본1.90%; 3~5개월 기본2.25%; 6~11개월 기본2.25%; 12~23개월 기본2.30%; 24~35개월 기본2.35%; 36~36개월 기본2.45% | [공식](https://obank.kbstar.com/quics?cc=b061761%3Ab061770&isNew=N&page=C020702&prcode=DP01000029) |
| NOV3-KB-SUPER-CD | KB국민은행 국민수퍼정기예금 · CD금리연동형 | 예치금액 1,000,000원 이상 · 상한 미확인 / 6~36개월 (지정 기간만 가입) | 현재 금리 추가 확인 | [공식](https://obank.kbstar.com/quics?cc=b061761%3Ab061770&isNew=N&page=C020702&prcode=DP01000214) |

## 중복·종료와 가입대상 판정

1. KB직장인우대적금은 초기20개 중 제외해 1차19개로 동결했다. 공식 「수신상품5종 판매종료 안내」 등록2025.11.20·시행2025.12.05에서 명시한다. 상품의 과거 금리 상세가 검색돼도 신규 판매로 간주하지 않는다.
   - 공식 종료 공고: https://obank.kbstar.com/quics?articleClass=1&articleId=141870&bbsMode=view&boardId=669&compId=b058334&page=C020721&searchCondition=title&searchStr=&viewPage=9
   - 단순 page=C016613+articleId는 상품목록으로 응답해 종료 근거로 사용하지 않았고, 위 실제 새소식 경로의 본문을 HTTP200으로 재확인했다.
2. 우리은행은 공통 금리표 URL을 공유하지만 공식 상품 상세의 PRD_CD와 제목이 다르다. 삼성월렛머니 P010002576 / WON P010002353 / SUPER정액 P010000109 / SUPER자유 P010000110 / 기존 우리WON모바일 P010002566은 별개 명칭·상품ID다. 공통 금리표만으로 신규 레코드를 복제한 것이 아니다.
3. IBK중기근로자우대적금은 중소기업 근로자 증빙, 사랑나눔은 법정 복지·특수대상 증빙, 하나/우리 미소드림은 서민금융진흥원 추천이 가입 자체에 필요해 일반 성인 추천 제외를 유지한다. 우리희망드림·사장님성장도 증빙/사업자 대상이어서 제외한다.
4. IBK부모급여우대적금은 실명의 개인(개인사업자·외국인 비거주자 제외)이 가입대상이다. 부모급여/아동수당 수급은 우대2.0%p 등 조건이며 가입 자체의 부모 자격 필수로 임의 변환하지 않는다. 기본2.50과 최고6.50을 구분하고 만원단위 계약을 보존한다.
5. IBK혁신창업기업응원통장은 창업기업 재직자만 가입하는 상품이 아니다. 공식 대상은 개인·개인사업자·법인이며 기본형과 무이자 기여형을 구분한다. 기본형36개월2.25와 응원문구 우대0.10%p를 별도로 기록한다.1~3년 월단위 계약을 확인했다.
6. KB가맹점우대적금도 만14세이상 일반 개인(개인사업자 포함) 가입이 가능하며 가맹점·카드실적은 우대 요건이다. 다만 INDEXED 근거와 만기1개월전 납입중단/후반부 적립비율 제한을 보존해 일반 동일월납 TOP에 올리지 않는다.

## 불일치·보류 경계

- 우리 삼성월렛/WON/SUPER/Npay는 공식 요약에 월상한은 있지만 최저금액을 확인하지 못해 minimum=null 및 hold를 유지한다. 다른 우리 상품의 최저금액을 복사하지 않았다.
- IBK생활금융은 보유 통장 잔액1% 자동적립 전용이라 CUSTOM_DATE와 hold를 유지한다. 월저축액을 임의로 정기 납입하는 계약으로 해석하지 않았다.
- IBK굴리기는 공식 접근 경로별3.50/3.65 차이를 발견해 rates=[]를 유지한다. 더굴리기/실세금리 예금은 상한 미명시로 UNKNOWN을 유지한다.
- 하나369는 공식 최고상한 없음·온라인최저1만원을 확인했지만 과거2024 표시금리를 현재추천으로 사용하지 않았다. 고단위 연동형은 미래변동금리를 전체기간 확정수익으로 사용하지 않는다.
- iM보너스는 유효2025.03.05~2027.02.28 공식 설명서를 읽되 기본금리2025.03.05를 현재금리로 채우지 않았다. 현재 금리 목록은 정상 HTTP200이지만 암호화 스크립트 외 읽을 본문이 없어 보안우회 없이 보류했다.검색 색인 수치를 직접 현재값으로 올리지 않았다.
- 추가 KB일반정기예금은 최저10만원/최고한도없음을 확인했지만 요약범위1.65~2.45와 기간별12개월2.50표가 달라 금리 추천에서 제외한다.3년초과계약은3년경과시 금리 재적용이므로37~60개월 금리를 생성하지 않았다.
- KB국민수퍼 고정형은 요약1.85~2.55와 기간별표1.90~2.45 차이, 예치상한 미명시를 보류한다. CD연동형은3개월마다 변동하고 상한도 불명이라 금리 추천에서 제외한다. 같은 국민수퍼 일반 상품의 지급식 옵션을 여러 상품으로 세지 않았다.

## 확인 방식·원문 보존

IBK 직접 HTTP 원본은 암호화된 페이지라 단순200을 상품 본문 확보로 사용하지 않았다. 웹 도구로 공식 상세 본문과 금액·기간·유효기간을 별도로 읽었다. 우리 상세3개,KB 신규3개와 종료 공고는 직접 HTTP200 및 읽을 수 있는 본문을 재확인했다.기존 공식 URL/원문 private scratch는 공개 대량업로드 대상이 아니다.

## 동결 SHA256

| 파일 | 카드 수 | SHA256 |
|---|---:|---|
| bank-additions-banks.json | 19 | 12928dcd44d5d46650b473ece1e1e90c5b29b4d795ab365dadc924905adc7eaf |
| bank-additions-banks-2.json | 6 | dd4c14c4812e1c6beab7bcfb2c0e6d0a0db8a634be042961948382783ce62503 |
| bank-additions-banks-3.json | 3 | 1af3d0c387d890eb63ac67aa73428855397c039a77a660532b5a03460d5acc6b |
