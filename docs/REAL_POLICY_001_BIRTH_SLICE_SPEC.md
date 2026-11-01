# 실제 정책 001 — 2026 Q3 생년월일 조건 계약 (M1.16)

현재 입력 모델은 19절 M1.16A, 독립 Rule 구조 모델은 20절 M1.16B, 독립 evaluator는 21절 M1.16E 기록을 따른다. 아래 1~18절의 문서 전용 작업·검증 기록은 M1.16 당시 기록이다.

검토일: **2026-10-20 / Asia/Seoul**. 산출물은 이 설계 문서 하나다. 코드·테스트·실제 데이터·기존 문서는 변경하지 않는다.

최종 판단: **READY_TO_IMPLEMENT_BIRTH_SLICE**.
이 판단은 아래 단일 Q3 조건의 BirthFact/BirthDateRule/독립 evaluator 최소 구현 준비에 한정한다. 연간 Policy의 분기 자동 선택·실제 JSON 등록·주민등록과의 결합·전체 자격 판정 준비를 뜻하지 않는다.

## 1. 정책 / 분기 식별

| 항목 | 계약 |
|---|---|
| 정책 | 2026년 안산시 청년기본소득 |
| 기존 canonical policy_id | KR-GG-ANSAN-YOUTH-BASIC-INCOME |
| 현재 edition_id | 문자열 `2026` 유지 |
| 이번 검토 대상 | **2026년 3분기 지급대상 생년월일 조건 하나** |
| leaf rule_id 제안 | ANSAN_YBI_2026_Q3_BIRTH_RANGE (미발행 내부 ID) |
| 기존 실제 실행 데이터 | r0001 주민등록-only DRAFT/CONDITION_SLICE. 그대로 보존 |

Q1/Q2/Q4 규칙을 함께 정규화하지 않는다. 분기는 지급대상 분기이며 신청일에서 자동 계산한 분기가 아니다. 이 문서의 새 타입·reason/error 이름·배치·연결 방식은 **M1.16 구현 계약/제안**으로서 현재 런타임 API가 아니다.

다시 검토한 기존 근거: REAL_POLICY_001_ANALYSIS.md, REAL_POLICY_001_IMPLEMENTATION.md, POLICY_DATA_ENVELOPE_SPEC.md, POLICY_RULE_SPEC.md, RULE_ROUTING_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md. 역사적 단계의 미구현 기록과 M1.15 현재 구현을 구별했다.

## 2. 공식 출처

2026-10-20에 안산시 공식 URL을 직접 다시 조회했다. 검색결과 요약·블로그를 판단 근거로 사용하지 않았다.

| 근거 | 공식 위치 / 재확인 사항 |
|---|---|
| S1 [공고 게시물](https://www.ansan.go.kr/danwongu/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1664308) | 제목: 2026년 안산시 청년기본소득 신청 일정 공고. 고시공고번호: 안산시 공고 제2026-399호. 담당: 청년정책관. 세부 생년월일은 첨부 참조 |
| S1-HWP [첨부 원문](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP) | 신청개요의 연령기준 항목과 신청기간 및 지급일정 표의 3분기 행. 원문 날짜 2026-02-19 |
| S2 [공식 정책 페이지](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001545) | 주요내용 → 2026년 지급일정 및 방법 → 3분기 행의 지급대상자 생년월일. 게시일/수정일 미확인 |
| S3 [3분기 공식 안내](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390) | 제목: 안산시, 24세 청년 대상 청년기본소득 3분기 접수 시작. 등록일 2026-08-31. 본문 두 번째 문단에서 대상 출생일을 4자리 연도로 확인 |

공고 게시물은 웹 도구의 응답 실패 후 같은 공식 URL을 읽기 전용 HTTP로 확인했다. HWP는 메모리에서 본문과 표의 텍스트를 추출했다. 파일 크기 **61,952 bytes**, SHA256 `b0d9f1e9f2de6844157021cab963b2e1dedd49183550036a9777dafa1de78106`으로 M1.15 확인본과 같다. HWP 추출의 공고번호 누락은 게시물 metadata로 보완했고 정확한 쪽번호는 검증하지 않아 만들지 않았다. S3의 이미지 첨부는 이번 근거가 아니다.

**이번 Q3 출생일 범위·연령 기준일에서 공식 자료 간 충돌을 발견하지 않았다.** 초본 발급일 안내 차이와 자동신청 변경은 기존 미해결 절차 문제이며 이번 생년월일 판정에 넣지 않는다. 후속 확인에서 출생일/기준일이 달라지면 실제 규칙 인코딩을 중단하고 재검토한다.

## 3. 공식 생년월일 범위

| 항목 | 값 | 근거 |
|---|---|---|
| min_birth_date | **2001-07-02** | S1-HWP/S2 표의 축약 연도와 S3의 전체 연도 교차 확인 |
| max_birth_date | **2002-07-01** | 동일 |
| 하한 포함 | **포함** | 명시된 대상 출생일 구간의 시작일로 해석 |
| 상한 포함 | **포함** | 명시된 대상 출생일 구간의 종료일로 해석 |
| 비교식 | **min_birth_date ≤ birth_date ≤ max_birth_date** | 이번 정규화 계약 |

원문 표는 연도를 01/02로 축약한다. 세기를 사용자 나이나 시스템 날짜에서 추측하지 않고 S3의 2001/2002 표기로 확인했다. 양끝 포함은 대상 출생일 구간의 통상적 해석과 5절의 만 나이 경계가 일치함을 함께 확인한 **정규화 해석**이다. 원문에 별도의 inclusive 필드나 수학적 부등호가 실려 있다고 주장하지 않는다. 반대되는 제외 문구는 이번 확인 자료에서 발견하지 않았다.

최소 중요 경계: 2001-07-01 FAIL / **2001-07-02 PASS** / **2002-07-01 PASS** / 2002-07-02 FAIL. 단위는 날짜이며 시각·타임존 절삭·숫자 YYYYMMDD 변환은 필요하지 않다.

## 4. 연령 기준일과 네 날짜

S1-HWP의 연령기준 항목은 분기 시작 월의 첫날을 제시하며 Q3은 **2026-07-01**이다. 이 기준일을 프로그램이 신청일로 대체하지 않는다.

| 날짜 | 의미 | 이 leaf의 처리 |
|---|---|---|
| quarter age reference date | 2026-07-01. 공식 연령 설명의 기준 | Q3 자료의 검토 metadata. 직접 범위 비교의 계산 인자로 불필요 |
| application date | 사용자가 해당 신청을 한 날짜 | 주민등록 leaf에 필요한 날짜. 생년월일 범위를 바꾸지 않음 |
| evaluation date | 명시적으로 전달하는 평가일 | 상위 재현 context에 보존. 고정 Q3 범위 비교를 바꾸지 않음 |
| birth date | 사용자의 출생일 | 공식 구간과 직접 비교하는 유일한 사용자 값 |

평가일·신청일 변경으로 선택된 Q3 규칙을 Q4 등으로 자동 전환하지 않는다. 평가일에 접수 가능한지, 당시 정책이 시행 중인지도 이 함수가 판정하지 않는다. 미래 신청일에 대한 주민등록 Resolver의 UNKNOWN 규칙을 생년월일 조건으로 복사하지 않는다.

## 5. “24세”와 생년월일 범위 관계

| 방식 | 실제 구현 시 정확성 / 영향 | 판단 |
|---|---|---|
| A. quarter_reference_date에 age == 24 | 정확한 생년월일로 만 나이를 계산하면 이번 범위와 일치하는지 검증할 수 있지만 날짜 산식·경계 처리와 기준일 바인딩이 추가됨. 현재 UserProfile.age는 기준일을 증명하지 못함 | 설명·교차 검증 용도 |
| B. 공식 birth_date 범위 직접 비교 | 원문이 제시한 대상 구간을 그대로 재현. 나이 재계산에 의한 공식 범위 대체가 없음 | **실행 규칙으로 채택** |

설명용 경계 검토: 2001-07-01 출생자는 기준일에 25세이므로 구간 밖이고, 2001-07-02 출생자는 24세로 구간 안이다. 2002-07-01 출생자는 기준일에 24세로 구간 안이며 2002-07-02 출생자는 아직 23세로 구간 밖이다. 이는 공식 구간과의 일치 확인이며 실행 나이 산식을 새로 만드는 지시가 아니다.

가령 2001-08-01 출생자는 Q3 기준일에는 24세이고 2026-10-20에는 25세다. Q3 출생일 조건은 PASS다. 현재 나이가 24가 아니라는 이유로 제외하면 안 된다. `24세 / 기준일 2026-07-01 / 지급분기 2026 Q3`는 설명/검토 metadata로 두며 min/max를 재생성하지 않는다.

## 6. BirthFact 계약

### 최소 입력과 타입

| 항목 | 추천 계약 |
|---|---|
| 모델 | frozen/slots BirthFact. 사용자 1명에 **하나** |
| birth_date | 정확한 `date` 또는 None. None은 날짜 미입력 |
| source | 필수 `BirthSource` Enum. 기본값으로 공식 확인을 부여하지 않음 |
| fact 자체 부재 | 함수 인자의 None. 정상 UNKNOWN |
| 컬렉션 | list/tuple/Sequence/map을 BirthFact 대신 받지 않음 |

`type(value) is date`를 기준으로 datetime 및 임의 하위 타입·문자열·정수·bool을 거부한다. 모델은 날짜 파싱·자동 보정·시스템 시각 조회를 하지 않는다. None과 잘못된 타입을 섞지 않는다. birth_date=None인 Fact에도 source는 유효해야 하며 잘못된 provenance는 UNKNOWN으로 숨기지 않는다.

### 단일 값 선택과 충돌

주민등록은 날짜별 여러 사실의 선택이 필요했지만 출생일은 이번 입력에서 한 값이므로 별도 fact selection Resolver를 만들지 않는다. 동일 날짜를 가진 Fact 두 개라도 evaluator에 컬렉션으로 전달하면 입력 형태 오류다. 이 계약은 여러 출처 중 하나를 자동 선택하지 않는다.

향후 여러 출처를 받는 수집 경계에서는 서로 다른 **알려진 birth_date**를 발견하면 Data Error로 중단해야 한다. OFFICIAL_DATA 우선·최근 입력 우선·첫 값 우선으로 해결하지 않는다. 동일 값의 provenance 통합과 정정 권한은 별도 기능이며 이번에 구현하지 않는다. 복수 Fact 자동 병합 API가 준비됐다고 주장하지 않는다.

### source/provenance 선택

**설계 결정:** 주민등록 전용 RegistrationSource는 재사용하지 않는다. 작은 `BirthSource`를 새 타입 후보로 정하고 SELF_REPORTED / MANUALLY_VERIFIED / OFFICIAL_DATA 세 값만 제안한다. 같은 문자열이어도 RegistrationSource 객체는 BirthSource가 아니다. generic UserFactSource로 전체 기존 체계를 이전하는 작업은 하지 않는다.

SELF_REPORTED는 사용자 진술, MANUALLY_VERIFIED는 외부 절차의 수동 확인 표식, OFFICIAL_DATA는 외부 공식자료 표식이다. Enum 값이 자료를 인증하거나 더 높은 자격을 주지 않는다. 같은 날짜이면 세 source의 판정은 같다. MVP 사용 입력은 SELF_REPORTED로 시작하며 나머지 두 경로의 인증·연결 기능은 미구현이다.

### 개인정보와 윤년

주민번호·초본·증빙 이미지를 수집하지 않고 필요한 생년월일만 요청/세션 메모리에서 사용한다. 영구 저장·전체 입력 로그·AI 전송을 추가하지 않는다. 결과에 출생일이 필요하면 evaluated_value 한 곳에만 보존하며 provenance details에 중복 복사하지 않는다. 향후 사용자 설명 서비스에는 경계 충족 결과만 보내는 방식부터 검토한다.

Python date는 유효한 2000-02-29를 표현·비교하며 2001-02-29는 생성할 수 없다. [Python 공식 datetime 문서](https://docs.python.org/3/library/datetime.html#datetime.date)를 기준으로 달력 유효성을 맡긴다. 별도 윤년/나이 계산기를 만들지 않는다. 2000-02-29는 이번 실제 구간 밖이므로 유효한 입력에 대한 FAIL이다. 일반 모델의 달력 유효성과 이 정책 조건 충족을 구별한다.

## 7. BirthDateRule 계약

| 필드 | 타입 / 제약 |
|---|---|
| rule_id | 비어 있지 않은 str. 기존 트리 전체의 중복 ID 금지 계약 적용 |
| min_birth_date | 정확한 date, 필수 |
| max_birth_date | 정확한 date, 필수. min ≤ max |
| evidence_refs | 비어 있지 않은 tuple[str, ...]. 공식 데이터 경계에서는 canonical ref·중복 금지·출처 버전/적용 범위 검증 |

불변 모델로 두며 양끝 포함은 **이 타입의 고정 의미**다. inclusive 플래그·operator 조합·나이 필드·신청일·as_of 입력을 추가하지 않는다. min=max도 일반 모델에서는 한 생일만 허용하는 유효한 구간이지만 이번 Q3 공식 데이터는 정해진 두 경계와 정확히 일치해야 한다.

범위 순서·타입 등 구조적 유효성과 **Q3 공식 의미의 정확성**은 다르다. 두 날짜가 순서대로 있다는 사실만으로 올바른 Q3 규칙이 되지 않는다. Q3 rule_id 문자열이나 Q3 locator 이름만으로 파서가 공식 내용까지 이해할 수 있다고 가정하지 않는다.

이번 공식 정규화 검토에서 고정할 값 묶음은 `{정책, 2026 Q3, 기준일 2026-07-01, min 2001-07-02, max 2002-07-01, 양끝 포함, 검토한 evidence 확인본}`이다. 추후 실제 데이터 수용 시 이 묶음을 공식 원문과 대조하는 acceptance 검토/명시적 golden 검증이 필요하다. 일반 evaluator 안에 정책 ID별 날짜 상수를 하드코딩하지 않는다.

## 8. PASS / FAIL / UNKNOWN 및 출력

**순서:** Rule 구조 검증 → Fact 타입/구조 검증 → 미입력 판정 → 날짜 직접 비교. 잘못된 Rule과 Fact 부재가 함께 있어도 Rule 오류를 UNKNOWN으로 감추지 않는다.

| 상태 | 조건 | reason_code 제안 | missing_fields 제안 |
|---|---|---|---|
| PASS | 알려진 date가 min/max 양끝 포함 구간 안 | BIRTH_DATE_IN_RANGE | 빈 tuple |
| FAIL | 알려진 date가 min보다 작거나 max보다 큼 | BIRTH_DATE_OUT_OF_RANGE | 빈 tuple |
| UNKNOWN | BirthFact 자체가 None | BIRTH_FACT_MISSING | birth |
| UNKNOWN | 유효한 BirthFact.birth_date가 None | BIRTH_DATE_MISSING | birth.birth_date |

코드 이름은 독립 BirthDateReasonCode 후보이며 현재 구현된 Enum 이름이 아니다. source에 따른 상태 가중치나 현재 나이 fallback은 없다. 달력상 유효한 미래 출생일도 이번 함수에서는 고정 구간 밖의 FAIL이며 evaluation_date에 따른 임의 유효성 규칙을 만들지 않는다.

출력 목표는 기존 RuleEvaluation이며 rule_id/status/reason_code/evaluated_value/expected_condition/missing_fields/evidence_refs/details를 보존한다. 알려진 evaluated_value는 정확한 date, UNKNOWN은 None이다. expected_condition에는 양끝 포함의 BirthDateCondition(min_birth_date,max_birth_date)을 두고, 사용자 provenance는 BirthDateDetails(source: BirthSource | None)로 최소 표현한다. Fact 부재면 source=None, 날짜만 부재면 입력 source를 보존한다. 정책 evidence는 상태와 무관하게 Rule에서 그대로 가져온다. 오류 메시지에는 생년월일을 넣지 않는다.

## 9. Data Error

아래는 3상태 결과가 아니라 예외 경로다. 기존 정상 Status에 DATA_ERROR를 추가하지 않는다.

| 오류 | 처리 경계 |
|---|---|
| Fact 대신 문자열/dict/Sequence 등 | 사용자 입력 타입 오류 |
| birth_date의 str/int/bool/datetime 등 | 사용자 값 타입 오류 |
| 존재하지 않는 날짜 문자열 | 향후 명시적 입력 파서에서 날짜 형식/달력 오류. 도메인으로 자동 보정 금지 |
| source 누락/None/다른 Enum/문자열 | 사용자 provenance 오류. 생성자 필수 인자 자체 누락은 Python TypeError |
| 두 출처의 상충 출생일 | 복수 출처를 다루는 입력 수집 경계에서 오류. 현재 단일 API는 컬렉션 자체를 거부 |
| Rule 날짜 누락/None/타입 오류/min > max | 정책 데이터 오류 |
| 빈 rule_id/빈 evidence_refs/잘못된 refs 타입 | 정책 구조 오류 |
| canonical ref 불량/locator 부재/버전 불일치/참조 금지 수명/적용 정책 불일치 | 기존 source/envelope 계층의 Data Error 계약 적용 |
| Q3로 표기하면서 다른 분기 범위를 넣음 | **Q3 공식 데이터 acceptance 오류**. 일반 범위 생성자만으로는 발견 불가 |

후속 최소 구현의 사용자 Fact 오류는 기존 ProfileValidationError 계열의 code/field를 갖는 작은 BirthFactValidationError 후보, 규칙 오류는 PolicyDataError 계열을 권장한다. 세부 오류 code는 구현 전 작은 테스트 계약에서 고정하되 위 오류/UNKNOWN 의미는 변경하지 않는다. 입력 모델과 공식 데이터 acceptance를 하나의 예외 처리 블록으로 뭉개지 않는다.

## 10. 기존 UserProfile.age와의 관계

현재 UserProfile에는 age:int|None이 있고 birth_date가 없다. PolicyFact는 가구소득만 다룬다. 생년월일을 이 둘의 우회 필드로 저장하지 않는다.

- age=24, BirthFact 없음 → **UNKNOWN**.
- age가 24가 아니어도 유효한 BirthFact 날짜가 공식 구간 안 → **PASS**.
- age=24여도 출생일이 공식 구간 밖 → **FAIL**.
- age에서 날짜를 역산하거나 birth_date에서 age를 덮어쓰지 않는다.

UserProfile.age의 기준일을 모르는 상태에서 두 값이 다르다는 이유만으로 birth leaf Data Error를 만들지 않는다. 출생일 진위 검증과 age 입력 품질 확인은 별도다. age 자체가 음수/문자열이면 기존 UserProfile 생성자가 먼저 거부하는 계약은 유지한다. age는 다른 단순 정책이나 UX에서 계속 사용할 수 있다.

## 11. 평가 구현 방식 A / B / C 비교

| 방식 | 타입 안전성 / 공식 의미 | 기존 atomic 영향 | 미래 확장 / 복잡도 | 판단 |
|---|---|---|---|---|
| A. specialized Rule + 작은 Birth Resolver + Adapter | 의미가 명확하고 주민등록 패턴과 유사 | 정수 비교 유지 | 사실 선택·기준일 바인딩이 없어 Resolver/중간 결과/Adapter가 동일 값을 반복 전달하게 됨 | 가능하지만 이번 단일 값에는 계층이 과함 |
| B. 기존 atomic gte/lte에 date 추가 | 등록 필드·RuleValue·비교 검증·결과 모두 명시적으로 확장해야 안전 | 현재 gte/lte는 AGE/HOUSEHOLD_INCOME의 정수 전용. 암묵 date 투입 불가 | 범용 날짜 DSL로 범위가 커짐. ALL 두 leaf로 범위가 분산됨 | 이번 최소 작업에 부적합 |
| C. BirthDateRule 전용 순수 evaluator | date/출생일 구간 의미를 전용 타입에 유지 | 기존 atomic 연산자를 바꾸지 않음 | 단일 비교·명시적 누락 처리. 미래 다른 공식 출생일 범위에도 재사용 가능 | **추천** |

현재 RuleValue는 str/int/bool 또는 그 tuple이며 Field에 birth_date가 없다. Python date에 비교 연산이 가능하다는 이유로 기존 numeric gte/lte에 넣으면 현재 strict 모델이 거부한다. 타입 검증을 느슨하게 하는 방식은 채택하지 않는다.

## 12. 추천 구현 방식과 현재 엔진 GAP

**설계 결정:** C, `BirthFact + BirthDateRule + 작은 specialized evaluator`를 추천한다. 주민등록과 다른 사실 선택 특성을 반영한다. 별도 Resolver framework·플러그인·generic provenance 개편은 필요 없다.

후속 함수 계약 제안: `evaluate_birth_date_rule(rule: BirthDateRule, fact: BirthFact | None = None) → RuleEvaluation`. profile/application_date/evaluation_date를 받지 않는다. I/O·현재시각·DB·네트워크·Fact 선택·나이 산식이 없는 순수 함수다. 입력을 바꾸지 않는다.

| 현재 구현 | 후속으로 필요한 최소 확장 (이번에는 미구현) |
|---|---|
| RuleNode/Policy root/RuleGroup은 atomic·resident·group만 허용 | BirthDateRule을 유한 타입 목록에 명시적으로 추가. 다른 모든 타입의 거부 유지 |
| RuleEvaluation.evaluated_value는 date 미지원 | 출생일 condition 분기에서만 정확한 date/None 허용. 기존 atomic date 거부 유지 |
| expected_condition/reason 검증은 기존 두 종류만 지원 | BirthDateCondition/BirthDateReasonCode와 상태·값의 일관성 검증 추가 |
| EvaluationDetails는 ResidentRegistrationDetails 단일 타입 | 유한 union에 BirthDateDetails 추가하고 실제 허용 타입 검사를 명시적으로 분기. 주민등록 EvaluationEvidence에 birth 필드를 섞지 않음 |
| PolicyEvaluation.reason_codes도 유한 reason 검증 | BirthDateReasonCode를 명시적으로 허용. 자유 문자열 허용 금지 |
| EvaluationFacts는 resident_registrations만 보유 | 연결 단계에서 birth:BirthFact|None=None 추가 제안. 기존 기본값/결과 불변 유지 |
| routing은 birth 분기 없음 | 연결 단계에서 birth 입력을 위 evaluator에 전달. age를 전달하지 않음 |
| m1.1 JSON leaf는 atomic/resident만 허용 | 실제 파일 인코딩 전 별도 문법/버전 결정 필요. 이번 문서는 새 schema나 loader 지원을 선언하지 않음 |

`_jsonable`의 날짜 직렬화 재사용 가능성과 별개로 생성자 허용 타입·condition/reason/detail 검증을 함께 확장해야 한다. date를 결과에 넣는 것만으로 현재 엔진에 연결됐다고 볼 수 없다.

**다음 최소 구현 경계:** 독립 BirthFact/BirthSource와 입력 검증부터 시작한다. Rule/결과/evaluator는 다음 작은 작업에서 연결하고 routing/loader/실제 데이터는 더 뒤에서 별도 승인한다. 이 단계적 준비는 분기 모델 결정 없이 가능하다.

## 13. evidence 계약

현재 실제 SourceRegistry의 세 문서에는 **eligibility-resident-registration만 존재**한다. 이를 birth evidence로 재사용하면 resolve 자체는 성공할 수 있어도 의미가 틀리므로 금지한다. 기존 validator는 원문의 의미까지 자동 검증하지 않는다.

새 locator 제안: **eligibility-birth-date-2026-q3**. 아직 sources.json에 존재하지 않으며 아래 ref는 문서상 후보다.

| evidence_ref 후보 | 사람이 다시 찾을 위치 / 의미 |
|---|---|
| ANSAN-2026-399-HWP#eligibility-birth-date-2026-q3 | 첨부 HWP → □ 신청개요 → ○ 연령기준 및 ○ 신청기간 및 지급일정 표 → 3분기 행 → 지급대상자 생년월일 열 |
| ANSAN-C0001545#eligibility-birth-date-2026-q3 | 주요내용 → 2026년 지급일정 및 방법 → 3분기 행 → 지급대상자 생년월일 열 |
| ANSAN-B0238-1681390#eligibility-birth-date-2026-q3 | 본문 두 번째 문단 → 3분기 지급 대상의 전체 연도 생년월일 구간 |

각 SourceEvidence의 applicable_policy_ids는 기존 canonical policy_id, section은 위 실제 위치, meaning_summary는 Q3 min/max와 필요시 기준일을 짧게 설명한다. page는 검증 전 null이다. S3에는 연령 기준일이 명시되지 않아 그 locator 단독으로 기준일을 입증한다고 쓰지 않는다. `#locator`는 내부 의미 위치로 원격 HTML anchor가 아니다.

실제 source 인코딩 시 기존 d0001 자료를 덮어쓰지 않고 **locator가 추가된 새 확인본 버전 후보 d0002**를 별도 dataset에 기록해야 한다. 원문 HWP hash가 같아도 registry의 locator 내용 변경은 확인본 변경이다. 새 Envelope의 source_bindings도 새 버전에 pin하고 last_verified_at은 사용 locator 확인일의 최소값 계약을 따른다. 이번에는 d0002·새 rule_version·dataset을 발행하지 않는다.

정책 evidence와 BirthFact.source는 다르다. OFFICIAL_DATA라는 사용자 provenance가 공식 정책 locator를 대신하지 않는다. PASS/FAIL/UNKNOWN 모두 rule evidence_refs를 보존해야 하고 소스가 없거나 잘못됐으면 UNKNOWN이 아니라 Data Error다. 구조 유효성·source resolve·정책 적용 검증의 통과가 생년월일 숫자의 원문 일치까지 보장하지 않는다.

## 14. 분기 / edition 문제

| 후보 | 장점 | 현재 제약 / 위험 | 판단 |
|---|---|---|---|
| A. 명시적 target quarter context로 적절한 Rule 선택 | 선택한 지급 분기 하나만 평가할 수 있음 | 현재 context에는 정책 ID/신청일만 있고 target quarter가 없음. ApplicationWindow는 미구현이며 신청일로 지급 분기 추정 시 소급/회차 오류 | 향후 통합 시 우선 검토. 명시적 지급 분기와 버전 선택 계약 필요 |
| B. 연도 edition 내부에 분기별 RuleGroup/condition 보유 | 연도 ID 유지, 여러 조건 보관 가능 | 현재 단일 root와 ALL/ANY/NOT만 있음. 모든 분기를 ALL로 합치면 대부분 잘못 FAIL, ANY로 합치면 선택하지 않은 분기로 잘못 PASS | selector 없이 실행 금지. Q1/Q2/Q4 모델링은 이번 범위 밖 |
| C. 분기별 edition | 분기별 트리 분리 쉬움 | 현재 edition_id는 ASCII 4자리 연도만 허용, Manifest는 한 policy_id당 edition 하나만 선택 | 현재 구현 불가. 문법·선택 계약 변경은 별도 결정 |

**현재 확정 범위:** 이 문서와 미래 독립 테스트는 Q3 규칙을 명시적으로 선택한 것으로 한정한다. edition_id는 2026으로 유지하고 Q3를 ID에 붙여 새 edition을 몰래 만들지 않는다. rule_version을 분기 selector로 쓰거나 평가일/신청일에서 분기를 추정하지 않는다.

**미결정:** 실제 연도 edition에 여러 지급 분기를 연결할 방식은 아직 결정하지 않았다. A를 추천하지만 이번에 QuarterContext/ApplicationWindow/selector를 구현·확정하지 않는다. 현재 r0001 주민등록-only Envelope에 Q3 birth를 즉시 추가하면 연도 전체에 Q3 출생일을 적용할 위험이 있다. 실제 트리/JSON 통합 전 이 결정이 필요하며 그 통합 단계의 판단은 NEEDS_QUARTER_MODEL_DECISION일 수 있다. 단일 BirthFact/전용 evaluator의 설계·검증을 막는 조건은 아니다.

## 15. 수동 테스트 시나리오

**아래 32개는 수동 기대 계약이며 새 테스트 실행 결과가 아니다.** 기본값: Q3 공식 min/max, 정확한 date 객체, 단일 SELF_REPORTED Fact, 유효한 rule/evidence. “정책 acceptance” 행은 일반 evaluator보다 앞선 실제 Q3 인코딩 검토 경계이며 현재 자동 validator가 이미 지원한다고 주장하지 않는다.

| ID | 사례 / 달라진 입력 | 기대 | 이유 / 판정 경계 |
|---|---|---|---|
| B01 | birth_date=2001-07-01 | FAIL | 하한 하루 전 |
| B02 | birth_date=2001-07-02 | PASS | 하한 포함 |
| B03 | birth_date=2001-12-15 | PASS | 구간 중간 |
| B04 | birth_date=2002-07-01 | PASS | 상한 포함 |
| B05 | birth_date=2002-07-02 | FAIL | 상한 하루 뒤 |
| B06 | fact=None | UNKNOWN | BIRTH_FACT_MISSING, missing=birth |
| B07 | BirthFact.birth_date=None, source 유효 | UNKNOWN | BIRTH_DATE_MISSING, missing=birth.birth_date |
| B08 | birth_date="2001-07-02" 문자열 직접 전달 | DATA ERROR | 도메인은 date 문자열 자동 파싱 안 함 |
| B09 | birth_date=20010702 정수 | DATA ERROR | YYYYMMDD 숫자 우회 금지 |
| B10 | birth_date=datetime(2001,7,2,0,0) | DATA ERROR | datetime 절삭 금지 |
| B11 | birth_date=True | DATA ERROR | bool은 date가 아님 |
| B12 | 출생일이 다른 Fact 두 개의 list 전달 | DATA ERROR | 단일 Fact API 위반. 향후 수집 경계에서도 알려진 값 충돌은 오류 |
| B13 | 같은 출생일의 Fact 두 개 tuple 전달 | DATA ERROR | 중복 자동 병합을 지원하지 않음 |
| B14 | UserProfile.age=24, fact=None | UNKNOWN | age fallback 금지 |
| B15 | age=25, birth_date=2001-08-01 | PASS | 기준일/평가일이 다른 age보다 공식 출생일 범위를 사용 |
| B16 | age=24, birth_date=2002-07-02 | FAIL | age로 범위 밖 날짜를 덮지 않음 |
| B17 | birth_date=2001-12-15, SELF_REPORTED | PASS | 출처 가중치 없음 |
| B18 | 같은 날짜, MANUALLY_VERIFIED | PASS | 같은 값의 동일 판정 |
| B19 | 같은 날짜, OFFICIAL_DATA | PASS | 표식은 자격 보너스가 아님 |
| B20 | birth_date=2000-02-29, 유효 date | FAIL | 윤년 날짜는 유효하나 이번 실제 구간 밖 |
| B21 | 외부 입력 "2001-02-29" | DATA ERROR | 달력상 없는 날짜. 미래 parser 경계에서 거부하고 2/28로 보정 금지 |
| B22 | Rule min=2002-07-01, max=2001-07-02 | DATA ERROR | min > max |
| B23 | Rule min=None 또는 문자열 | DATA ERROR | 정책 날짜는 필수 정확한 date |
| B24 | Rule evidence_refs=() | DATA ERROR | 근거 없는 규칙 구조 거부 |
| B25 | 새 Q3 refs가 새 확인본에 정상 resolve, 원문 날짜 일치; B03 입력 | PASS | 향후 승인 후의 정책 acceptance + 비교. 현재 실제 registry에는 새 locator 없음 |
| B26 | 새 Q3 ref를 현재 d0001 registry에 조회 | DATA ERROR | LOCATOR_NOT_FOUND. resident locator로 대체 금지 |
| B27 | Q3 표기인데 Q2의 생년월일 범위를 잘못 복사 | DATA ERROR | Q3 공식 묶음과 불일치하는 정책 acceptance 오류. 순서가 맞는 date만 검사하는 일반 생성자는 검출 불가 |
| B28 | B03의 평가일을 2026-09-15에서 2026-10-20으로 변경 | PASS → PASS | 고정 Q3 출생일 비교는 평가일에 불변 |
| B29 | B03의 신청일을 2026-09-01에서 2026-10-21로 변경 | PASS → PASS | 신청일을 읽지 않음. 미래 신청/접수상태 판정이 아님 |
| B30 | birth_date=None인데 source에 RegistrationSource.SELF_REPORTED 전달 | DATA ERROR | BirthSource와 다른 Enum. 정보 부족보다 잘못된 타입을 먼저 거부 |
| B31 | birth_date=2001-12-15, source=None | DATA ERROR | provenance 필수, 임의 기본 source 부여 금지 |
| B32 | Rule min > max이고 fact=None | DATA ERROR | 잘못된 정책을 사용자 누락 UNKNOWN으로 숨기지 않음 |

윤년의 일반성은 별도 합성 구간 `[2000-02-29, 2000-02-29]`에서 해당 날짜가 PASS인 사례로 후속 단위 테스트에 추가할 수 있다. 이를 실제 Q3 규칙이나 실제 정책 데이터로 등록하지 않는다.

## 16. 실제 전체 Policy Tree 연결 예시

아래는 **명시적으로 2026 Q3를 선택한 뒤의 미래 부분 트리**다. 현재 생성·로드·실행되는 데이터가 아니며 전체 자격 트리도 아니다.

```text
ALL (선택된 지급대상 분기 = 2026 Q3)
├─ BirthDateRule [2001-07-02, 2002-07-01], 양끝 포함
└─ ResidentRegistrationRule [GYEONGGI/ANSAN], APPLICATION_DATE
```

타입 목록·결과·routing 확장을 명시적으로 적용한 후에는 기존 ALL 3상태 집계에 자연스럽게 연결할 수 있다. birth 함수는 출생일만 읽고 resident 함수는 신청일의 주민등록 사실을 읽는다. 두 leaf의 기준일을 공유하거나 application_date를 birth에 바인딩하지 않는다.

이후 전체 자격 조건에 거주기간 가지가 추가될 수 있다.

```text
ALL (선택된 Q3, 전체 구현은 아직 아님)
├─ BirthDateRule
├─ ResidentRegistrationRule
├─ ANY
│  ├─ 경기도 연속 거주 조건 (미구현)
│  └─ 경기도 합산 거주 조건 (미구현)
└─ 등록분류·국적/귀화 등 적용 조건 (미구현·계약 별도)
```

신청창 OPEN/CLOSED, 자동·소급신청, 지급 계산은 이 예시의 자격 집계에 임의로 넣지 않는다. 두 leaf가 PASS여도 전체 정책 자격 확정은 아니다. 실제 연결 시 DRAFT/CONDITION_SLICE를 유지하고 coverage에 생년월일 leaf 추가 및 남은 제외 조건을 반영해야 한다. 현 resident-only 데이터와 r0001은 변경하지 않는다.

## 17. 미해결 질문과 Assumptions

| 항목 | 상태 / 다음에 필요한 일 |
|---|---|
| Assumption A1 | 한 호출은 동일 사용자 한 명이며 출생일 Fact는 호출자가 명시한 단일 값이다. 수집 경계의 신원 인증이나 정정 이력은 범위 밖 |
| Assumption A2 | 이번 독립 검증은 Q3가 명시적으로 선택된 상태다. 평가일/신청일에서 분기를 자동 선택하지 않음 |
| Assumption A3 | 초기 실제 사용자 입력의 source는 SELF_REPORTED. 수동/공식 provenance 값은 자료 진위 인증 기능이 아님 |
| 확정된 설계 선택 | 단일 BirthFact, 별도 BirthSource, inclusive BirthDateRule, C 전용 evaluator, age fallback 금지. 이 문서의 현재 추천 계약이며 구현된 모델이 아님 |
| 실제 연도 edition의 분기 선택 | A/B/C 중 통합 방식을 확정해야 함. 명시적 target quarter를 우선 추천하나 새 context/selector는 후속 승인 |
| JSON schema/version | 기존 m1.1은 birth leaf를 거부한다. 추가 종류를 같은 버전으로 확장할지 새 버전으로 분리할지 실제 loader 작업 전에 결정 |
| 공통 결과 연결 | 기존 exact 타입 검사/유한 reason/details/condition 허용 목록을 함께 확장해야 함. 현재 평가 엔진에 그대로 꽂을 수는 없음 |
| evidence 발행 | Q3 locator와 새 source 확인본/정책 버전을 원문 대조 후 별도 dataset에 기록해야 함. 이번 실제 sources.json은 그대로 |
| 복수 출처 정정 절차 | 충돌 오류 원칙은 정했으나 동일 값의 provenance 통합·권한 있는 정정·검토 절차는 미구현 |
| 공식 자료의 확인 한계 | Q3 날짜와 기준일은 일치. 초본 발급 기준 차이/자동신청 효력 등은 기존 분석의 미해결 사항으로 유지 |
| 개인정보 | 생년월일 영구 저장 없이 최소 입력. API/로그/설명 서비스의 구체 전송 계약은 해당 단계에서 별도 검토 |

구현을 막는 공식 출생일 범위·날짜 타입·경계 의미의 불확실성은 없다. 위 분기/loader 질문은 **독립 모델·evaluator 구현 이후 실제 연도 Policy 통합 전**에 해결할 항목이다. 미결정을 임의의 분기 라우팅으로 채우지 않는다.

## 18. 최종 판단

**READY_TO_IMPLEMENT_BIRTH_SLICE**

판단 근거: 세 공식 자료로 Q3 출생일 범위를 교차 확인했고 공고에서 연령 기준일을 확인했다. 단일 Fact·직접 범위 비교·양끝 포함·누락/오류·age fallback 금지·provenance·근거/버전 경계·32개 수동 기대 사례를 정의했다. 기존 정수 atomic 비교와 주민등록 Resolver를 바꿀 필요 없이 작은 전용 모델/함수로 시작할 수 있다.

**다음 가장 작은 작업 1개:** 독립 `BirthFact / BirthSource` 불변 모델과 타입·누락·provenance 검증만 구현·단위 테스트한다. BirthDateRule/evaluator/결과 타입/routing/loader/실제 데이터/분기 selector는 그 작업에 포함하지 않는다.

이번 회귀 실행 결과와 기존 파일 무변경 확인은 아래 검증 기록을 따른다. 이 문서의 수동 기대 사례를 구현된 신규 테스트라고 보고하지 않는다.

### 검증 기록

- 전체 pytest: **1,782 passed in 5.52s**. 기존 테스트와 기대값을 변경하지 않았다. 신규 실행 테스트는 없다.
- 작업 전 backend/tests/data/docs 기존 파일 **66개**의 SHA256을 기록하고 비교했다. **66개 모두 동일**, 추가 파일은 이 문서 하나다. 기존 actual resident slice·SourceRegistry·loader·routing·Envelope·합성 fixtures는 불변이다.
- 문서의 필수 18개 절과 B01~B32 수동 시나리오의 순서·중복·누락을 확인했다. 수동 기대표는 birth 구현 완료를 뜻하지 않는다.
- Git 저장소가 아니므로 git diff 대신 파일 해시를 사용했다. 적용되는 AGENTS.md는 발견되지 않았다.

## 19. M1.16A — IMPLEMENTED: BirthSource / BirthFact 입력 모델

`backend/policy_engine/facts/birth.py`에 독립 불변 모델을 구현하고 facts 패키지에서 BirthSource, BirthFact, BirthFactValidationError를 공개한다. 기존 주민등록 파일·RegistrationSource·UserProfile·평가 입력·엔진·loader·실제 데이터는 변경하지 않았다.

| 항목 | 구현 계약 |
|---|---|
| BirthSource | SELF_REPORTED / MANUALLY_VERIFIED / OFFICIAL_DATA. RegistrationSource와 별도 Enum |
| BirthFact | frozen/slots dataclass. birth_date:date\|None, source:BirthSource 두 필수 인자 |
| 날짜 | 정확한 date/None만 허용. datetime·date 하위 타입·str/int/float/bool/list 등 거부 |
| source | 정확한 BirthSource만 허용. 문자열·None·RegistrationSource는 거부 |
| 정보 부족 | birth_date=None을 보존. 상태 판정은 수행하지 않음 |
| 오류 | BirthFactValidationError → ProfileValidationError → EngineValidationError → ValueError |
| 오류 code/field | INVALID_DATE / birth.birth_date, INVALID_SOURCE / birth.source |
| 필수 인자 누락 | Python TypeError. source를 임의로 채우지 않음 |
| to_dict | 새 dict에 birth_date의 ISO 날짜 문자열 또는 None, source의 Enum 문자열만 표현 |

사용자 입력을 오류 메시지에 복사하지 않는다. 달력 유효성은 Python date 생성에 맡기며 윤년 산식이나 문자열 parser를 추가하지 않았다. 유효한 2000-02-29와 date.min/date.max도 이 **입력 모델**은 보존하며 정책 적합성·현재 시점의 출생 가능성 판단을 하지 않는다.

M1.16의 BirthSource 후보 세 값은 이번 승인된 직접 지시에 따라 그대로 확정했다. 출처 간 자동 우선순위·오타/별칭 보정·UserProfile.age 역산·복수 Fact collection은 없다. to_dict는 값 표현이고 JSON parser/loader/API schema가 아니다. 일반 repr에 대한 자동 로그나 영구 저장 기능도 추가하지 않았다.

IMPLEMENTED: BirthSource, BirthFact, strict 입력 검증, 불변성, 최소 값 표현, 모델 단위 테스트.

NOT IMPLEMENTED: BirthDateRule, birth PASS/FAIL/UNKNOWN, evaluator/Resolver/Adapter/routing, 결과 타입 확장, JSON loader, Q3 birth rule/locator/Envelope 수정, 분기 선택·나이 계산·API/UI/AI.

최종 판단: **READY_FOR_BIRTH_DATE_RULE**. 다음 가장 작은 작업 1개는 **BirthDateRule의 불변 모델과 min/max·필수 근거 구조 검증만 구현·단위 테스트**하는 것이다. evaluator·routing·실제 데이터 연결을 자동 포함하지 않는다.

### M1.16A 검증 기록

- 작업 전: **1,782 passed in 5.55s**. 신규 tests/test_birth_fact.py: **74 passed in 0.21s**. 최종 전체: **1,856 passed in 6.17s**.
- 신규 테스트는 세 출처·미입력·윤년·date 하위 타입/datetime 거부·잘못된 타입·필수 provenance·불변성·동등성·새 직렬화 dict·외부 입력 변경 영향 없음·age 분리·오류 메시지의 원본 값 비노출을 확인한다. 생년월일 정책 판정 테스트는 아니다.
- Git 저장소가 아니므로 기존 backend/tests/data/docs **67개**의 SHA256을 비교했다. facts/__init__.py와 문서 3개만 수정됐고 나머지 **63개는 동일**하다. 기존 1,782개 테스트 파일과 기대값·모든 데이터·주민등록 모델·routing·loader·결과 타입은 그대로다.
- 신규 파일은 facts/birth.py와 tests/test_birth_fact.py 두 개다. 적용되는 AGENTS.md는 발견되지 않았다.

## 20. M1.16B — IMPLEMENTED: 독립 BirthDateRule 구조 모델

`backend/policy_engine/specialized_rules/birth_date.py`에 frozen/slots BirthDateRule을 추가했다. specialized_rules 패키지에서만 공개하며 기존 RuleNode/Policy.root/RuleGroup 허용 타입에는 아직 등록하지 않았다.

| 필드 | 구현 계약 |
|---|---|
| rule_id | 필수 정확한 str, 공백만 있는 값 금지. 자동 생성/strip 없음 |
| min_birth_date | 필수 정확한 date. 실제 Q3 기본값 없음 |
| max_birth_date | 필수 정확한 date. min_birth_date ≤ max_birth_date 필요 |
| evidence_refs | 비어 있지 않은 정확한 tuple, 각 원소는 비어 있지 않은 정확한 str |

범위의 의미는 **양끝 포함**으로 고정한다. min=max인 하루 구간도 구조적으로 유효하며 inclusive_min/max 옵션은 없다. 날짜는 datetime/date 하위 타입/문자열/숫자/None을 거부한다. 문자열 파싱·나이 산식·BirthFact 비교를 하지 않는다.

rule_id와 evidence_refs는 기존 ResidentRegistrationRule의 구조적 의미와 동일하다. ID 주변 공백과 ref 순서/중복을 보존하며 자동 보정하지 않는다. 기존 모델과 같이 evidence_refs의 기본값은 빈 tuple이지만 생성을 시도하면 PolicyDataError다. ref 문법·중복 금지·실제 source 존재/버전/locator 검증은 실제 데이터 연결 단계의 Envelope/Registry 책임으로 남는다. **현재 BirthDateRule은 그 계층에 아직 연결되지 않았다.** 구조 생성 성공이 근거 검증 성공이라는 뜻은 아니다.

공통 validation helper가 ResidentRegistrationRule에는 없고 models.require_text는 specialized rule을 다시 import하므로, 모델 레지스트리/기존 파일을 수정하지 않고 같은 작은 검증식을 사용했다. 규칙 오류는 기존 PolicyDataError → EngineValidationError → ValueError 계층을 그대로 사용한다. 필수 생성자 인자 누락은 TypeError이며 새 오류 타입이나 정상 판정 상태는 추가하지 않았다.

to_dict는 rule_id, ISO 날짜 문자열 두 개, evidence_refs의 새 list를 반환한다. 이 값 표현은 현재 m1.1 loader가 지원하는 입력 형식이 아니며 parser/serializer framework를 추가하지 않았다.

테스트는 임의 합성 날짜와 SYNTH-SOURCE-001#birth-date-range 등을 사용한다. 실제 Q3 날짜·locator·source 확인본·PolicyEnvelope는 생성/수정하지 않았다. BirthFact/UserProfile.age/quarter/reference_date는 모델 필드가 아니다.

IMPLEMENTED: BirthDateRule structural model, 엄격한 필드 검증, min ≤ max invariant, 불변성, 최소 값 표현, 구조 단위 테스트.

NOT IMPLEMENTED: birth PASS/FAIL/UNKNOWN, BirthFact 비교, evaluator/Resolver/Adapter, RuleNode 연결, 결과 타입 변경, routing, JSON loader/schema 확장, actual Q3 birth rule/locator/Envelope, 분기 선택.

최종 판단: **READY_FOR_BIRTH_DATE_EVALUATOR**. 다음 가장 작은 작업 1개는 **기존 RuleEvaluation이 아직 date/출생일 condition·reason·details를 지원하지 않는 GAP을 반영하여 birth evaluator의 최소 결과 계약을 설계**하는 것이다. 코드·routing·loader·실제 자료 연결은 그 설계에 자동 포함하지 않는다.

### M1.16B 검증 기록

- 작업 전 전체 pytest: **1,856 passed in 5.66s**. 신규 tests/test_birth_date_rule.py: **83 passed in 0.21s**. 최종 전체: **1,939 passed in 6.24s**.
- 정상/동일 날짜/윤년 구간, min/max 각각의 strict date, 역전 범위, 필수 인자, ID, 근거 타입·중복 보존, 불변성, 동등성, 새 직렬화 값, 금지 필드와 기존 RuleNode/m1.1 거부 경계를 검증했다. 사용자 생년월일 판정은 실행하지 않았다.
- Git 저장소가 아니므로 작업 전 backend/tests/data/docs **69개** 파일의 SHA256과 비교했다. specialized_rules/__init__.py와 이 명세/DATA_MODEL/ARCHITECTURE 문서만 수정됐고 나머지 **65개는 동일**하다. 기존 테스트 파일·BirthFact·주민등록 모델·RuleNode·결과 타입·모든 loader/routing·실제/합성 데이터는 변경하지 않았다.
- 신규 파일은 specialized_rules/birth_date.py와 tests/test_birth_date_rule.py 두 개다. 적용되는 AGENTS.md는 발견되지 않았다.

## 21. M1.16E — IMPLEMENTED: Rule / Fact 직접 비교

birth_evaluator.py의 evaluate_birth_date_rule(rule,birth_fact)는 이미 생성·검증된 단일 BirthDateRule/BirthFact|None을 받아 RuleEvaluation을 직접 반환한다. 별도 Resolver/Adapter는 없다. 모델에 실제 Q3 기본값을 넣지 않으며 함수도 전달받은 min/max만 비교한다.

양끝 포함 PASS, min 이전 BEFORE FAIL, max 이후 AFTER FAIL을 구분한다. Fact 부재/날짜 부재는 동일 MISSING UNKNOWN이고 두 경우의 source 차이를 보존한다. missing_fields는 결과 계약에서 정한 단일 birth.birth_date 경로다. M1.16 당시 두 누락 코드·경로 후보보다 승인된 M1.16C~D 계약을 우선한다.

함수는 UserProfile/평가 context/신청 context/시스템 날짜에 의존하지 않고 사용자 출생일이나 age를 추정하지 않는다. 정확한 객체 타입만 경계에서 검사하고 기존 모델 내부 검증은 반복하지 않는다. 정책 근거 순서·중복·rule_id·관찰 date·요구 구간·provenance를 보존하며 직렬화는 기존 결과 모델을 사용한다.

IMPLEMENTED: 독립 birth evaluator와 PASS/FAIL/UNKNOWN 실제 비교·단위 테스트. NOT IMPLEMENTED: RuleNode/정책 트리/routing/loader/실제 Q3 데이터·근거 연결/분기 선택. 현재 Policy/RuleGroup과 m1.1 loader는 계속 birth를 거부한다. 상세 구현·검증 기록은 REAL_POLICY_001_BIRTH_RESULT_CONTRACT.md 25절이다.
