# M3.3 — 공식 금융상품 스냅샷 검증 및 비교

검증일2026-10-25 KST. 최종 판정: **M3_PRODUCT_CALCULATION_COMPATIBILITY_BLOCKED**.
공식 자료 확인 상품3개, 핵심 계산조건 전체 검증0개, 실제 만기 계산 지원0개.
정보 비교/예산 연결 구현과 전체 M3.3 계산 목표 완료를 구분한다.

## 1. 기존 M3.2 재사용 구조

새 금융 프레임워크 없이 `backend/finance/products.py`에서 기존 `recurring.RecurringSavingsInput`과 `calculate_recurring_savings`를 호출한다.
공식 조건·기간·한도·금리·납입·반올림이 모두 대응할 때만 호출한다. 기존 M3.2 산식·Decimal50·총이자 ROUND_HALF_UP 계약은 변경하지 않았다.

## 2. 수집한 금융회사·상품 목록

IBK기업은행(중소기업은행) 한 기관의 서로 다른3개: IBK중기근로자우대적금, IBK D-DAY적금, IBK모으기통장.
서로 다른 금융회사3개를 수집했다고 주장하지 않는다. 모두 과거 자유적립식 자료다.

## 3. 실제 공식 원문 링크

[공공데이터포털15011687](https://www.data.go.kr/data/15011687/fileData.do)에서 실제 XLSX를 내려받았다.
원문·각 상품 셀·개별 상세/목록 링크·약관 미확보 이력은 `data/financial-products/README.md`에 있다.
상품 상세와 데이터셋/목록 링크를 구분한다. 모으기통장 상세는 미확인이다.

## 4. 확인 기준일

원문2025-12-31(적립식!A1). 포털 등록2026-08-18/수정2026-09-03을 금리 기준일로 대체하지 않는다.
현재2026-10-25 금리로 표시하지 않는다. 다른 날짜의 은행 페이지 수치와 합치지 않는다.

## 5. 수집·확인일

2026-10-25 KST 실제 다운로드/셀 추출/원문 검사. 포털 Quick AI Summary는 근거가 아니다.

## 6. 출처 이용 조건

포털 해당 데이터는 비용무료/이용허락범위 제한 없음. [이용정책](https://www.data.go.kr/ugs/selectPortalPolicyView.do)도 확인했다.
허락 범위의 원문/추출 필드만 저장·표시한다. 타 은행 웹페이지 전문/로고/약관 등에 이 허락을 확장하지 않는다.
금융감독원 한눈에는 조회 시간 초과, 약관/설명서 링크는 도구 오류로 원문 미확보다. 유료 API·대량 수집·로그인/키 발급은 하지 않았다.

## 7. 상품 스냅샷 저장 구조

`data/financial-products/catalog-v1.json` (schema_version=m3.3, dataset_version=IBK-20251231-VERIFIED-20261025-V1),
`sources/ibk-rates-20251231.xlsx`, 출처/조건 검증README. 한 원문에서 독립 상품ID/버전/셀 근거를 보존한다.
Source/ProductSnapshot/RateBand 최소 DTO를 추가했다. 공식 근거 확인·핵심 필드·신규가입 상태·계산 대응·사용자 자격을 분리한다.
없는 값은 null + unknown_fields, 알려진0은0으로 보존한다. 금리는 소수 문자열/Decimal이다.
로더는 중복ID/중복JSON키/필수키/추가키/날짜/기간구간/공식URL/근거 위치/허락/원문SHA256을 검증하고 실패 시503이다.

## 8. 기본·우대금리

| 상품 | 12개월 기본 연% | 우대 포함 최고 연% | 최대 가산%p |
|---|---:|---:|---:|
| IBK중기근로자우대적금 | 2.50 | 4.70 | 2.20 |
| IBK D-DAY적금 | 2.85 | 4.35 | 1.50 |
| IBK모으기통장 | 2.55 | 2.75 | 0.20 |

모두2025-12-31 세전 스냅샷. 기간별 금리를 별도보존하고 우대 충족을 자동 가정하지 않는다.
원문의 우대조건·기간 구간·납입한도는 각 상품 원본 셀과 대응하며 추측으로 최신화하지 않는다.

## 9. 상품별 계산 지원 여부

3개 모두 INFORMATION_ONLY. 계산 호환0개/실제 금액 계산0개. 사용자 자격은 NOT_EVALUATED.
현재 신규가입은 UNCONFIRMED. 문서에 상품이 존재하거나 은행 페이지가 열리는 사실만으로 신규가입을 확정하지 않는다.

## 10. 계산 불가 이유

원문C16/D16/E16은 모두 자유적립. 매월 초 동일 금액 정액 납입 조건과 대응하지 않는다.
단리/고정 계약/일수/반올림 근거 미확인, 현재 가입 상태 미확인, 오래된 자료를 각각 별도 reason_code로 보존한다.
최소/최대/납입단위/기간 불일치도 추가 판정한다. 고객 자격 판정이나 정책3상태를 만들지 않는다.
Assumption:90일 초과는 서비스 재검토 기준. 금융기관의 금리 유효기간이 아니다. 미래 확인일도 계산 보류한다.

## 11. 기존 Python 계산기 재사용

합성 호환 계약 시험에서 기존 함수1회 호출과 기본3%/20만원/12개월→2,439,000원을 확인했다.
우대 최고8%인 합성 응답이어도 기본금리만 사용한다. 이 시험을 실제 상품 계산 증거로 사용하지 않는다.
실제3개 부적합 상품에서 기존 계산기 호출0회를 검증했다. 실제 일수·자유적립을 정액 단리로 대체하지 않는다.

## 12. 상품 비교 API

- GET `/api/financial-products`: 출처/기준일/정보3개/계산 가정 대응0개/확인 상태/재검토 기준.
- POST `/api/financial-products/compare`: profile, optional after_profile, monthly_payment 정수, term_months 정수, product_ids(1~10/중복금지).
- 결과: 상품별 원본정보·선택 기간 기본/최고금리·계산지원·이유·calculation(null 또는 M3.2 결과), 현재/변경 예산.
- 고객이 금리/계산된 상한/지원금/as_of를 덮어쓸 수 없다. 잘못된 입력/ID422, 자료 오류503, 기존 no-store/원문 비반환 오류 계약 유지.
- 금액 순위는 null. 같은 금액·기간·기본금리 계산방식이 검증된2개 이상일 때만 direct_maturity_comparison_supported=true.
- 외부 통신·금융 산식은 라우터에 없다. 현재3개 결과의 금액은 모두null이며0원으로 바꾸지 않는다.

## 13. React 비교 화면

현재 상황 계산 후05단계에서 공식 목록을 불러온다. 기본/우대금리·기간구간·납입한도·출처·기준일·확인일·오래됨·가입 상태 미확인을 표시한다.
체크박스로 선택하고 월 납입/개월을 제출한다. 서버가 준 결과/이유만 표시하며 JS에 이자/월 예산 공식을 복제하지 않는다.
빈칸/형식/선택누락/연결/서버/잘못된JSON/timeout/중복 제출/늦은 응답을 처리한다. 카드/반응형 구조를 재사용했다.

## 14. Cashflow 상한 연결

기존 `service.simulate(profile).cashflow`를 호출한다. 상한 None/0·적자 구분, 초과경고, 입력 납입액 유지, 정책지원금0원.
상한 이내여도 장기 납입 여력/가입을 보장하지 않는다.

## 15. What-if 연결 범위

기존 WhatIf에 선택 콜백만 추가해 원본 결과를 부모에 전달한다. 새 비교 엔진/예산 공식 없음.
상품 비교에 before/after 프로필을 전달하면 기존 adapter를 각각 호출해 선택 월 납입액과 두 상한을 비교한다.
After 수정/초기화/실패/현재 입력 변경 시 이전 연결을 지우고 상품 비교 결과를 무효화한다. 미래 금리 변동을 가정하지 않는다.

## 16. 실제 HTTP 검증

실제 localhost 서버에서 `products-live-http.mts` 통과. 공식3개/실제계산0개, 자유적립식 거부,
D-DAY 40만원 납입 한도초과, 현재상한30만원/변경후50만원, 지원금0원, 잘못된ID422를 확인했다.
기존 savings/comparison/live-http.mts도 통과했다. 네 경로 모두 fetch mock이 없다.
새 API를 반영하기 위해 이전에 실행한 같은 프로젝트의 Uvicorn 프로세스만 확인·갱신했다.

## 17. 실제 브라우저 검증

실제 React 화면에서 공식정보3개·계산가정대응0개, 상품별 출처/기준일/금리/선택과 계산보류 이유를 확인했다.
선택3→2→3, 빈 기간 오류 및 복구를 확인했다. What-if 소득180만원/월세55만원/상한50만원으로 변경한 뒤
선택 납입액40만원이 현재상한30만원은10만원초과, 변경후상한50만원은이내로 표시됐다.
390×844px: 문서 clientWidth375=scrollWidth375, 가로 넘침 없음. 브라우저 오류로그0개.
검증 후 원래 viewport로 복원했다. 실물 휴대폰의 키보드/터치/사용성 시험은 미실행이다.

## 18. 신규 Backend 테스트

신규91 passed/기존warning1. 실제 원문/ID/근거/날짜/Decimal/우대 분리/한도/기간/호환 거부/기존 함수 호출/예산/HTTP/오류를 검증했다.
합성 호환성 테스트와 실제3개 상품의 계산0개를 명시적으로 구분한다. 기존 테스트 기대값 변경 없음.

## 19. 신규 Frontend 테스트

실제 프로젝트에서 신규27개 포함97 passed(기존70개 보존). 출처/기준일/기본·우대/선택/요청 계약/미계산/합성계산응답표시/오류/What-if 연결 검증.
타입검사 `tsc -b` 및 Vite 프로덕션빌드 성공(1.71초). 브라우저가 서버 금액을 표시하는 분기는 합성 계약 응답으로만 시험했으며 실제 상품의 수익 증거가 아니다.

## 20. 전체 회귀 결과

변경 전11,490 passed/1 skipped/1 warning(73.77초).
변경 후 **11,581 passed/1 skipped/1 warning(70.01초)** = 기존11,490 + 신규91.
Frontend **97 passed(10.10초)** = 기존70 + 신규27. 기존 파일의 기대값은 바꾸지 않았다.

실제 실행 명령(루트에서pytest, 화면명령은frontend에서):

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -ra -p no:cacheprovider
pnpm test
pnpm build
node --experimental-strip-types tests/products-live-http.mts
node --experimental-strip-types tests/savings-live-http.mts
node --experimental-strip-types tests/comparison-live-http.mts
node --experimental-strip-types tests/live-http.mts
```

pytest basetemp/TEMP/TMP는 작업 채팅 폴더의tmp를 사용했다. 현재PC에서는 번들 pnpm.cmd 경로를 사용했다.
실제 로그: `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp`의 `m33-pytest-before.txt`, `m33-pytest-new.txt`,
`m33-pytest-after.txt`, `m33-frontend.txt`, `m33-build.txt`, `m33-http.txt`.
임시 로그이므로 장기 제출 증거는 별도로 보존할 필요가 있다.

## 21. 기존 skipped/warning

skip1=실제NTFS 파일symlink 생성 권한 부족. warning1=Starlette/httpx TestClient deprecation. 새 기능으로 승격/수정하지 않는다.

## 22. GV/BV

GV01~GV15/BV01~BV16 및 기존 모든 테스트·fixture SHA256/크기/mtime 불변을 확인했다. 기대값 변경 없음.
기준선258개 중253개 불변. 허용한 연결/문서5개(app.py/App.tsx/WhatIf.tsx/styles.css/ARCHITECTURE.md) 수정과 신규13개만 추가했다.
M3.2 recurring.py/savings.py와 반올림 계약도 불변이다. 감사: 작업폴더tmp/m33-preservation-audit.json.

## 23. Coverage freeze

동결된 generic core 변경 없음. 도메인 코드/로더/Acceptance/Benefit/CrossValidator/Same-call/RawBytes 보호.

## 24. 실제 release SHA256

release6개 모두 SHA256/크기/mtime 불변. 신규 XLSX는 별도 금융data이며 정책release가 아니다.

| release/파일 | SHA256 |
|---|---|
| 2026-10-20-001 / policy JSON | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 |
| 2026-10-20-001 / README | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f |
| 2026-10-20-001 / sources JSON | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b |
| 2026-10-20-002 / policy JSON | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 |
| 2026-10-20-002 / README | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 |
| 2026-10-20-002 / sources JSON | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 |

## 25. 실제 정책 및 지원금0원

실제 안산 DRAFT/CONDITION_SLICE, ResidenceHistory OFFICIAL_INQUIRY_REQUIRED, M2.77 SYNTHETIC_ONLY 유지.
미승인 실제 지원금 반영0원. 전국 청년 대상/안산 첫 검증 지역이라는 기획 유지.

## 26. Obsidian 갱신 결과

실제 Vault `<USER_HOME>\Documents\Obsidian\AI+X-Project`에 기존18개 필요한 절만 갱신하고 신규5개를 추가했다.
M3.3 마일스톤(status=blocked), 공식비교개념(status=partial), 상품별3개 스냅샷(status=partial)이다.
기존 M3.2는 완료 유지, M3.3을 전체완료로 체크하지 않았다. 과거 개발노트는 소급 재작성하지 않고 후속 링크를 추가했다.
Dashboard/현재상태/로드맵/할일/API/React/테스트/미구현/원본바로가기를 연결했다.
Markdown58개, Wikilink344개, source_paths153개, 외부로컬링크15개 검사: **깨진 링크0개**.
기존 앱설정8개/Bookmarks13개4그룹/템플릿5/Bases1/Canvas1은 불변이다.
감사: 작업폴더tmp/m33-vault-audit.json. 북마크 후보만 노트에 표시했다.

## 27. Obsidian 앱 GUI 미확인 사항

Dashboard/Bookmarks/Bases의 앱 렌더링·클릭은 미확인 유지. 커뮤니티 플러그인/Sync/Publish 변경 없음.

## 28. 개인정보·외부 API 사용 범위

경제 입력은 현재 화면과 localhost 요청에만 사용한다. 로그인/DB/영구저장/외부 LLM/은행 전송 없음.
원문 수집은 개발 중 공식 공개자료의 제한된 수동 다운로드/조회. 서비스 실행 중 무허가 수집이나 유료 API 없음.
학기 공동 기획/기존 자산과 개인 추가 개발을 구분한다.

## 29. 최종 판단

**M3_PRODUCT_CALCULATION_COMPATIBILITY_BLOCKED**. 실제 계산에 필수인 자료/정액 조건 대응이 없으므로 COMPLETE를 선택하지 않는다.
공식 정보3개와 실제 계산0개를 공개한다. 과거 원문의 기준일을 오늘로 바꾸거나 합성 상품으로 개수를 채우지 않았다.

## 30. 다음 최소 작업

공식 근거와 이용허락이 확보된 정액적금1개에 대해 납입일·단리·기간·고정금리·일수·원 단위 처리까지 확인하는 작은 검증을 제안한다.
확인 전 실제 금액 계산을 허용하지 않는다. M3.2 변경/실제 일수 계산기 확장은 별도 설계·승인 범위다. 새 기능을 이번에 추가하지 않는다.

### 실행 중 오류와 해결 이력

- 원문 다운로드 첫 클릭의 브라우저 응답 지연 후 다운로드 이벤트/실제 XLSX 경로를 확인했다. 접근 제한을 우회하지 않았다.
- 원문 셀 추출의 기본cp949 출력 오류를 UTF-8로 수정하고 재실행했다. 원문 바이트는 수정하지 않았다.
- 실제 Frontend/빌드는 성공했지만 요약을 터미널에 출력하는 작업용 유틸에서 같은 인코딩 오류로 종료1이 발생했다.
  원본 m33-frontend.txt의97 passed 및 m33-build.txt의빌드성공을 확인했다. 유틸 출력만UTF-8로 수정했으며 테스트를 임의 통과 처리하거나 기대값을 바꾸지 않았다.
- 신규Backend91개/Frontend27개는 최초 실행부터 모두 통과했다. 임시복사본 및 반영된 실제 저장소 시험을 구분해 로그를 남겼다.
- 브라우저 자동화의 After상한 라벨 정확일치 실패는 실제 라벨을 확인해 부분일치 선택으로 해결했다. 제품 계산 결함은 발견하지 않았다.
- 금융감독원/약관 전문 미확보는 데이터 검증 한계로 남겼다. mock을 실제 공식 원문으로 대체 표기하지 않았다.

브라우저 증거: 작업폴더tmp/m33-products-desktop.png 및 m33-products-mobile.png. 입력은 합성 프로필이다.
