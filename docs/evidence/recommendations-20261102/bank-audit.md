# 은행 상품 확장 공식 근거 감사 — 2026-11-02

## 범위와 검증 경계

신규 후보 30개: 1차11개,2차13개,3차6개. 운영 코드는 수정하지 않았습니다. 공식 자료 조회와 Product 모델 검증만 수행했습니다. 실제 상품 만기금액 계산은 모두 null이며 계산가능상품0개 계약을 유지합니다.

금리표 기준일과 2026-11-02 확인일은 다릅니다. 공식 페이지가 존재한다고 특판 잔여한도·신규가입 가능을 실시간 확정하지 않습니다.

상한 미기재를 무제한으로 추론하지 않았습니다. BNK 행복Dream·상호부금만 공식적으로 최고 제한 없음이 명시되어 UNLIMITED를 사용합니다.

## 상품별 근거

| ID / 상품 | 공식 금액 조건 | 기간 | 금리표 기준일 | 공식 근거 |
| --- | --- | --- | --- | --- |
| NOV2-WSB-ESG / 우리E음정기적금_ESG | 월 납입액 100,000원 이상 300,000원 이하 | 12개월 | 2026-03-01 | [공식 안내](https://www.woorisavingsbank.com/product/deposite/view.do?depositeOrder=high&page=1&prdSn=321) |
| NOV2-WSB-PLUS / 우리E음플러스정기적금 | 월 납입액 100,000원 이상 300,000원 이하 | 12개월 | 2022-10-21 | [공식 안내](https://www.woorisavingsbank.com/product/deposite/view.do?depositeOrder=high&page=1&prdSn=320) |
| NOV2-WSB-TOK7 / TOK7적금 | 월 납입액 10,000원 이상 500,000원 이하 | 7개월 | 페이지 미명시 | [공식 안내](https://www.woorisavingsbank.com/product/deposite/view.do?depositeOrder=high&page=1&prdSn=325) |
| NOV2-WSB-INSTALLMENT / 정기적금 | 월 납입액 10,000원 이상 · 상한은 공식 페이지에서 확인되지 않아 추가 확인 | 6~36개월 | 페이지 미명시 | [공식 안내](https://www.woorisavingsbank.com/product/deposite/view.do?depositeOrder=high&page=1&prdSn=319) |
| NOV2-WSB-EUM-DEPOSIT / 우리E음정기예금 | 예치금액 100,000원 이상 · 상한은 공식 페이지에서 확인되지 않아 추가 확인 | 1~36개월 | 2026-06-12 | [공식 안내](https://www.woorisavingsbank.com/product/deposite/view.do?depositeOrder=high&page=1&prdSn=311) |
| NOV2-WSB-DEPOSIT / 정기예금 | 예치금액 100,000원 이상 · 상한은 공식 페이지에서 확인되지 않아 추가 확인 | 1~36개월 | 2026-06-12 | [공식 안내](https://www.woorisavingsbank.com/product/deposite/view.do?depositeOrder=high&page=1&prdSn=324) |
| NOV2-WSB-ROTATING / 회전정기예금 | 예치금액 100,000원 이상 · 상한은 공식 페이지에서 확인되지 않아 추가 확인 | 36개월 | 2026-08-28 | [공식 안내](https://www.woorisavingsbank.com/product/deposite/view.do?depositeOrder=high&page=1&prdSn=323) |
| NOV2-WSB-PARK / 우리E음파킹정기예금 | 예치금액 100,000원 이상 · 상한은 공식 페이지에서 확인되지 않아 추가 확인 | 36개월 | 페이지 미명시 | [공식 안내](https://www.woorisavingsbank.com/product/deposite/view.do?depositeOrder=high&page=1&prdSn=322) |
| NOV2-WSB-PARKPLUS / 위비파킹플러스정기예금 | 예치금액 100,000원 이상 · 상한은 공식 페이지에서 확인되지 않아 추가 확인 | 12개월 | 2026-06-12 | [공식 안내](https://www.woorisavingsbank.com/product/deposite/view.do?depositeOrder=high&page=1&prdSn=343) |
| NOV2-KJ-VIP / VIP플러스적금 · 정액적립식 | 월 납입액 100,000원 이상 5,000,000원 이하 | 12개월 | 2026-09-29 | [공식 안내](https://www.kjbank.com/ib20/mnu/FPMDPTR030100?INBN_GDS_NO=DEP20230906001) |
| NOV2-KJ-FC / 광주FC적금 · 정액적립식 | 월 납입액 50,000원 이상 500,000원 이하 | 12개월 | 페이지 미명시 | [공식 안내](https://www.kjbank.com/ib20/mnu/FPMDPTR030100?INBN_GDS_NO=DEP20240220001) |

### bank-additions.json: 11개 모델 검증 통과

| NOV2-HANA-TAEKWON / 날아라 태권브이 적금 | 월 납입액 10,000원 이상 200,000원 이하 | 6개월 | 2026-10-30 | [공식 안내](https://www.kebhana.com/cont/mall/mall08/mall0801/mall080102/1528527_115157.jsp) |
| NOV2-KB-STAR3 / KB스타적금Ⅲ | 월 납입액 10,000원 이상 300,000원 이하 | 12개월 | 2026-09-11 | [공식 안내](https://kbthink.com/savings/basics/principal-guaranteed.html) |
| NOV2-KB-CARD / KB카드쓰담적금 | 월 납입액 10,000원 이상 300,000원 이하 | 6개월 | 2026-08-28 | [공식 안내](https://obank.kbstar.com/quics?cc=b061496%3Ab061645&isNew=N&page=C016613&prcode=DP01001668) |
| NOV2-KB-CHILDLOVE / KB아이사랑적금 | 월 납입액 10,000원 이상 300,000원 이하 | 12개월 | 2026-08-25 | [공식 안내](https://obank.kbstar.com/quics?cc=b061496%3Ab061645&page=C016613&prcode=DP01001587) |
| NOV2-WOORI-TOGETHER2 / 우리금융 다함께 적금 2 | 월 납입액 1원 이상 300,000원 이하 | 12개월 | 2026-10-01 | [공식 안내](https://spot.wooribank.com/pot/Dream?PRD_CD=P010002603&PRD_YN=Y&cc=c021299%3Ac009166&withyou=PORMG0044) |
| NOV2-WOORI-MOBILE / 우리WON모바일 적금 | 월 납입액 1원 이상 200,000원 이하 | 12개월 | 2026-07-20 | [공식 안내](https://spot.wooribank.com/pot/Dream?PRD_CD=P010002566&PRD_YN=Y&cc=c021299%3Ac009166&withyou=PORMG0044) |
| NOV2-IBKSB-CHILD / IBKSB 사랑愛 얼라 정기적금 | 월 납입액 10,000원 이상 500,000원 이하 | 6~36개월 | 2025-09-01 | [공식 안내](https://www.ibksb.co.kr/download/579013822) |
| NOV2-KAKAO-AIGOAL / 카카오뱅크 AI 목표적금 | 월 납입액 1,000원 이상 1,000,000원 이하 | 3~12개월 | 2026-11-02 | [공식 안내](https://www.kakaobank.com/products/AiGoalSavings) |
| NOV2-KAKAO-CHILD / 카카오뱅크 우리아이적금 | 월 납입액 1,000원 이상 200,000원 이하 | 12개월 | 2026-09-11 | [공식 안내](https://www.kakaobank.com/products/childsavings) |
| NOV2-KBANK-MYKIDS / 마이키즈 적금 | 월 납입액 0원 이상 300,000원 이하 | 1/2/3/4/5년 중 선택 | 2026-10-07 | [공식 안내](https://www.kbanknow.com/web/product/deposit/mykids-saving) |
| NOV2-WELCOME-FIRST-M / WELCOME 첫거래우대 m정기적금 | 월 납입액 10,000원 이상 200,000원 이하 | 12개월 | 페이지 미명시 | [공식 안내](https://www.welcomebank.co.kr/ib20/mnu/IBNFPMDSP001?ib20_wc=IBNFPMDSP001_00%3AIBNFPMCMN001_00&prdCd=1130313504&sysDsCd=01) |
| NOV2-WELCOME-FIRST-E / WELCOME 첫거래우대 e정기적금 | 월 납입액 10,000원 이상 200,000원 이하 | 12개월 | 페이지 미명시 | [공식 안내](https://www.welcomebank.co.kr/ib20/mnu/IBNFPMDSP001?ib20_wc=IBNFPMDSP001_00%3AIBNFPMCMN001_00&prdCd=1130312007&sysDsCd=01) |
| NOV2-KN-HAPPYDREAM / 행복Dream적금 | 월5만원이상,최고제한없음(공식명시) | 12~36개월 | 페이지 미명시 | [공식 안내](https://m.knbank.co.kr/ib20/mnu/MBWSFM030103000?FNC_PRD_DIS_CD=01&FNC_PRD_NO=0000017123&ib20_wc=MBWSFM010LSTV01M%3AMBWSFM024JNGV02M) |

### bank-additions-2.json: 13개 모델 검증 통과

- 일반 성인 추천 제외: NOV2-KAKAO-CHILD: 만17세미만 자녀명의 대리가입 상품: 일반 성인 자신의 추천TOP 제외
- 일반 성인 추천 제외: NOV2-KBANK-MYKIDS: 만17세미만 자녀명의 대리가입 상품: 일반 성인 자신의 추천TOP 제외
- 일반 성인 추천 제외: NOV2-IBKSB-CHILD: 출산예정·당해출산부모·한부모가정 가입조건 확인 전 일반추천TOP 제외
| NOV2-KN-MANIMANI / 마니마니자유적금 | 월 납입액 10,000원 이상 100,000,000원 이하 | 12~60개월 | 2026-10-26 | [공식 안내](https://www.knbank.co.kr/ib20/mnu/FPMDPT020103000?FNC_PRD_DIS_CD=01&FNC_PRD_NO=0000017030&ib20_wc=FPMDPT110LSTV00M%3AFPMDPT221DETV00M) |
| NOV2-KN-MUTUAL / 상호부금 | 월1만원이상,최고금액제한없음(공식명시) | 6~60개월 | 2026-09-18 | [공식 안내](https://www.knbank.co.kr/ib20/mnu/FPMREP020101000?DUP_CHK=N&FNC_PRD_DIS_CD=01&FNC_PRD_NO=0000017032&ib20_redirect_org_mnu=FPMCOM990000000&ib20_wc=FPMDPT110LSTV00M%3AFPMDPT221DETV00M) |
| NOV2-KN-GOAL / 목표달성자유적금 | 월 납입액 10,000원 이상 1,000,000원 이하 | 12~36개월 | 2026-10-24 | [공식 안내](https://m.knbank.co.kr/ib20/mnu/MBWSFM030103000?fnc_prd_no=0000210389&ib20_cur_mnu=MBWSFM030000000&ib20_cur_wgt=MBWSFM024JNGV01M&ib20_wc=MBWSFM024JNGV01M%3AMBWSFM024JNGV02M) |
| NOV2-KN-JUNIOR / 주니어Dream적금 | 월 납입액 1,000원 이상 300,000원 이하 | 12~36개월 | 2026-10-05 | [공식 안내](https://m.knbank.co.kr/ib20/mnu/MBWSFM030103000?FNC_PRD_DIS_CD=01&FNC_PRD_NO=0000203122&historyIgnore=Y) |
| NOV2-TOSS-PRENATAL / 토스뱅크 태아적금 | 월 납입액 0원 이상 200,000원 이하 | 12개월 | 2026-07-14 | [공식 안내](https://www.tossbank.com/articles/baby-savings-account) |
| NOV2-TOSS-KIDS / 토스뱅크 아이적금 | 월 납입액 0원 이상 200,000원 이하 | 12개월 | 2026-07-14 | [공식 안내](https://www.tossbank.com/articles/baby-savings-account) |

### bank-additions-3.json: 6개 모델 검증 통과

- 일반 성인 추천 제외: NOV2-KN-JUNIOR: 만19세미만전용:일반성인추천TOP제외
- 일반 성인 추천 제외: NOV2-KN-GOAL: 목표달성후조기자동해지계약은단순금액기간추천TOP제외
- 일반 성인 추천 제외: NOV2-TOSS-PRENATAL: 예비부모용:출생후아이계좌개설조건확인전일반성인추천TOP제외
- 일반 성인 추천 제외: NOV2-TOSS-KIDS: 만15세이하자녀명의상품:일반성인추천TOP제외

## 추천 계약 주의

- 카드·첫거래·급여·임신·출산·자녀·한부모·VIP·스포츠성과 우대는 사용자 확인 전 UNKNOWN입니다. 최고금리만으로 상위 추천하지 않습니다.
- 우리E음 ESG/플러스 및 BNK 주니어는 천원 단위를 보존했습니다. 현재 엔진의 amount_increment 관련 보류 계약을 우회하지 않습니다.
- 우리금융저축은행 회전정기예금은 현재3.60%를36개월 고정금리로 확대하면 안 됩니다.
- 위비파킹플러스는 월복리이며 nominal3.70%와 복리수익률3.76%를 섞지 않습니다.
- 목표달성자유적금은 목표300만~3600만원 달성후 가입6개월 이후 자동해지됩니다. 단순12~36개월 유지 상품으로 확정하지 않고 comparison_hold_reason을 설정했습니다.
- 카카오 AI목표적금 공식HTML 상품안내 팝업에서 14세이상·월1천~100만원·3~12개월을 확인했습니다. raw 파일 kakao-ai-page.html을 보존했습니다. 은행 자체 AI기능을 본 서비스의 AI성능 근거로 사용하지 않습니다.
- IBK기업은행과 IBK저축은행은 별도 금융회사입니다. IBKSB사랑愛얼라의2026.01.01설명서 내부금리표 기준은2025.09.01이며 신규금리는 은행 재확인이 필요합니다. IBK기업은행 적금 계산 보류를 해제하지 않습니다.
- 날짜없는 공식 수취이자 예시가 있어도 날짜기반 독립 검산 완료로 처리하지 않았습니다.

## 제외·보류한 조사 후보

- 광주은행 행운적금:2023년 이벤트 자료. 현행판매·금리근거로 추가하지 않음.
- 하나 Best11:확인한2026.05.27~06.24 판매기간 종료.
- 하나1004:2019신규중단 문구.
- 우리 퍼스트정기적금·우리WON하는LCK·스무살우리 자유적금·우리여행적금:공식 판매종료 표기.
- BNK 아이Dream자유적금:공식 제목에 판매중단 표기.
- 웰컴드림·체크플러스e/m:공식 판매중단목록에 있어 제외.
- 신한1982전설·모두의적금:오래된한정판매자료와심의기한만확보,신규판매근거 부족.
- SBI금리표:공식 HTML에서 기본금리 값이 비어있어 추가하지 않음.
- 다올 상품목록:직접접속은 공개 WAF차단,검색인덱스 상세조건만으로 승격하지 않음.
- 수협공식현재금리는확인했으나 상세상품GET조회가목록으로돌아와 금액·대상 원문 검증을완결하지 못해 추가하지 않음. 제한을 우회하지 않음.
- JT정기적금은기존113개에포함돼 신규중복추가하지 않음.

## 실행 검증

- Product.model_validate:신규30개 전부 통과(이 작업 프로세스에서만공식호스트합집합사용;productionHOSTS수정없음).
- 30개 product_id 유일함. calculation 모두 null,eligibility 모두 UNKNOWN.
- production 및 기존 golden/release 수정 없음. 전체 pytest 실행은 본 조사 하위작업에서 수행하지 않음.
- 1차·2차 전달이후 파일은 동결 보존했고 3차를 별도파일로 저장.

## 호스트

- 1차추가필요:www.woorisavingsbank.com
- 2차추가필요:spot.wooribank.com,ssmt.wooribank.com
- 3차추가호스트없음:기존 www.knbank.co.kr,m.knbank.co.kr,www.tossbank.com 사용.
