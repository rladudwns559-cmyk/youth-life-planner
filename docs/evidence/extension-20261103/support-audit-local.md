# 2026-11-03 추가 지역지원38카드 검증

## 범위와 실제 확인

인천청년포털 상세27건·목록3쪽30건,부산청년플랫폼 상세13건,진주시공식1건 및 지정Google신청폼,진천군청년센터 공개 지원사업8행과 공식AI구독료공고PDF를 조사했다. 지역22인천/10부산/5진천/1진주 총38카드다. 별도 교육·상담·회차 안내도 포함하므로 독립정책38개로 과장하지 않는다.

현재(2026-11-03) **VERIFIED_OPEN18개 / WINDOW_GUIDANCE20개**. Program38개/Rule38개 strict검증·기존344 ID/첫공식URL중복0. 전체자격은UNKNOWN·실제지원금계산반영0원이다. 외부기관 문의·접수·로그인·개인정보입력·동의·응답제출은0건이다.

인천 OPEN은 상세의접수중+해당수강신청경로와본문/일정/현재정원을대조했다. 정원을 잔여인원으로 읽지 않았다. 계양2241은모집20/신청25이며추첨제로유효접수표시를유지하고추첨/확정필요를명시했다. 본정원만원2229(8/8,대기1/4),2230(8/8,대기0/4),2262(15/15,대기0/3)는수강신청링크가있어도로그인후실제대기접수활성을확인하지않아기간안내로하향했다.

부산3983·3986은공식공고가직접지정한Google폼에서동일제목·설명·신청질문·제출화면을확인했다. 진주116은공식본문과상단서로다른축약신청링크가실제로같은경남경총신청폼으로연결됨을확인했다. 진천은공식Next.js페이지가조회하는공개GET /api/policies의해당id·status모집중·isApplicationAvailable=true·신청기간과본문을대조했다. 비공개계정/대시보드API를사용하지않았다.

## 조건 표현

- 진천AI32는공식PDF(9/30수정첨부)의출생1986.1.1~2007.12.31·공고일부터신청일까지진천주소·본인계정·2026실결제·대상AI5종·최대10만원을근거로표현했다. 서류승인과예산내최종선정은다름을명시했다.
- 영도면접2950은공식출생1987.1.1~2007.12.31을사용한다. 미취업·미창업은면접응시일기준이므로현재취업입력으로PASS/FAIL하지않고UNKNOWN이다.
- 인천2248/2250/2251/2256/2257은15~34세일반경로와인천청년35~39세예외를단순상한으로변환하지않고나이UNKNOWN으로보류했다. 2251·부산3988·진주116의현재미취업명시만현재근로상태FAIL/미취업부분PASS로표현했다. 전체자격은여전히UNKNOWN이다.
- 진주116은상세표15~39/본문19~39/신청폼일반15~34와지역특화35~39가달라나이를UNKNOWN으로유지했다. 수료2개5만원/3개8만원은지급요건확인안내이며자동합산하지않는다.
- 인천2258은서해·검단주민한정이다. 단일city모델로두구의OR를확정할수없어대표서해구/다른경로UNKNOWN으로두고두구외대상아님을명시했다. 검단구를임의FAIL로확정하거나둘로나누어카드를부풀리지않았다.
- 인천일부와부산청년공간은거주우대와실제대상제한이다르므로대부분시도범위+타지역생활권UNKNOWN이다. 강의장소가있는구에만거주해야한다고추정하지않았다.
- 가구소득/재산/세대/주거유형을추정하지않는다. 모든rent_required=false이며월세여부가참여자격을증명하지않는다.

## 제외·보류와 실패 이력

- 인천2253/2254/2255/2260:목록접수중과달리현재상세접수마감이므로신규제외. 인천2246은청년자녀의부모대상교육이라이번청년이용카드범위에서제외.
- 부산3996은기존해운대디지털AI마케팅2기와같은11/9~23일과정재게시,3984는기존집반찬6회차라중복제외.3985발레온천은11/4개시이므로현재접수확대에서제외.
- 진천29면접정장은기존OPEN-JINCHEON-SUIT-2026와동일하여제외. 진천34AI영상/33이모티콘은status모집중이어도신청일종료·isApplicationAvailable=false라제외.
- 인천외부네이버폼은HTTP200이나본문5자짜리클라이언트앱만받아질문·현재접수미확인,부평상담별도신청·부산QR/인포크도특정신청창미확인이라GUIDANCE로유지. 영도구신청경로는연결시간초과여서GUIDANCE.철원공식홈HTTPS인증서검증실패는우회하지않고추가하지않았다.
- IC2268시간/장소는표13~15시/본문19~21시로상충하여최종확인필요.2261표19시/본문18시30분도명시.2249마감시각11시/15시상충은마감당일OPEN단정금지.2232시작일10/26표/10/27본문은늦은10/27적용.
- 최초네트워크조회는제한된실행에서소켓차단됐고허용된실행으로정상조회했다. PDF읽기에서canonical pypdf미설치,번들Python bs4미설치를확인한뒤이미있는번들pypdf경로를참조했다.새설치없음. 제작스크립트의미사용age_status import오류1건을제거후strict검증재실행통과. production코드수정없음.

## 최종 데이터와 근거

별도독립조건/시각검사 **217개 통과**. 이는pytest개수에합산하지않는다.

|카드|공식상세|시작|종료|현재상태|
|---|---|---|---|---|
|인천 청년 진로탐색 집단상담 · 11월|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2229&prgmdiv=all)|2026-10-26|2026-11-06|WINDOW_GUIDANCE|
|인천 청년 마음회복 집단상담 · 11월|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2230&prgmdiv=all)|2026-10-26|2026-11-06|WINDOW_GUIDANCE|
|남동 로컬크리에이터 창업교육 · 7회차|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2232&prgmdiv=all)|2026-10-27|2026-11-06|VERIFIED_OPEN|
|계양 청년 SNS 플랫폼 마케팅 트렌드|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2241&prgmdiv=all)|2026-10-22|2026-11-19|VERIFIED_OPEN|
|서해 청년 퍼스널컬러·면접 이미지메이킹|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2248&prgmdiv=all)|2026-10-23|2026-11-06|VERIFIED_OPEN|
|제물포 청년 실무 마스터 · AI 디자인|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2249&prgmdiv=all)|2026-10-25|2026-11-05|WINDOW_GUIDANCE|
|서해 청년 TCI 심리검사·강점 설계|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2250&prgmdiv=all)|2026-10-26|2026-11-16|VERIFIED_OPEN|
|서해 미취업 청년 요가·명상|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2251&prgmdiv=all)|2026-10-26|2026-11-13|VERIFIED_OPEN|
|서해 청년 강점 발굴·실전 면접|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2256&prgmdiv=all)|2026-10-27|2026-11-17|VERIFIED_OPEN|
|서해 청년 면접 메이크업 · 2기|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2257&prgmdiv=all)|2026-10-27|2026-11-10|VERIFIED_OPEN|
|서해·검단 청년 내 마음 상담소 · 11월|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2258&prgmdiv=all)|2026-10-27|2026-11-11|VERIFIED_OPEN|
|서해 청년 금요일 모임 · 야구 관람|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2261&prgmdiv=all)|2026-10-28|2026-11-09|VERIFIED_OPEN|
|영종 청년 퍼스널컬러·이미지 브랜딩|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2262&prgmdiv=all)|2026-10-28|2026-11-24|WINDOW_GUIDANCE|
|제물포 청년 AI 3D 모델 만들기|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2263&prgmdiv=all)|2026-10-28|2026-11-10|WINDOW_GUIDANCE|
|제물포 청년 SNS PR·릴스 제작|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2264&prgmdiv=all)|2026-10-28|2026-11-06|WINDOW_GUIDANCE|
|제물포 청년 디지털 드로잉·스티커|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2265&prgmdiv=all)|2026-10-28|2026-11-07|WINDOW_GUIDANCE|
|제물포 청년 AI 숏폼 영상 만들기|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2266&prgmdiv=all)|2026-10-28|2026-11-13|WINDOW_GUIDANCE|
|제물포 청년 소리 채집·감각 기록|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2267&prgmdiv=all)|2026-10-28|2026-11-14|WINDOW_GUIDANCE|
|제물포 청년 AI 음악창작·음악일기|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2268&prgmdiv=all)|2026-10-28|2026-11-20|WINDOW_GUIDANCE|
|제물포 청년 캘리그라피 선물 만들기|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2271&prgmdiv=all)|2026-10-28|2026-11-08|WINDOW_GUIDANCE|
|남동 청년 독서모임 · 모든 요일의 기록|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2272&prgmdiv=all)|2026-11-02|2026-11-10|VERIFIED_OPEN|
|부평 유유심표 개인 심리상담 · 11월|[공식](https://youth.incheon.go.kr/program/programInfoDetail.do?prgm_seq=2273&prgmdiv=all)|2026-11-02|2026-11-20|WINDOW_GUIDANCE|
|영도 청년 면접수당 · 2026|[공식](https://young.busan.go.kr/policySupport/view.nm?menuCd=13&bizSid=SUP0000002950)|2026-03-23|2026-12-11|WINDOW_GUIDANCE|
|부산 남구 공간숲 바른 움직임 · 시즌3|[공식](https://young.busan.go.kr/policySupport/view.nm?menuCd=13&bizSid=SUP0000003982)|2026-10-31|2026-11-25|WINDOW_GUIDANCE|
|부산 남구 UN 평화밥상 · 에티오피아편|[공식](https://young.busan.go.kr/policySupport/view.nm?menuCd=13&bizSid=SUP0000003983)|2026-10-31|2026-12-02|VERIFIED_OPEN|
|부산 청년작당소 이상한 만남 · 11월|[공식](https://young.busan.go.kr/policySupport/view.nm?menuCd=13&bizSid=SUP0000003986)|2026-11-02|2026-11-12|VERIFIED_OPEN|
|부산 해운대 청년 스피치 역량 교육|[공식](https://young.busan.go.kr/policySupport/view.nm?menuCd=13&bizSid=SUP0000003987)|2026-11-02|2026-12-02|WINDOW_GUIDANCE|
|부산 해운대 미취업 청년 공예 클래스|[공식](https://young.busan.go.kr/policySupport/view.nm?menuCd=13&bizSid=SUP0000003988)|2026-11-02|2026-11-20|WINDOW_GUIDANCE|
|부산 해운대 청년 무역실무·취업전략|[공식](https://young.busan.go.kr/policySupport/view.nm?menuCd=13&bizSid=SUP0000003989)|2026-11-02|2026-11-06|WINDOW_GUIDANCE|
|부산 연제 비즈니스 예비창업학교|[공식](https://young.busan.go.kr/policySupport/view.nm?menuCd=13&bizSid=SUP0000003993)|2026-11-03|2026-11-16|WINDOW_GUIDANCE|
|부산 연제 동네청년활동공간 · 11월|[공식](https://young.busan.go.kr/policySupport/view.nm?menuCd=13&bizSid=SUP0000003994)|2026-11-03|2026-11-13|WINDOW_GUIDANCE|
|부산진 청년취업플렉스 AI·업무자동화|[공식](https://young.busan.go.kr/policySupport/view.nm?menuCd=13&bizSid=SUP0000003995)|2026-11-03|2026-11-12|WINDOW_GUIDANCE|
|진천 청년 생성형AI 구독료 지원|[공식](https://jcy.kr/policy/32)|2026-10-01|2026-12-10|VERIFIED_OPEN|
|진천 청년 진로·직업 상담|[공식](https://jcy.kr/policy/26)|2026-07-13|2026-11-30|VERIFIED_OPEN|
|진천 청년 마음상담소|[공식](https://jcy.kr/policy/25)|2026-07-13|2026-11-30|VERIFIED_OPEN|
|진천 청년 안심 택배함|[공식](https://jcy.kr/policy/24)|2026-07-08|2026-12-31|VERIFIED_OPEN|
|진천 청년 자격증 취득 지원|[공식](https://jcy.kr/policy/20)|2026-02-02|2026-12-10|VERIFIED_OPEN|
|진주 청년카페 · 11월 취업·재테크 프로그램|[공식](https://young.jinju.go.kr/young/business/read/116)|2026-04-16|2026-11-30|VERIFIED_OPEN|

원본HTML/신청폼본문/PDF는tmp/expand3/local에보관한다.공개프로젝트에는구조화요약·직접공식URL·검증결과만반영하고은행/정부원문전체를새공개자료로복제하지않는다.실제응답자·계좌·민감정보없음.

동결JSON SHA256: a0266954f09ab3f234c07f86031c375a0ddc563a6dac4c4f3f5db9dac8007997
