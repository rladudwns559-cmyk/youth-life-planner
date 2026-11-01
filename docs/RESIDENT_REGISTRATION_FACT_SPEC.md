# ResidentRegistrationFact 입력·판정 계약 — M1.6

최초 설계 기준일: 2026-10-20, Asia/Seoul. M1.6 당시 산출물은 문서 1개였으며, 후속 M1.6A/M1.6B 승인·구현 현황은 17~18절에 구분한다. 실제 정책 JSON은 추가하지 않았다.

**후속 상태 안내:** M1.6A 모델 계약은 17절, M1.6B 독립 resolver 계약은 18절을 우선한다. M1.6B 승인에 따라 구현 전에 부분 지역 설명과 12절 수동 기대표를 엄격한 RegionRef에 맞춰 갱신했다. 과거 판단·변경 이유는 16~17절에 보존한다. PolicyRule 연결은 이번 범위 밖이다.

이 문서는 M1.6 설계와 승인된 후속 구현을 기록한다. M1.6 당시의 `READY_TO_IMPLEMENT` 판단은 단일 조건의 구현 준비를 뜻했으며, 실제 정책 전체의 실행 승인이나 자동 자격 확정을 뜻하지 않는다. 각 항목의 현재 구현 상태는 후속 절에 명시한다.

## 1. 목적

**정책의 명시적인 기준일에 주민등록지역이 요구 지역과 일치하는가**를 재현 가능하게 판단하기 위한 최소 사실 모델과 평가 계약을 정의한다.

판정 범위는 주민등록지역 조건 하나다. M1의 PASS/FAIL/UNKNOWN과 ALL/ANY/NOT 의미를 유지한다. 경기도 연속/합산 거주기간, 전체 이력, 귀화, 생년월일, 신청기간, 혜택은 이 모델에 넣지 않는다. 거주기간은 후속 ResidenceHistoryFact에서 설계한다.

## 2. 실제 정책에서 필요한 이유

M1.5 분석의 E02는 안산시 주민등록 여부를 **신청일 기준**으로 요구한다. 단순히 현재 사용자가 안산에 산다고 입력한 것과 의미가 다르다.

- 기존 근거: [안산시 공식 정책 페이지의 사업개요·지급조건](https://ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001545), M1.5 원문 분석에 기록.
- 이번에 다시 읽은 근거: [2026-08-31 안산시 공식 3분기 안내](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390)의 지급대상 문단. 신청일을 기준으로 안산시 주민등록을 요구한다.
- 상세 원문 식별정보는 기존 `REAL_POLICY_001_ANALYSIS.md`의 S1~S3와 E02를 참조한다. 이번에는 다른 정책을 수집하거나 자격조건을 추가하지 않았다.

특정 날짜의 일치 결과는 **이 주민등록지역 조건만의 충족**이다. 다른 정책 조건이 충족됐다는 뜻이 아니다. 자기신고 값에 따른 결과도 최종 행정 검증과 구분해서 표시한다.

## 3. 용어 정의

| 용어 | 의미 | 이 문서의 제한 |
|---|---|---|
| 현재 주민등록 사실 | 지정한 날짜에 주민등록지역이 어디였는지에 대한 점 형태의 주장 | ‘현재’는 시스템 오늘을 자동 조회한다는 뜻이 아님 |
| fact.as_of_date | 해당 사실이 주장하는 주민등록 상태의 날짜 | 발급일·입력일·검토일과 혼동하지 않음 |
| evaluation_date | 평가자가 이번 계산에서 명시적으로 제공한 평가 기준 날짜 | 시스템 현재시간 자동 조회 없음 |
| reference_date | 이 정책 조건이 요구하는 주민등록 검토 기준일 | 이 조건에서는 신청일. 평가일로 자동 대체하지 않음 |
| required_region | 정책이 요구하는 완전한 지역 참조 | 이 계약 예시는 경기도/안산시 |
| source | 사실이 어떤 경로에서 왔는지 나타내는 메타데이터 | 자격 상태의 가중치나 우선순위가 아님 |
| 후보 사실 묶음 | 동일 사용자에 대해 한 요청에서 제시된 주민등록 스냅샷들 | 영구 이력 저장소나 거주기간 계산 자료가 아님 |
| 기준일 유효 | fact.as_of_date가 reference_date와 정확히 일치하고, 그 기준일이 evaluation_date 이후가 아님 | 날짜 사이의 지속성을 추정하지 않음 |

발급일만 아는 초본의 발급일을 as_of_date로 복사하지 않는다. 문서에서 확인한 실제 기준일 또는 사용자가 명시적으로 신고한 기준일이 필요하다. 이 계약은 초본 업로드·해석 기능을 포함하지 않는다.

## 4. 모델 후보 및 선택

### 선택: 점 시점의 불변 사실

```text
ResidentRegistrationFact
  region: RegionRef | None
  as_of_date: date | None
  source: RegistrationSource

RegistrationSource
  SELF_REPORTED
  MANUALLY_VERIFIED
  OFFICIAL_DATA
```

| 필드 | 필요한 이유 | 누락·타입 계약 |
|---|---|---|
| region | 주민등록지역 비교 대상 | 미입력/None은 허용하되 UNKNOWN. 문자열·숫자·bool을 RegionRef로 간주하지 않음 |
| as_of_date | 정책 기준일의 사실임을 확인 | 미입력/None은 UNKNOWN. 존재하지만 형식·타입이 틀리면 DATA ERROR |
| source | 자기신고·수동확인·공식자료 경로를 설명 | 명시적 enum 필수. 누락/None/미등록 값은 DATA ERROR |

source가 누락됐다고 임의로 공식 확인이나 자기신고로 채우지 않는다. 사용자 직접 입력 경로가 SELF_REPORTED를 명시적으로 부여하는 것은 가능하다. source 필드 오류는 구조 검증 실패이며, 유효한 source 종류 사이에 자격 점수 차이를 주는 것이 아니다.

독립적인 confidence 숫자나 verification_level은 추가하지 않는다. 출처와 별도 신뢰 점수를 함께 두면 서로 충돌할 수 있고 이번 판정에 필요하지 않다.

valid_from/valid_to는 채택하지 않는다. 한 날짜의 입력으로 유효기간을 만들거나 다음 입력일까지 지속된 것으로 추정하지 않기 위해서다. 거주기간·주소·주민번호·문서 원본·국적·대리인 정보도 이 모델에 추가하지 않는다.

후속 구현에서 frozen dataclass와 tuple을 사용하는 방향을 유지할 수 있다. 이번 문서는 새 클래스를 정의하거나 기존 PolicyFact에 데이터를 넣지 않는다.

## 5. RegionRef 후보 및 최소 계약

### 5.1 선택한 구조

```text
RegionRef
  sido: InternalSidoKey
  sigungu: InternalSigunguKey

문서상 이름공간: MVP_INTERNAL_REGION_V1
현재 계약의 완전한 조합:
  GYEONGGI / ANSAN → 경기도 안산시
  GYEONGGI / SUWON → 경기도 수원시
  SEOUL / JONGNO → 서울 종로구 (조합 검증용)
```

이 값은 **프로젝트 내부 canonical key**다. 공식 행정코드·법정동코드·주민등록 기관코드가 아니다. official_code는 제외한다. 기본 두 지역과 조합 검증용 한 지역만 둔 최소 집합이며 전국 행정구역 DB가 아니다.

요구 지역과 사실 지역은 **sido와 sigungu 쌍 전체**로 비교한다. sigungu 문자열 하나만 비교하지 않는다. 구·동 및 도내 포함관계를 자동 추론하지 않는다.

### 5.2 입력 문자열 차이 처리

| 입력·표시 문자열 후보 | 해석 가능한 같은 지역 후보 | 사실 생성 조건 |
|---|---|---|
| 안산 | GYEONGGI / ANSAN | 사용자에게 경기도 안산시로 확인한 뒤 두 값을 구성 |
| 안산시 | GYEONGGI / ANSAN | 동일 |
| 경기도 안산시 | GYEONGGI / ANSAN | 동일 |
| 경기 안산 | GYEONGGI / ANSAN | 동일 |

위 문자열은 입력 어댑터의 **명시적인 유한 별칭표** 후보다. 원문 문자열끼리 직접 eq 비교하지 않는다. 같은 확인된 선택은 같은 RegionRef가 된다. 별칭 처리로 as_of_date를 채우거나 UserProfile.region을 주민등록 사실로 승격하지 않는다.

가장 작은 입력 계약은 정해진 지역 선택이 완전한 두 키를 전달하는 것이다. 자유입력을 사용한다면 알려진 별칭을 후보로 제시하고 확인을 받아 구성한다. 화면·정규화 코드·전국 검색을 이번에 구현하지 않는다.

M1.6A 계약에서 sigungu만 있거나 sido만 있는 RegionRef는 생성 단계의 INVALID_REGION이다. 정보 부족은 Fact.region=None으로 표현하며 다른 필드를 추론하지 않는다. ‘안산’이라는 표시 문자열을 확인하는 것은 별도 입력 계층의 책임이며, 이 별칭 처리도 현재 구현하지 않았다.

미등록 자유입력은 불일치 FAIL의 근거가 아니다. 선택/확인이 필요하다고 안내한다. canonical 계약에 존재하지 않는 토큰을 RegionRef라고 제출하면 INVALID_REGION으로 거부한다. 이 구분으로 미지원 도시를 임의의 다른 지역으로 판정하지 않는다.

### 5.3 누락과 잘못된 구조

- region=None: 지역 전체 미입력, UNKNOWN.
- RegionRef(None,None): 필수 구성요소가 없으므로 INVALID_REGION.
- RegionRef(GYEONGGI,None) 또는 RegionRef(None,ANSAN): 부분 구조이므로 INVALID_REGION.
- 각 키의 빈 문자열·숫자·bool·미등록 canonical 값, 모순되는 지역 계층: INVALID_REGION.
- 잘못된 키 이름이나 객체 대신 배열/문자열을 주는 것도 INVALID_REGION.
- None을 빈 문자열·0·OTHER로 바꾸지 않는다.
- 향후 지역 허용 목록을 늘리면 내부 목록 버전을 명시한다. 공식 코드 도입은 코드 체계·공식 출처·버전을 검증한 후 별도 결정한다.

## 6. 날짜·기준일 계약

### 6.1 세 날짜의 관계

| 비교 | 계약 |
|---|---|
| fact.as_of_date와 reference_date | PASS/FAIL을 내리려면 정확히 같아야 함 |
| reference_date와 evaluation_date | 같거나 과거일 수 있음. 미래이면 UNKNOWN |
| fact.as_of_date와 evaluation_date | 과거 사실의 과거 기준일 평가는 가능. 미래 사실은 현재 평가의 증거로 채택하지 않음 |

예를 들어 평가일 2026-11-10에 2026-10-01 신청 기준을 검토하고, 그날의 주민등록 사실이 명시되어 있다면 판정할 수 있다. 반대로 10월 1일의 안산 등록을 11월 10일까지 연장하지 않는다. 11월 10일 안산 등록에서 10월 1일 상태를 역추론하지도 않는다.

정책 기준일이 평가일 이후면, 미래 날짜와 일치하는 fact를 보내더라도 UNKNOWN이다. source가 OFFICIAL_DATA라고 표시되어 있어도 이 계약에서 미래 주민등록 상태를 확정하지 않는다. 이러한 입력은 날짜 타입 자체가 유효하면 DATA ERROR가 아닌 시간적 입증 부족이다.

### 6.2 평가일과 M1 호환

현재 M1의 EvaluationContext 필드는 `as_of: date`다. 이번에 이름을 바꾸거나 evaluation_date를 추가하지 않는다. 이 명세의 evaluation_date는 **새 단일 조건 평가 계약의 의미상 입력 이름**이다.

후속 어댑터가 M1 context.as_of를 evaluation_date 역할로 전달하는 것은 명시적으로 매핑할 수 있다. 그러나 이를 정책의 reference_date로 자동 복사하면 안 된다. reference_date는 별도 정책 바인딩에서 받는다.

평가일은 호출자가 제공한 평가의 시간 관점이다. 미래 날짜를 평가일로 둔 수동 사례는 그 날짜를 전제로 한 가상 테스트이며 오늘의 미래 행정상태를 확인한 것이 아니다. 운영 호출자의 평가일 관리 방식은 후속 통합 과제다.

### 6.3 날짜 입력과 오류

- 도메인 값은 정확한 date 타입이다. datetime, bool, 숫자, 모호한 날짜 문자열을 자동 변환하지 않는다.
- 향후 JSON 어댑터가 필요하다면 YYYY-MM-DD 형식만 명시적으로 파싱하고 실제 존재하는 날짜인지 검증한다. 이는 JSON 전송 계약일 뿐 도메인의 문자열 날짜 허용이 아니다.
- reference_date=None은 정책에 바인딩할 사용자 신청 기준일 미입력으로 UNKNOWN이다.
- evaluation_date=None은 시간적 증거를 검토할 평가 기준 자체가 없으므로 DATA ERROR다.
- fact.as_of_date=None은 기준일을 입증하지 못한 유효한 불완전 입력이므로 UNKNOWN이다.
- 이 명세는 날짜 단위 조건만 다룬다. 같은 날 안에서의 이사 시각이나 접수시각을 추정하지 않는다. 원문이 요구하지 않은 시각 규칙을 추가하지 않는다.

## 7. PASS / FAIL / UNKNOWN 판정 계약

### 7.1 계약의 입력과 출력

```text
입력
  facts: 동일 사용자의 ResidentRegistrationFact tuple
  required_region: 완전하고 유효한 RegionRef
  reference_date: date | None
  evaluation_date: date

정상 결과
  status: PASS | FAIL | UNKNOWN
  reason_code: 이 명세의 고정 코드
  missing_fields: 정렬·중복 제거한 필드 경로
  reference_date, evaluation_date
  evaluated_region, fact_as_of_date: 선택된 사실이 있을 때만
  sources: 선택된 의미상 사실의 출처들을 정렬·중복 제거한 값

오류
  별도 validation exception / error code
  판정 status나 UNKNOWN을 함께 반환하지 않음
```

### 7.2 적용 순서

1. 요구 지역, 날짜 타입, 모든 후보 fact와 source의 구조를 검증한다. 다른 날짜의 fact라도 잘못된 타입을 숨기지 않는다.
2. 검증된 후보에서 같은 알려진 as_of_date의 모순을 검사한다. 출처로 우열을 정하지 않는다.
3. reference_date가 없으면 RESIDENT_REFERENCE_DATE_MISSING.
4. reference_date가 evaluation_date 이후면 RESIDENT_REFERENCE_DATE_IN_FUTURE.
5. fact 묶음이 비어 있으면 RESIDENT_REGISTRATION_MISSING.
6. reference_date와 정확히 같은 as_of_date를 가진 후보만 선택한다. 가장 가까운 과거/미래 값을 사용하지 않는다.
7. 일치 후보가 없고 날짜 미입력 fact가 있으면 RESIDENT_REGISTRATION_DATE_MISSING. 모두 다른 알려진 날짜면 RESIDENT_REGISTRATION_DATE_UNPROVEN.
8. 일치 후보 중 지역이 있는 사실을 사용한다. 일치 후보들의 region이 모두 None이면 RESIDENT_REGION_MISSING이다. 부분 RegionRef는 생성 단계에서 거부한다.
9. 완전한 지역 쌍이 required_region과 같으면 PASS, 다르면 FAIL.

여러 입력 문제가 있으면 먼저 구조 오류를 보고하며, 모순 검사는 구조가 유효한 자료에 적용한다. 실제 결과를 만들지 않고 오류 코드와 필드 경로를 반환한다. UNKNOWN 경로가 검증 오류를 덮지 않는다.

| 상태 | 필요한 조건 | 대표 코드 |
|---|---|---|
| PASS | reference_date <= evaluation_date, 해당 날짜의 완전한 지역 사실, 요구 지역과 일치 | RESIDENT_REGION_MATCH |
| FAIL | 같은 조건의 완전한 사실이 요구 지역과 명확히 불일치 | RESIDENT_REGION_MISMATCH |
| UNKNOWN | fact/지역/기준일 부족, 날짜 불일치, 미래 기준일 등으로 입증할 수 없음 | 아래 13절의 원인별 코드 |

SELF_REPORTED도 위 사실·날짜가 충족되면 PASS/FAIL이 가능하다. 이는 사용자 신고 기준의 조건 결과이며 공식 검증 표시와는 별개다.

### 7.3 후보 여러 개, 중복, 부분 정보

- 같은 날짜·같은 지역의 동일 fact 중복은 멱등적으로 취급한다. 중복 횟수나 배열 순서가 결과를 바꾸지 않는다.
- 같은 날짜·같은 지역이고 출처만 다르면 같은 의미상 사실로 취급하며 출처들을 보존한다. 한 출처를 더 높은 자격 근거로 선택하지 않는다.
- 같은 날짜에 안산과 수원이 함께 명시되면 DATA ERROR다. 수동/공식 출처가 있다는 이유로 다른 사실을 무시하지 않는다.
- 부분 RegionRef는 모델 생성 단계의 오류이므로 resolver의 후보가 되지 않는다.
- 같은 날짜에 region=None인 사실과 완전한 지역 사실이 있으면 지역을 가진 사실을 선택한다. None은 반대 지역 주장으로 보지 않는다.
- 서로 다른 입력을 결합해 새 지역을 만들지 않는다. 기존 완전 지역 사실만 선택한다.
- 서로 다른 날짜의 다른 지역은 그 자체로 모순이 아니다. 그 사이에 언제 이동했는지, 얼마나 거주했는지 추론하지 않는다.
- as_of_date=None인 두 사실의 지역이 다르더라도 같은 날의 모순이라고 단정하지 않는다. 날짜를 확인할 수 없으므로 DATE_MISSING이며, 유효한 날짜 사실이 따로 있으면 그것으로 검토한다.

### 7.4 missing_fields의 의미

진짜 누락된 필드만 반환한다. 날짜값이 존재하지만 reference_date와 다른 경우에는 missing_fields=[]다. 이때 reason_code와 required reference_date가 새 근거가 필요한 이유를 설명한다.

정확한 날짜의 fact에 region이 모두 None이면 resident_registration.region을 반환한다. sido/sigungu만 누락된 부분 RegionRef는 UNKNOWN의 누락 경로가 아니라 입력 오류다.

완전한 지역 사실을 선택했다면 선택되지 않은 region=None 사실의 누락을 요구하지 않는다. 이는 기존 M1의 RuleGroup 전체 누락 합집합을 변경하는 것이 아니라 독립적인 사실 선택 단계의 계약이다.

## 8. DATA ERROR 계약

| 오류 | 조건 | UNKNOWN과의 차이 |
|---|---|---|
| INVALID_DATE | 날짜 값이 존재하지만 타입/형식/달력 날짜가 틀림 | 유효한 날짜 없음과 구분 |
| INVALID_EVALUATION_DATE | 평가일 없음 또는 잘못된 타입 | 평가 기준 자체를 구성할 수 없음 |
| INVALID_REGION | RegionRef 구조·필수 키·허용 토큰·계층이 잘못됨 | Fact.region=None은 정보 부족, 부분 RegionRef는 오류 |
| INVALID_REQUIRED_REGION | 정책의 요구 지역이 없거나 불완전/잘못됨 | 정책 설정 오류이지 사용자 정보 부족이 아님 |
| INVALID_SOURCE | source 없음·잘못된 타입·미등록 값 | 유효한 출처 간 신뢰 수준 차이와 무관 |
| INVALID_RESIDENT_REGISTRATION_FACT | fact 객체·컬렉션·허용 키 등 구조가 잘못됨 | 빈 tuple은 fact 없음으로 UNKNOWN |
| CONFLICTING_RESIDENT_REGISTRATION_FACTS | 같은 알려진 날짜의 양립 불가능한 지역 주장 | 다른 날짜 또는 단순 누락과 구분 |

상충하는 fact를 최신 입력 우선, 높은 출처 우선, 임의 첫 값으로 해결하지 않는다. 오류에는 코드와 필드 경로를 제공하고 사용자 전체 자료나 문서 원문을 복사하지 않는다. 잘못된 정책 요구값을 UNKNOWN으로 변환하지 않는다.

오류가 여러 개면 구조 검증 오류 목록을 코드·필드 경로 기준으로 정렬해 보고하는 계약을 권장한다. 구조 검증 성공 후에만 모순 검사를 한다. 이번에는 예외 클래스나 오류 수집 코드를 추가하지 않았다.

## 9. UserProfile과의 관계

현재 UserProfile.region은 그대로 유지한다. M1의 합성 정책과 기존 테스트가 이 값을 직접 사용하므로 이번에 삭제·이름변경·의미변경하지 않는다.

후속 통합에서 기존 region은 일반 지역 입력/탐색 UX 용도로 정의할 수 있다. 그러나 기존 데이터가 실제 거주지인지 생활권인지도 확정되지 않았으므로 지금 current_region으로 자동 이름을 바꾸거나 의미를 재해석하지 않는다.

정책의 주민등록지역 조건은 명시적인 ResidentRegistrationFact만 사용해야 한다. 기존 region="안산시"가 있어도 사실·기준일·출처를 자동으로 생성하지 않는다. policy_facts의 household_income 전용 제약을 몰래 우회해 주민등록값을 저장하지 않는다.

가장 작은 후속 구현에서는 새 모델과 단일 조건 평가를 기존 UserProfile 외부의 명시적 인자로 전달할 수 있다. 프로필에 새 필드를 붙이거나 일반 Fact 컨테이너를 만드는 결정은 별도 통합 단계로 남긴다.

## 10. PolicyRule과의 관계

정책 요구의 의미는 ‘resident_registration.region이 required_region과 같고 그 fact의 날짜가 명시적으로 바인딩한 신청 기준일과 같음’이다. sigungu eq만으로 날짜 검증을 생략하면 안 된다.

| 방식 | 장점 | 위험·비용 | M1.6 판단 |
|---|---|---|---|
| A. 조회 단계에서 기준일 fact 선택 | eq 비교를 단순하게 유지 | 기준일 검증이 호출자마다 흩어지면 잘못 고른 fact를 비교할 수 있음 | 선택 규칙을 공통 순수 함수로 고정한다면 가능 |
| B. Rule 원자 자체에 날짜 해석 추가 | 규칙에 요구 의미가 보임 | 기존 eq evaluator가 사실 조회·시간·모순 처리까지 떠맡고 범위가 커짐 | 지금 기존 원자 엔진을 수정하지 않음 |
| C. 작은 전용 resolver | 선택·기준일·모순 처리를 한 계약으로 검증 가능 | 미지원 필드를 동적으로 실행하는 범용 프레임워크로 키우면 과도함 | **단일 전용 순수 함수 수준으로 권장** |

추천 연결 계약:

```text
정책 요구(설계용, 실제 JSON 아님)
  fact_kind = RESIDENT_REGISTRATION
  expected_region = RegionRef(GYEONGGI, ANSAN)
  reference_date_binding = APPLICATION_REFERENCE_DATE

전용 resolver
  facts + reference_date + evaluation_date
  → 선택된 완전 fact 또는 원인별 UNKNOWN
  → 타입/모순 오류는 별도 오류

조건 비교
  선택된 RegionRef 전체의 동등성 비교
  → 이 조건의 PASS/FAIL/UNKNOWN 결과
```

binding의 **종류**가 정책 데이터에 없거나 잘못됐으면 정책 설정 오류다. 종류는 유효하지만 호출자가 그 신청 기준일 값을 아직 주지 않았다면 REFERENCE_DATE_MISSING이다. 후속 Rule 설계에서 이 둘을 구분한다.

C는 A의 안전한 선택 기능을 한 곳에 명시하는 최소 방식이며, 외부 API·플러그인·동적 필드 실행·DB 조회가 없다. 아직 resolver, 새 rule kind, RegionRef 비교 확장, 결과 어댑터를 구현하지 않는다.

이 조건 결과가 추후 기존 ALL/ANY/NOT에 연결되더라도 3상태 진리표는 그대로다. 현재 ExpectedCondition/Scalar에는 RegionRef가 들어가지 않으므로, 이번 명세를 현 M1 JSON에 바로 넣을 수 있다고 주장하지 않는다.

## 11. source 처리

| 값 | 의미 | 상태에 대한 영향 |
|---|---|---|
| SELF_REPORTED | 사용자가 주민등록지역과 기준일을 직접 신고 | 날짜·지역 계약 충족 시 PASS/FAIL 가능 |
| MANUALLY_VERIFIED | 담당 검토자가 해당 사실을 수동 확인했다고 기록 | 같은 계약 적용. 더 높은 우선순위를 주지 않음 |
| OFFICIAL_DATA | 공식자료 경로에서 얻은 사실이라고 기록 | 같은 계약 적용. 현재 공식 시스템 연결은 없음 |

source는 진위를 자동 인증하는 장치가 아니다. 특히 사용자가 OFFICIAL_DATA 문자열을 선택했다는 이유로 ‘기관 검증 완료’ 표시를 해서는 안 된다. 실제 입력 경로가 입증할 수 있는 출처만 부여해야 한다. 이 문서의 수동 예시는 각 라벨이 적절하게 부여됐다는 가정이며 연결 시스템을 구현한 것이 아니다.

같은 지역·날짜의 source 차이는 status/reason을 바꾸지 않는다. 출처가 다른 상충 주장도 DATA ERROR다. 별도 검증점수, 가중치, 공식 출처 우선 덮어쓰기 규칙은 없다. source가 같아도 날짜 불일치는 해결되지 않는다.

주민번호, 상세 주소, 인증서, 초본 원본, 검토자 실명은 이 단일 조건에 필요하지 않아 수집 계약에 넣지 않는다.

## 12. 수동 기대표

### 12.1 공통 입력

- 표의 모든 인물·날짜 입력은 가상 검토 사례다.
- 기본 evaluation_date=2026-11-10, reference_date=2026-11-10.
- 기본 fact: region=(GYEONGGI,ANSAN), as_of_date=2026-11-10, source=SELF_REPORTED.
- required_region=(GYEONGGI,ANSAN).
- 각 행에서 바꾼 값만 적고 나머지는 기본값이다. ‘없음’은 명시적 None 또는 빈 tuple을 뜻한다.
- 표의 미래는 **evaluation_date 대비 미래**다. 11월 10일이라는 가상 평가 관점을 현재 실제 사실로 주장하지 않는다.
- 오류 행의 상태 ‘—’는 PASS/FAIL/UNKNOWN 중 어떤 상태도 반환하지 않는다는 뜻이다.
- 이 표는 실행 테스트가 아니다. 후속 구현의 사람이 읽을 수 있는 독립 기대값이다.

### 12.2 기대 결과 35개

| ID | 입력 변경 | reference_date | 예상 상태 | 예상 reason_code 또는 error code | missing_fields 또는 오류 필드 | 이유 |
|---|---|---|---|---|---|---|
| RR01 | 기본 안산 사실, SELF_REPORTED | 2026-11-10 | PASS | RESIDENT_REGION_MATCH | [] | 기준일과 완전 지역 일치 |
| RR02 | region=(GYEONGGI,SUWON) | 2026-11-10 | FAIL | RESIDENT_REGION_MISMATCH | [] | 같은 날의 명확한 타 시 등록 |
| RR03 | fact.region=None | 2026-11-10 | UNKNOWN | RESIDENT_REGION_MISSING | [resident_registration.region] | fact는 있지만 지역 없음 |
| RR04 | facts=빈 tuple | 2026-11-10 | UNKNOWN | RESIDENT_REGISTRATION_MISSING | [resident_registration] | 주민등록 사실 자체 없음 |
| RR05 | fact.as_of_date=2026-10-01 | 2026-11-10 | UNKNOWN | RESIDENT_REGISTRATION_DATE_UNPROVEN | [] | 과거 사실을 이후로 연장하지 않음 |
| RR06 | fact.as_of_date=2026-11-11 | 2026-11-10 | UNKNOWN | RESIDENT_REGISTRATION_DATE_UNPROVEN | [] | 미래 사실을 과거 기준일로 역추론하지 않음 |
| RR07 | reference_date=None | 없음 | UNKNOWN | RESIDENT_REFERENCE_DATE_MISSING | [reference_date] | 평가일을 신청 기준일로 복사하지 않음 |
| RR08 | 입력 어댑터에서 fact 날짜가 2026-02-30 | 2026-11-10 | — | INVALID_DATE | error: resident_registration.as_of_date | 존재하지 않는 날짜 |
| RR09 | fact.region=123 | 2026-11-10 | — | INVALID_REGION | error: resident_registration.region | 지역 객체가 아닌 숫자 |
| RR10 | RegionRef(GYEONGGI,None) 생성 시도 | 2026-11-10 | — | INVALID_REGION | error: region.sigungu | 필수 시군구 없음. resolver 호출 전에 거부 |
| RR11 | RegionRef(None,ANSAN) 생성 시도 | 2026-11-10 | — | INVALID_REGION | error: region.sido | 필수 시도 없음. 자동 보완하지 않음 |
| RR12 | 같은 날 안산 fact와 수원 fact | 2026-11-10 | — | CONFLICTING_RESIDENT_REGISTRATION_FACTS | error: resident_registration_facts | 같은 날짜의 상충 주장 |
| RR13 | 기본 fact를 완전히 동일하게 두 번 제공 | 2026-11-10 | PASS | RESIDENT_REGION_MATCH | [] | 동일 입력 중복은 멱등 처리 |
| RR14 | source=MANUALLY_VERIFIED | 2026-11-10 | PASS | RESIDENT_REGION_MATCH | [] | 유효한 source 변경이 상태를 바꾸지 않음 |
| RR15 | source=OFFICIAL_DATA인 가상 입력 | 2026-11-10 | PASS | RESIDENT_REGION_MATCH | [] | 같은 날짜·지역 계약 적용. 실제 공식 연결을 뜻하지 않음 |
| RR16 | evaluation_date=2026-10-20, fact.as_of_date=2026-10-20 | 2026-11-10 | UNKNOWN | RESIDENT_REFERENCE_DATE_IN_FUTURE | [] | 현재 안산 상태로 미래 신청일을 예측하지 않음 |
| RR17 | evaluation_date=2026-10-20, fact.as_of_date=2026-11-10 | 2026-11-10 | UNKNOWN | RESIDENT_REFERENCE_DATE_IN_FUTURE | [] | 미래 날짜끼리 일치해도 현재 입증한 사실로 채택하지 않음 |
| RR18 | evaluation_date=2026-11-10, fact.as_of_date=2026-10-01 | 2026-10-01 | PASS | RESIDENT_REGION_MATCH | [] | 평가일과 기준일이 달라도 정확한 과거 스냅샷으로 검토 가능 |
| RR19 | evaluation_date=2026-11-10, fact.as_of_date=2026-11-10 | 2026-10-01 | UNKNOWN | RESIDENT_REGISTRATION_DATE_UNPROVEN | [] | 현재 등록으로 과거 상태를 역추론하지 않음 |
| RR20 | fact.as_of_date=None | 2026-11-10 | UNKNOWN | RESIDENT_REGISTRATION_DATE_MISSING | [resident_registration.as_of_date] | 날짜 누락과 잘못된 날짜 구별 |
| RR21 | evaluation_date=None | 2026-11-10 | — | INVALID_EVALUATION_DATE | error: evaluation_date | 평가의 시간 관점 자체가 없음 |
| RR22 | source=UNKNOWN_SOURCE 문자열 | 2026-11-10 | — | INVALID_SOURCE | error: resident_registration.source | 허용 출처 enum에 없는 값 |
| RR23 | 같은 날·안산, source만 SELF_REPORTED와 MANUALLY_VERIFIED | 2026-11-10 | PASS | RESIDENT_REGION_MATCH | [] | 동일 의미의 사실과 두 출처를 보존 |
| RR24 | 같은 날 SELF_REPORTED 안산, OFFICIAL_DATA 수원 | 2026-11-10 | — | CONFLICTING_RESIDENT_REGISTRATION_FACTS | error: resident_registration_facts | 높은 출처라고 임의 덮어쓰지 않음 |
| RR25 | 10월 1일 안산, 11월 10일 수원 | 2026-11-10 | FAIL | RESIDENT_REGION_MISMATCH | [] | 다른 날짜는 모순 아님. 정확한 날짜의 수원 사실 선택 |
| RR26 | UserProfile.region=안산시만 존재, 등록 fact 없음 | 2026-11-10 | UNKNOWN | RESIDENT_REGISTRATION_MISSING | [resident_registration] | 일반 지역 입력 자동 승격 금지 |
| RR27 | RegionRef(None,None) 생성 시도 | 2026-11-10 | — | INVALID_REGION | error: region.sido | 완전하지 않은 지역 객체를 생성하지 않음 |
| RR28 | canonical sigungu=UNREGISTERED_CITY | 2026-11-10 | — | INVALID_REGION | error: resident_registration.region.sigungu | 등록하지 않은 내부 키를 정상 데이터로 취급하지 않음 |
| RR29 | required_region=None | 2026-11-10 | — | INVALID_REQUIRED_REGION | error: required_region | 요구 지역 누락은 정책 설정 오류 |
| RR30 | 부분 RegionRef(GYEONGGI,None)를 생성해 완전 fact와 함께 보내려는 시도 | 2026-11-10 | — | INVALID_REGION | error: region.sigungu | 잘못된 모델 생성을 먼저 거부. 정확한 fact가 있어도 오류를 숨기지 않음 |
| RR31 | RegionRef(GYEONGGI,None), RegionRef(None,ANSAN) 생성 시도 | 2026-11-10 | — | INVALID_REGION | error: region.sigungu 또는 region.sido | 각 모델 생성 단계의 오류. 두 부분을 합치지 않음 |
| RR32 | 입력 별칭 ‘안산’을 경기도 안산시로 명시 확인 후 기본 fact 생성 | 2026-11-10 | PASS | RESIDENT_REGION_MATCH | [] | 확인된 canonical 쌍 기준 비교 |
| RR33 | 입력 별칭 ‘안산시’를 같은 지역으로 명시 확인 후 기본 fact 생성 | 2026-11-10 | PASS | RESIDENT_REGION_MATCH | [] | 표기 차이로 상태를 바꾸지 않음 |
| RR34 | 입력 별칭 ‘경기도 안산시’를 명시 확인 후 기본 fact 생성 | 2026-11-10 | PASS | RESIDENT_REGION_MATCH | [] | 동일 |
| RR35 | 입력 별칭 ‘경기 안산’을 명시 확인 후 기본 fact 생성 | 2026-11-10 | PASS | RESIDENT_REGION_MATCH | [] | 동일. 별칭만으로 날짜·출처를 만들지 않음 |

RR32~RR35는 명시적인 확인과 별칭 입력 어댑터를 거친다는 **계약 전제**다. 미확인 문자열을 domain.region에 그대로 넣으면 이 표의 PASS 경로가 아니다. 이 표를 근거로 UI나 자동 지역 추론을 선제 구현하지 않는다.

## 13. reason/error code

### 정상 판정 사유

| reason_code | status | missing_fields |
|---|---|---|
| RESIDENT_REGION_MATCH | PASS | [] |
| RESIDENT_REGION_MISMATCH | FAIL | [] |
| RESIDENT_REGISTRATION_MISSING | UNKNOWN | [resident_registration] |
| RESIDENT_REGION_MISSING | UNKNOWN | [resident_registration.region] |
| RESIDENT_REGISTRATION_DATE_MISSING | UNKNOWN | [resident_registration.as_of_date] |
| RESIDENT_REGISTRATION_DATE_UNPROVEN | UNKNOWN | [] — 날짜값은 존재하지만 요구 기준일을 입증하지 못함 |
| RESIDENT_REFERENCE_DATE_MISSING | UNKNOWN | [reference_date] |
| RESIDENT_REFERENCE_DATE_IN_FUTURE | UNKNOWN | [] — 미래라는 이유를 누락으로 바꾸지 않음 |

오류 코드는 8절의 7종으로 분리한다. DATA_ERROR를 네 번째 Status 값으로 추가하지 않는다. 오류 행에는 reason_code와 정상 상태를 만들지 않는다. reason/error 문자열에는 사용자 지역·날짜·전체 프로필을 삽입하지 않고 해당 값은 필요한 구조화 필드에만 담는다.

정렬된 출처 목록, 누락 경로, 후보 선택 계약을 통해 입력 순서·중복 횟수에 관계없이 동일한 의미의 자료는 같은 status/reason을 내도록 한다. 임의 타임스탬프·현재시간·외부 조회는 사용하지 않는다. 과거의 RESIDENT_REGION_INCOMPLETE는 엄격한 RegionRef에서 발생하지 않으므로 현재 사유 목록에서 제외했다. 새 정상 상태나 임의 변환은 추가하지 않았다.

## 14. 이번 문서에서 선택한 결정사항

이 항목은 M1.6 입력·판정 계약의 제안 결론이며 구현 승인은 별도다.

1. region/as_of_date/source의 점 시점 모델. 이력·기간·국적·서류는 포함하지 않는다.
2. 두 계층의 내부 canonical RegionRef를 사용하고 공식 행정코드는 넣지 않는다.
3. fact 날짜와 정책 기준일의 정확한 일치만 인정하며 기간 연장·역추론·미래 예측을 하지 않는다.
4. 자기신고도 현재 입력 기준 PASS/FAIL이 가능하다. 출처 차이로 상태를 바꾸지 않는다.
5. 모순은 DATA ERROR, 완전히 같은 사실의 중복은 멱등 처리한다.
6. 기존 UserProfile.region을 보존하고 주민등록 사실로 자동 승격하지 않는다.
7. 전용 순수 resolver와 완전 지역 비교를 최소 연결 구조로 권장한다. 범용 Fact 프레임워크나 기존 논리 엔진 전면 재작성은 필요 없다.
8. 정상 상태와 오류를 분리하고 미래·불일치 날짜와 진짜 누락을 구분한다.
9. 실제 정책 전체 PASS나 신청 가능 확정으로 확대하지 않는다.

## 15. 미결정사항

다음은 이 단일 조건 계약의 선행 차단 요건이 아닌 후속 통합/확장 사항이다.

- RegionRef와 Fact를 UserProfile에 추가할지, 별도 request/Fact 묶음으로 전달할지. 다음 최소 구현은 독립 인자를 사용해 미룰 수 있다.
- 전국 지역·구/동 매핑, 공식 코드 체계 도입. 현재 최소 허용 목록으로 이번 계약을 구현할 수 있다.
- 실제 입력 화면과 지역 후보 확인 UX. 이번에는 입력 계약만 제시했다.
- 수동 확인/공식자료 provenance의 운영상 생성 권한과 검증 기록. 초기에는 SELF_REPORTED만 생성해도 이 조건 판정이 가능하다.
- 정책 원자 Rule의 최종 직렬화 구조와 현재 RuleEvaluation에 대한 결과 어댑터. 실제 정책 JSON을 승인하기 전에 따로 결정한다.
- 운영 평가일을 신뢰 가능한 호출자가 어떻게 제공할지. 이번 순수 함수는 evaluation_date를 명시 인자로 받는다.
- 거주기간, 국적, 나이, 신청기간 등 다른 조건. 이번 M1.6을 이들의 해결로 간주하지 않는다.

이 단일 주민등록지역 조건을 설계하는 데 새로운 행정기간 산식은 필요하지 않다. M1.5의 초본 발급 기준·거주기간 산식 질문은 여전히 남아 있지만 이번 점 시점 조건과 분리한다. SELF_REPORTED 사실의 진위를 자동 증명한다는 주장은 하지 않는다.

## 16. 다음 구현 작업과 최종 판단

**다음 가장 작은 작업 1개:** 기존 엔진 밖에 RegionRef/RegistrationSource/ResidentRegistrationFact의 불변 모델과 입력 검증만 추가하고, 정상·누락·잘못된 타입·불변성 테스트를 작성한다. 기존 UserProfile/PolicyFact/EvaluationContext와 138개 테스트를 그대로 유지한다. resolver·정책 Rule 연결·실제 정책 JSON은 그다음 별도 승인 범위다.

작업 전 상태: Git 저장소가 아니므로 git diff를 사용할 수 없었다. 적용되는 AGENTS.md는 발견되지 않았다. 기존 코드·테스트·데이터·문서·루트 설정 파일 24개의 SHA256을 기준선으로 기록했고, 기존 pytest는 **138 passed in 1.44s**였다. 문서 작성 후 비교 결과 기존 24개 파일 모두 해시가 동일했다. 문서의 필수 절 16개 및 중복·누락 없는 수동 사례 35개도 확인했다. 이번에 새 수동 사례를 실행 테스트로 통과했다고 주장하지 않는다.

최종 판단: **READY_TO_IMPLEMENT**

판단 범위는 ‘신청 기준일에 요구 주민등록지역과 일치하는가’ 한 조건의 입력·평가 계약이다. 정확한 날짜 선택, 미래 추정 금지, 지역 정규화 경계, 누락/오류, 모순/중복, 출처 처리와 수동 기대값을 정의했으므로 작은 독립 구현으로 검증할 수 있다. 기존 3상태 논리 엔진의 폐기나 전면 재작성은 필요하지 않다.

## 17. M1.6A — 승인·구현된 모델 부분과 변경 기록

### IMPLEMENTED

- RegionRef: sido와 sigungu 모두 필수이며 완전한 유효 canonical 쌍만 생성한다.
- RegistrationSource: SELF_REPORTED / MANUALLY_VERIFIED / OFFICIAL_DATA의 명시적 Enum.
- ResidentRegistrationFact: region은 RegionRef 또는 None, as_of_date는 date 또는 None, source는 필수 Enum. frozen dataclass이며 중첩 RegionRef도 불변이다.
- 입력 검증 및 최소 to_dict() 표현. 날짜 파싱, source 자동 변환, 별칭 변환은 없다.
- 코드 위치: backend/policy_engine/facts/resident_registration.py. 기존 M1 파일과 동작을 변경하지 않는다.

### M1.6A 직접 지시가 명확히 한 계약 차이

M1.6 5절은 부분 RegionRef를 허용했다. 그러나 M1.6A 지시는 RegionRef의 완전한 구조와 필수 내부값을 요구하고 누락 정보는 상위 Fact의 None과 구분하도록 명시했다. 코드 작성 전 이 차이를 보고했으며, 최신 직접 지시에 따라 다음을 적용한다.

| 입력 | M1.6A 입력 모델의 처리 |
|---|---|
| RegionRef(GYEONGGI,ANSAN) | 유효 |
| RegionRef(GYEONGGI,None), RegionRef(None,ANSAN), RegionRef(None,None) | INVALID_REGION |
| ResidentRegistrationFact(region=None, ...) | 유효한 정보 부족. 아직 UNKNOWN 판정을 수행하지 않음 |
| as_of_date=None | 허용. 아직 기준일 판정 없음 |
| 문자열 날짜·datetime | INVALID_DATE. 문자열 자동 파싱 없음 |
| Fact에 source 문자열/None 직접 전달 | INVALID_SOURCE. 유효한 Enum을 명시해야 함 |
| 필수 생성자 인자 source 자체 생략 | Python TypeError. 기본 출처를 임의로 부여하지 않음 |

따라서 부분 RegionRef를 전제로 한 RR10/RR11/RR27/RR30/RR31은 현재 모델에 그대로 입력하면 INVALID_REGION이다. 이 행들의 원래 UNKNOWN/PASS 기대는 역사적 설계이며 실행된 결과가 아니다. M1.6B 승인에 따라 코드 구현 전에 해당 행들을 입력 오류로 갱신했다. 검증 오류를 UNKNOWN으로 바꾸는 adapter는 만들지 않는다.

잘못된 지역 쌍을 검증하기 위해 지시문이 허용한 최소 비교 지역 SEOUL/JONGNO를 추가했다. 현재 내부 목록은 GYEONGGI/ANSAN, GYEONGGI/SUWON, SEOUL/JONGNO 세 쌍이며 이름공간은 MVP_INTERNAL_REGION_V1이다. 이 값은 공식 정부 행정코드가 아니며 official_code 필드는 없다.

### M1.6A 완료 당시 미구현 — 이후 상태는 18절 참조

resolver, reference/evaluation date 비교, PASS/FAIL/UNKNOWN 주민등록 판정, 모순 fact 선택/중복 처리, Rule 연결, 실제 정책 JSON, 사용자 프로필 통합, alias parser는 구현하지 않았다. source가 사실 확인을 인증하거나 실제 시스템에 연결됐다는 뜻도 아니다.

후속 가장 작은 작업 후보는 별도 resolver의 기준일 선택·누락 사유 계약을 이번 엄격한 RegionRef와 맞춰 검토하는 것이다. 추가 구현 승인은 이 변경 기록으로 대체하지 않는다.

## 18. M1.6B 독립 resolver 계약

상태: **IMPLEMENTED**. 구현 전에 수동 기대표와 이 계약을 먼저 갱신했고, 독립 resolver와 신규 테스트를 추가했다. 전체 pytest 결과 **313 passed in 1.33s**로 기존 229개와 신규 84개가 모두 통과했다. 실제 정책 JSON이나 PolicyRule 연결은 포함하지 않는다.

### 인터페이스와 입력 경계

`resolve_resident_registration(facts, *, required_region, reference_date, evaluation_date)`를 순수 함수로 제공한다. 기존 프로젝트의 evaluate_policy 함수 스타일과 일관되게 클래스나 범용 resolver 프레임워크를 추가하지 않는다.

- facts는 ResidentRegistrationFact의 list 또는 tuple 등 Sequence다. 문자열·bytes·mapping·generator·None은 컬렉션 오류다. 비어 있는 list/tuple은 정보 부족이다. 한 요청의 동일 사용자 자료라는 전제를 둔다.
- required_region은 완전한 RegionRef다. 잘못된 타입은 기존 INVALID_REQUIRED_REGION 오류다.
- reference_date는 정확한 date 또는 None이다. 잘못된 타입은 기존 INVALID_DATE 코드와 field=reference_date로 구분한다. INVALID_REFERENCE_DATE라는 중복 코드는 만들지 않는다.
- evaluation_date는 정확한 date이며 None/datetime/문자열은 INVALID_EVALUATION_DATE다. 기존 EvaluationContext를 바꾸거나 암묵적으로 reference_date를 채우지 않는다.
- 전체 후보의 모델 타입을 검증한 후 같은 알려진 날짜의 지역 충돌을 검사한다. 충돌 검사는 선택 날짜 밖의 후보도 포함한다. 미입력 날짜끼리는 같은 날짜라고 가정하지 않는다. 오류가 있으면 미래/누락 UNKNOWN보다 먼저 거부한다.
- 이 계약의 오류는 M1.6A ResidentRegistrationValidationError를 재사용하며 code와 field를 제공한다. 정상 Status에 DATA_ERROR를 추가하지 않는다.

### 선택·결과·멱등성

1. 구조 검증과 충돌 검사 후 reference_date 누락, 미래 기준일, 빈 facts 순서로 UNKNOWN을 판정한다.
2. 날짜가 정확히 일치하는 후보만 선택한다. 일치 후보가 없을 때 날짜 없는 fact가 있으면 DATE_MISSING, 그렇지 않으면 DATE_UNPROVEN이다.
3. 일치 후보 중 region이 있는 사실만으로 지역을 결정한다. 모두 region=None이면 REGION_MISSING이며 날짜 일치 증거는 결과에 남길 수 있다.
4. 같은 날짜의 다른 완전 지역은 source와 관계없이 CONFLICTING_RESIDENT_REGISTRATION_FACTS다. None은 반대 주장이 아니다.
5. 동일 fact의 중복은 제거한다. 같은 날짜·지역에 출처만 다른 사실은 함께 보존하되 상태·사유는 바꾸지 않는다. 출처 정렬은 사전순이며 신뢰도 우선순위가 아니다.
6. 결과 ResidentRegistrationResolution은 불변이며 status, reason_code, required_region, reference_date, evaluation_date, resolved_region, fact_as_of_date, missing_fields, used_facts와 sources를 제공한다.
7. used_facts는 선택한 정확한 날짜의 근거를 중복 제거해 결정적인 순서로 보관한다. 완전 지역이 있으면 region=None인 후보는 사용 근거에서 제외한다. 정확한 날짜의 후보가 없거나 미래 기준일이면 빈 근거를 반환한다.
8. sources는 used_facts에서만 추출한다. 입력 전체를 결과나 reason 문자열에 복사하지 않는다. 작은 to_dict()로 Enum·date·근거를 명시적으로 표현한다.

활성 reason_code는 13절의 8개다. 예시 지시문의 POLICY_REFERENCE_DATE_IN_FUTURE 대신 기존 확정명 RESIDENT_REFERENCE_DATE_IN_FUTURE를 유지한다. 같은 입력 및 입력 순서 변경·동일 fact 중복에서 결과 전체의 동등성을 검증한다. 출처가 추가되면 근거 메타데이터는 늘 수 있지만 status/reason은 동일하다.

### 범위와 보존

신청기간·거주기간·생년월일·귀화·금액은 평가하지 않는다. UserProfile.region을 읽지 않고 기존 PolicyRule/연산자/평가기/합성 데이터와 통합하지 않는다. 새 테스트는 기존 229개 기대값을 변경하지 않고 추가한다.
