# 합성 정책 테스트 자료

모든 정책과 사용자는 synthetic/test_only다. 실제 정책명·기관·공식 URL·실제 소득 문턱을 사용하지 않는다. 안산시는 지역 문자열 일치 테스트에만 사용한다. 실제 사용자의 자료를 저장하는 폴더가 아니다.

## SAMPLE-001

테스트 조건: age >= 19, age <= 34, region == "안산시"를 모두 만족한다. 샘플 24세 안산 거주자는 PASS다.

## SAMPLE-002

테스트 조건: employment_status == "unemployed". 샘플은 employed이므로 FAIL이다. 재학 중이면서 취업한 상태가 가능하며 두 필드는 독립적이다.

## SAMPLE-003

테스트 조건: region == "안산시" AND household_income <= 3,000,000. 소득 정의는 synthetic_gross, household, monthly, 2026, KRW다. 이 숫자는 실제 정책 기준이 아니다.

샘플에는 household_income이 없어 UNKNOWN이다. monthly_income=1,500,000이 있어도 대신 사용하지 않는다.
