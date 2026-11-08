# 실제 정책 001 — 경기도 거주이력·기간 계약 검토 (M1.17)

확인일: **2026-10-20 / Asia/Seoul**. **문서 전용**, 신규 산출물은 이 문서 하나다. 최종 판단: **NEEDS_DURATION_SEMANTICS_DECISION**.

확정할 수 있는 공식 의미와 소프트웨어 입력 계약을 구분했다. 현재 안산시 근거만으로 행정 기간 산식·원시 전출입 날짜의 유효 경계를 확정하지 못했다. 이에 실제 기간 판정을 구현할 준비가 됐다고 보고하지 않는다. ResidenceHistoryFact/Rule/evaluator/loader/routing·실제 JSON은 구현하지 않는다. 완료된 Q3 Birth 단계도 다시 확장하지 않는다.

## 1. 목적

경기도 주민등록의 계속 거주 경로와 합산 거주 경로를 계산하기 위해 필요한 사실·지역·날짜·완전성·오류 경계를 정의한다. 정책 판단은 Python, 설명은 구조화 결과를 받은 AI라는 원칙을 유지한다. 불확실한 행정 산식을 개발 편의로 확정하지 않는다.

검토한 기존 문서: REAL_POLICY_001_ANALYSIS.md, REAL_POLICY_001_IMPLEMENTATION.md, REAL_POLICY_001_Q3_BIRTH_IMPLEMENTATION.md, POLICY_RULE_SPEC.md, RULE_ROUTING_SPEC.md, POLICY_DATA_ENVELOPE_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md. 기존 정책 분석의 미해결 산정 문제와 현재 구현을 구별한다.

실제 001 release는 resident-only/r0001/d0001, 002는 resident+Q3 birth/r0002/d0002다. 둘 다 DRAFT/CONDITION_SLICE이며 거주기간을 coverage에서 제외한다. 두 release의 sources·정책·README와 기존 Fact/Resolver/ANY 의미를 확인했다. 이번 문서로 기존 snapshot을 변경하지 않는다.

## 2. 공식 출처

이번 작업에서 공식 게시물·첨부·정책 페이지·Q3 안내를 직접 재조회했다. HWP는 메모리에서 OLE/압축 본문을 추출했다. 원문 전체를 저장소에 복제하지 않았다. 웹 도구에서 안산시 페이지 접근이 실패한 경우 같은 공식 URL의 읽기 전용 HTTP 본문으로 확인했다.

| 근거 | 직접 확인한 위치 | 역할·한계 |
|---|---|---|
| S1 [안산시 공고 제2026-399호](https://www.ansan.go.kr/danwongu/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1664308), [첨부 HWP](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP) | 신청개요 → 신청대상 아래 두 거주경로·거주요건 기준일·등록분류/국적취득 주석, 제출서류 → 초본 각주 | 최우선 2026 안산시 근거. 일수 환산·윤일·발생일/신고일 중 선택은 명시되지 않음 |
| S2 [안산시 정책 페이지](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001545) | 사업개요 → 지급조건 두 항목, 제출서류 | 최근·계속·합산 및 주민등록 확인. 게시일/수정일 미확인 |
| S3 [2026 Q3 공식 안내](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390) | 본문 두 번째 문단의 경기도 거주기간 | 3년 연속 또는 합산 10년 교차 확인. 세부 산식 없음 |
| S4 [경기청년포털 2026 Q2 안내](https://youth.gg.go.kr/gg/intro/notice.do?articleNo=9707&mode=view) | 2026-05-27 공지 → 지원대상 ①/② | 같은 연도 OR·신청일·최근 계속 표현의 보조 확인. 안산 Q3 산식의 대체 근거 아님 |
| H1 [경기청년포털 공식 Q&A](https://youth.gg.go.kr/gg/info/qna.do?articleNo=2498&mode=view) | 질문 2021-09-22 / 통합관리자 답변 2021-09-23 | 출생 후 경기도 과거 이력·타지역 이동 후 재전입 사례를 설명. 역사적 보조 해석이며 2026 세부 산식으로 승격하지 않음 |
| H2 [용인시 수지구 2019 Q4 안내](https://www.sujigu.go.kr/lmth/03com02.asp?block=91&no=MjU2OTQg&page=907) | 2019-11-05 상현1동 공지 → 신청자격 표 ② | 합산 10년 옆 3650일 표기가 실제 본문에 있음. 과거·다른 시 안내이므로 2026 안산 산정 규칙으로 채택하지 않음 |

S1 HWP: **61,952 bytes / SHA256 b0d9f1e9f2de6844157021cab963b2e1dedd49183550036a9777dafa1de78106**. 기존 확인본과 같다. 정확한 쪽번호는 만들지 않는다. 검색결과 요약은 발견 경로로만 쓰고 H1/H2도 열린 공식 본문으로 확인했다. 블로그·언론·사용자 자유게시판은 판단 근거에서 제외했다. 공식 사이트의 사용자 질문과 관리자 답변도 구별했다.

H2의 일수 표기는 calendar 방식이 당연하다고 가정할 수 없다는 **주의 근거**다. 현행 안산 자료와 직접 충돌했다고 단정할 수는 없다. 현행 자료는 그 세부 산식을 제시하지 않기 때문이다. H1/H2의 오래된 신청기간·연령·절차는 이 정책에 가져오지 않는다.

## 3. 정확한 공식 문구

짧은 인용은 띄어쓰기와 줄바꿈만 읽기 편하게 표시한다. 범위 의미를 요약으로 바꾸는 부분은 별도로 설명한다.

| 위치 | 직접 문구 |
|---|---|
| S1 첨부 신청대상 | “①경기도 내 연속 3년 주민등록을 두고 계속 거주 또는 ②합산 10년 이상 거주” |
| S1 첨부 바로 아래 주석 | “거주요건 : 신청일 기준으로 산정” |
| S2 지급조건 두 번째 항목 | “경기도에 최근 3년 이상 계속 거주 또는 합산 10년 이상 주민등록을 두고 있는 경우” |
| S3 두 번째 본문 문단의 기간 부분 | “경기도에 3년 이상 연속 거주했거나 합산 거주 기간이 10년 이상인 경우” |

S1은 연속·계속을 함께 쓰고, S2는 최근·계속, S3는 연속을 쓴다. 이를 한 출처의 완전 동일 문구라고 표시하지 않는다. S1의 3년 문구와 다른 두 자료의 이상 표현을 함께 읽어 최소 3년 경로로 해석한다. 최근은 연속 경로가 기준일에 이어지는 최근 구간이라는 해석을 지지한다. 합산에 최근 10년이라는 제한을 임의 추가하지 않는다.

국적취득·외국인 관련 사항은 25절에서 의미를 요약한다. 공고의 제출서류 요구가 프로그램의 증빙 수집 권한을 뜻하지는 않는다.

## 4. OR 논리

공식 또는/했거나와 S4의 ① 또는 ②에 따라 기간 조건은 **A OR B**다.

- A: 경기도 주민등록을 둔 최근 계속 거주가 3년 이상.
- B: 경기도 주민등록 거주기간의 합산이 10년 이상.

기간 조건 자체는 한 경로만 충족해도 PASS다. 신청일 안산시 주민등록 조건은 별도 필수 leaf다. 점 시점의 안산 등록만으로 과거 기간을 증명할 수 없고, 과거 경기도 기간만으로 신청일 안산 등록을 증명할 수도 없다. 전체 조합은 현재 주민등록 AND 선택한 Q3 출생일 AND (A OR B)의 미래 부분 트리다. 등록분류 등 다른 필수조건까지 완료했다는 뜻은 아니다.

## 5. 지역 범위

기간 범위는 **경기도 전체**, 안산시만의 거주기간이 아니다. 도내 시군명이 바뀌어도 경기도 주민등록이 날짜상 끊기지 않았다면 도 경계의 계속성은 유지된다고 해석한다. 이는 경기도 내라는 공식 범위의 논리적 귀결이며 개별 이동일의 빈틈까지 자동 면제한다는 뜻은 아니다.

현재 RegionRef는 GYEONGGI/ANSAN, GYEONGGI/SUWON, SEOUL/JONGNO만 허용한다. 지원된 객체의 sido 비교는 가능하지만 성남 등 다른 시군이나 시군을 모르는 도 단위 입력은 생성할 수 없다. **현재 RegionRef만으로 일반 거주이력을 표현하기에는 GAP이 있다.** 성남을 수원으로 바꾸거나 허용 목록 전체를 느슨하게 만들지 않는다.

추천은 이력 계산용 도 단위 ProvinceRef(sido) 후보를 분리하고 확인된 canonical 코드만 받는 것이다. 시군·상세 주소는 기간 판정에 불필요하므로 필수 수집하지 않는다. 이름·허용 코드 체계는 후속 Fact 계약에서 승인할 사항이며 현재 클래스를 추가하지 않는다. 다른 도나 지역 미상은 명시적으로 구별한다. 지역 미상은 경기도 밖이 아니다. 시군의 당해 사업 참여 여부도 과거 경기도 거주기간의 도 범위를 자동 축소하는 근거가 아니다.

## 6. 기준일

**APPLICATION_DATE**가 직접 근거로 확인됐다. S1의 기간 산정 주석에서 확인했으며 기존 resident leaf와 같다는 이유로 추정한 것이 아니다. Q3 연령 기준일·접수 시작일·평가일을 대신 사용하지 않는다.

reference_date=None은 유효한 미입력 → UNKNOWN, 잘못된 date 타입은 호출/입력 오류 후보, reference_date가 명시적 evaluation_date보다 미래면 기간을 예측하지 않고 UNKNOWN 후보로 둔다. reference context 자체가 없는 호출은 기존 routing과 같이 계약 오류다. 시스템 오늘은 읽지 않는다.

## 7. 연속 3년 의미

기준일까지 이어지는 인정 가능한 경기도 주민등록의 최근 연속 구간을 찾는 방향이 맞다. 오래전에 3년 연속 살았지만 지금 재전입한 지 한 달인 사람을 A PASS로 처리하지 않는다. 그 과거 기간은 B에서 검토할 수 있다.

**미확정:** 2026-09-15 기준 2023-09-15 시작을 정확히 3년으로 보는지, 초일·말일을 어떻게 처리하는지, 윤년을 일수로 환산하는지 직접 확인된 현행 산식이 없다. calendar anniversary 방식이면 해당 시작일이 경계이고 다음 날 시작은 하루 부족하겠지만 이는 **조건부 예시**이지 현행 판정 확정이 아니다. 1095일과 같다고 결정하지 않는다.

연속 구간 계산과 3년 기준 비교를 분리한다. 입력에서 확인된 경기도 연속 구간 자체는 표현 가능하지만 그 구간을 정책상 3년으로 판정하려면 9·10절 결정이 필요하다.

## 8. 합산 10년 의미

경기도로 확인된 여러 인정 구간을 한 번씩 합산한다. 사이의 타시도 거주를 포함하지 않으며 타시도로 나갔다 돌아왔다는 이유로 이전 경기도 기간을 버리지 않는다. S1의 전체 주소변동 이력 요구와 H1의 역사적 사례가 이 해석을 지지한다. 합산을 최근 10년 또는 청년이 된 뒤의 기간으로 제한하는 근거는 확인하지 못했다.

다만 일반적인 출생 이후 모든 주소 이력을 무조건 인정하지 않는다. 주민등록·등록분류·국적취득 이후 인정 여부가 선행한다. 외국인등록 등 다른 등록제도 기간은 주소가 경기도라는 이유만으로 포함할 수 없다.

**미확정:** 분리된 여러 구간을 어떤 단위·순서로 10년에 환산하는가. 개별 구간의 연·월·일을 단순히 더하거나 3650일로 고정하지 않는다. 5년+타시도 2년+5년은 두 인정 기간이 공식 산식으로 합계 10년이라고 확인된 경우 B PASS다. 날짜만으로 이를 자동 산출하는 계약은 아직 차단되어 있다.

## 9. Calendar-year/day-count 분석

| 후보 | 장점 | 문제 / 이번 결정 |
|---|---|---|
| 고정 1095일/3650일 | 단순·재현 가능 | 현행 안산 적용 근거 없음. H2의 과거 3650일만으로 현행 두 임계값을 확정할 수 없음 |
| Calendar anniversary | 연속 시작일과 3주년 비교에 직관적 | 윤일 기산·초일 규칙과 합산된 여러 기간 환산은 별도 정의 필요 |
| 행정 지침의 연·월·일/일수 산식 | 실제 심사와 일치시킬 근거가 될 수 있음 | 현행 상세 지침과 예제 확인 필요. 지금 임의로 만들 수 없음 |

2023-09-15→2026-09-15의 날짜 차이는 윤일을 포함해 1096일이고, 2016-09-15→2026-09-15는 3652일이다. 이는 단순 날짜 차이의 예이며 공식 인정 일수라는 뜻이 아니다. 포함 끝점 선택에 따라 개수도 달라진다. 2024-02-29 기산의 2027-02-28/03-01 도달 문제 역시 1095일·anniversary·말일 보정 중 무엇인지 결정해야 한다. 2025/2026-02-28은 별도 중간 경계 사례다.

Python timedelta나 임의 replace(year=...)의 동작을 법적 기준으로 삼지 않는다. 일반 민사 기간 계산 규정을 이 사업에 자동 적용하는 법률 해석도 하지 않는다. **최종 산식 선택은 미결정이며 실제 evaluator 구현 차단 요인**이다. 이 불확실성을 사용자 history 누락과 혼동하지 않는다.

## 10. Interval boundary

**추천 소프트웨어 정규형:** ResidencePeriod는 `[start_date, end_date_exclusive)`다. start는 등록 상태가 유효해진 첫 날짜, end는 그 상태가 더 이상 유효하지 않은 첫 날짜다. finite end는 start보다 커야 한다. 마지막 거주일을 받은 경우 그 다음 날로 바꾸는 일은 입력 정규화 경계가 명시적으로 수행해야 한다.

이 정규형은 중복 일자 방지를 위한 내부 설계 선택이며 주민등록초본의 날짜 의미를 확정한 것이 아니다. S1은 발생일·신고일을 모두 요구하나 어느 것을 유효 시작으로 삼는지, 지연 신고·소급 정정이 있을 때 어떻게 처리하는지 설명하지 않는다. **원시 발생일/신고일 → 유효 시작·종료일 매핑은 GAP**이다. 원시 자료가 이를 증명하지 못하면 유효한 interval이라고 가장해 넣지 않는다.

신청일의 상태 포함 여부는 정규형에서 R에 해당하는 상태를 확인하는 것으로 표현할 수 있다. 기간 길이에 신청일 하루를 더 셀지는 별개 행정 산식이다. `[start,R+1)`의 날짜 집합과 `(R-start).days`의 경과 시간을 혼동하지 않는다. date.max 다음 날 같은 표현 범위도 구현 전에 별도 검증해야 하며 이번에 함수를 만들지 않는다.

## 11. 연속성/gap

정규화된 A의 종료일과 B의 시작일이 같은 반개구간은 공백이 없다. 하루라도 명시적으로 타시도 등록이면 계속성은 끊긴다고 해석하며 임의 grace period를 만들지 않는다. 예외·말소·거주불명 인정은 별도 공식 근거 없이 동일 취급하지 않는다.

**미상 gap은 타시도 거주가 아니다.** 경기도 두 구간 사이에 기록이 없으면 그 사이를 연결하지 않는다. 연속 길이의 증명 가능 범위가 부족하면 UNKNOWN이다. 다만 이미 확인된 최근 구간만으로 기준을 확실히 충족하면 더 오래된 gap은 PASS를 막지 않는다. 반대로 알려진 최근 타시도 하루가 모든 가능한 연속 경로를 차단하면 나머지 오래된 이력이 부족해도 A FAIL이 가능하다. 이는 산식과 경계가 확정된 이후의 증명 규칙이다.

## 12. 경기도 내 이동

안산→수원→성남의 정규화 구간이 도 단위로 연접하면 경기도 연속 구간으로 계산한다. 같은 시군 문자열 비교를 하지 않는다. 연접한 기간을 계산상 연결해도 원본 입력 구간·provenance를 삭제하거나 하나의 새 행정 사실로 바꾸지 않는다.

사용자 예처럼 앞 구간의 날짜를 마지막 거주일로 적었는지 end_exclusive로 적었는지 먼저 확인해야 한다. 전자는 다음 날 시작과 연결될 수 있고, 후자는 실제 하루 gap이 생길 수 있다. 단순히 시군이 모두 경기도라는 이유로 그 차이를 없애지 않는다. 현재 RegionRef가 성남을 거부하는 제한은 5절과 같이 남는다.

## 13. Open-ended period

end_date_exclusive=None은 종료일이 관측되지 않은 열린 구간으로 추천한다. 무제한 미래 거주를 뜻하지 않는다. HistoryFact의 **observed_through**가 보증하는 날짜까지만 증거로 쓴다.

R까지 확인된 열린 경기도 기간은 R에서 잘라 계산할 수 있다. observed_through<R이면 마지막 주소를 R까지 연장하지 않으며 그 이후는 미상이다. 시스템 오늘을 종료일로 넣지 않는다. 과거 R 평가에는 이후 관측 종료일이 R보다 늦다는 정보가 추가돼도 R 이전 구간 의미가 같으면 같은 결과가 나와야 한다.

## 14. Future history

reference_date 뒤의 **유효한 과거 관측 기록**은 R 계산에 포함하지 않는다. R 이후 시작은 제외, R을 가로지르는 기간은 R에서 절단한다. 현재에 이미 관측된 이력이 과거 신청일보다 미래라는 이유로 Data Error가 되지는 않는다.

반면 observed_through 이후를 이미 발생한 이력으로 제출하거나 명시적 evaluation_date보다 미래인 기록을 확정 사실로 주장하면 입력 정합성 오류 후보다. 예정 전입은 이 Fact가 다루지 않는다. reference_date 자체가 미래면 UNKNOWN이며 미래 이력으로 PASS를 예측하지 않는다.

타입·역전 등 구조 오류는 입력 전체에서 먼저 거부한다. 겹침·충돌 데이터도 오류이며 미래라는 이유로 숨기지 않는다. **정상적인 미래 suffix 추가의 과거 결과 불변성**과 잘못된 입력 묶음의 오류 전파를 구별한다. 이후에 과거 구간 자체를 정정했다면 동일 historical facts라는 전제가 달라진 것이다. 기존 resident Resolver의 미래 기준일 UNKNOWN·충돌 우선 원칙과 맞추되 exact-date fact 선택 알고리즘을 복사하지 않는다.

## 15. Duplicate/overlap/conflict

이번 문서의 추천 선택은 다음과 같다. 아직 구현된 validation 코드가 아니다.

| 입력 | 추천 처리 |
|---|---|
| 순서만 다른 정상 구간 | 불변 snapshot을 계산용으로 canonical 정렬. 사용자 입력 순서 불변. 날짜/지역/출처 동률 정렬 기준 명시 |
| 모든 필드가 같은 exact duplicate | idempotent 허용, 계산용으로 한 번만 반영. 주민등록 Resolver의 동일 사실 중복 제거와 일관 |
| 날짜·지역은 같고 provenance만 다름 | 같은 사실의 복수 증거로 보존하되 기간은 한 번만 계산. source 우선 선택 없음 |
| 일부만 겹치는 같은 지역 구간 | 정규화 이력 계약 오류. 자동 merge로 고치지 않음 |
| 겹치는 경기도/서울 구간 | 모순 Data Error. UNKNOWN으로 바꾸거나 출처 등급으로 승자 선택 금지 |
| 반개구간의 end==다음 start | overlap 아님. 도가 같으면 연속성 계산 가능 |
| start>=finite end / 잘못된 날짜 타입 | Data Error. 일자 절삭·자동 뒤집기 금지 |

주소 한 줄의 이력이라는 모델에서는 서로 다른 두 주소 상태가 같은 날짜에 동시에 유효하다고 가정하지 않는다. 실제 원시 기록에 정정·동일일 이동·복수 행이 있을 수 있으므로 그것을 이 모델이 해결했다고 하지 않는다. 이 제약을 공식 주민등록의 모든 예외를 증명한 법률 주장으로 확대하지 않는다. 원시 event를 정규화하는 경계에서 해결할 사항이다.

## 16. Incomplete history

periods만으로 FAIL을 내릴 수 없다. 목록 밖 기간은 기본 미상이고 타시도로 채우지 않는다. 추천 최소 완전성 선언은 **complete_from / complete_through / origin_complete**다.

- complete_from/through는 모든 도의 주민등록 상태가 빠짐없이 알려진 연속 날짜 창이다. 두 값은 함께 존재하거나 함께 None이며 through<=observed_through다.
- origin_complete=True는 complete_from이 계산에 필요한 최초 인정 가능 이력부터 시작하고 그 이전에 누락된 인정기간이 없다고 증명하는 별도 주장이다. 단순히 목록의 첫 날짜라는 뜻이 아니다.
- 완전 창 안에는 미상 gap·region 미상 상태가 없어야 한다. 완전하다는 선언과 실제 공백/미상 구간이 모순이면 Data Error다. 등록 없음도 필요하다면 명시적 상태로 표현해야 하며 빈 공간으로 대신하지 않는다.
- 창 밖에도 유효하게 알려진 구간을 보유할 수 있다. 알려진 충분한 부분은 PASS의 증거가 될 수 있지만 전 생애 FAIL 증명으로 쓰지 않는다.

합산 FAIL에는 원칙적으로 최초 인정 가능 시점부터 R까지의 완전한 이력이 필요하다. 정확한 출생일·국적취득 시점 또는 최초 등록 근거와 origin_complete를 함께 검토해야 한다. 최근 5년 초본은 연속 경로의 증거일 수 있지만 합산 10년 미달의 전 생애 증거는 아니다. 전체 이력이라는 문구만으로 모든 누락·국적 예외까지 자동 해결됐다고 하지 않는다.

연속 FAIL에는 항상 전 생애 이력이 필요하지 않다. 확정된 산식의 최근 판정창을 완전히 덮거나 그 창 안의 확실한 단절이 증명되면 된다. 합산 PASS도 충분한 알려진 인정 구간만으로 증명될 수 있다. 소스가 OFFICIAL_DATA라는 이유로 completeness=True를 자동 부여하지 않는다.

## 17. PASS/FAIL/UNKNOWN/Data Error

아래는 **향후 산식 확정 후**의 판정 계약이다. 현재 구현된 새 실행 상태가 아니다.

| 상태 | 개별 기간 경로의 기준 |
|---|---|
| PASS | 확실하게 인정되는 기간만으로 경로 기준 충족이 증명됨. 관련 완전성·국적·경계 불확실성이 그 증명에 영향을 주지 않아야 함 |
| FAIL | 완전 이력 또는 확실한 단절/상한으로 어떤 누락 가능성을 고려해도 해당 경로 미충족임이 증명됨 |
| UNKNOWN | 이력/기준일/인정 시점/완전성이 부족하여 어느 쪽도 증명 못함 |
| Data Error | 잘못된 타입·날짜·모순 구간·완전성 선언 모순. 정상 결과 없이 오류 전파 |

전체 기간 OR의 FAIL은 **A와 B가 둘 다 FAIL**일 때만 가능하다. A FAIL+B UNKNOWN은 UNKNOWN이다. 정보 부족을 0일로 보지 않는다.

산식 자체가 미확정인 현재는 **정책 설계 GAP**이다. 사용자의 입력만 더 받으면 해결된다고 하지 않는다. 실제 Rule을 발행·실행하지 않으며, 문서 시나리오에서는 U/GAP으로 표시한다. 후속에 미확정 정책을 억지로 정상 UNKNOWN Rule로 만들어 기존 데이터에 넣지 않는다.

## 18. Fact model 후보

| 후보 | 판단 |
|---|---|
| A. 유효 기간과 이력 묶음 | **추천**. 원시 행정 이력을 최소 정규화한 구조로 날짜·단절·불완전성을 추적 가능 |
| B. 날짜별 snapshot 목록 | 현재 주민등록 한 날짜 확인에는 적합. 희소 snapshot으로 사이 날짜를 증명할 수 없고 매일 입력은 부적절 |
| C. continuous_years/cumulative_years 숫자 | 산정 근거·윤일·중복·귀화 범위를 재검증할 수 없어 원본 Fact로 미채택 |

추천 개념 구조는 다음과 같다. **아직 생성자/API/JSON 문법이 아니다.**

```text
ResidencePeriod
  province: ProvinceRef | None         확인된 도, None은 지역 미상
  registration_state                  REGISTERED / NOT_REGISTERED / UNKNOWN 후보
  start_date: date                     정규화된 유효 시작일
  end_date_exclusive: date | None       정규화된 첫 비유효일, None은 관측 종료 미상
  source: ResidenceHistorySource

ResidenceHistoryFact
  periods: tuple[ResidencePeriod, ...]
  observed_through: date               실제 관측 범위의 끝, 미래 예측 금지
  complete_from: date | None
  complete_through: date | None
  origin_complete: bool                전체 인정 가능 이력의 시작부터 빠짐없다는 주장

ResidenceEligibilityContext            정책별 계산 전 필요한 인정 시점의 사실 후보
  origin_basis: FROM_BIRTH / NATURALIZED / UNKNOWN
  citizenship_acquired_on: date | None
```

NOT_REGISTERED이면 province=None, REGISTERED이면 province의 완전성 여부를 명시해야 한다. UNKNOWN 상태를 타시도나 무등록으로 바꾸지 않는다. 도 미상 REGISTERED와 등록 여부 미상을 구분한다. dates는 정확한 date만 받고 문자열·datetime·bool 자동 변환을 하지 않는 기존 원칙을 따른다. 임의 상세 주소·증빙 파일·신원 ID·수집 프레임워크는 넣지 않는다.

origin_complete=True에 필요한 근거와 FROM_BIRTH가 증명하는 범위, 별도 context의 최종 필드명은 후속 설계 승인 사항이다. 귀화사실을 history의 None 날짜로 숨기지 않는다. 상위 BirthFact가 있다면 구간이 출생 전인 모순을 **입력 간 consistency 경계**에서 거부하도록 추천한다. History Fact 자체에 BirthFact를 복제하지 않는다. 출생일이 없다고 정책 age로 역산하지 않으며 관련 완전성 판단은 미확인으로 남긴다.

## 19. Provenance

새 **ResidenceHistorySource** 후보에 SELF_REPORTED / MANUALLY_VERIFIED / OFFICIAL_DATA를 추천한다. BirthSource와 점 시점 RegistrationSource는 특정 사실 책임에 묶여 있으므로 재사용하거나 기존 Enum 전체를 generic하게 이전하지 않는다.

출처는 각 구간에 보존해 복수 자료의 이력을 추적한다. 값이 같으면 source가 달라도 기간·상태는 같고, 서로 모순되면 공식 표식이 있다고 자동 선택하지 않는다. completeness/observed_through는 이력 묶음의 주장이고 진위 인증이 아니다. 공식 원문 evidence_refs는 정책 Rule의 근거이며 사용자 history source와 별개다.

초본은 S1에서 주소변동 이력·발생일·신고일·변동사유를 요구하는 행정 확인 자료다. 우리 Fact는 그중 도 단위 유효 등록 상태와 관측/완전성만 추상화한다. 초본 업로드·OCR·정부 DB·주민번호 수집·영구 저장·전체 요청 로그·LLM 전송은 설계하지 않는다.

## 20. Rule model 후보

| 후보 | 투명성·설명·UNKNOWN·확장성 | 판단 |
|---|---|---|
| A. ANY(ContinuousResidenceRule,CumulativeResidenceRule) | 공식 OR와 직접 대응, 각 충족 경로·미확인 이유·evidence를 보존. 유한 타입 추가와 별도 loader 지원 설계는 필요 | **추천** |
| B. 단일 GyeonggiResidenceDurationRule | 상위 노드는 단순하지만 개별 P/F/U·근거·BOTH PASS가 내부 결과 계약으로 숨음 | 미채택 |
| C. 기존 atomic 두 개 | 기존 Field가 기간·기준일·완전성을 표현 못함. 숫자 연수로 우회하면 사실 의미 손실 | 미채택 |

두 Rule 후보의 최소 개념 필드는 rule_id, required_province=GYEONGGI, minimum_years=3 또는 10, reference_date_source=APPLICATION_DATE, evidence_refs다. **minimum_years만으로 실행 정의가 완성되지 않는다.** 확정된 기간 산정 기준·입력 boundary 계약을 별도 문서와 rule_version에 고정한 뒤 JSON/routing 설계를 승인해야 한다. 현재 m1.1이 두 새 rule_type을 지원한다고 주장하지 않는다. 새 schema·calculator 전략 registry를 지금 만들지 않는다.

## 21. ANY 구조 검토

기존 진리표를 그대로 재사용한다. 모든 child를 평가해 양쪽 충족·누락·근거를 보존하고 short-circuit하지 않는다.

| A | B | ANY |
|---|---|---|
| P | P | P |
| P | F | P |
| P | U | P |
| F | P | P |
| F | F | F |
| F | U | U |
| U | P | P |
| U | F | U |
| U | U | U |

P/U의 U는 알려진 산식에 대해 증명이 부족한 경우다. 잘못된 history나 Rule의 오류를 U로 바꾼 것이 아니다. 한 child가 PASS여도 다른 child의 Data Error를 숨기지 않는다. 양쪽이 PASS면 두 leaf 결과를 유지한다.

## 22. Shared calculator 필요성

**작은 shared pure utility가 필요할 가능성이 높다.** 같은 history의 타입·중복·정렬·겹침·기준일 절단·인정 시점 제한·도 매칭을 두 번 다르게 구현하면 오류가 생긴다. 추천 흐름은 다음과 같다.

```text
명시적 History / reference date / 관측·인정시점
  → 구조·모순 검사 / 불변 계산용 canonical snapshot
  → 확인된 구간·미상 구간·완전성의 계산용 표현
  ├─ 최근 연속 경로 증명 → 개별 evaluation
  └─ 합산 경로 증명 → 개별 evaluation
  → 기존 ANY
```

utility는 상태 집계·원문 조회·I/O·시스템 현재일·정책별 자동 분기·사용자 기록 저장을 하지 않는다. 계산 단위와 공식 산식이 확정되기 전 generic interval engine·플러그인·캐시 프레임워크를 만들지 않는다. 두 Rule이 같은 입력을 읽는 것과 미래 What-if의 기준일·사용자 이력 변화를 재평가하는 책임을 구분한다.

## 23. Reason codes 후보

아래 이름은 **미구현 후보**이며 Enum/공통 결과 타입을 변경하지 않는다.

| 상태 / 이유 | 후보 |
|---|---|
| 연속 충족 | CONTINUOUS_RESIDENCE_SATISFIED |
| 합산 충족 | CUMULATIVE_RESIDENCE_SATISFIED |
| 증명된 개별 미달 | CONTINUOUS_RESIDENCE_INSUFFICIENT / CUMULATIVE_RESIDENCE_INSUFFICIENT |
| Fact 부재 | RESIDENCE_HISTORY_MISSING |
| 불완전·관측 종료 부족 | RESIDENCE_HISTORY_INCOMPLETE |
| 기준일 누락/미래 | RESIDENCE_REFERENCE_DATE_MISSING / RESIDENCE_REFERENCE_DATE_IN_FUTURE |
| 인정 기산 사실 부족 | RESIDENCE_ELIGIBILITY_START_UNKNOWN |

어느 gap·범위가 부족한지는 typed details/누락 경로의 후속 최소 결과 계약에서 정한다. 상세 주소·전체 이력 복제는 피한다. 산식 미결정은 현재 배포 전 정책 GAP이며 사용자 누락 reason으로 숨기지 않는다. overlap/conflict/invalid dates는 오류 code 후보이며 정상 reason이 아니다.

## 24. Current resident leaf와 관계

신청일 안산 ResidentRegistrationFact에서 history를 생성하지 않는다. 마지막 history interval이 안산이라는 이유로 exact-date Fact를 자동 생성하지도 않는다. 도 단위 history만 수집한다면 애초에 시군을 알 수 없다. 두 입력 책임을 유지하고 알려진 공통 사실이 명시적으로 모순될 때의 consistency 검사는 후속 입력 경계에서 검토한다.

현재 resident Resolver를 일반화하거나 과거 사실을 현재까지 연장하지 않는다. reference_date는 양쪽에 같게 전달될 수 있지만 그 근거·증명 방식은 다르다. 이번에 기존 모델·birth·routing·실제 release를 바꾸지 않는다.

## 25. 귀화/외국인 문제

S1 주석은 거주자·재외국민 포함, 거주불명자·외국인 제외를 구분하고, 대한민국 국적취득자는 취득 후 거주기간을 산정하도록 한다. 따라서 **귀화 전 주소 기간을 무조건 합산하는 설계는 틀리다.** 재외국민을 외국인으로 합쳐 제외하지 않는다. 출국·해외 체류가 곧 주민등록 말소라는 추정도 하지 않는다. [공고 첨부](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP).

확정 가능한 원칙: 귀화 전은 해당 인정 기간에서 제외, 귀화 후라도 인정되는 경기도 주민등록 구간만 검토. 외국인등록·국내거소 신고·단순 실거주를 주민등록으로 자동 변환하지 않는다. 전체 신청자의 외국인/등록분류 자격 판단은 별도 leaf·계약이며 history source나 region으로 추론하지 않는다.

남은 GAP: 취득 당일 포함 여부, 취득일과 주민등록 최초 유효일 차이, 말소/거주불명/재등록 경계의 인정 산정, 과거 등록분류 변화의 적용. 단순 주소 interval만으로 해결되지 않는다. origin_basis=UNKNOWN 또는 취득일 미입력은 관련 기간을 포함해 PASS로 만들지 않으며 인정 기산 UNKNOWN이다. 날짜가 확인돼도 취득일 하루에 결과가 달리는 사례는 공식 경계 확인 전 U/GAP이다. 귀화하지 않은 사용자에게 취득일을 강제로 요구하지 않는다.

## 26. 수동 시나리오

**54개 수동 기대표이며 신규 실행 테스트가 아니다.** 기본 R=2026-09-15, evaluation_date>=R, 날짜는 10절의 정규화된 반개구간, GG=경기도, 등록·출처·인정기산 사실은 행별 예외 외 정상이다.

표기 **P*/F***는 산식·원시 날짜 매핑·초일/말일·윤일 규칙이 공식 확인되어 해당 길이가 증명됐다는 전제하의 기대다. 해당 조건이 미해결인 현재 실제 인코딩 판단은 **U/GAP(정책 설계 차단)**이며 실행 결과가 아니다. U는 사용자 이력 부족으로 인한 미래 정상 UNKNOWN, ERROR는 구조/모순 오류다. 날짜 예시는 calendar 후보의 조건부 기대이며 이를 최종 산식으로 채택하지 않는다.

| ID | 사례 | 기대 / 경계 |
|---|---|---|
| RH01 | 최근 GG 시작=2023-09-15, R까지 완전 | calendar 후보 A=P*; 현행 확정은 GAP |
| RH02 | 같은 조건 시작=2023-09-16 | calendar 후보 A=F*; 하루 차이 산식 미확정 |
| RH03 | 시작=2023-09-14 | calendar 후보 A=P* |
| RH04 | 위 3년을 안산→수원→성남 연접 구간으로 분할 | A는 RH01과 동일. 시군 변화로 끊지 않음 |
| RH05 | 최근 3년 안의 확실한 타시도 등록 하루 | A=F*, grace period 없음 |
| RH06 | 최근 구간 중 하루 정보 없음, 충분한 최근 증명 없음 | A=U. 서울로 추정 안 함 |
| RH07 | 2016-09-15부터 R까지 계속, 기산/완전성 확보 | calendar 후보 B=P*; 합산 공식 환산은 GAP |
| RH08 | 위 시작=2016-09-16 | calendar 후보 B=F*; 실제 행정 산식 확인 필요 |
| RH09 | 위 시작=2016-09-14 | calendar 후보 B=P* |
| RH10 | 인정 GG 5년 + 서울 2년 + 인정 GG 5년 | 공식 산식상 합계 10년이 증명되면 B=P* |
| RH11 | GG 4년 + 서울 2년 + GG 4년, 전체 인정 이력 완전 | B=F*, 서울 2년을 더하지 않음 |
| RH12 | GG 구간 일부 겹침, 동일 사실 복제 아님 | ERROR, double count/자동 merge 금지 |
| RH13 | A=P, B=F가 각각 증명됨 | ANY=P |
| RH14 | A=F, B=P가 각각 증명됨 | ANY=P |
| RH15 | A=P, B=P | ANY=P, 두 evaluation 보존 |
| RH16 | A=F, B=F | ANY=F |
| RH17 | A=F, B=U | ANY=U |
| RH18 | A=U, B=F | ANY=U |
| RH19 | A=P, B=U | ANY=P, B의 누락도 보존 |
| RH20 | A=U, B=P | ANY=P |
| RH21 | A=U, B=U | ANY=U |
| RH22 | HistoryFact 없음 | 두 경로 U/MISSING |
| RH23 | periods=(), completeness 선언 없음 | 두 경로 U/INCOMPLETE. 0년으로 FAIL 안 함 |
| RH24 | 모든 필드 같은 interval 두 번 | idempotent 계산, 원본 불변 |
| RH25 | 같은 날 GG와 서울 interval 중첩 | ERROR / conflict |
| RH26 | 정상 구간이 역순으로 전달됨 | 계산용 canonical sorting 후 동일 결과 |
| RH27 | 정상 관측된 R+1 이후 이동 기록 | R 계산 제외. 과거 정상 결과 불변 |
| RH28 | end=None, observed_through>=R, 최근 경로 충분 | A=P* 가능. 시스템 오늘 불사용 |
| RH29 | GG 구간 사이 미상 30일, 완전성 없음 | 그 구간을 잇지 않음. 증명 부족 경로 U |
| RH30 | start>=finite end / 문자열·datetime 날짜 | ERROR |
| RH31 | 안산→수원, 도 상태·유효 날짜 연접 | GG 계속성 유지 |
| RH32 | 수원→성남 연접 | 같은 도 의미. 현재 RegionRef로 성남 입력 불가 GAP |
| RH33 | GG→서울→GG | A는 재전입부터, B는 이전 GG도 검토 |
| RH34 | 신청일 안산 Fact만 있고 history 없음 | current resident P 가능, 두 기간 경로 U |
| RH35 | R을 하루 전/뒤로 변경하며 동일 유효 이력 선택 | 경계 결과는 확정 산식에 따라 재평가. 시스템 실행일은 무관 |
| RH36 | R 고정, 유효한 R 이후 suffix만 추가 | R의 기간 결과 동일 |
| RH37 | 같은 이력에 SELF_REPORTED | source 보존, 값 기반 판정 |
| RH38 | 같은 이력에 MANUALLY_VERIFIED | RH37과 상태 같음 |
| RH39 | 같은 이력에 OFFICIAL_DATA | RH37과 상태 같음. 완전성 자동 상승 없음 |
| RH40 | 귀화 전 GG 기간만으로 임계값 도달 | 그 기간 제외. 남은 미달은 충분한 완전성이 있을 때만 F* |
| RH41 | 귀화 후 인정 GG 기간만으로 충분 | 국적/날짜 경계 확정 후 P* |
| RH42 | 귀화 여부·취득일·당일 포함 근거 부족 | 인정 기산 U/GAP, 임의 포함 안 함 |
| RH43 | known GG 합계 충분, 더 오래된 구간 일부 미상 | 누락이 인정 증명에 영향 없으면 B=P* |
| RH44 | 최근 5년만 완전하고 B는 10년 미만 | 과거 누락 가능 → B=U |
| RH45 | origin_complete=True, 전 인정 이력 완전하고 두 기준 미달 | A=F*, B=F*, ANY=F* |
| RH46 | complete 창 안에 미상 gap인데 완전하다고 선언 | ERROR / completeness 모순 |
| RH47 | end=None이나 observed_through<R | 이후 연장 금지. 증명 부족 경로 U |
| RH48 | 같은 구간·도, provenance만 다른 두 근거 | 출처 둘 보존, 기간 한 번만 계산 |
| RH49 | 출생 전 구간과 확인된 BirthFact가 함께 입력 | 상위 consistency ERROR 후보. birth 역산 금지 |
| RH50 | 2024-02-29 시작, 2027-02-28 또는 03-01 R | 임계 도달일 GAP. 어느 쪽도 자동 보정 안 함 |
| RH51 | 위 이력의 R=2025-02-28 / 2026-02-28 | 윤일 calendar 처리 golden 후보. 공식 산식 전 P/F 확정 금지 |
| RH52 | 원시 발생일/신고일 불일치, 유효일 미확인 | 정규화 boundary GAP. 한 날짜를 임의 선택 안 함 |
| RH53 | observed_through 뒤의 예정 전입을 확정 사실로 제출 | 입력 오류 후보. 미래 거주 예측 안 함 |
| RH54 | 실제 외국인등록 기간이나 실거주 주소를 GG 주민등록으로 제출 | 의미 불일치, 입력 정규화 거부. 단순 주소 기간에 포함 금지 |

RH13~21은 사실 데이터로 그 상태를 어떻게 증명하는지와 분리한 논리 집계 기대다. 도내 분할·순서·중복 동일성은 동일 정규형 입력의 계산 계약이고 실제 기간 임계값을 이미 검증했다는 뜻이 아니다.

## 27. 실제 tree 향후 모습

```text
ALL — 명시적으로 선택한 Q3의 구현된 조건 일부
├─ Current Ansan Resident (기존)
├─ Q3 Birth (완료, 재설계하지 않음)
└─ ANY (거주기간, 미구현)
   ├─ ContinuousResidenceRule / GYEONGGI / 3년
   └─ CumulativeResidenceRule / GYEONGGI / 10년
```

등록분류/국적 등 별도 필수조건과 신청창·절차·지급 계산은 이 그림에 완료된 것으로 넣지 않는다. 기간 Rule에 귀화 기산 제한이 적용되더라도 전체 국적·등록분류 eligibility가 완성되는 것은 아니다. 미래 통합에는 새 release·rule_version·source locator·coverage 검토가 필요하다. 이번 실제 001/002를 수정하지 않는다.

## 28. 미해결 문제

| GAP | 현재 확인 / 필요한 공식 근거 | 영향 |
|---|---|---|
| D1 기간 단위 | 현행 안산의 3년/10년 일수·연월일 산식 미확인. 과거 용인 3650일 표기는 전이 불가 | **주 차단 요인** |
| D2 초일/말일·윤일 | 3주년·2/29 기산·신청일 포함·합산 rounding 규칙 | 하루 경계 P/F 확정 불가 |
| D3 원시 event 매핑 | 초본 발생일/신고일 중 유효일, 지연 신고·동일일 정정·전출입 처리 | 임의 interval 생성 금지 |
| N1 국적취득 | 취득 후 인정은 확인, 취득 당일·최초 등록·말소/재등록 경계 미확인 | 영향받는 기간 U/GAP |
| C1 완전성 검증 | 어떤 증거가 origin_complete와 complete 창을 증명하는가 | 부족한 기록으로 합산 FAIL 금지 |
| R1 도 단위 모델 | 기존 RegionRef가 일부 시군만 허용 | 독립 ProvinceRef 등 최소 입력 모델 후속 승인 필요 |

최종 판단은 한 값으로 D1/D2/D3의 **NEEDS_DURATION_SEMANTICS_DECISION**을 선택한다. N1은 부가 미해결이며 이를 무시하지 않는다. C1은 구체적 추천 계약을 제시했지만 구현·행정 인증 완료가 아니다. 현재 자료 간 OR·지역·기준일 충돌은 발견하지 않아 OFFICIAL_SOURCE_CONFLICT로 판단하지 않는다.

## 29. 추천 구현 방식

지금 구현하지 않는다. 먼저 현행 2026 안산/경기도 지침·공식 FAQ의 세부 산정 예제로 D1~D3를 확인한다. 특히 3년 경계·여러 구간 합산·윤일·발생일/신고일·귀화 당일 예제가 필요하다. 공식 확인 경로를 찾지 못하면 해당 쟁점을 미해결로 유지하며 사용자에게 calendar/일수 중 취향으로 고르게 하지 않는다. 담당기관 문의 초안은 만들 수 있으나 실제 메시지 발송은 별도 명시적 승인이 필요하다.

그 다음 최소 Fact 계약을 먼저 확정하고 strict 모델·날짜/완전성/지역 검증만 별도 승인 후 구현한다. 이후 순수 계산·결과 계약·각 Rule·ANY 연결·loader·실제 자료 순으로 작은 단위를 검증한다. 새 infrastructure를 선제 생성하지 않는다.

재현성은 같은 정규화 history·완전성·reference_date·인정 기산·정책 산식/자료 버전으로 같은 결과다. 실행 시간이 늦어졌다고 이력을 R까지 연장하지 않는다. What-if에서도 같은 계산 정의를 고정하고 명시적 입력만 변경한다.

## 30. 최종 판단

**NEEDS_DURATION_SEMANTICS_DECISION**

공식 OR·도 범위·신청일·귀화 후 인정 원칙은 확인했다. 그러나 현행 산식과 원시 날짜의 경계가 불명확한 상태에서 1095일/3650일 또는 calendar anniversary를 선택하면 하루 경계 오판을 만들 수 있다. Fact/Rule 추천과 54개 수동 시나리오를 제시했으나 실제 판정 구현 준비 완료로 간주하지 않는다.

**다음 가장 작은 작업 1개:** 2026 안산시 청년기본소득의 **기간 산정 세부 근거 대조표**를 작성해 일수/연월일·초일/말일·윤일·발생일/신고일·귀화 기산일의 공식 예제를 확인한다. 확보되지 않으면 쟁점별 문의 초안까지 준비하되 발송하지 않는다. 이 단계에서 코드·정책 데이터 변경은 없다.

### M1.17 검증 기록

작업 전 전체 pytest는 **2372 passed in 4.79s**였다. 수동 표는 새 실행 테스트가 아니다. 작업 전 backend/tests/data/docs 기존 파일의 SHA256 기준선을 기록했으며 최종 기존 파일 불변 확인과 문서 형식·회귀 결과는 아래 기록을 따른다.

문서 작성 후 전체 pytest는 **2372 passed in 6.22s**다. 기존 **86개 파일 전부 SHA256 동일**, 추가 파일은 이 문서 하나다. 실제 001/002 releases, synthetic 자료, facts/rules/evaluator/routing/loader, 기존 테스트·기대값·문서를 변경하지 않았다. 필수 30개 절과 RH01~RH54의 순서·중복·누락 및 한국어 문서를 확인했다. 이는 문서 형식·기존 회귀 검증이며 새 거주기간 계산 구현이나 공식 산식 확정의 증거가 아니다.
