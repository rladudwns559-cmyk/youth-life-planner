# 지원사업 자동 대조 (재확인)

지원사업은 출처 확인일로부터 7일이 지나면 앱에서 "최신 공고 재확인"으로 바뀝니다.
`tools/support_recheck.py`는 마감되지 않은 사업의 공식 출처 페이지를 열어 다시 대조하고, 통과한 사업만 7일 더 모집 상태를 보여 주게 합니다.
**사람이 공고를 읽은 확인이 아닙니다.** 앱에도 "자동 대조 · 사람이 읽은 확인 아님"으로 표시합니다.

## 통과 조건

출처 페이지 중 하나 이상에서 아래를 모두 만족해야 합니다.

1. 사업명이 보인다. 우리 자료의 이름 그대로이거나, 앞의 지역명("군포", "나주시")을 뺀 이름.
2. 신청기간이 있는 사업(`WINDOW`)은 공고 마감일이 보인다. `2026.11.17`, `11.17`, `11월 17일`, `11/17` 등.
3. 사업명 앞뒤 40자 안에 마감 표시가 없다. `[조기마감]`, `[마감]`, `모집종료`, `접수마감` 등.
   "신청마감일 11.17"처럼 날짜를 설명하는 말과 "예산 소진 시 조기마감" 같은 안내는 마감 표시로 보지 않습니다.

다른 출처 페이지 하나라도 사업명 옆에 마감 표시가 있으면 갱신하지 않습니다(`CLOSED_SIGNAL`).
마감 표시를 찾았다고 자동으로 "마감" 처리하지도 않습니다. 그 사업은 "최신 공고 재확인"으로 남고, 사람이 공고를 보고 판단합니다.

## 실행

```bash
pip install playwright pypdf && python -m playwright install chromium   # 처음 한 번
python tools/support_recheck.py              # 오늘(한국 시간) 기준 대조 → data/support-programs/rechecks/YYYYMMDD.json
python -m backend.opportunities.current_discovery   # 공개 자료(frontend/src/public-data/current-support*.json) 다시 만들기
```

- 사업마다 가장 최근 대조 결과만 반영합니다.
- 통과한 페이지는 출처 맨 앞에 `AUTOMATED_PAGE_MATCH`로, 대조한 날짜와 함께 들어갑니다. 통과하지 못한 다른 출처는 그대로 둡니다.
- 앱의 "자료 확인"일(`updated_on`)은 가장 최근 대조 날짜입니다.
- 효력은 7일입니다. 발표·시연 전 주에 다시 실행하세요.

## 결과 파일 읽기

`results[].status`

| 값 | 뜻 |
|---|---|
| `RENEWED` | 갱신함 |
| `NOT_MATCHED` | 사업명이나 마감일을 찾지 못함, 로그인·차단으로 본문이 비어 있음, 열기 실패 |
| `CLOSED_SIGNAL` | 출처 페이지에 마감 표시가 있음 → 사람이 확인할 목록 |

`results[].pages[]`에 페이지별 판정(`MATCH`, `NO_NAME`, `NO_DATE`, `CLOSED_SIGNAL`, `TOO_SHORT`, `FETCH_FAILED`)과 이유가 남습니다.
