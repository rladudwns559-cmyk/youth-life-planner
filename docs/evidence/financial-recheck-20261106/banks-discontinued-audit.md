# 기존 판매종료 상품의 공식 공지 재확인

2026-11-06 KB국민은행 「수신상품5종판매종료안내」를 직접 HTTP200으로 다시 읽었다. 등록2025-11-20, 시행2025-12-05, 종료 대상 직장인우대적금이다. 기존 제외 ID NOV3-KB-SALARY는 과거 remove-ended.py/finalize-bank-audit.py에서 확인했다. 현재326개 카탈로그에 포함되지 않아 이번에 신규로 종료된 상품으로 세지 않는다.

[공식 종료 공지](https://obank.kbstar.com/quics?articleClass=1&articleId=141870&bbsMode=view&boardId=669&compId=b058334&page=C020721&searchCondition=title&searchStr=&viewPage=9)

기존 은행 재검증 제안 banks-reviewed.json은 변경하지 않았다. timeout/현재 판매 미확인을 판매종료로 표시하지 않았다.
