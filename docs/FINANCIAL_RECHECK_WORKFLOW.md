# 공식 금융자료 반복 점검 절차

목적은 금리·납입한도·기간·현재 판매 여부를 공식 근거로 확인하고, 검증된 상품만 추천 상태를 유지하는 것이다. HTTP200·검색 색인·PDF 존재만으로 확인일을 바꾸지 않는다.

## 자료와 경계

- 원본: 기존 `data/financial-products/discovery-extended-20261103.json`과 `verified-basic-rates-extended-20261103.json`은 역사 자료로 보존한다.
- 재확인 원문을 정리한 기록: `data/financial-products/renewals/YYYYMMDD/`. 같은 날·같은 ID의 중복 판단은 컴파일러가 거부한다.
- 새 조회 자료: `frontend/src/public-data/financial-renewals.json`. 제품별 최신 재확인만 싣는다. 이전 재확인 입력은 일자별 파일과 Git 이력으로 재현한다.
- 판매 종료 공지 재확인: `financial-sales-ended.json`. 원래 제외된 상품을 새 종료 건수로 세거나 현재 목록에 되살리지 않는다.
- 은행상품 실제 만기 계산·정책 자격·Cashflow/Coverage/Acceptance/Historical·LLM 검증·시간 제한·release/golden은 변경하지 않는다.

## 1. 접속과 변경 감지

프로젝트 루트에서 기존 Python 환경으로 실행한다.

```powershell
python -m tools.check_financial_sources --catalog data/financial-products/discovery-extended-20261103.json --renewals frontend/src/public-data/financial-renewals.json --output <비공개작업폴더>/source-check.json
```

이전 점검 결과가 있으면 `--previous <이전 결과>`를 추가한다. 공식 허용 호스트의 HTTPS만 조회하고, 최대500 URL·동시3건·요청12초·응답6MiB로 제한한다. 인증서 검증을 우회하지 않는다. 이 단계는 해시·접속 실패 기록만 만들며 데이터·기한·판매 상태를 변경하지 않는다. 은행별 일시 오류를 막무가내 재시도하지 않는다.

## 2. 내용 확인

다음을 상품 ID별로 확인한다.

1. 현재 판매 목록·가입 안내와 정확한 상품/채널 일치.
2. 가입 대상·납입 방식·최소/최대금액·합산한도·납입 단위·계약기간.
3. 기본금리와 조건부 최고금리의 구분, 게시 기준일과 실제 확인일 구분.
4. 판매 종료 공식 공지의 상품명·시행일. 목록 부재·접속 실패는 종료로 단정하지 않음.
5. 회전금리·기존 고객·증빙·특정 연령·거래실적 조건을 충족했다고 가정하지 않음.

정상 조회한 원문이 이전 검증 자료와 동일해도 현재 판매 근거를 별도로 확인한다. 원문과 현재 목록의 금리가 충돌하면 추천을 보류한다. 이전 원문에 접근하지 못했거나 일부 요건만 확인했으면 그 범위를 명시한다. 확인한 사실 없이 확인일만 일괄 치환하지 않는다.

## 3. 날짜별 입력

새 일자 폴더에 다음 구조의 JSON을 만든다. Product와 Source는 기존 strict 모델을 사용한다.

```json
{
  "checked_on": "YYYY-MM-DD",
  "updates": [
    {"product": "기존 ID의 전체 Product 객체", "review": "검증된 rates/sources 또는 null", "sale_status": "CURRENT", "evidence_note": "현재 판매·조건을 확인한 구체적 위치", "change_notes": []}
  ],
  "holds": [
    {"product_id": "기존 ID", "sale_status": "UNCONFIRMED", "reason": "부족한 근거", "sources": []}
  ]
}
```

위 예시의 문자열 설명은 실제 입력에서 객체로 바꾼다. 활성 Source는 실제 재확인 일자와 일치하는 공식 페이지·문서만 사용하며 최소1개 현재 판매 페이지가 필요하다. 과거 Source 날짜는 원본 파일에서 변경하지 않는다. 접속 시도 기록은 `fetch_evidence`로 분리하며 검증된 Source로 위장하지 않는다. DISCONTINUED는 공식 종료 근거가 있어야 한다. 판매 중이어도 추천 보류 사유가 남으면 기존 reference/hold/excluded 상태를 유지한다.

## 4. 생성·검증

```powershell
python -m tools.build_financial_renewals --catalog data/financial-products/discovery-extended-20261103.json --reviews data/financial-products/verified-basic-rates-extended-20261103.json --batch <기존 재확인 배치> --batch <새 재확인 배치> --as-of YYYY-MM-DD --output frontend/src/public-data/financial-renewals.json
python -m pytest -q
```

`--batch`는 여러 번 지정할 수 있다. 동일 ID는 최신 날짜를 선택하며 같은 날 중복 판단은 거부한다. 재확인 기한은 기존7일 계약을 사용한다. 기존 `decision`과 `compile_recommendations`로 비교표와 순서를 생성한다. 브라우저는 준비표를 조회하고 금리·자격을 자체 계산하지 않는다.

`frontend`에서 `pnpm test --maxWorkers=1` 및 `pnpm build`를 수행한다. 기존 11월3일 스냅샷 검증은 재확인 없는 fixture로 분리해 원래 기대값을 보존하고, 새 재확인 자료의 지속 추천·기한 만료·보류·이전 상품 제외는 별도 테스트로 검증한다. 테스트 실패를 숨기려고 기대값·timeout을 임의 변경하지 않는다.

## 5. 공개와 반복

원본 프로젝트·공개 GitHub 복사본·Sites 소스에서 대상 파일을 대조한다. 친구의 디자인 변경이 있으면 보존하고 충돌을 확인한다. 테스트 후 기존 Sites의 audience와 project_id를 유지해 지원되는 소스/저장/배포 도구로 공개한다. 기존 공개 GitHub도 업데이트하고 Obsidian Workflow에 따라 검증·미확인 상태를 기록한다.

금리 정정·판매 종료·접속 실패·검증 실패·배포 실패는 구분해 남긴다. 검증 실패 시 새 자료를 배포하지 않고 기존 버전과 만료 차단을 유지한다. 유료 API/서버, 은행 문의 발송, 로그인/계좌 개설, 보안 설정 변경은 하지 않는다.

반복 점검은 이 채팅의 로컬 예약 실행으로 관리한다. PC가 꺼져 있거나 앱이 실행되지 않으면 점검하지 못한다. 공개 사이트의 백그라운드 서버·실시간 수집·방문자 알림이 생기는 것은 아니다. 의미 있는 변경이나 조치가 필요한 실패가 없으면 동일 상태 보고와 배포를 반복하지 않는다.
