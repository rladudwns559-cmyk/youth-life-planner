# 11월 심사 기간 주간 재확인·배포 계획

2026-11-07 작성. 목적은 심사 기간(11월 말까지) 내내 공개 사이트의 금융 추천이 비지 않게 하는 것이다. 기존 7일 기한 계약과 [반복 점검 절차](FINANCIAL_RECHECK_WORKFLOW.md)를 그대로 따른다. 기한을 늘리거나 날짜만 바꾸는 방법은 쓰지 않는다.

## 왜 필요한가

- 재확인 기록은 확인일 + 7일까지 유효하다. 화면은 기한 다음 날부터 그 상품을 추천하지 않는다(`financial-snapshots.ts`의 `asOf > valid_until`).
- 2026-11-07 기준 재확인 123개 중 **추천 화면에 실제로 나올 수 있는 상품은 50개**(11개 은행)이고, 50개 모두 기한이 **2026-11-13**이다. 11/14부터는 다시 확인한 상품만 추천에 남는다.
- 나머지 73개(납입 상한 UNKNOWN 등)는 재확인해도 추천 후보가 아니다. 주간 재확인은 이 50개를 우선한다.
- 공개 사이트는 정적 빌드다. 재확인 자료는 빌드에 포함되므로 **재확인할 때마다 다시 빌드하고 Sites에 배포해야** 화면에 반영된다. GitHub push만으로는 바뀌지 않는다.

## 2026-11-09 진행 상황

추천 상위에 오르는 15개 상품(페퍼·카카오·모아·부림·KB)을 읽어 기한을 **11/16**으로 늘렸다([기록](FINANCIAL_RECHECK_20261109.md)). 나머지 35개(케이뱅크 3개 포함)는 11/13~11/14에 만료된다. 아래 일정의 1회차(11/12)는 케이뱅크·부산·경남 상품을 우선한다. 4번 명령의 `--batch` 목록에는 `renewals/20261109/kb-reviewed.json`과 `priority-reviewed.json`도 넣는다.

## 일정 (권장)

| 회차 | 재확인·배포 권장일 | 늦어도 | 새 기한 | 이어지는 기간 |
| --- | --- | --- | --- | --- |
| 1 | 11/12(목) | 11/13 배포 완료 | 11/19~11/20 | 11/14~11/20 |
| 2 | 11/19(목) | 11/20 배포 완료 | 11/26~11/27 | 11/21~11/27 |
| 3 | 11/26(목) | 11/27 배포 완료 | 12/3~12/4 | 11/28~12/4 (심사 종료까지) |

하루 여유를 둔 이유: 은행 페이지 접속 실패나 금리 충돌로 보류가 생기면 다시 확인할 시간이 필요하다. 심사 날짜가 정해지면 그날이 기한 안에 들어가는지 이 표로 다시 확인한다.

## 회차별 순서

1. 대상 목록 뽑기 (저장소 루트)

   ```powershell
   python -m tools.list_recommendable_products
   ```

   은행별 체크리스트(Markdown)가 나온다. 이 도구는 읽기 전용이며 자료를 바꾸지 않는다.

2. 공식 페이지 확인: 상품마다 현재 판매 경로, 가입 대상, 납입 한도·기간, **기본금리**(우대 제외), 공시 기준일을 원문과 대조한다. 금리가 바뀌면 `change_notes`에 이전→현재를 적는다. 접속 실패·내용 충돌은 hold로 남기고 과거 금리로 되돌리지 않는다.
3. 새 날짜 폴더에 배치 작성: `data/financial-products/renewals/YYYYMMDD/` (기존 폴더는 수정하지 않음).
4. 공개 자료 생성: 기존 배치 전부 + 새 배치를 `--batch`로 넣고 `--as-of`를 확인일로 한다.

   ```powershell
   python -m tools.build_financial_renewals --catalog data/financial-products/discovery-extended-20261103.json --reviews data/financial-products/verified-basic-rates-extended-20261103.json --batch data/financial-products/renewals/20261106/banks-reviewed.json --batch data/financial-products/renewals/20261106/regional-reviewed.json --batch data/financial-products/renewals/20261106/savings-hanwha-reviewed.json --batch data/financial-products/renewals/20261106/savings-reviewed.json --batch data/financial-products/renewals/20261107/savings-banks-reviewed.json --batch data/financial-products/renewals/<새날짜>/<새파일>.json --as-of <새날짜> --output frontend/src/public-data/financial-renewals.json
   ```

5. 검증: Backend `pytest`, Frontend `vitest --maxWorkers=1`, `tsc -b`, 공개 모드 `vite build`. 실패하면 배포하지 않는다(기존 버전과 만료 차단 유지).
6. 화면 확인: `/#/savings`에서 예금 6개월·1천만원, 적금 월 30만원·12개월을 입력해 추천 카드와 "가장 가까운 재검토 기한"을 본다.
7. 배포: 사용자가 기존 Sites 프로젝트에 공개 모드 빌드를 게시한다(배포 권한은 사용자에게 있음). 배포 후 공개 URL에서 6번을 다시 확인한다.
8. 기록: `docs/FINANCIAL_RECHECK_<날짜>.md`에 범위·변경·보류·실행한 시험 결과를 남긴다.

## 정책 통장 10개 (2026-11-08 추가)

금융 상품과 별개로 `data/asset-programs`의 정책 통장(청년미래적금 등)도 7일 기한을 쓴다. 확인일이 7일을 넘으면 화면이 "최신 공고 재확인 필요"로 바꾸고, 날짜별 상태 표는 **45일치만** 들어 있어 표 범위(2026-12-23)를 벗어나면 모집 중 표시가 사라진다. 회차마다:

1. 원문 변경 점검 (읽기만 하고 카탈로그를 바꾸지 않는다):

   ```powershell
   python -m tools.check_asset_program_sources --output <새 점검 결과 파일>
   ```

2. 바뀐 출처는 **사람이 원문을 읽고** 일정·조건이 카탈로그와 맞는지 대조한다. 해시가 같거나 달라진 것만으로 확인일을 올리지 않는다. 읽은 출처만 `data/asset-programs/verification-<날짜>.json`에 근거와 함께 적는다.
3. 공개 자료 재생성(화면은 이 파일을 읽는다):

   ```powershell
   python -m tools.build_asset_programs_public --start <오늘> --days 45 --verification data/asset-programs/verification-20261108.json --verification data/asset-programs/verification-20261109.json --verification data/asset-programs/verification-<날짜>.json --source-check <새 점검 결과 파일> --rates data/asset-programs/rates-<날짜>.json
   ```

   `--rates`에는 **그날 출처를 읽고 확인한** 금리만 넣는다. 그날 읽지 않은 출처의 금리는 빌더가 거부한다(`RATE_SOURCE_NOT_VERIFIED_ON_CHECK_DATE`). 새 회차에 청년미래적금 보도자료를 다시 읽지 않았다면 `--rates`를 빼면 금리 상자가 사라진다. 이것이 의도된 동작이다(낡은 금리를 현재처럼 보이지 않기 위함).
4. `pytest`(`tests/test_build_asset_programs_public.py`가 커밋된 JSON이 입력 파일로 재생성한 결과와 같은지 검사)와 프런트엔드 시험·빌드를 돌린다.

## 실행 주체

로컬 Codex의 매일 09:00 점검과 이 계획이 같은 `financial-renewals.json`을 수정할 수 있다. **한 회차는 한 주체만** 수행한다. 어느 쪽이 할지 사용자가 정한다.

## 하지 않는 것

- 기한 연장, 확인 없이 날짜 갱신, 과거 금리 복원.
- 상한 UNKNOWN 상품을 추천에 넣기 위해 `UNLIMITED`로 바꾸기(공식 "한도 없음" 문구가 있을 때만 근거로 반영).
- 유료 서버·API·자동 배포 서비스 신청.
