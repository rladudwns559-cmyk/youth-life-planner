# 금감원 공시 자료 자동 갱신 (2026-11-11)

예·적금 상품을 매일 자동으로 받아 오는 장치. 출처는 **금융감독원 금융상품통합비교공시(금융상품한눈에) Open API**이고 무료다.

## 무엇을 하나
- `tools/fetch_finlife.py`: 은행(020000)·저축은행(030300)의 정기예금·적금 목록을 모든 페이지에서 받아 `frontend/src/public-data/finlife-disclosures.json`으로 정리한다.
  - 기간별 기본금리·최고금리, 가입 방법·대상·제한, 납입 한도, 우대조건 문구, 공시 시작일.
  - 금리가 없거나 숫자가 아닌 항목은 버리고 `rejected`에 이유를 남긴다. 최고금리가 기본금리보다 낮으면 믿지 않고 비워 둔다. 한도가 비어 있으면 `null`(모름).
  - 계산·순위·추천은 하지 않는다.
- `.github/workflows/finlife-refresh.yml`: 매일 06:10(한국시간) 실행. 자료가 바뀌면 커밋하고 공개 사이트 배포를 시작한다. Actions 탭에서 "Run workflow"로 바로 실행할 수도 있다.
- API 키가 없으면 아무것도 하지 않고 정상 종료한다.

## 직접 확인 자료와의 관계
- 이 자료는 금융회사가 금감원에 **공시한** 값이다. 은행 페이지를 사람이 직접 읽은 `financial-renewals.json`과 섞지 않고 `basis: DISCLOSURE`로 구분한다.
- 현재 화면과 추천 순위에는 아직 연결하지 않았다. 실제 응답을 받아 본 뒤(한도 공란 비율, 상품 수) 화면에 "금감원 공시 기준" 목록으로 붙일지, 만료된 직접 확인 자료를 대신할지 정한다.

## 키 등록 (소유자가 한 번만)
1. https://finlife.fss.or.kr 에서 회원가입 후 "오픈 API" 메뉴에서 인증키를 무료로 발급받는다.
2. GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret
   - Name: `FINLIFE_API_KEY`, Secret: 발급받은 키
3. Actions 탭 → "Refresh FSS disclosure data" → Run workflow 로 첫 실행을 확인한다.

키를 문서·코드·채팅에 적지 않는다.

## 시험
`tests/test_fetch_finlife.py`는 API 응답 형식을 본뜬 **가짜 예시**(`tests/fixtures/finlife/`)로 페이지 넘김, 금리 검증, 오류 코드, 키 없음, 빈 결과를 확인한다. 실제 API로는 아직 시험하지 않았다.
