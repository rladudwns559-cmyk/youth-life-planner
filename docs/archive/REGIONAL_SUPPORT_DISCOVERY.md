# 지역별 청년지원사업 탐색 확장

완료일 2026-11-01 KST. 최종 판단 **REGIONAL_YOUTH_SUPPORT_DISCOVERY_EXPANDED**. [공개 지원사업 찾기](https://youth-life-planner.rladudwns559.chatgpt.site/#/programs),공개v7 succeeded 및 실제 화면 확인.

## 결과와 승인 범위

이전10개는 전국 청년지원사업의 총수가 아니라 자산형성 위주 등록목록이었다. 사용자의 후속 요청에 따라 월세·주거·취업·면접·교육·응시료·생활·문화까지 정보 탐색 범위를 확장했다. 기존10개를 보존하고28개를 추가해 **고유사업38개**다. 분야별로 자산형성10·취업8·생활8·주거5·교육5·문화2개이며 **17개 광역지역의 자료**를 포함한다. 각 광역지역의 모든 시군구·사업을 수집한 것은 아니다. 세부 시군구는 안산·달서·광산·청양·함평·포항·진주7곳의 확인 자료다.

전국 국토부 월세지원과 안산의 접수 안내는 하나의 사업에2공식출처로 병합했다. 같은 국가지원을 지자체마다 별도 사업으로 중복 집계하지 않는다. 서울·대전·세종의 자체 월세지원은 별도 사업이다. 지역구별 응시료 지원은 관할별 공고가 달라 구분했다. 향후 지역 확대에 필요한 구조는 갖추었으나 전국 전수 수집·실시간 운영·전체 자격 판정 완료를 의미하지 않는다.

## 사용자 흐름

홈 주요 버튼을 ‘내 지역 지원 찾기’로 변경했다. 청년 지원사업 페이지에서 광역지역·시군구를 고르면 **전국+해당 광역지역+해당 시군구** 목록을 찾는다. 분야·모집상태·텍스트 검색과12개씩 더 보기,다른지역 포함,초기화를 제공한다. 시군구를 모르면 해당 지역 조건은UNKNOWN으로 남겨 확인사항을 표시한다. 목록에 없는 시군구를 명시하면 다른 시군구 사업을 일치로 올리지 않는다. 광역지역 변경 시 선택한 시군구는 초기화한다.

안산 선택 시 전체 검토목록13개,주거 분야2개(전국 청년월세+안산 중개보수·이사비)를 실제 확인했다. 이는 신청자격을 충족한13개/2개가 아니다. 미입력·실제 나이·가구소득·자산·무주택·근로·기준일 주민등록·거주기간·중복수급·선발은 모두 추가 확인한다. 생활비 소득을 공식 소득으로 환산하지 않는다. 최종 자격 PASS·‘이용 가능성 높음’을 만들어내지 않는다.

카드에는 지원내용·모집정보·현재 지역의 관련성·추가확인이 나오고 펼치면 연령·소득·일정·필요 증빙·출처·자료기준일·확인일을 볼 수 있다. 증빙서류는 외부 공식 신청 시 확인할 정보이며 우리 사이트에서 파일·주민번호·계좌정보를 받지 않는다. 입력 선택은 메모리에서만 사용하고 서버/LLM 전송·영구 저장하지 않는다. 목록 밖의 정책은 검증한 온통청년 공식 통합검색 링크로 추가 탐색할 수 있다. 링크를 등록 사업 수에 포함하지 않는다.

## 공식 자료 검토와 주요 변경

- [경기도 면접수당10/19 공지](https://youth.gg.go.kr/gg/intro/notice.do?article.offset=330&articleLimit=10&articleNo=10454&mode=view)의11월2차 미운영을 반영했다. 과거 ‘11월 예정’ 문구로 다음 모집을 만들어내지 않는다.
- [인천 드림나래](https://youth.incheon.go.kr/job/suit.jsp)는12/11까지 사업기간 안내보다 현재 공식 정장·컨설팅 접수마감 표기를 우선했다. 실제 조기마감일은 미확인이다.
- [안산 응시료 하반기 일정변경](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1681767)은9/4 09시로 바뀌었다.예산 잔여 미확인으로 UNKNOWN이다. 원공고12/4만 보고 현재 접수중으로 단정하지 않는다.
- 제주 전입지원의 ‘연중’ 안내보다7월 조기마감 임박 후속 공지를 함께 보존했고 현재 접수는UNKNOWN이다.
- 광산구 취업조건,전북 소득기준,포항 재게재 신청일의 공식 자료 충돌은 텍스트로 명시하고 판정에 사용하지 않는다. 광산구는 서울시 공식 타지역정책 재게재이며 현지 페이지 접근 실패라는 한계가 있다. 포항 자료의 출처가 고령군이라고 관할을 고령군으로 바꾸지 않는다.
- 충북 일경험·함평 문화카드는 공식 도메인의 검색색인 증거이며 직접 원문이502/timeout인 점을 표시했다. 직접 확인한 자료와 같은 증거 수준으로 표현하지 않는다. 공고 첨부/실제 공적 기준이 미확인인 곳도 남은 확인사항으로 기록했다.

공식 확인 사업별 자료:

| 사업 | 적용 지역·분야 | 모집 근거와 불확실성 | 공식 출처 |
|---|---|---|---|
| 청년 주택드림 청약통장 | 전국  /ASSET | 확인한 은행 공시는 2028.12.31까지 가입 안내. 10월 소득요건 완화는 개정 예정 보도와 현행 공시가 달라 시행·적용 기준 재확인이 필요합니다. | [PREVIOUS_VERIFIED_SNAPSHOT](https://www.korea.kr/common/download.do?fileId=198568323&tblKey=GMN) · 기준2026-10-12 · 확인2026-10-30<br>[PREVIOUS_VERIFIED_SNAPSHOT](https://obank.kbstar.com/quics?cc=b061496:b061645&isNew=Y&page=C016613&prcode=DP01000935) · 기준2026-06-30 · 확인2026-10-30 |
| 드림For 청년통장 | 인천  /ASSET | 확인한 2026년 모집 회차입니다. 추가·다음 연도 모집을 추정하지 않습니다. | [PREVIOUS_VERIFIED_SNAPSHOT](https://youth.incheon.go.kr/financial/dreamfor.jsp) · 기준미표시 · 확인2026-10-30 |
| 모다드림 청년통장 | 경남  /ASSET | 확인한 2026년 모집 회차입니다. 추가·다음 연도 모집을 추정하지 않습니다. | [PREVIOUS_VERIFIED_SNAPSHOT](https://www.modadream.kr/upload/board/20260727092534-77423622.pdf) · 기준2026-07-27 · 확인2026-10-30 |
| 미래두배 청년통장 | 대전  /ASSET | 확인한 2026년 모집 회차입니다. 추가·다음 연도 모집을 추정하지 않습니다. | [PREVIOUS_VERIFIED_SNAPSHOT](https://daejeonyouthportal.kr/content/CT_000000000067/cntPage.do?commonMenuNo=&dpmSectionFst=1&dpmSectionScd=16) · 기준2026-09-22 · 확인2026-10-30 |
| 부산청년 기쁨두배통장 | 부산  /ASSET | 확인한 2026년 모집 회차입니다. 추가·다음 연도 모집을 추정하지 않습니다. | [PREVIOUS_VERIFIED_SNAPSHOT](https://young.busan.go.kr/index.nm?menuCd=53) · 기준2026-08-03 · 확인2026-10-30 |
| 전북청년 함께 두배적금 | 전북  /ASSET | 확인한 2026년 모집 회차입니다. 추가·다음 연도 모집을 추정하지 않습니다. | [PREVIOUS_VERIFIED_SNAPSHOT](https://double.jb2030.or.kr/sub/2024_data.html) · 기준2026-03-03 · 확인2026-10-30 |
| 청년내일저축계좌 | 전국  /ASSET | 확인한 2026년 모집 회차입니다. 추가·다음 연도 모집을 추정하지 않습니다. | [PREVIOUS_VERIFIED_SNAPSHOT](https://www.bokjiro.go.kr/ssis-tbu/cms/pc/customer/notice/1309680_1141.html) · 기준2026-04-24 · 확인2026-10-30<br>[PREVIOUS_VERIFIED_SNAPSHOT](https://www.bokjiro.go.kr/ssis-tbu/cms/pc/news/news/1309724_1114.html) · 기준2026-05-02 · 확인2026-10-30 |
| 청년미래적금 | 전국  /ASSET | 10월 16일 신규 신청 종료. 11월 16~27일은 기존 신청자 중 심사 통과자의 계좌개설 기간이며 신규 모집이 아닙니다. | [PREVIOUS_VERIFIED_SNAPSHOT](https://www.korea.kr/news/policyNewsView.do?newsId=148972819) · 기준2026-09-30 · 확인2026-10-30 |
| 희망두배 청년통장 | 서울  /ASSET | 확인한 2026년 모집 회차입니다. 추가·다음 연도 모집을 추정하지 않습니다. | [PREVIOUS_VERIFIED_SNAPSHOT](https://news.seoul.go.kr/welfare/archives/581505?listPage=1) · 기준2026-06-15 · 확인2026-10-30 |
| 경기도 청년 노동자 통장 | 경기  /ASSET | 2026.10.14 공식 공지: 2026년 신규모집 미운영. 과거 또는 연초 모집 계획을 현재 모집으로 사용하지 않습니다. | [PREVIOUS_VERIFIED_SNAPSHOT](https://account.gfgf.kr/hpdsk/ntc/list.do?mode=list&searchBbsSeCd=01&searchOpnpYn=Y) · 기준2026-10-14 · 확인2026-10-30 |
| 청년월세 지원사업 | 전국  /HOUSING | 2026 신규 모집은3월30일~5월29일.9월 이후 지급·심사 일정은 신규 신청기간이 아닙니다.안산시는 주소지 행정복지센터/복지로로 접수합니다. | [OFFICIAL_PAGE](https://www.korea.kr/news/policyNewsView.do?newsId=148961039) · 기준2026-03-18 · 확인2026-11-01<br>[OFFICIAL_PAGE](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001565) · 기준미표시 · 확인2026-11-01 |
| 국민취업지원제도 청년 선발형 안내 | 전국  /EMPLOYMENT | 2026-04-27부터 추가모집 안내,선착순3만명 도달 시 조기종료.종료/잔여인원을 확인하지 못해 모집 중으로 확정하지 않습니다. | [OFFICIAL_PAGE](https://www.110.go.kr/data/counselView.do?curPage=2&num=A01_721021&scCate1=&scCate2=&scIntt=&scText=&scType=) · 기준2026-05-18 · 확인2026-11-01 |
| 국민내일배움카드 | 전국  /EDUCATION | 고용24 카드 발급 절차 안내입니다.개별 교육과정의 모집기간·잔여석을 보장하지 않습니다. | [OFFICIAL_PAGE](https://www.work24.go.kr/cm/c/f/1100/selecSystInfo.do?currentPageNo=1&recordCountPerPage=12&systClId=SC00000004&systId=SI00000351) · 기준2026-07-27 · 확인2026-11-01 |
| 2026 안산 청년취업 면접복장 무료대여 | 경기 안산시 /EMPLOYMENT | 2026 사업 재개 안내; 정확 접수일 미확인 / 실제 신청 시작일·마감일 및 현재 예산 잔여가 확인되지 않아 모집중 표시 금지. | [OFFICIAL_NOTICE](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1660127) · 기준2026-01-14 · 확인2026-11-01 |
| 2026 경기청년 역량강화 기회지원 · 안산 응시료 지원 | 경기 안산시 /EDUCATION | 상반기 원공고; 예산 소진 조기마감; 2026-05-11; 09:00; 2026-12-04; 18:00 / 하반기 변경 공고: 선착순·예산 소진 시 종료; 2026-09-04; 09:00 / 변경공고 게시일 및 하반기 실제 예산 소진 여부 미확인. / 민간 사이트의 마감 주장만으로 CLOSED를 확정하지 않음. / 원공고의 12/4 종료일만으로 현재 접수중이라고 단정하면 안 됨. | [OFFICIAL_NOTICE](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1681767) · 기준미표시 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1670879&key=271) · 기준2026-04-29 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://www.ansan.go.kr/ansantalktalk/content/ansantalk/cityNews.html?fidx=24748&opt=&page=136&pg=vv&sword=) · 기준2026-05-08 · 확인2026-11-01 |
| 2026 안산 청년 부동산 중개보수 및 이사비 지원 | 경기 안산시 /HOUSING | 2026년 모집; 2026-03-01; 2026-03-31 / 공고 게시일과 시작·종료 시각 미기재. / 청소비 제외는 공식 사업안내 페이지 www01786에서 별도 확인. | [OFFICIAL_NOTICE](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1665156&currentPage=1&key=271&sch_text=&sch_type=sj) · 기준미표시 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=www01786) · 기준미표시 · 확인2026-11-01 |
| 2026 경기도 청년 면접수당 | 경기  /EMPLOYMENT | 2026년 1차; 2026-06-24; 09:00; 2026-07-23; 18:00 / 2026년 2차; 2026-10-19 공식 공지에서 11월 예정 모집 미운영 확정 / 일반 소개 페이지의 7/7과 실제 1차 모집공고의 7/23이 달라 후자 우선. / 과거 11월 예정 안내는 10/19 취소 공지로 대체. 다음 모집 알림 생성 금지. | [OFFICIAL_NOTICE](https://youth.gg.go.kr/gg/intro/notice.do?article.offset=330&articleLimit=10&articleNo=10454&mode=view) · 기준2026-10-19 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://youth.gg.go.kr/gg/intro/notice.do?article.offset=550&articleLimit=10&articleNo=9808&mode=view) · 기준2026-06-17 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://www.hknu.ac.kr/bbs/kor/597/112626/download.do) · 기준2026-06-17 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://www.gccity.go.kr/gcyouth/bbs/view.do?bIdx=192996&mId=0101000000&ptIdx=467) · 기준2026-06-18 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://www.gg.go.kr/contents/contents.do?ciIdx=987029&menuId=265937) · 기준미표시 · 확인2026-11-01 |
| 2026 경기도 청년 복지포인트 | 경기  /LIVING | 2026년 모집; 2026-07-01; 09:00; 2026-07-13; 18:00 / 연초 선발계획의 1만명을 확정 선발인원으로 재사용하지 않음. / 세부 근무기간·제외 조건은 첨부 공고문 추가 검토 필요. | [OFFICIAL_NOTICE](https://gjf.or.kr/main/pst/view.do?pst_id=notice_ap&pst_sn=202825) · 기준2026-06-26 · 확인2026-11-01 |
| 2026 서울시 청년월세지원 | 서울  /HOUSING | 2026년 모집; 2026-05-06; 10:00; 2026-05-19; 18:00 / 국토부 전국 월세지원과 다른 서울시 사업. / 주택 예외와 가구소득을 단순 monthly_income으로 판정하지 않음. | [OFFICIAL_NOTICE](https://housing.seoul.go.kr/site/main/content/sh01_060513?tr_code=short) · 기준미표시 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://www.seoul.go.kr/news/news_report.do?nttNo=457144) · 기준2026-04-30 · 확인2026-11-01 |
| 2026 서울시 청년수당 · 5월 모집 안내 | 서울  /EMPLOYMENT | 2026년 5월 모집; 2026-05-27; 10:00; 2026-05-29; 16:00 / 출생일 범위는 공식 5월 모집 안내값 보존, 다른 회차에 재사용 금지. / 수당을 임의 현금 여유자금·저축가능액으로 합산하지 않음. | [OFFICIAL_NOTICE](https://youth.seoul.go.kr/youthConts.do?key=2310100061&sc_bbsStngSn=2212200001&sc_faqCtgryCd=005&sc_pbancSeCd=012&sc_qnaCtgryCd=004) · 기준미표시 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://youth.seoul.go.kr/youthConts.do?key=2310100061&orderBy=regYmd+desc&pageIndex=1&recordCountPerPage=10&sc_bbsCtgrySn=2310200011&sc_bbsStngSn=2212200001&sc_faqCtgryCd=005&sc_pbancSeCd=012&sc_plcyQnaSn=0&sc_pstSn=2605220005&sc_qnaCtgryCd=004&sc_rvwSn=0&tabKind=201) · 기준2026-05-22 · 확인2026-11-01 |
| 2026 부산 청년 일하는 기쁨카드 | 부산  /LIVING | 2026년 모집; 2026-04-06; 10:00; 2026-04-24; 18:00 / 2년 내 입사라는 요약과 명시 날짜를 임의 환산·정정하지 않음. | [OFFICIAL_NOTICE](https://www.busan.go.kr/nbgosi/view?curPage=118&gosiGbn=A&sno=77096) · 기준2026-04-01 · 확인2026-11-01 |
| 2026 부산 청년 사회진입 활동비 · 디딤돌카드+ | 부산  /EMPLOYMENT | 2026년 모집; 2026-03-09; 10:00; 2026-03-27; 18:00 / 부산청년센터가 공식 운영사이트로 연결함을 확인. / 2027 모집 알림 사전신청은 2026 본사업 신규 모집과 다름. | [OFFICIAL_NOTICE](https://young.busan.go.kr/bycenter/article/view.nm?article_id=3959&menuCd=136) · 기준2026-03-12 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://youthdidimdol.kr/intro) · 기준2026-03-03 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId=WLF00002555) · 기준2026-07-04 · 확인2026-11-01 |
| 2026 인천 재직청년 복지포인트 | 인천  /LIVING | 2026년 모집; 2026-04-01; 10:00; 2026-04-10 / 종료 시각 미기재. / 일반 소득 입력값을 공식 건강보험 과세급여로 대체하지 않음. | [OFFICIAL_NOTICE](https://youth.incheon.go.kr/financial/point.jsp) · 기준미표시 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://youth.incheon.go.kr/financial/point_notice.jsp) · 기준2026-04-01 · 확인2026-11-01 |
| 2026 인천 드림나래 · 면접정장·이미지컨설팅 | 인천  /EMPLOYMENT | 사업기간; 실제 모집종료일과 구분; 2026-01-26; 2026-12-11 / 공식 현재 팝업·접수마감 표기를 예정 사업종료12/11보다 우선. / 실제 조기마감 날짜 미기재. / 18세 문구와 출생연도 범위는 그대로 보존; 임의로 한쪽을 정정하지 않음. | [OFFICIAL_NOTICE](https://youth.incheon.go.kr/job/suit.jsp) · 기준미표시 · 확인2026-11-01<br>[OFFICIAL_NOTICE](https://youth.incheon.go.kr/main/bbs/bbsMsgList.do?bcd=suit_faq&pgno=2) · 기준미표시 · 확인2026-11-01 |
| 2026년 대전 청년 월세지원사업 | 대전  /HOUSING | 공고에 실제 접수기간이 명시됐으며 기준일 현재 종료됨. 후속 모집 여부는 별도 확인 필요.  지자체 모집공고 본문 직접 확인 신청시작 2026-08-31T09:00:00+09:00 신청종료 2026-09-10T18:00:00+09:00 | [OFFICIAL_PAGE](https://www.daejeon.go.kr/drh/drhGosiView.do?conifmenddt=2026-12-31&conifmstdt=2026-01-01&gosigbn=A&menuSeq=1908&pageIndex=1&sno=56586) · 기준2026-08-24 · 확인2026-11-01 |
| 2026년 달서청년 자격증 응시료 지원사업 | 대구 달서구 /EDUCATION | 공식 예정 접수기간 안에 있으나 예산 소진 시 조기 종료. 잔여예산·실제 접수 가능 여부 미확인.  지자체 사업안내 및 공고 본문 직접 확인 신청시작 2026-01-15 신청종료 2026-11-30 | [OFFICIAL_PAGE](https://www.dalseo.daegu.kr/index.do?menu_id=00004358) · 기준2026-01-06 · 확인2026-11-01 |
| 2026년 광산구 구직청년 자격증 취득비용 지원사업 | 광주 광산구 /EDUCATION | 예산 소진 시 조기마감 조건. 현재 잔여예산 미확인  서울시 공식 청년정책 타지역 목록 상세 본문 직접 확인. 현지 원문은 리다이렉트 접근 실패 신청시작 2026-02-02T09:00:00+09:00 신청종료 2026-11-30T18:00:00+09:00 | [OFFICIAL_PAGE](https://youth.seoul.go.kr/infoData/youthPlcyInfo/view.do?key=2309160001&plcyBizId=20260408005400212632) · 기준미표시 · 확인2026-11-01 |
| 2026년 울산 청년 스포츠·문화패스 | 울산  /CULTURE | 보도 본문은 5월 26일 접수 개시 예정이라고 설명하나 실제 공고의 확정 종료일·현재 잔여 인원은 미확인  울산시 공식 청년포털 보도자료 본문 직접 확인 | [OFFICIAL_PAGE](https://ulsan.go.kr/s/ulsanyouth/bbs/view.do?bbsId=BBS_0000000000000311&dataId=59982&mId=008006002000000000) · 기준2026-07-29 · 확인2026-11-01 |
| 2026년 세종청년 주거임대료 지원사업 상반기 모집 | 세종  /HOUSING | 해당 상반기 모집은 종료. 별도 하반기 공식 안내 검색색인에는 8.25~8.27 접수 및 9.22 선정결과가 확인되지만 현재 신규 모집 근거는 아님  세종청년센터 공식 공지 본문 직접 확인. 하반기 세종복지재단 자료는 공식 검색색인만 확인 신청시작 2026-03-03 신청종료 2026-03-05 | [OFFICIAL_PAGE](https://www.4242.or.kr/sub0506/view/page/4/id/2477) · 기준2026-02-23 · 확인2026-11-01 |
| 강원특별자치도 청년 취업준비 쿠폰 지원 | 강원  /LIVING | 연도별 실제 모집 회차·접수일은 사업안내에 없음  도청 공식 사업안내 본문 직접 확인 | [OFFICIAL_PAGE](https://state.gwd.go.kr/portal/partinfo/investmentEconomy/jobInformation/youngman/jobcoupon) · 기준2026-02-04 · 확인2026-11-01 |
| 미취업 청년 취업연계 일경험 지원 | 충북  /EMPLOYMENT | 공식 안내 자체가 모집시기 별도 문의라고 표시. 사업기간을 신청기간으로 쓰지 않음  도청 공식 사업안내의 검색색인 본문 확인. 직접 열람은 502 실패 | [OFFICIAL_INDEXED_PAGE](https://www.chungbuk.go.kr/jobinfo/contents.do?key=1652) · 기준미표시 · 확인2026-11-01 |
| 2026 청양군 청년취업수당 지원사업 | 충남 청양군 /LIVING | 월 단위 연중 안내만 있어 임의로 1월1일·12월31일을 생성하지 않음. 예산·실제 접수 미확인 2026.01~12, 연중상시 충남청년포털 공식 정책소식 본문 직접 확인 | [OFFICIAL_PAGE](https://youth.chungnam.go.kr/web/main/bbs/cnyouth_prom_ref/562) · 기준2026-03-31 · 확인2026-11-01 |
| 2026년 전북청년 지역정착 지원사업 | 전북  /LIVING | 도청 안내에 실제 모집일 명시, 종료됨  도청 안내 및 전주시 보도자료 직접 확인 신청시작 2026-03-06 신청종료 2026-03-20T17:00:00+09:00 | [OFFICIAL_PAGE](https://www.jeonbuk.go.kr/index.jeonbuk?menuCd=DOM_000000104006005002) · 기준2026-03-06 · 확인2026-11-01 |
| 2026년 전남광주 청년 문화복지카드 지원사업 3차 모집(함평군 공고) | 전남 함평군 /CULTURE | 3차 실제 접수기간 명시, 기준일 현재 종료  함평군 공식 모집공고 검색색인 확인. 원문 직접 열람 timeout. 지원내용은 곡성군 공식 2026 시책 PDF로 교차 확인 신청시작 2026-09-14 신청종료 2026-10-08 | [OFFICIAL_INDEXED_PAGE](https://www.hampyeong.go.kr/pg/GosiDetail.do?SEQ=32637&listGubun=&notAncmtSeCode=01%2C03%2C04&pageId=www273&pageIndex=1&search_Text=&search_Type=) · 기준2026-09-14 · 확인2026-11-01 |
| 2026년 진주시 청년 자격증 응시료 지원사업 | 경남 진주시 /EDUCATION | 실제 개시일은 확정됐으나 연중·예산 소진형 종료일과 잔여예산 미확인 2026.2.11~연중, 예산 소진 시 조기 마감 진주시 공식 공고 PDF 직접 확인 신청시작 2026-02-11 | [OFFICIAL_PAGE](https://young.jinju.go.kr/young/upload/board/20260210161746-76468660.pdf) · 기준2026-02-09 · 확인2026-11-01 |
| 청년 전입 축하장려금(2026 탐라청년출발패키지) | 제주  /LIVING | 조기마감 임박이라는 후속 공식 자료가 있어 상시 접수 문구만으로 모집중 표시 금지. 실제 마감일 미확인 정책 상세는 연중 예산 소진 시까지. 7.28 보도는 정부24 온라인 신청을 조만간 마감한다고 공지 제주도 공식 정책 상세 및 조기마감 예고 보도 본문 직접 확인 신청시작 2026-02-23 | [OFFICIAL_PAGE](https://www.jeju.go.kr/lifecycle/policy/list.htm?act=view&category=001&page=2&seq=108) · 기준2026-07-28 · 확인2026-11-01 |
| 2026 안산 청년기본소득 · 3분기 | 경기 안산시 /LIVING | 공식3분기 신규 접수9월1일~10월2일.10월20일 이후 지급은 신규 모집이 아닙니다.3분기 신규자 자동신청 중단 안내를 보존합니다. | [OFFICIAL_NOTICE](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390) · 기준2026-08-31 · 확인2026-11-01 |
| 2026 포항 청년 취업 준비 패키지 | 경북 포항시 /EMPLOYMENT | 고령군 공식 재게재 본문은2월3일09시~12월5일18시(일·월·공휴일 제외),하단 구조화 항목은3월24일09시~12월5일11:59로 다릅니다.예산 소진형이며 실제 접수를 확인하기 전 모집 중으로 표시하지 않습니다.고령군 사업이 아니라 포항시 사업입니다. | [OFFICIAL_PAGE](https://www.goryeong.go.kr/kor/boardView.do?BOARD_IDX=865&BRD_ID=1143&IDX=410) · 기준2026-03-11 · 확인2026-11-01 |

## 아키텍처와 계약

기존 Policy/Cashflow/Coverage/Acceptance/Historical 및 자산형성10개 엔진을 수정하지 않았다. 새 `backend/opportunities/regional_discovery.py`는 정보탐색 계층으로,기존 M1 원자 지역 비교를 재사용한다. 전국→광역→시군구의 관련성을 PASS/FAIL/UNKNOWN으로 비교하지만 이것은 **현재 관심지역 목록 필터**다. 법적 주민등록 자격 판정이나 거주기간 계산이 아니다. 미확인 전체조건을 UNKNOWN으로 남기고 지원금 반영0원을 고정했다.

공식 자료를 엄격한 로컬 모델로 검증한 후 지역별 결과표와 날짜별 모집표를 Python에서 생성한다. 브라우저는 표만 조회하며 자격 규칙을 새로 추론하지 않는다. 모집일은 정확한 날짜가 있는 경우에만 저장한다. 연중·월 단위·사업기간만으로1/1·12/31 또는 신청일을 생성하지 않는다. 정확한 시각은 원문 안내를 보존하되 신규모집 확정 상태를 표방하지 않는다. 기간 안이어도 잔여예산 미확인 사업은UNKNOWN이다.

현재 접수 확정 대신 ‘공고상 신청기간·잔여 확인’ 또는 ‘상시 제도 안내·접수 확인’으로 구분한다.확인된 마감/미운영은 우선한다. 각 출처의 기존 검토일을 보존하고7일 검토창이 지나면 긍정적인 일정 안내를 재확인으로 내린다. 공개표 생성일은11/1,표의 마지막 날짜는11/8이며 이전10개 자료의 확인일10/30은 새 날짜로 갱신하지 않았다. 새 연도/회차를 자동 생성하지 않는다.

기존 개인별 자산형성10개 API·조건비교는 로컬 검증 보관 영역으로 보존했다. 공개 사이트는 새 지역 탐색을 서버 없이 사용한다. 금융상품74개/18회사·공시299개 및 기존 비교기능은 그대로다. 새 유료자원·알림·자동화·로그인·LLM 호출0건.

## 실제 시험

| 검사 | 실제 결과 |
|---|---|
| 새 Backend |32 passed,0.84초 |
| 관련 UI/라우팅 |36 passed,19.67초 |
| Backend 전체 |12,698 passed /1 skipped /1 warning,171.48초 |
| Frontend 전체 최종 |238 passed /16 files,83.07초 |
| 신규 Frontend |8개 지역 탐색·개인정보·페이지/무결성 시험 |
| TypeScript·local/public build |실제 통과,빌드 로그 별도 보존 |
| 실제 브라우저 |안산 주거2개·서울 월세2개 분리·시군구 초기화·공식 링크·38/17 표시 확인 |
| 반응형 |320설정에서문서305/scroll305,390설정에서375/scroll375. 임시viewport 해제 |
| 공개 사이트 |v7 succeeded·실제 공개 경로 확인 |
| 사용자 효과·실물폰·Obsidian GUI |이번 시험 미실행 |

skip은기존M2.77 NTFS file symlink 필수증거 보류,warning은기존Starlette/httpx사용중단예고다. 지역 일치 수를 실제 수급 가능 수나 참가자 효과로 해석하지 않는다.

최초 실패 이력: 새 M1 재사용 호출에 evidence_refs를 누락해 자료표 생성이 거부됐다. 공식 출처URL을 전달하도록 새 모듈만 수정했고32개 시험을 통과했다. 첫 전체Frontend는 기존 금융상품시험3건 시간초과(235pass/3fail),한 worker 실행에서도6건 시간초과(232pass/6fail)였다. 상품 제출버튼 조회를 입력form 안으로 제한하고 관심/3개비교 시험에서 불필요한74카드 대신 기본12카드를 렌더링했다. **기존 기대값·제품 코드·5초 시험제한·LLM시간제한은 변경하지 않았다.** 첫 조회범위 보완 뒤에도3건 시간초과(235pass/3fail,106.32초)가 남아,개별 상품행 시험은 실제 검색으로 해당 카드를 표시하도록 바꾸었다.전체74개 목록을 확인하는3개 시험은 그대로 보존했다.상품별 판정 기대값을 변경하지 않고 최종238개 전체를 실제 재실행했고 이전 실패 로그도 보존했다. 구 검증탭은 유효하지 않아 동일 브라우저의 새 탭을 사용했으며 보안 우회는 없었다.

## 보호 감사와 기록

기준선520파일 중 기존 제품 변경은 App·홈·가이드 및 관련 화면시험/시험조회최적화7개다. 기존backend/tests/data보호232파일·release6개·GV/BV 지문4개·모든 기존 금융자료·기존10사업 스냅샷·Coverage freeze SHA256 불변. 새 모듈/자료/화면/시험/문서는 별도로 추가했다. 실제 상품 만기계산0개·미승인지원금0원,실제정책DRAFT/CONDITION_SLICE·ResidenceHistory OFFICIAL_INQUIRY_REQUIRED·M2.77 SYNTHETIC_ONLY 유지.

자료: `data/support-programs/regional-20261101.json`, `frontend/src/public-data/regional-programs.json`. 원본 조사 JSON과 실패/성공 로그는 `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\regional-programs`,보존감사·배포·실제화면 증거는 `<USER_HOME>\Documents\ChatGPT\AI+X채팅\output\regional-programs`. 조사 JSON은 참고 근거이며 카탈로그에 무검토 자동 편입하지 않았다.

공개commit `ace4fe0b6e1b4cf3a8c389e20216a10aa782d0e9`,version `appgprj_6ae4993139c08191975b01a22068da5c~appgver_60e40122f6e08191a2cee329a3dc3a3a`,deployment `appgdep_6ae62626e87081919b1a553b19552bfb`. 기존 public audience 유지. 토큰·개인자료·원자료 문서·실제 평가응답을 업로드하지 않았다.

## 다음 최소 작업 제안

현재 관련지역 후보에서 생년월일·무주택·실제 근로상태 등을 추가 입력받아도 안전하게 비교할 수 있는 특정 사업 하나를 선정하고,공식 기준일·가구소득 의미·미확인 항목을 먼저 확정한다. 현재 지역검색을 전체 자격 추천 완료로 승격하지 않는다. 시군구와사업을 계속 늘릴 수 있지만 전국 전수·실시간 운영 완료라고 부르지 않는다.
