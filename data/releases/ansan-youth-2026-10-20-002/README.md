# 2026 Q3 주민등록·생년월일 조건 일부 — DRAFT

Release ID / dataset_version: **ansan-youth-2026-10-20-002**. M1.16K에서 새로 생성한 실제 공식자료 기반 snapshot이다. 경로명 releases는 운영 승인 상태를 뜻하지 않는다. 기존 001 경로가 아닌 미사용 002 경로에 생성했다.

- REAL DATA: 외부·내부 synthetic=false / test_only=false.
- DRAFT / CONDITION_SLICE. **production approved 자료가 아니며 전체 정책 자격·신청·수급을 확정하지 않는다.**
- 명시적으로 선택한 **2026년 3분기 지급대상 조건 일부**다. edition=2026은 모든 분기 구현을 뜻하지 않는다.
- 구현: 신청일의 안산시 주민등록 + Q3 생년월일 2001-07-02~2002-07-01(양끝 포함).
- 트리: ALL(resident, birth), 순서 고정. rule_version=r0002, rule_schema=m1.1, edition_id=2026.
- 미구현: 경기도 최근 연속 3년 OR 합산 10년, 등록분류·국적·귀화 인정기간, 신청창·시각, 자동·소급신청, 서류·대리신청 절차, 지원금·지급 계산, 다른 분기 출생일 조건.
- 분기 자동선택 없음. 현재일·평가일·신청일·연도로 Q3를 선택하지 않는다. 호출자가 이 release의 정확한 경로를 선택한다.
- 실제 사용자 정보·증빙·주민번호·소득·입력·결과를 저장하지 않는다. 테스트 입력은 가상 SELF_REPORTED 사실이다.

## 파일과 이전 release 관계

sources.json과 정규화 PolicyEnvelope JSON을 함께 snapshot한다. 기존 `ansan-youth-2026-10-20-001`은 resident-only / r0001 / 세 d0001 자료로 보존한다. 이 release는 r0002의 두 조건 트리와 세 d0002 확인본을 포함한다. old 파일을 변경하지 않았고 old 테스트도 유지했다.

**d0002는 우리 normalized source metadata/locator 확인본 버전**이다. 같은 공식 문서에 새 birth locator를 추가한 것이며 안산시 공식 공고 자체가 개정됐다는 뜻이 아니다. 기존 resident locator·leaf의 의미와 refs는 보존했다. 공식 대체를 뜻하는 supersedes는 추가하지 않았다.

| 파일 | SHA256 (UTF-8 파일 bytes) |
|---|---|
| sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 |
| policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 |

README 자체 hash를 자기 내용에 포함하지 않는다. 전체 세 파일의 최종 hash는 구현 문서에 기록한다.

## 공식 출처와 확인 범위

2026-10-20에 세 직접 근거를 다시 확인했다.

| source ID | 공식 출처 / Birth 위치 |
|---|---|
| ANSAN-2026-399-HWP | [공고 게시물](https://www.ansan.go.kr/danwongu/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1664308), [첨부 HWP](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP): 신청개요 → 연령기준 및 지급일정 표의 3분기 행 |
| ANSAN-C0001545 | [정책 페이지](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001545): 주요내용 → 2026년 지급일정 및 방법 → 3분기 행 |
| ANSAN-B0238-1681390 | [3분기 안내](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390): 본문 두 번째 문단의 대상 출생일 |

각 문서에 eligibility-birth-date-2026-q3를 추가했다. S1·S2 축약 연도는 S3 전체 연도로 대조했다. 양끝 포함은 대상 구간과 기준일의 정규화 해석이다. 연령 기준일 2026-07-01의 직접 근거는 S1이며 S2·S3가 그 날짜를 별도로 명시한다고 주장하지 않는다.

공고 HWP는 61,952 bytes / SHA256 b0d9f1e9f2de6844157021cab963b2e1dedd49183550036a9777dafa1de78106으로 기존 확인본과 같았다. 원문 전체를 복제하지 않았다. 미확인 쪽번호·S2 게시일·독립 효력 시작/종료일은 null이다. locator VERIFIED가 Envelope DRAFT를 승격시키지는 않는다. 확인일 이후 변경은 재확인이 필요하다.

## 실행·해석

기존 strict SourceRegistry/PolicyEnvelope loader → validate_envelope_sources → 기존 evaluate_policy_tree를 사용한다. 새 actual parser나 엔진 코드는 없다. source bindings는 세 d0002에 고정한다.

PASS의 정확한 의미는 **resident + 2026 Q3 birth implemented condition slice PASS**다. 미구현 거주기간 등이 면제·충족됐다는 뜻이 아니다. PolicyEvaluation 자체에는 coverage가 없으므로 Envelope의 scope/coverage/DRAFT와 함께 해석한다. 일반 display_status만 단독 사용해 전체 정책 결과로 표시하지 않는다.

검증된 engine artifact hash가 없어 실제 DatasetManifest/review JSON을 생성하지 않았다. 파일 hash와 engine_version 호환 표지만으로 실행 빌드 동일성·production acceptance를 보장하지 않는다.

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:TEMP=(Resolve-Path '.\tmp\python-temp').Path
$env:TMP=$env:TEMP
& '.\.venv\Scripts\python.exe' -m pytest tests/test_real_policy_001_q3_birth_slice.py -q
& '.\.venv\Scripts\python.exe' -m pytest -q
```

신규 통합 테스트 **56 passed**, 전체 **2372 passed**. 경계·누락/provenance·ALL 9조합·age 분리·exact-date·근거 역추적·참조 오류·실제/합성 격리·결정적 직렬화·old/synthetic SHA 불변을 확인했다.

상세 기록: `docs/REAL_POLICY_001_Q3_BIRTH_IMPLEMENTATION.md`. 최종 판단: **Q3_BIRTH_SLICE_COMPLETE**. 생년월일 통합 단계는 종료하며 다음 검토 조건은 경기도 연속 3년 OR 합산 10년 거주기간이다.
