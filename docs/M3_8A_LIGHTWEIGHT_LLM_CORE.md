# M3.8A — 경량 LLM 투영·검사·서버 조립 구현 보고

검증일: 2026-10-26 KST. 최종 판단: **M3_LIGHTWEIGHT_LLM_CORE_COMPLETE_SYNTHETIC_ONLY**.

기존 TEAM복학생 AI+X에 독립 순수 코어를 추가했다. 실제 Provider·Ollama·/api/chat·공개 API·화면에는 연결하지 않았다. 이번 실제 LLM 실행은0건이며 M3.7의 품질 보류 판단은 유지한다.

## 1. 생성·수정 파일

| 구분 | 파일 |
|---|---|
| 신규 코어 | [narrative_contract.py](../backend/explanation/narrative_contract.py) |
| 신규 합성 시험 | [test_narrative_contract.py](../tests/test_narrative_contract.py) |
| 신규 합성 응답 | [narrative_response_v1.json](../tests/fixtures/narrative_response_v1.json) |
| 신규 재현 도구 | [evaluate_narrative_contract.py](../tools/evaluate_narrative_contract.py) |
| 신규 산출물 | [고정30 합성 결과](evidence/m3_8a_narrative_core_evaluation.json) |
| 신규 구현 기록 | 이 문서 |
| 기존 수정 | [ARCHITECTURE.md](ARCHITECTURE.md)에 M3.8A 절만 추가 |

기준선303개 중 기존 변경은 Architecture 문서1개이며 나머지302개는 SHA256·크기·mtime가 불변이다. 기존 제품 코드/테스트/DTO/Provider/validator/Frontend 변경은0개다. 새 의존성·범용 AI 프레임워크를 도입하지 않았다.

## 2. 실제 Projection 구조

`project_facts(ExplanationFacts) -> NarrativeProjection`은 원본 delta의 부호와 이미 계산된 값의 표시 분류만 수행한다. 차액·이자·정책 자격을 새로 계산하지 않는다. 같은 Facts는 같은 compact JSON과 서버 슬롯 표를 만든다.

모델용 공개 영역은 `model_input_json` 또는 이를 새 dict로 돌려주는 `model_input()`뿐이다. 실제 policy_id가 들어 있는 `slots`는 서버 전용이다. 전체 Projection 객체를 모델 payload로 직렬화하면 안 된다.

```json
{
  "budget_changes": {
    "disposable_after_policy": "SAME",
    "monthly_fixed_expenses": "SAME",
    "monthly_income": "SAME",
    "monthly_rent": "SAME",
    "other_monthly_expenses": "SAME",
    "savable_amount": "SAME"
  },
  "cashflow_after_state": "SURPLUS",
  "changed_input_fields": [
    "취업상태"
  ],
  "contract": "narrative-v1",
  "policies": {
    "p01": {
      "after_status": "PASS",
      "before_status": "PASS",
      "changed_checks": [],
      "missing_after": [],
      "missing_before": []
    },
    "p02": {
      "after_status": "FAIL",
      "before_status": "PASS",
      "changed_checks": [
        {
          "after_status": "FAIL",
          "before_status": "PASS",
          "field_label": "취업상태"
        }
      ],
      "missing_after": [],
      "missing_before": []
    },
    "p03": {
      "after_status": "UNKNOWN",
      "before_status": "UNKNOWN",
      "changed_checks": [],
      "missing_after": [
        "정책 기준의 가구소득"
      ],
      "missing_before": [
        "정책 기준의 가구소득"
      ]
    }
  },
  "savings_cap": {
    "after": "SET_POSITIVE",
    "before": "SET_POSITIVE"
  }
}
```

기존 필드명·정책/조건 상태·변경 조건·누락 정보만 사용한다. raw profile, 정확한 원화 금액, 실제 정책/규칙 ID, reason 원문, 정책명·정형 설명·출처 경로·가정 원문은 포함하지 않는다. 필드 표시명은 기존 서버 LABELS를 복사한 읽기 전용 allowlist이다. 이유는 상태·누락·변경 항목으로만 제한하며 임의의 reason 문장을 생성하지 않는다.
순수 함수는 이미 검증된 서버 Facts를 전제로 한다. Python 모델 타입을 출처 인증서로 보거나 임의의 클라이언트 JSON을 정책 결과로 승인하는 공개 경로를 만들지 않았다.

## 3. 모델 입력 크기

고정30에서 compact 투영 본문은 **최소749 / 최대959 UTF-8 bytes**였다. context 상한은4KiB다. 합성 응답 fixture 파일은 **312bytes**, 작은 출력 상한은4KiB다.
이는 **투영 본문과 fixture 파일의 크기**이며 시스템 Prompt·출력 schema·HTTP envelope·실제 tokenizer를 포함한 측정이 아니다. 토큰 제한256과 통신 envelope32KiB 검사는 후속 Provider의 책임이며 이번에는 생성 토큰 수나 모델 지연을 측정하지 않았다.

## 4. Slot mapping

canonical 정책 순서를 그대로 사용해 p01~p03을 부여하며 policy_id의 사전순이나 응답 JSON 키 순서로 재배열하지 않는다. 중복 정책ID/규칙ID·잘못된 누락 매핑은 거부한다.
`PolicySlot`/`NarrativeProjection`은 frozen dataclass와 tuple/JSON 문자열을 사용한다. `PreparedNarrative`는 canonical 문서의 JSON snapshot과 요청마다 다른 비직렬화 객체 binding을 보관한다. 동일 요청의 대응은 불변이고 공유 결과 캐시는 없다.
V1은 **0·1·2·3개 정책**을 지원한다.4개 이상은 승인된 M3.8 초기 범위 밖이므로 전체 정형 대체하며 자동 분할·생략하지 않는다. 기존 Policy Engine의 지원 범위를 줄이는 것은 아니다.
다른 준비 요청에서 검사한 CheckedNarrative를 조립에 재사용하면 REQUEST_MAPPING_MISMATCH로 거부한다. **원시 JSON은 슬롯 집합이 같을 수 있어 스스로 요청 출처를 증명하지 못한다.** M3.8B의 실제 제공자는 요청별 coroutine/응답을 해당 PreparedNarrative에 묶어야 한다. 이를 완전한 네트워크 상관관계 검증으로 과장하지 않는다.

## 5. 작은 출력 JSON

```json
{
  "summary": "비교 결과와 확인할 자료를 함께 살펴보세요.",
  "policy_texts": {
    "p01": "현재와 변경 상황의 조건표를 비교해 보세요.",
    "p02": "평가된 취업 항목을 함께 살펴보세요.",
    "p03": "가구소득 자료는 별도로 확인해 주세요."
  }
}
```

위 파일은 **합성 fixture**다. 실제 모델 출력이 아니다. 허용 root 필드는 summary와 policy_texts 두 개뿐이며, policy_texts는 요청의 슬롯을 모두 정확히 포함해야 한다. 수치·상태·원본 정책ID·승인 결과·근거·next_actions 필드를 추가하면 거부한다.
`output_schema(prepared)`는 동일한 슬롯/문자 제한을 갖는 새 schema dict를 제공한다. 실제 제공자에 전달하는 작업은 하지 않았다.

## 6. Strict 검사

`parse_narrative()`는 str/bytes만 받는다. UTF-8 bytes4KiB를 확인하고 JSON 객체를 엄격히 읽는다. 중복 root/슬롯 key, NaN/Infinity, 잘못된 타입·미완성 JSON·trailing text·마크다운·누락/추가 필드를 거부한다. 슬롯은 정확한 집합으로 비교한다.
문자열을 이미 파싱한 dict나 bytearray로 넘겨 검사 경계를 우회할 수 없다. 깊은 JSON의 RecursionError도 원문을 노출하지 않는 계약 실패로 처리한다. 잘못된 내부 Facts의 Pydantic 직렬화는 warnings='error'로 다뤄 입력값을 포함한 경고를 stderr에 출력하지 않는다.

## 7. 텍스트 검증

요약은 **1~60**, 정책 문장은 **1~40 Unicode code points**로 제한한다. Python len을 사용하므로 grapheme/보이는 글자 수·토큰 수와 다를 수 있다. 공백뿐인 값과 Unicode C계열·U+2028/U+2029를 거부한다.
NFKC는 검사에만 사용한다. 원문을 정규화·trim·숫자 삭제·문장 절단해 통과시키지 않는다. 허용된 NFC/NFD 한국어와 앞뒤 공백은 그대로 보존한다.
기존 validator와 같은 금지 표현·영문/숫자/HTML 경계를 조기 검사하며, 명시적 자격/이용 단정·금융 지급/만기 표현, 알려진 한글 금액/배수 주장과 확인 불필요 문구를 추가로 보수적 거부한다. 예를 들어 UNKNOWN/누락이 남은 정책의 “가구 자료는 더 살펴보지 않아도 됩니다.”를 차단한다. 반면 “자격 기준은 조건표와 함께 살펴보세요.” 같은 비단정 문장은 보존한다.
이 조기 guard는 기존 검증기 변경이나 자연어 전체 의미 판정기가 아니다. 선언한 문구 밖의 패러프레이즈를 모두 막았다고 주장하지 않는다.

## 8. 기존 문서 조립 방식

`prepare_narrative(facts, expected)`는 서버 canonical 문서와 Facts의 money/policy/UNKNOWN/actions 대응을 확인하고 snapshot을 만든다. `assemble_narrative(prepared, checked)`는 요청 binding·슬롯·문장 경계를 재확인한다.
그다음 snapshot에서 새 문서를 만들고 **summary와 해당 policy.text만** 교체한다. 입력 문서나 그 내부 목록을 직접 수정하지 않는다. 응답 순서나 정책명 문자열을 추측해 연결하지 않는다. 반환 문서의 mutable 목록을 호출자가 수정해도 입력/다음 결과/다른 요청은 바뀌지 않는다.

## 9. 핵심 금액·정책 상태 불변성

changed_facts 전체, before/after/delta, 금액 표시 문장, 정책·규칙 ID/3상태/reason/source_refs, 정책 순서, next_actions는 서버 원본만 사용한다. 합성 여부와 지원금0원은 기존 Facts 계약을 유지한다. 정책별 자연어 text 외 core 필드를 모델에서 읽지 않는다.
고정30 합성 검사에서 원본 대비 차이0건을 확인했다. 이것은 서버가 원본을 보유·조립했기 때문이며 **모델의 금액 재현 정확도100%라는 실적은 아니다**.

## 10. UNKNOWN 보존

unknown_information의 before/after 목록과 상태를 그대로 유지하고, FAIL 정책에 남은 누락도 보존했다. UNKNOWN과 누락 유무를 같은 개념으로 합치지 않았다.
상한 None/0·delta None과 여유자금 음수/0을 별도 분류한다. 생활비 월소득으로 정책 가구소득을 채우지 않는다. 조기 문장 guard는 변경 후 UNKNOWN/미확인 자료의 알려진 부정 문구를 검사하지만, 모든 시간적·의미적 오류를 보장하지는 않는다.

## 11. 기존 validate_output 재사용

조립 결과는 반드시 기존 `backend.explanation.service.validate_output(raw, expected)`로 전달한다. 기존 service.py의 코드·SHA256·길이·숫자·정책·UNKNOWN·행동·표현 검사 규칙을 변경하지 않았다.
spy로 호출을 확인했고, 기존 검증기의 실제 조립 문서32KiB 초과와 OutputRejected 실패에서 전체 정형 대체를 확인했다. 정상 fixture도 기존 검증기를 통과해야 성공한다.

## 12. Fallback 처리와 내부 오류

합성 전용 진입점 `evaluate_synthetic_narrative(facts, expected, raw)`은 Projection→준비→작은 검사→조립→기존검증을 연결한다. 예상한 NarrativeContractError 또는 기존 OutputRejected만 잡아 **canonical 문서 전체**를 돌려준다. 실패 문장만 고치거나 다른 정책을 부분 교체하지 않는다. retry·repair·모델 호출은 없다.
기존 의미와 맞춰 INVALID_JSON/UNSUPPORTED_NARRATIVE/RESPONSE_TOO_LONG 또는 기존 검증기 코드를 fallback_reason으로 사용한다. 실패 단계와 세부 진단 코드는 내부 결과에 분리했다. 원문 입력·응답·비밀값은 오류 문자열/로그에 넣지 않는다.
손상된/없는 canonical 문서나 예상하지 못한 RuntimeError 등 내부 오류는 정상 모델 품질 실패로 숨기지 않고 전파한다. 임의의 정상 문서를 만들어 성공으로 처리하지 않는다. 이 라이브러리는 공개 API로 등록되지 않았으며, 후속 통합 시 기존 서버 오류 경계를 유지해야 한다.
합성 성공은 validated_test_double/ai_executed=false/ai_success=false이고, 실패는 deterministic_fallback이다. 실제 LLM 성공으로 표시하지 않는다.

## 13. 합성 테스트 수와 재현

신규 **139 passed, 1.58초**, 신규 warning0. 고정30별 정상 투영·조립·원본 불변,0~3정책,슬롯/순서/요청혼합,100회 결정성,입력/결과 목록 격리,JSON·Unicode·금액/확정·UNKNOWN 문구,경계 길이/바이트,기존검증 호출/실패,오류 전파를 검사했다.
정책명·지역·근거 문자열의 지시문은 모델 입력에 포함하지 않음을 합성 시험으로 확인했다. 이것을 모든 Prompt Injection 방어 완료로 확대하지 않는다.
별도 고정30 재현 도구는 fixture30/30 통과·실제모델0건을 산출한다. 기존 고정 시나리오의 fault 라벨은 입력 이력이고 이번 실제 모델 오류 주입/품질 평가가 아니다.

```text
python -m pytest -q tests/test_narrative_contract.py
python -m tools.evaluate_narrative_contract --output docs/evidence/m3_8a_narrative_core_evaluation.json
```

최초 신규132개 통과 후 경계 시험을 추가해139개가 됐다. 손상 모델 시험에서 직렬화 경고1개를 발견해 오류로 처리하고, 경고/원문 미출력까지 시험한 뒤139개 무경고로 재통과했다. 기존 테스트/기대값 변경은 없다.

## 14. 전체 Backend 회귀

작업 전 실제 기준은 **11,733 passed/1 skipped/1 warning,73.83초**로 재확인했다. 지시문의11,679는 과거 수치다.
작업 후 **11,872 passed/1 skipped/1 warning,73.01초**를 확인했다.11,733+신규139이다. skip은 NTFS 파일 symlink 생성 권한 증거 미확보,warning은 기존 Starlette/httpx deprecation으로 그대로다.
기록은 `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m38a-pytest-before.txt`,`<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m38a-pytest-new.txt`,`<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m38a-pytest-after.txt`다.

## 15. Frontend 영향

Frontend·기존 FastAPI·Provider 선택/통신 코드는 변경0개다. 기존 **115 passed(10.09초)**,TypeScript·Vite build 성공(1.94초)을 다시 확인했다. 새 설명 코어를 UI에 연결하지 않았다.
실제 HTTP/브라우저·Ollama·/api/chat 호출은 이번에 하지 않았다. Frontend 테스트는 기존 가짜 fetch 응답을 사용하는 회귀이며 실모델 성공 화면 증거가 아니다.

## 16. 실제 LLM 실행 횟수

**이번 M3.8A 실제 LLM0건, Provider/모델API/외부 네트워크 호출0건, 설치·다운로드0건**이다. 모든 모델 응답은 합성 fixture다. M3.7의35회는 이전 실행 이력이며 이번 실적에 합산하지 않는다. actual_llm_output은 합성 산출물에서 null이다.
실제 모델 라이선스 재승인·성능 측정·/chat envelope·256토큰 제한 구현은 하지 않았다. 후속 M3.8B의 일이다.

## 17. 기존 보안·금융·정책 상태

현재 기본 정형 설명, M3.7 QUALITY_REVISION_REQUIRED, 실제 상품 만기 계산0개, 실제 미승인 지원금0원을 유지한다. 실제 정책 DRAFT/CONDITION_SLICE,ResidenceHistory OFFICIAL_INQUIRY_REQUIRED,M2.77SYNTHETIC_ONLY도 유지한다.
Source Gate·Policy/Cashflow/Coverage·Acceptance/Historical·기존 보안 계약을 변경하지 않았다. 신규 코어는 DB·파일·환경키 조회·네트워크·Provider 실행을 하지 않는 순수 라이브러리다. 합성 재현 도구만 명시한 산출물 경로에 공개 합성 결과를 저장한다.

## 18. 실제 release6·GV/BV·동결 보존

실제 release6개 SHA256을 이전 검증값과 대조해 일치했다. GV01~GV15/BV01~BV16·기존 tests/fixtures와 Coverage freeze 파일은 기존303개 보존 감사로 확인했다. 계산·판정·validator를 완화하지 않았다.
감사 기록: `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m38a-preservation-audit.json`. 저장소 기준 신규6개와 Architecture의 문서 추가 외 변경은 없다.

## 19. Obsidian 갱신

기존 workflow에 따라 M3.8 설계와 M3.8A 구현을 구분한 노트,Projection/slot/validator/fallback/합성시험·미구현Provider를 기록했다. 관련 아키텍처·Prompt·Provider·테스트·대시보드·마일스톤·자료실을 연결하고 파일/heading/source_paths를 검사한다. 최종 파일 검사에서 Wikilink567개/깨진링크0개를 확인했다. 상세 보존 결과는 아래 감사에 기록했다.
Obsidian GUI/Bookmarks/Bases/템플릿은 미확인 상태를 유지하며 앱 설정이나 플러그인을 변경하지 않는다. IBK는 사용자 발송 완료 보고/공식 회신 대기로 유지한다.

## 20. 미해결 의미 검증 한계

알려진 자격·금액·불확실성 부정 문구는 보수적으로 거부하지만 모든 자연어 의미·인과·패러프레이즈를 검증하지 못한다. 원본 UNKNOWN/숫자 보존과 문장의 의미 정확성은 별개다.
합성 fixture와 기존 validator 통과는 실제 LLM 수용률·한국어 품질·사용자 이해도 증거가 아니다. 원시 JSON의 요청 출처 연결,실제 token/envelope/완료이유·지연·cold/warm·의미 검토는 M3.8B 이후에 별도로 검증해야 한다. 기본 정형 서비스를 이번 합성 결과만으로 실모델 서비스로 승격하지 않는다.

## 21. 최종 판단

**M3_LIGHTWEIGHT_LLM_CORE_COMPLETE_SYNTHETIC_ONLY**.
최소 Projection·불변 슬롯·엄격한 작은 JSON/문장 검사·텍스트만 조립·기존 validator·전체 fallback·139합성시험/고정30/전체회귀를 완료했다. 기존 계약과 충돌해 동결 코드를 바꾼 부분은 없다. 실제 모델 연결/운영 검증 완료를 뜻하지 않는다.

## 22. 다음 최소 작업

**M3.8B — 기존 로컬 모델과 /api/chat을 경량 코어에 연결하고 실제 고정30을 평가**하는 단계를 제안한다. 현재 요청별 PreparedNarrative에 실제 응답을 연결하고,기존6초/8초/12초·32KiB·생성1회/무재시도를 유지하며 실패대체·실모델metadata·API/UI를 확인해야 한다.
이번에는 해당 Provider·설정 분기·Prompt·모델 실행·공개 API/UI 변경을 구현하지 않았다. 다음 단계를 완료된 것으로 표시하지 않는다.

## 최종 감사 기록

Vault Markdown70개/Wikilink567개(heading15/block1)/source_paths300개/로컬파일링크51개,깨진링크0개. 기존13개노트갱신/신규1개,Bookmarks13개·4그룹/Base1/Canvas1/템플릿5/앱설정8개를보존했다. GUI미확인·최신완료북마크M3.1구버전상태는유지한다.

기준선303개중Architecture1개문서추가외302개SHA256/크기/mtime불변,신규6개. 기존validator/DTO/Provider/API/Frontend/정책·금융·Coverage·Acceptance/Historical·기존tests/GV/BV/release6를보존했다. 이번Provider/LLM/모델API/외부네트워크호출0건이다.

M3.8B는합성전용evaluate_synthetic_narrative의성공metadata를실제모델실적으로재사용하지않아야한다. 실제제공자는하위prepare/parse/assemble을사용하고기존service의실행/검증metadata를거쳐야한다. 실제envelope/256토큰/완료이유·요청별응답연결·성능·의미검증은후속단계미구현이다.
