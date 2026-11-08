# 나이·취업·월세 기반 지원사업 후보 추천

완료일: 2026-11-01. 최종 판단 **PERSONAL_SUPPORT_DISCOVERY_DEPLOYED_WITH_UNKNOWNS**.
[공개 화면](https://youth-life-planner.rladudwns559.chatgpt.site/#/programs) · 공개v8 실제 배포 성공. 전체 자격판정 승인이나 전국 전수 수집 완료를 뜻하지 않는다.

## 변경 결과

지역·현재 만 나이·현재 취업상태·현재 월세 거주 여부를 입력하면 Python에서 준비한 비교 결과에 따라 후보가 자동 변경된다. 명확히 다른 개인조건은 기본적으로 숨기며 ‘현재 조건과 다른 사업도 보기’로 복원할 수 있다. 별도의 ‘다른 지역 사업도 함께 보기’도 유지했다. 미입력·미확인 규칙은 UNKNOWN이고 제외하지 않는다. 일치한 입력 조건 수를 보여주되 **최종 자격은 항상 UNKNOWN, 실제 지원금 반영은0원**이다.

홈 주요 공개 버튼은 ‘내 조건에 맞는 지원 찾기’다. 사용자가 찾는 것은 이사할 지역이 아니라 개인조건에 맞는 지원이므로 이 표현을 사용했다. 현재 나이·고용·주거 입력은 화면 메모리만 사용하고 서버/LLM 전송 및 영구 저장하지 않는다. 학생과 취업 여부를 상호 배타적으로 취급하지 않으며 학적을 추정하지 않는다.

기존38개 원본을 수정하지 않고 신규3개를 별도 스냅샷으로 추가해 **41개**를 제공한다. 기존 금융상품74개/공시299개 및 자산형성10개 자료는 그대로 보존했다. 이번 은행 적금 추가는0개다.

- 서울청년문화패스: 현행 공식 안내의2002~2005년생, 의무복무 특례,20만원 문화이용권. 2025년 보도와 달라진 범위를 구분하며 예산 잔여·현재 접수는UNKNOWN.
- 서울 청년 부동산 중개보수·이사비 하반기:8/18~8/31 종료.11~12월 지급예정은 신규 모집이 아니다. 전세도 검토 가능하므로 월세 없음으로 제외하지 않는다.
- 경남 청년 면접정장 무료대여: 공식 현재 마감9/18을 반영. 단순 연중 사업기간으로 다시 모집중 처리하지 않는다.

안성 취업옷장은 공식 자료를 확보했지만 관내학생의 거주 예외 OR와 연령 표현이 불명확해 이번 추천 목록 편입은 보류했다. 조사만 한 항목을 등록/추천 수에 더하지 않는다.

## 실제 비교 범위와 안전장치

41개 중20개에 조건 근거/주의사항을 연결했다. 자동 비교 가능한 연령 규칙16개, 고용 상태4개, 월세 필수2개이며 서로 겹친다. 나머지는 원문 안내와 UNKNOWN을 유지한다. 모든 사업의 모든 입력항목을 판정한다고 주장하지 않는다.

현재 만 나이는 가능한 생년월일 구간으로 바꾸어 공식 고정 출생범위와 비교한다. 구간 전체가 포함되면PASS, 전부 벗어나면FAIL, 일부만 겹치면UNKNOWN이다. 예:2026-11-01의 만35세는1990-11-02~1991-11-01 출생 가능성이 있어 국토부 월세의1991-01-01 경계에서는UNKNOWN이다. 만36세는기본범위밖이고,만25세는연령범위안이다. 생년월일을 임의로 만들지 않는다.

가입일 현재 나이를 사용하는 청년주택드림은 ‘오늘 가입한다고 가정한 기본 범위’만 비교한다. 병역/특례 정보가 없으면 나이가 기본 상한을 넘어도 UNKNOWN을 보존한다. 특례를 최대기간으로 임의 적용하지 않는다. 원문의 기준일이 없거나 충돌하면 나이 규칙 전체를UNKNOWN으로 둔다.

안산 응시료는 공고의 출생연도와 현행 페이지의 신청일 나이 표현이 달라 연령을 자동 확정하지 않는다. 시험 응시일 미취업·1년 미만 단기근로 예외가 있어 현재 근로 중이어도 제외하지 않는다. 서울 청년수당은 주30시간 이하 OR3개월 이하 예외가 있어 근로 중은UNKNOWN이다. 경기 복지포인트는 현재 근로 여부의 관련성을 비교하지만 공고 당시 재직·기업유형·시간·소득은 추가 확인한다. 과거 신청일의 상태를 현재 상태로 증명하지 않는다.

월세 여부는 국토부/서울 월세지원의 기본 주거형태만 비교한다. 월세=yes라도 무주택·임대차계약·금액·납부·소득·재산·부모 별도거주를PASS 처리하지 않는다. 이사비 지원은 전세도 가능하므로 no를FAIL로 바꾸지 않는다. 월세 미기재 사업에도 임의 필수조건을 추가하지 않는다.

가구소득·자산·증빙·기준일 주민등록·중복 수급·선정 여부는 전부 추가 확인한다. 생활비 소득을 정책 소득으로 환산하지 않는다. 지역 관련성/조건 일치/접수상태/최종자격은 별도로 표시한다. 모집이 종료된 사업은 조건이 맞아도 CLOSED다.

## 구조와 재현

새 `backend/opportunities/personal_discovery.py`가 엄격한 입력/근거 모델, 나이 구간 비교, 고용/월세 비교,4조건 요약표 및 공용 데이터 컴파일을 맡는다. 기존 M1 지역 비교는 기존 regional 모듈을 통해 재사용한다. 기존 Policy Engine·Cashflow·금융 계산·Coverage·Historical·Acceptance 구현은 수정하지 않았다.

`python -m backend.opportunities.personal_discovery`로 재현한다. 입력은 기존38개,신규3개,별도조건근거 JSON이다. 웹은 Python 결과표를 조회하고 정렬/숨김만 수행한다. 법적 자격이나 금액을 브라우저/LLM에서 계산하지 않는다. 입력 조합 요약81가지 모두eligibilityUNKNOWN/benefit0을 검증했다.

나이 계산표는11/1부터366일을29개의 중복 없는 패턴으로 저장하며 범위 밖은UNKNOWN이다. 이1년은 **날짜 연산의 제공 범위이며 공식정보 유효기간이나 새 확인일이 아니다**. 모집 검토창은 기존11/8까지 그대로이고, 이후 표시에는 최신 공고 재확인이 필요하다. 이전 자료 확인일10/30을11/1로 위장 갱신하지 않았다. 재검토12개 조건 근거와 신규3개는 별도로11/1 확인을 기록했다.

공식 조건 연결표:

| 사업 ID | 연령 비교 | 취업 비교 | 월세 필수 | 공식 근거 |
|---|---|---|---|---|
| KR-YOUTH-RENT-2026 | BIRTH_RANGE · 2026년 공고의 명시 생년월일 범위 · 1991-01-01~2007-12-31 | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 확인 | [청년월세 지원사업 조건 공식 확인](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001565) (확인2026-11-01)<br>[청년월세 지원사업 추가 공식 근거](https://www.korea.kr/news/policyNewsView.do?newsId=148961039) (확인2026-11-01) |
| ANSAN-INTERVIEW-SUIT-2026 | UNKNOWN · 2026-01-14 보도자료, 나이 산정 기준일 미명시 | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [2026 안산 청년취업 면접복장 무료대여 조건 공식 확인](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1660127) (확인2026-11-01) |
| ANSAN-YOUTH-EXAM-FEE-2026 | UNKNOWN · 2026 공고 생년범위와 현행 안내의 신청일 기준 만 나이 표현이 달라 연령을 확정하지 않습니다. 담당기관 확인 필요. | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [2026 경기청년 역량강화 기회지원 · 안산 응시료 지원 조건 공식 확인](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1670879&key=271) (확인2026-11-01)<br>[2026 경기청년 역량강화 기회지원 · 안산 응시료 지원 추가 공식 근거](https://ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=www01609) (확인2026-11-01) |
| ANSAN-YOUTH-MOVE-FEE-2026 | BIRTH_RANGE · 2026년 공고의 명시 생년월일 범위 · 1986-01-01~2007-12-31 | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [2026 안산 청년 부동산 중개보수 및 이사비 지원 조건 공식 확인](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1665156&currentPage=1&key=271&sch_text=&sch_type=sj) (확인2026-11-01)<br>[2026 안산 청년 부동산 중개보수 및 이사비 지원 추가 공식 근거](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=www01786) (확인2026-11-01) |
| ANSAN-YOUTH-BASIC-INCOME-2026-Q3 | BIRTH_RANGE · 2026년 3분기 명시 출생범위 · 2001-07-02~2002-07-01 | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [2026 안산 청년기본소득 · 3분기 조건 공식 확인](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390) (확인2026-11-01) |
| GG-YOUTH-INTERVIEW-ALLOWANCE-2026 | BIRTH_RANGE · 2026년 공고의 명시 생년월일 범위 · 1986-01-01~2008-12-31 · 병역 특례는 추가 확인 | 근로 PASS, 미취업 PASS, 자영업 PASS | 필수로 단정하지 않음 | [2026 경기도 청년 면접수당 조건 공식 확인](https://youth.gg.go.kr/gg/intro/notice.do?article.offset=550&articleLimit=10&articleNo=9808&mode=view) (확인2026-11-01)<br>[2026 경기도 청년 면접수당 추가 공식 근거](https://youth.gg.go.kr/gg/intro/notice.do?article.offset=330&articleLimit=10&articleNo=10454&mode=view) (확인2026-11-01) |
| GG-YOUTH-WELFARE-POINTS-2026 | BIRTH_RANGE · 2026년 공고의 명시 생년월일 범위 · 1986-01-01~2007-12-31 · 병역 특례는 추가 확인 | 근로 PASS, 미취업 FAIL, 자영업 UNKNOWN | 필수로 단정하지 않음 | [2026 경기도 청년 복지포인트 조건 공식 확인](https://gjf.or.kr/main/pst/view.do?pst_id=notice_ap&pst_sn=202825) (확인2026-11-01) |
| KR-YOUTH-TOMORROW | UNKNOWN · 실제 신청일 | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [청년내일저축계좌 조건 공식 확인](https://www.bokjiro.go.kr/ssis-tbu/cms/pc/customer/notice/1309680_1141.html) (확인2026-11-01) |
| KR-YOUTH-FUTURE | BIRTH_RANGE · 2026년2차 가입절차에 대해 공식 명시된 출생범위 · 1991-11-17~2007-11-27 · 병역 특례는 추가 확인 | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [청년미래적금 조건 공식 확인](https://www.korea.kr/news/policyNewsView.do?newsId=148972819) (확인2026-11-01) |
| KR-YOUTH-HOUSING | CURRENT · 오늘 가입한다고 가정한 기본 만19~34세 범위 비교. 병역·소득 특례와 실제 가입일은 추가 확인. | 근로 PASS, 미취업 PASS, 자영업 PASS | 필수로 단정하지 않음 | [청년 주택드림 청약통장 조건 공식 확인](https://obank.kbstar.com/quics?cc=b061496:b061645&isNew=Y&page=C016613&prcode=DP01000935) (확인2026-11-01) |
| SEOUL-YOUTH-RENT-2026 | BIRTH_RANGE · 2026년 공고의 명시 생년월일 범위 · 1986-01-01~2007-12-31 · 병역 특례는 추가 확인 | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 확인 | [2026 서울시 청년월세지원 조건 공식 확인](https://housing.seoul.go.kr/site/main/content/sh01_060513?tr_code=short) (확인2026-11-01) |
| SEOUL-YOUTH-ALLOWANCE-2026 | BIRTH_RANGE · 2026년5월 모집 공식 안내의 명시 출생일 범위 · 1991-05-01~2007-05-31 · 병역 특례는 추가 확인 | 근로 UNKNOWN, 미취업 PASS, 자영업 UNKNOWN | 필수로 단정하지 않음 | [2026 서울시 청년수당 · 5월 모집 안내 조건 공식 확인](https://youth.seoul.go.kr/youthConts.do?key=2310100061&sc_bbsStngSn=2212200001&sc_faqCtgryCd=005&sc_pbancSeCd=012&sc_qnaCtgryCd=004) (확인2026-11-01) |
| BUSAN-JOY-DOUBLE | BIRTH_RANGE · 2026 공식 공고의 출생범위 1986.1.1~2008.12.31을 사용합니다. | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [부산청년플랫폼 2026 기쁨두배통장 사업 안내](https://young.busan.go.kr/index.nm?menuCd=53) (확인2026-10-30) |
| INCHEON-DREAM-FOR | BIRTH_RANGE · 2026.1.1 기준 1986.1.2~2008.1.1 출생. 의무복무 제대군인 연령 연장은 추가 확인. | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [인천청년포털 2026 드림For 청년통장 안내](https://youth.incheon.go.kr/financial/dreamfor.jsp) (확인2026-10-30) |
| GN-MODADREAM | BIRTH_RANGE · 2026.7.1 기준 공식 출생범위 1986.7.2~2008.7.1. | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [모다드림 청년통장 2026 하반기 공식 모집 공고](https://www.modadream.kr/upload/board/20260727092534-77423622.pdf) (확인2026-10-30) |
| DAEJEON-FUTURE-DOUBLE | BIRTH_RANGE · 2026 공고의 명시 출생범위 1986.1.1~2008.12.31. 기준일2026.9.22. | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [대전청년포털 2026 미래두배 청년통장 안내](https://daejeonyouthportal.kr/content/CT_000000000067/cntPage.do?commonMenuNo=&dpmSectionFst=1&dpmSectionScd=16) (확인2026-10-30) |
| JB-TOGETHER-DOUBLE | BIRTH_RANGE · 2025.12.31 기준 공식 출생범위 1986.1.1~2007.12.31. 현재 만 나이로 대체하지 않습니다. | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [전북청년 함께 두배적금 2026 사업 안내](https://double.jb2030.or.kr/sub/2024_data.html) (확인2026-10-30) |
| SEOUL-YOUTH-CULTURE-PASS-2026 | BIRTH_RANGE · 현행 서울 공식 사업안내의 일반2002~2005년생. 과거 보도보다 확장된 범위를 사용하며 병역 예외는 추가 확인합니다. | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [서울청년문화패스 현재 공식 사업안내](https://youth.seoul.go.kr/youthConts.do?key=2310200023&sc_bbsCtgrySn=2310200005&sc_bbsStngSn=2212200001&sc_faqCtgryCd=002&sc_pbancSeCd=005&sc_qnaCtgryCd=) (확인2026-11-01)<br>[2026 서울청년문화패스 조기 모집 보도(과거 연령 안내 보존)](https://news.seoul.go.kr/culture/archives/531194) (확인2026-11-01) |
| SEOUL-YOUTH-MOVE-FEE-2026-H2 | BIRTH_RANGE · 2026년 기준 만19~39세로 표기하며 공식 출생범위는1986.1.1~2007.12.31. 신청 시 기준 서울 거주·무주택·세대주 및 임차인 본인 조건을 확인합니다. | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [서울시 청년 부동산 중개보수 및 이사비 2026 하반기 공식 사업안내](https://youth.seoul.go.kr/youthConts.do?key=2310100044&orderBy=regYmd+desc&pageIndex=1&pstSn=&recordCountPerPage=10&sc_bbsCtgrySn=2310200013&sc_bbsStngSn=2212200001&sc_ctgry=&sc_delYn=&sc_detailAt=&sc_faqCtgryCd=003&sc_ntcPstYn=&sc_pbancSe=&sc_pbancSeCd=015&sc_plcyQnaSn=0&sc_pstSn=0&sc_qnaCtgryCd=002&sc_userId=&tabKind=300&useYn=) (확인2026-11-01) |
| GN-YOUTH-INTERVIEW-SUIT-2026 | UNKNOWN · 출생연도1986~2008과 고교졸업예정자 포함 범위의 정확한 적용은 추가 확인합니다. | 근로 UNKNOWN, 미취업 UNKNOWN, 자영업 UNKNOWN | 필수로 단정하지 않음 | [경남바로서비스 2026 청년 면접정장 무료대여](https://baro.gyeongnam.go.kr/baro/serviceView.es?mid=a10202000000&service_no=438) (확인2026-11-01) |

## 검증 결과

- 새 Python 테스트42개; 기존 지역32개 포함74 passed,11.73초.
- 관련 화면20 passed,17.87초; 신규 개인조건 화면9개.
- 전체 Backend **12,740 passed /1 skipped /1 warning**,195.20초.
- 전체 Frontend **247 passed /17files**,106.28초.
- TypeScript·로컬/공개 build 성공. local3.37초/public2.77초. 공용 지원자료 chunk175.98kB(gzip30.41),공개main311.68kB(gzip95.73).500kB 경고 없음.
- 실제 로컬/공개 화면:안산25세미취업월세→국가월세/안산이사비;월세없음→국가월세제외·전세가능이사비유지;불일치보기복원;35세경계UNKNOWN·36세기본범위밖.모바일390설정에서문서375/scroll375로가로넘침없음.
- skip은기존M2.77파일symlink미검증,warning은기존Starlette/httpx사용중단예고.이번신규논리/UI시험실패0.전체회귀를실제실행했다.
- 최초 source helper의 네트워크 DNS 제한은 승인된 외부 저장소 접속으로 해결했다. 배포 준비 시 자격만료는 같은 사이트의 단기 자격을 재발급해 해결했다. 제품·보안 설정을 바꾸지 않았다.

## 보호 감사

기준선293개 중 보호235개 기존backend/tests/data는SHA256동일하다.원본지역38개·기존은행74개·공시299개·release6개·golden과Coverage동결에변경없음.기존src변경7개는화면·홈·가이드및관련시험이며별도로vite chunk설정1개를수정했다.수량시험38→41과홈문구기대값은이번요청에맞게변경했고기존판정/계산/골든기대값은변경하지않았다.

실제상품만기계산0개,미승인지원금0원,실제정책DRAFT/CONDITION_SLICE,ResidenceHistory OFFICIAL_INQUIRY_REQUIRED,M2.77 SYNTHETIC_ONLY를유지한다.추가LLM실행·유료서버·자동수집·예약알림·계정연결없음.

## 배포와 기록

기존public audience 유지. 공개v8,commit `29503c0482524a09fa113fdea60bdd155cb9c4fd`. 배포 `appgdep_6ae62dacea5081919792525704e6c439`. 원본조사/시험로그:`<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\personal-support`. 공개증거/보존감사:`<USER_HOME>\Documents\ChatGPT\AI+X채팅\output\personal-support`. 공개source에는실제개인입력·비밀키·원자료문서·실험응답을포함하지않았다.

Obsidian 개발노트/대시보드/현재상태/테스트기록을갱신한다.파일/Wikilink검사와앱GUI확인은별도다.이번Obsidian GUI는미확인이다.

## 남은 한계와 다음 최소 작업

전체지원사업41개가현재모집중이거나전체개인조건검증이완료된것은아니다.전국전수/실시간서비스가아니다.다음제안은안산응시료처럼예외가있는사업하나의응시일·단기근로기준을공식확정한뒤추가질문을붙이는것이다.사용자의‘계속추가’는이번공식검토와목록확장으로수행했으며자동감시/자동수집을예약하지않았다.
