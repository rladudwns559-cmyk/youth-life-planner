# M3.8D — 문장 후보 준비·정확 일치 검사 구현 및 합성 검증

확인일: **2026-10-26 KST**. **M3_NARRATIVE_CATALOG_CORE_COMPLETE_SYNTHETIC_ONLY**.

[승인된 M3.8C 설계](M3_8C_SEMANTIC_EXPLANATION_CONTRACT_DESIGN.md)의 작은 순수 코어를 구현했다. **새 Provider/실제 모델/API 연결은 하지 않았다.** 신규155시험·고정30의480후보조합·과거응답30건 오프라인 거부를 검증했다. 이전 M3.8B 실제모델 품질 보류와 정형 기본값을 유지한다.

## 1. 실제 변경 범위

신규3개: `backend/explanation/narrative_catalog.py`, `tests/test_narrative_catalog.py`, `tools/evaluate_narrative_catalog.py`. 이 보고서와 [합성 검증 증거](../evidence/m3_8d_synthetic_catalog_evaluation.json)를 추가했다. 기존317파일은 수정하지 않는다. 기존M3.8A 코어/Facts/정형생성기/validator/Provider/Prompt/factory/API/React/계산·판정 엔진/기존tests는 그대로다.

## 2. 공개 코어 입력·출력

| 진입점 | 입력 → 반환 | 책임 |
|---|---|---|
| prepare_catalog | 기존 ExplanationFacts, canonical ExplanationDocument → CatalogPrepared | V1 정합성 검사 후 S1~S6/P1~P6 후보와 요청 snapshot 고정 |
| CatalogPrepared.model_input/model_input_json | 불변 후보 → 새 dict/compact JSON 복사본 | 계약 버전·요약후보·slot별 문장만 노출 |
| catalog_output_schema | CatalogPrepared → 새 schema dict | 기존 schema에 현재 후보 enum만 추가. 전송 등록 없음 |
| parse_catalog | raw str/bytes, 같은 CatalogPrepared → CatalogChecked | 기존 strict parser 후 현재 요청/slot의 exact membership |
| assemble_catalog | 같은 prepared, checked → 기존 ExplanationDocument | binding·membership 재검사 후 기존 조립/validate_output |
| evaluate_synthetic_catalog | Facts/canonical/raw → 기존 NarrativeCoreResult | 예상 계약 실패의 전체 정형 대체, 합성 성공 metadata |

CatalogPrepared/PolicyOptions/CatalogChecked는 frozen dataclass와 tuple을 사용한다. 서버 원본은 기존 V1 JSON snapshot에 보관하며 반환 model_input/schema는 새 복사본이다. 전역 최근요청 캐시나 mutable후보 저장소는 없다. 객체는 신뢰된 서버 내부 준비값이며 문자열만으로 응답 출처를 증명하지 않는다.

## 3. 후보 준비와 의미 범위

요약 우선순위는 저축 상한 설정변경(S1)→단일 예산지표와 여유자금 각각의 방향(S2)→여러 예산항목 변화(S3)→고정순서의 비금융 입력변화(S4)→입력/금액/상태/누락정보 동일(S5)→지원되는 나머지 비교의 중립안내(S6)다. 기존 delta의 부호를 복사하며 차액을 새로 계산하지 않는다.

정책 후보 P1~P6는 Python의 **종합 상태가 같은지/달라졌는지**, 정책/규칙 UNKNOWN과 missing의 전후 표시만 사용한다. 최종 FAIL에도 미확인이 남으면 모든 후보에 확인 문장이 들어간다. 일부만 해소되면 해소 문구를 선택하지 않는다. 비사용 조건을 전체 입력 불변으로 쓰지 않고 개별 규칙이 달라도 같은 최종 상태는 “종합 판정은 같아요”로 한정한다. 전체 자격·공식 증빙 확인을 의미하지 않는다.

상한 None/0/양수는 서로 다르게 보관한다. 모델 문장에는 소득·월세의 금액을 넣지 않으며 미입력을 숫자0으로 바꾸지 않는다. 허용 label만 사용하고 사용자의 지역 원문·정책 ID·reason/source·정형 문장/개인정보를 후보에 삽입하지 않는다.

## 4. 정합성 및 모든 후보 사전 검사

기존 prepare_narrative의 canonical/Facts·정책수·ID·규칙·UNKNOWN 검사를 먼저 실행한다. 추가 표시 정합성 검사에서는 지원입력 allowlist, 기존 delta 방향과 전후 대소관계, 숫자 입력변경 flag, 규칙 input_changed와 전역 변경목록의 대응을 확인한다. UNKNOWN 규칙의 자료가 빠진 경우도 거부한다. 이는 표시 자료의 일관성 검사이며 금액/정책 자격을 재산출하지 않는다.

후보는 필드당1~2개이고 중복/빈 묶음/3개 이상을 허용하지 않는다. 후보의 조합 최대16개를 **기존 parser→기존 조립→기존 validate_output**으로 준비 단계에서 모두 검사한다. 모델 응답이 들어온 뒤에도 strict parse→membership→기존 조립/validator를 다시 실행한다. 기존 검증기를 느슨하게 하지 않았다.

## 5. 정확 일치와 요청 격리

summary는 현재 요청의 summary_options, policy text는 같은 요청의 해당 slot options와 정확히 같아야 한다. JSON key순서·바깥공백·표준escape는 JSON 의미로 읽되 문장 값의 공백 trim/Unicode정규화/부분일치/유사도/문구보정은 하지 않는다. 후보 문장을 조각내거나 추가 이유를 붙이면 거부한다.

검사 객체에는 요청별 binding을 붙이고 조립에서 재확인한다. 다른 요청의 checked객체는 후보가 동일해도 사용할 수 없다. 원시 문자열이 두 요청 모두에 허용된다면 같은 문장은 다시 검사해 통과할 수 있다. 이는 의미가 일치하는 문장의 허용이며 암호학적 출처 증명이 아니다. 실제 전송 연결은 후속 Provider가 요청과 묶어야 한다.

## 6. 실패와 전체 정형 대체

기존 parser가 거부하는 오류는 그 코드/단계/이유를 유지한다. 기존 parser를 통과한 후보 밖 문장은 `TEXT_NOT_IN_REQUEST_CATALOG`(내부진단)/`catalog_membership` 단계/`UNSUPPORTED_NARRATIVE` 이유로 거부한다. 예상 계약오류나 기존 OutputRejected는 canonical 문서 **전체**를 반환하며 일부 정책 문장만 채택하지 않는다.

합성 성공은 validated_test_double, ai_executed=false, ai_success=false다. 실제AI 성공으로 표시하지 않는다. canonical 자체가 손상됐거나 예상밖 내부 RuntimeError가 나면 정상 모델 품질 실패로 숨기지 않는다. 예외/원문/개인입력을 제품로그에 추가하지 않았다.

## 7. 신규155시험

- 고정30의 모든 후보조합, S1~S6와 P1~P6/상태전이9조합, 금액·정책·규칙·UNKNOWN·근거·행동 불변.
- 월세 감소/소득 증가의 분리, 고정·기타지출, 다항목 변화/표시 우선순위, 적자·여유자금0, 상한None/0/양수9조합.
- 미확인 유지/생성/해소/일부해소, 최종FAIL+missing과FAIL유지중미확인해소, UNKNOWN규칙이 있지만 누락label이 없는 자료, 개별규칙변경중종합상태유지.
- 후보 그대로/단일후보/정책0~3개, slot추가·누락/slot바꾸기/문장교차/문구추가·삭제/공백·NFD/숫자·없는문장/중복JSONkey·잘못된UTF8·nonfinite거부.
- 요약60/61·정책40/41codepoints·inner4096/4097bytes, context크기거부와측정경계, 후보수/중복정합성.
- 요청binding·동시요청·mutable호출자/반환값격리, 기존validator호출/거부, 내부오류전파, 경고없이잘못된Facts거부, 반복결정성, socket연결차단상태에서순수코어실행.

신규 최종 **155passed(5.61초)**. 기존 테스트 수정0. 최초148개 통과 후 경계를 보강해156개를 통과했고, 향후 factory등록을 영구 차단하는 임시 구조제한1개는 현재 소스 보존 감사로 확인하도록 정리해 최종155개다. 제품기능실패는 없었다. 테스트 결과를 늘리기 위한 구현복제·실제모델로위장한mock실적을 만들지 않았다.

## 8. 고정30 합성 평가와 과거응답 재생

고정30각각2개요약×정책별2개후보로16개, 총**480조합 통과**. Python 값·최종상태·rules/source·UNKNOWN·next_actions 불일치0. 합성context535~609UTF8bytes. 숫자/정책ID/원문근거는모델용복사본에없다.

M3.8B의 **저장된 실제 원문30개를 오프라인 재생**했다. 기존V1검사통과25개는 새membership에서 거부됐고, 기존금지표현거부5개는 같은기존검사에서거부됐다. 30/30전체정형대체이며사례EX10월세→소득/EX07생활비→정책통과/EX02·03입력불변혼동등을채택하지않았다. 과거원문SHA256은 증거에보관했으며기존파일을수정하지않았다.

이 결과는 **실제모델새30실행이나 의미정확도100%가 아니다.** 서버가 고정한 합성 후보의 조립·원본 불변과 정해진 과거 오류 차단 증거다. 예전 fault label은metadata만남겼고 EX21~30반복입력을새로운공격10개로주장하지않는다. 별도사람의한국어평가/사용자효용실험은미실행이며사용자의M3.8C설계승인과구분한다.

| 사례 | 요약군 | 정책군순서 | 합성조합 | 과거원문 재생 거부 |
|---|---|---|---:|---|
| EX01 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX02 | S4 | P1, P2, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX03 | S4 | P1, P2, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX04 | S5 | P1, P3, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX05 | S4 | P1, P4, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX06 | S4 | P1, P6, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX07 | S2 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX08 | S2 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX09 | S2 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX10 | S2 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX11 | S1 | P1, P1, P3 | 16 | FORBIDDEN_NARRATIVE |
| EX12 | S2 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX13 | S4 | P4, P1, P3 | 16 | FORBIDDEN_NARRATIVE |
| EX14 | S4 | P4, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX15 | S4 | P1, P1, P3 | 16 | FORBIDDEN_NARRATIVE |
| EX16 | S1 | P1, P1, P3 | 16 | FORBIDDEN_NARRATIVE |
| EX17 | S1 | P1, P1, P3 | 16 | FORBIDDEN_NARRATIVE |
| EX18 | S4 | P2, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX19 | S4 | P2, P1, P4 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX20 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX21 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX22 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX23 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX24 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX25 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX26 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX27 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX28 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX29 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |
| EX30 | S5 | P1, P1, P3 | 16 | TEXT_NOT_IN_REQUEST_CATALOG |

## 9. 전체 회귀

Backend **12095passed/1skipped/1warning(77.06초)** = 기존11940 + 신규155. 이번 전체 실행의 실패0. skip은기존NTFS실제파일symlink권한부족, warning은기존Starlette/httpx deprecation이다. M2.77검증완료로승격하지않았다.

Frontend **115passed/5files(9.04초)**, TypeScript검사/Vitebuild성공(Vite1.40초). 기존API·화면코드는불변이다. 실제HTTP/브라우저/Obsidian GUI/새모델실행은이번범위에서수행하지않았으며기존화면에서V2가동작한다고보고하지않는다. 추가변경/실패가없는상태에서회귀를중복실행하지않았다.

## 10. 기존 제한과 연결 경계

기존6초전송/8초서비스/12초UI, request8KiB/envelope32KiB/최대256토큰·자동재시도0은 해당기존코드가불변이다. 새순수코어는context4KiB/inner4KiB/요약60/정책40과0~3개slot/후보1~2개를검사한다. **V2의실제전송request/envelope/시간동작은아직연결·검증하지않았다.** 이번의순수평가를새V2통신검증이라고쓰지않는다.

`narrative_catalog_v2` factory등록0, Provider/Prompt/env변경0, API/UI연결0, 모델호출0/설치0/다운로드0이다. 기존default/legacy/V1동작과M3.8B품질보류판단은유지한다. 후보작성·조건매핑자체의오류나사람이해석을완전방어한다고약속하지않는다.

## 11. 코드·데이터·동결 보존

기준선기존317개전체의SHA256/크기/mtime불변을감사한다. Policy/Cashflow/금융/Coverage/Acceptance/Historical·M3.2반올림·M3.8A검사기·기존테스트/golden/GV01~GV15/BV01~BV16·Coveragefreeze를보존했다. 실제release6개는아래해시를유지한다.

| 파일 | SHA256 |
|---|---|
| `data/releases/ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json` | `9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025` |
| `data/releases/ansan-youth-2026-10-20-001/README.md` | `4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f` |
| `data/releases/ansan-youth-2026-10-20-001/sources.json` | `a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b` |
| `data/releases/ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json` | `d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92` |
| `data/releases/ansan-youth-2026-10-20-002/README.md` | `8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99` |
| `data/releases/ansan-youth-2026-10-20-002/sources.json` | `711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620` |

실제상품만기계산0/검증되지않은실제지원금0원/실제정책DRAFT·CONDITION_SLICE/ResidenceHistory OFFICIAL_INQUIRY_REQUIRED/M2.77SYNTHETIC_ONLY/IBK사용자발송보고·공식회신대기를유지한다. 외부문의/개인정보전송/계좌연결·새플러그인설치0이다.

## 12. Obsidian 기록

기존OBSIDIAN_WORKFLOW에따라M3.8D구현노트와현재개발·대시보드·테스트·계약·남은작업을갱신한다. completed는독립합성코어범위이고실제V2모델연결·운영품질은미검증으로남긴다. 후보의정해진뜻과서버원본보존을구분하고, GUI미확인/구버전최신완료Bookmark M3.1상태는유지한다. 게시후실제링크감사수치를추가한다.

## 13. 재현

기존프로젝트.venv실행기로 `python -B -m pytest -q tests/test_narrative_catalog.py`를실행한다. 합성평가는 `python -B -m tools.evaluate_narrative_catalog --output <별도합성결과경로>`다. 고정30입력과M3.8B저장응답을읽을뿐모델서버는필요없다. 과거실제원문파일을출력대상으로지정하지않는다. 실제개인입력/키/계좌를합성증거에넣지않는다.

## 14. 최종 판단과 다음 최소 작업

**M3_NARRATIVE_CATALOG_CORE_COMPLETE_SYNTHETIC_ONLY**. 후보준비·strict검사·요청/slot정확일치·기존조립/검증기·전체대체와합성검증을완료했다. 실제V2모델의선택성공률·cold성능·한국어유용성·운영승인은미검증이다.

다음최소작업제안하나: **M3.8E — 후보계약의로컬Provider연결및실제고정30검증**. 승인된후기존로컬모델과6/8/12초·원본/UNKNOWN·검증기·실패대체를그대로유지해연결하는범위다. 이번에실행하거나승인된것으로간주하지않는다.


## 15. 게시 후 감사와 Obsidian 결과

기존 repository317개 전체의 SHA256·크기·mtime 불변, 신규 소스/테스트/도구3개와 문서/합성증거2개만 확인했다. 실제 release6개 SHA256·기존 golden/GV/BV/Coverage freeze를 보존했다. 기존 factory에 제안 V2값을 격리된 프로세스 환경으로 조회했을 때 NoProvider임을 확인했고 generate/네트워크는 호출하지 않았다. 이 확인을 미래 확장을 차단하는 영구 테스트로 남기지 않았다.

Obsidian은 기존13노트 갱신/신규1노트, Markdown73/Wikilink652(제목15·블록1)/source_paths384/로컬파일링크71, 깨진링크0이다. Bookmarks13·4그룹/Base1/Canvas1/템플릿5/앱설정은 보존했다. GUI미확인/최신완료Bookmark M3.1구버전상태는그대로다. 설계/합성코어완료와 실모델운영검증을 구분했다.

최종155시험/전체12095·Frontend115·빌드 이후 제품 코드 추가수정0이다. 합성증거에 파일 보존·Vault 감사를 연결했고 실제 모델/Provider/API/UI는 연결하지 않았다. **M3_NARRATIVE_CATALOG_CORE_COMPLETE_SYNTHETIC_ONLY**를 유지한다.
