# M3.4 — 공식 정액적금 계산 적합성 검증

검증일: 2026-10-25 KST. 최종 판단: **M3_OFFICIAL_SAVINGS_CALCULATION_BLOCKED**.
공식 예시의 수치 재현은 성공했으나 계산 계약은 불일치(C)다. M3.3은 정보 비교/React·FastAPI/What-if 예산 연결의 부분 완료를 유지하고, 실제 상품 계산은0개로 유지한다.

## 1. 대상 은행·상품

IBK기업은행 `정기적금 [정액적금]`. 공식 URL 식별 매개변수 grcd=21, lncd=01, pdcd=0001, tmcd=121.
본문은 정액적립식으로 안내한다. 가입 안내/링크의 존재와 현재 신규가입 절차 검증은 구분한다. 현재 판매·개별 고객 가입 자격은 UNKNOWN이다.

## 2. 공식 상품 URL

[은행 공식 상세](https://mybank.ibk.co.kr/uib/jsp/guest/ntr/ntr70/ntr7010/PNTR701000_i2.jsp?MENU_DIV=GNB&grcd=21&lncd=01&pdcd=0001&tmcd=121).
공개 조회 도구의 페이지 기준일은2026-10-23이며, 이번 조사일은2026-10-25다. 페이지의 날짜를 특정 기간 금리의 최신성 검증으로 대체하지 않는다.

## 3. 상품설명서와 약관

- [정기적금 상품설명서](https://www.ibk.co.kr/fup/customer/form/202609031854581017151883581128.pdf):6쪽 전체를 읽었다.1쪽 기준일2026-09-07, 심의필2026-7136(2026-09-03).2쪽 금리·이자산식·절사,4쪽 휴일만기 규칙을 이미지로도 확인했다.
- [적립식예금약관](https://www.ibk.co.kr/fup/customer/form/2025082212224211645643595611066.pdf):2쪽 전체를 읽었다. 제3조 약정 납입일, 제4조 이자·지연 납입, 제5조 앞당김, 제6조 중도/만기후 이율. 본문 시행일은 UNKNOWN이다.
- [예금거래기본약관](https://www.ibk.co.kr/fup/customer/form/2026040617314631276989664590757.pdf):10쪽 전체를 읽었다. 제7조 예금 성립시점, 제9조 계약 당시 금리 원칙·원 단위·세후 구분, 제22조 개별합의 우선. 본문 시행일은 UNKNOWN이다. 링크 파일명의 개정일과 본문 확인일을 구분한다.

상품 페이지의 실제 다운로드 링크 fullName 경로에서 PDF를 HTTP200으로 직접 확보했다. 웹 조회 도구의 application/octet-stream 처리 실패를 접근 불가로 단정하지 않고 원문을 읽었다.
은행 PDF의 전문 재배포 허락은 UNKNOWN이다. 임시 연구 폴더에서 읽었고, 저장소/Vault에는 URL·위치·최소 사실·SHA256과 검증 결과만 남긴다. 기존 공공데이터 XLSX의 이용허락을 은행 PDF에 확장하지 않는다.

## 4. 공식 금리 출처·기준일

설명서1~2쪽의2026-09-07 기준 세전 기본금리는1~5개월2.15%,6~11개월2.35%,12~23개월2.40%,24~35개월2.50%,36개월2.60%,37~72개월2.60%(3년 후 잔여기간 금리로 변경)이다.
우대금리는 별도 명시되지 않았으며 UNKNOWN이다. ‘우대 없음0%’로 추정하지 않는다.
상품 페이지 상단 최고/기본2.60%는72개월 안내여서12개월 금리로 쓰지 않는다.
공식 금리안내 경로와 상품의 금리보기 링크도 조사했다. 실시간 브라우저는 보안프로그램 설치 안내로 전환되어 설치 없이 중단했다.
**2026-10-25 현재12개월 금리는 검증하지 못했다.** 설명서 기준금리·공식 예시율2.40%와 현재 적용금리를 분리한다. 금융감독원 추가 조회는 위 직접 계약 불일치 판단에 필요하지 않아 이번에 수행하지 않았다.

## 5. 정액적립식 확인

설명서1쪽 상품유형/공식 상세에서 확인했다. 매월 동일 납입이라는 한 조건만으로 계산 적합성을 승인하지 않는다.
가입금액은1만원 이상 원 단위. 최대 월 납입한도는 UNKNOWN이며 무제한으로 대체하지 않는다.
자동이체의 천원 단위는 수동 납입 원 단위와 별도다. 계약기간1~72개월은 확인했지만3년 초과 금리 변동을 전체 고정금리로 바꾸지 않는다.

## 6. 납입 시점

적립식예금약관 제3조/제4조는 매월 약정한 날짜와 각 실제 입금일을 사용한다. 매월1일로 강제하지 않는다.
공식 예시의 첫 회차/마지막 회차 날짜는 UNKNOWN이다. M3.2의 명목 월수 가정을 은행의 실제 달력에 자동 대응시키지 않는다.

## 7. 납입일·휴일 처리

설명서2쪽은 자동이체 지정일이 휴일이면 다음 영업일, 지정한 날짜가 없는 월이면 마지막 영업일로 처리한다.
약관 제4조는 늦은 납입 시 순지연일수에 따른 차감 또는 평균 지연일수만큼 만기 이연을 허용한다. 선납/지연의 구체 달력과 일수 처리 전체를 새로 구현하지 않는다.
설명서3쪽은 만기 이연 후 당초 만기일 해지가 중도해지가 될 수 있음을 안내한다.

## 8. 만기일 계산

개별 최초 만기일 생성 세칙과 예시의 실제 만기일은 UNKNOWN이다. n개월을 더하는 임의 알고리즘으로 채우지 않는다.
설명서4쪽은 휴일 만기의 직전 영업일부터 만기 전일까지 만기해지가 가능하며 이자를 일수로 계산한다고 명시한다.
약관의 지연 납입/만기 이연과 달력 처리도 필요하다. M3.2 입력에는 이 날짜 정보가 없다.

## 9. 이자 계산 공식

설명서2쪽은 각 입금액에 약정 연이율과 실제 예치일수/365를 곱한 이자를 합산한다고 명시한다.
문서의 규칙을 기호로 요약하면 `sum(P_i * r_i * D_i / 365)` 및 총이자 원 미만 절사다. 이는 **문서 요약이며 새 계산기 구현이 아니다**.
입금일부터 만기 전일까지가 계산 기간이다. 원금이자를 다시 원금에 넣는 복리식을 도입하지 않는다.

## 10. 실제 일수 적용

설명서2쪽 분모365와 실제 예치일수를 확인했다. M3.2의 `P*r*n*(n+1)/24`와 입력·계약이 다르다.
윤년 예외/연도별 세부 처리에 대한 별도 문구는 확보한 자료에서 확인하지 못해 UNKNOWN이다. 임의로366 분모로 바꾸지 않는다.

## 11. 반올림 계약

설명서2쪽의 합산 도식과 원 미만 절사 표기를 확인했다. M3.2는 총이자에 `ROUND_HALF_UP`으로 반올림한다. 둘은 동일하지 않다.
회차별 중간 정밀도/중간 절사 여부의 별도 상세는 UNKNOWN이다. ‘회차별 절사가 절대 없다’는 추가 보장으로 확대하지 않는다.
합성 산술 반례: M3.2의10,025원·12개월·2.40%는 반올림 전1,563.9원, 반올림1,564원이다. 같은 값의 절사는1,563원이다. 이는 은행이 실제 지급할 금액의 계산 사례가 아니다.

## 12. 공식 예시와 계산 결과

공식 페이지 상품요약: 월500,000원/12개월/연2.40%/예상 세전이자78,000원. 고객별 납입시점 등의 차이에 따른 변동 안내가 있다.
기존 함수를 그대로 실행하면 원금6,000,000원/반올림 전이자78,000원/세전이자78,000원/원리금합계6,078,000원이다.
공식 페이지가 직접 제시한 비교 대상은 이자78,000원이며, 원리금합계는 우리 함수의 결과임을 구분한다. 예시의 납입·만기 날짜 전제는 UNKNOWN이다.

| 별도 검증 | 결과 |
|---|---|
| 공식 예시 수치 재현 | 성공 · 이자78,000원 |
| 실제 상품 전체 계약과 M3.2 일치 | 불일치 · 실일수/절사 |
| 현재 적용금리 검증 | 미확인 |
| 사용자별 가입·납입 조건 | 미검증 |

## 13. M3.2 함수 호환 여부

판정 **C: 실제 상품의 일수/납입/원 단위 처리 방식이 다르다**. B(예시만 같고 나머지 불확실)보다 강한 불일치 근거를 확보했다.
78000원처럼 소수 부분이 없는 사례 하나가 일치해도 날짜·절사·윤년·휴일·금리 재설정 계약의 동등성을 입증하지 못한다.
M3.2 함수·의미·반올림 계약은 그대로 보존한다.

## 14. 현재 상품 계산 승인 여부

**승인하지 않는다. 실제 계산0개 유지.** 후보 자료는 research 전용이고 서비스용 catalog에 등록하지 않았다.
공식 정보 일부 확인과 현재 판매/사용자 자격/계산 승인은 다르다. 불일치를 모델의 MATCH로 바꾸지 않았다.

## 15. 구현한 API/React

계산 지원 조건 불충족으로 이번에 신규 계산 API/React/상품 페이지를 추가하지 않았다. 기존 M3.3 목록·비교·예산 연결 및 정보3개/실제계산0개를 보존했다.
지시문8에 따라 실제 지원 범위가 확정된 상품용 API/React 테스트도 새로 만들지 않았다. 기존 관련 시험은 전체 회귀에서 실행한다.
추가물은 연구 JSON, 신규 검증 테스트, 이 보고서와 기존 아키텍처의 조사결과 설명이다. 범용 엔진/수집 프레임워크 없음.

## 16. 계산 보류 사유

확인된 불일치: 실제 예치일수/365, 합산 후 원 미만 절사, 휴일·지연·만기 이연,3년 초과 금리 재설정.
남은 UNKNOWN: 예시의 첫/마지막/만기일, 최초 만기일 생성 세칙, 윤년 별도 규정, 중간 정밀도, 최대 월 납입액, 현재금리/가입상태/사용자조건.
Unknown을0/통과/무제한으로 대체하지 않는다.

## 17. 신규 테스트

`tests/test_official_fixed_savings_example.py`:19개 통과. 공식78,000원 재현·네 상태 분리·정액 식별만으로 승인 불가·기준일/금리분리·기간/최소/최대미확인·납입일/윤년UNKNOWN·반올림 반례·일수/절사에 따른 호출차단·근거누락/충돌·기존3개보류를 검증했다.
검증 전용 투영 객체는 서비스Source/상품 등록이 아니며 새 계산 공식을 구현하지 않는다. Cashflow 상한·지원금0원·API 허용범위는 기존 M3.2/M3.3 회귀도 그대로 실행한다.

## 18. 전체 Backend/Frontend 회귀

변경 전11,581 passed/1 skipped/1 warning(68.09초).
변경 후 **11,600 passed/1 skipped/1 warning(71.54초)** = 기존11,581 + 신규19.
Frontend **97 passed(14.59초)**, 타입 검사 및 프로덕션 빌드 성공(2.75초). 화면 테스트를 새로 추가하거나 기존 기대값을 수정하지 않았다.
기존 실제 HTTP4경로(products/savings/comparison/simulate)도 mock 없이 통과했다. 공식 정보3개·실제계산0개·상한/지원금0원 유지.
skip1은 기존 실제 NTFS 파일symlink 생성 권한 부족, warning1은 기존 Starlette/httpx TestClient deprecation이다. 보안 설정/의존성을 이 이유로 바꾸지 않았다.

실행 명령(백엔드는루트, 화면/HTTP는frontend):

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -ra -p no:cacheprovider
pnpm test
pnpm build
node --experimental-strip-types tests/products-live-http.mts
node --experimental-strip-types tests/savings-live-http.mts
node --experimental-strip-types tests/comparison-live-http.mts
node --experimental-strip-types tests/live-http.mts
```

pytest의 basetemp/TEMP/TMP는 작업 폴더tmp로 지정했다. 현재PC의 번들 pnpm.cmd를 사용했다.
실행 로그: 작업 폴더 `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp`의 `m34-pytest-before.txt`, `m34-pytest-new.txt`,
`m34-pytest-after.txt`, `m34-frontend.txt`, `m34-build.txt`, `m34-http.txt`.
임시 경로에 있는 증거의 장기 보존 여부는 별도로 관리한다. 이번 로컬 서비스 UI 브라우저 재시험은 하지 않았으며 제품 코드가 불변인 것과 기존97개 시험/HTTP 실행을 구분한다.

## 19. 실제 정책·지원금0원

실제 안산 정책 DRAFT/CONDITION_SLICE, ResidenceHistory OFFICIAL_INQUIRY_REQUIRED, M2.77 SYNTHETIC_ONLY 유지. 미승인 실제 지원금 반영0원.
전국 청년 대상/안산 첫 검증 지역, 학기 공동 기획·기존 자산과 개인 추가 작업의 구분을 유지한다.

## 20. GV/BV·Coverage freeze·release 불변

모든 backend/frontend 제품 코드·기존 시험/fixture/catalog·계산기/금리/반올림/Policy/Cashflow/Coverage/Acceptance/Benefit/Historical6/Same-call/CrossValidator/RawBytes 불변을 확인했다.
GV01~GV15/BV01~BV16과 release6개의 SHA256/크기/mtime가 모두 기준선과 같다.
기존271개 중270개 불변, 기존 docs/ARCHITECTURE.md 설명1개와 신규3개(연구JSON/검증테스트/보고서)만 추가했다.
전체 release SHA256은 작업 폴더tmp/m34-preservation-audit.json에 정확한 경로별로 기록했다.

## 21. Obsidian 기록

실제 Vault `<USER_HOME>\Documents\Obsidian\AI+X-Project`에 기존15개 필요한 절을 갱신하고 신규3개를 추가했다.
신규 노트는 M3.4 공식 정액적금 검증(blocked), 금융상품 계산 계약(partial), IBK 정기적금 정액 검증(blocked)이다.
M3.2/M3.3/Cashflow/테스트/대시보드와 연결했다. 과거 노트의 당시 미확보 사실은 지우지 않고 이번에 확보한 근거를 후속 절로 추가했다.
Markdown61개/Wikilink382개/source_paths176개/외부로컬링크18개 검사: **깨진 링크0개**.
기존 앱설정8개/Bookmarks13개4그룹/Bases1/Canvas1/템플릿5는 불변이다. 앱 GUI의 북마크·Bases·템플릿 확인 미완료 상태는 유지한다.
커뮤니티 플러그인/Sync/Publish는 추가하지 않았다. 감사: 작업 폴더tmp/m34-vault-audit.json.

## 22. 미해결 근거

현재금리·신규가입은 실시간 절차에서 확인하지 못했다. 은행 사이트 보안프로그램을 설치하거나 설정을 변경하지 않았다.
윤년/중간절사/개별 납입·만기일 세칙과 날짜가 명시된 은행의 계산 사례가 필요하다.
현재 확보한 PDF는 이번 조사 때의 바이트이며, 은행이 같은 URL의 문서를 나중에 바꿀 수 있으므로 해시·확인일로 구분한다.

## 23. 최종 판단

**M3_OFFICIAL_SAVINGS_CALCULATION_BLOCKED**. 공식 예시 재현 성공은 별도로 보존하지만, 문서에서 실제 일수/절사 불일치를 확인했으므로 COMPLETE나 일반 입력 계산 승인을 선택하지 않는다.
M3.3의 부분 완료 상태·최종 판단은 유지한다. 전체 제품 진행률45~50%는 사용자 제공 추정치이며 이번 조사로 검증된 비율이 아니다.

## 24. 다음 최소 작업 하나

**납입 회차별 실제 날짜와 만기일이 명시된 은행 공식 계산 사례1건 확보 및 대조**를 제안한다. 날짜·윤년·절사 세칙을 확인하기 위한 후속 검증이며 이번 미착수다.
외부 문의를 자동 전송하지 않았고, 새 실일수 계산기 구현/기존 M3.2 일반화도 시작하지 않았다.

### 공식 조건과 M3.2의 대조표

아래 UNKNOWN은 원문을 확인한 범위에서 미확인이라는 뜻이다. Source ID는 연구 JSON의 sources에서 URL/기준일/해시와 대응한다.

| 항목 | 확인 상태 | 확인 내용 | 공식 근거 위치 | M3.2 대응 |
|---|---|---|---|---|
| accumulation_method | CONFIRMED | FIXED_MONTHLY | DESCRIPTION · 1쪽 상품유형 | MATCH |
| minimum_monthly_payment | CONFIRMED | 10000 | DESCRIPTION · 1쪽 가입금액 | MATCH |
| maximum_monthly_payment | UNKNOWN | UNKNOWN | DESCRIPTION · 1쪽 가입금액에 최대 월 납입액 미기재 | UNKNOWN |
| manual_payment_step | CONFIRMED | 1 | DESCRIPTION · 1쪽 가입금액 원 단위 | MATCH |
| auto_transfer_step | CONFIRMED | 1000 | DESCRIPTION · 2쪽 자동이체 유의사항 | UNKNOWN |
| contract_months | CONFIRMED | {"min": 1, "max": 72} | DESCRIPTION · 1쪽 계약기간 | MATCH |
| base_rate | CONFIRMED | {"percent": "2.40", "min_months": 12, "max_months": 23, "as_of": "2026-09-07"} | DESCRIPTION · 1쪽 기준일 및2쪽 기본이자율 | UNKNOWN |
| rate_fixing | CONFIRMED | 가입 당시 계약기간별 고시금리; 3년 초과 상품은 3년 후 잔여기간별 금리로 변경 | DESCRIPTION · 2쪽 기본이자율 및 각주 | MISMATCH_FOR_TERMS_OVER_36 |
| agreed_payment_day | CONFIRMED | 매월 약정한 날짜; 매월 1일로 고정하지 않음 | INSTALLMENT-TERMS · 제3조·제4조1항 | UNKNOWN |
| first_installment_date | UNKNOWN | UNKNOWN | PRODUCT-PAGE · 상품요약의 공식 예시에 시작일 미기재 | UNKNOWN |
| last_installment_date | UNKNOWN | UNKNOWN | PRODUCT-PAGE · 상품요약의 공식 예시에 최종 회차 날짜 미기재 | UNKNOWN |
| initial_maturity_date | UNKNOWN | UNKNOWN | DESCRIPTION · 개별 계약상 만기일 산정 세칙 전체 미확인 | UNKNOWN |
| late_payment | CONFIRMED | 지연이율에 따른 차감 또는 순지연일수/계약월수만큼 만기 이연 가능 | INSTALLMENT-TERMS · 제4조3항·4항 | MISMATCH |
| holiday_payment | CONFIRMED | 자동이체는 다음 영업일; 지정한 날이 없는 월은 마지막 영업일 | DESCRIPTION · 2쪽 자동이체 유의사항 | MISMATCH |
| holiday_maturity | CONFIRMED | 직전 영업일부터 만기 전일까지 만기해지 적용 가능; 실제 일수 이자 | DESCRIPTION · 4쪽 계약해지방법 | MISMATCH |
| interest_formula | CONFIRMED | 입금액별 약정연이율×실제 예치일수/365를 합산 | DESCRIPTION · 2쪽 만기이자 산출근거 | MISMATCH |
| day_count_basis | CONFIRMED | ACTUAL_DAYS_DENOMINATOR_365 | DESCRIPTION · 2쪽 만기이자 산출근거 | MISMATCH |
| leap_year_special_rule | UNKNOWN | UNKNOWN | DESCRIPTION · 2쪽은365를 명시하지만 윤년 별도 예외/처리 세칙은 미기재 | UNKNOWN |
| whole_interest_won_treatment | CONFIRMED | SUM_THEN_TRUNCATE_KRW | DESCRIPTION · 2쪽 만기이자 산출근거 및 합산 도식 | MISMATCH |
| installment_intermediate_rounding | UNKNOWN | UNKNOWN | DESCRIPTION · 회차별 중간 정밀도/절사 여부 별도 상세는 미기재 | UNKNOWN |
| tax_basis | CONFIRMED | PRE_TAX | DESCRIPTION · 1쪽 거래조건 기준 및 공식 페이지 예시 | MATCH |
| preferential_rate | UNKNOWN | UNKNOWN | DESCRIPTION · 이 설명서에 별도 우대조건/가산율 미제공;0%로 대체하지 않음 | UNKNOWN |
| current_base_rate | UNKNOWN | UNKNOWN | PRODUCT-PAGE · 실시간 브라우저가 보안프로그램 설치 안내로 전환; 설치하지 않고 중단 | UNKNOWN |
| current_subscription | UNKNOWN | UNKNOWN | PRODUCT-PAGE · 상품안내/가입링크 존재와 신규가입 절차 완료는 구분 | UNKNOWN |
| user_eligibility | UNKNOWN | UNKNOWN | PRODUCT-PAGE · 가입대상 제한없음 표기만으로 고객확인·계약 요건 검증을 대체하지 않음 | UNKNOWN |

### 원문 증거와 실행 이력

- 적립식예금약관: SHA256 `0bb40f25422c84f46de018013d29beaa3b8b10b40e17e7a3b9eaf3abdd7c7576`, 2쪽.
- 예금거래기본약관: SHA256 `262f2afe0ff0643668e95604dc45ada116f8d70829b9d616ad1c9236900d7bd9`, 10쪽.
- 정기적금 상품설명서: SHA256 `264dc55beb91b868feabd903d219061e399fb8248e1477139493cb68fefee087`, 6쪽.

PDF/추출문/렌더링은 작업폴더 `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m34-evidence`에만 있다. 저장소/Vault에 전문을 복제하지 않는다.
신규 시험 최초18통과/1실패는 반올림 전 Decimal 문자열의 소수 끝0 개수(78000.000 vs78000.00)를 과도하게 고정한 시험 오류였다.
신규 시험만 Decimal 금액 비교로 수정하여19개 통과했다. 기존 함수/기대값은 변경하지 않았다.
웹 조회 도구의 PDF/octet-stream 처리 제한은 실제 다운로드로 해결했다. Poppler의 일부 비한글 nameToUnicode 경로 경고가 있었으나2/4쪽 렌더링 결과를 직접 보고 산식/단위/도식을 확인했다.
