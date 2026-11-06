# Claude 페이지(Artifact)로 공개 화면 올리기

2026-11-07. 기존 Sites 사이트(`...chatgpt.site`)와 **별개의** 주소를 만드는 방법이다. Sites 게시는 Codex 전용 도구가 필요하고, 이 방법은 Claude 계정만 있으면 된다. 같은 소스(`frontend/`)의 공개 모드 화면을 그대로 올린다.

## 한계 (먼저 읽기)

- **비공개로 시작한다.** 올린 사람과 공유받은 사람만 볼 수 있다. 팀원에게 보이려면 Claude 페이지의 Share 메뉴에서 직접 공유해야 한다. 이 문서에는 주소를 적지 않았다.
- 이 화면은 정적이다. 생활비 계산·What-if·알림은 공개 모드에 없다(원래 한계 그대로).
- 금융 재확인 기한(`valid_until`)이 지나면 추천이 비는 것도 똑같다. 자료를 갱신했으면 **다시 빌드해서 같은 주소에 다시 게시**해야 한다.
- Artifact는 주소창에 `#/savings` 같은 경로를 반영하지 못한다고 알려져 있다. 화면 안에서 메뉴로 이동하는 것은 되지만, 특정 화면을 가리키는 링크는 만들 수 없다.
- Artifact 실행 환경(보안 정책)에서 이 앱이 완전히 작동하는지는 게시자가 첫 게시 후 직접 확인해야 한다. 기본 화면·입력·추천을 눈으로 확인한다.

## 만들기

```powershell
# 저장소 루트. frontend\node_modules 가 설치돼 있어야 함 (corepack pnpm install --frozen-lockfile)
powershell -ExecutionPolicy Bypass -File tools\build_artifact_package.ps1 -OutDir $env:TEMP\youth-life-artifact
```

스크립트는 공개 모드(`VITE_PUBLIC_BACKEND_PENDING=true`)로 상대 경로(`--base=./`) 빌드를 하고, Artifact용 첫 페이지 `page.html`(문서 틀 없는 조각)을 만든다. 출력의 파일 목록(`assets/…`, `favicon.svg`)과 크기(약 8MB, 한도 16MB)를 확인한다. 저장소의 `frontend/dist`는 건드리지 않는다.

## 올리기 (Claude)

Claude Code에서 Artifact 도구로 `page.html`을 게시하고, 스크립트가 출력한 파일들을 `files`로 함께 올린다(`root`는 `-OutDir`). 첫 게시에는 아이콘(예: `chart`)과 한 문장 설명이 필요하다. 같은 파일 경로로 다시 게시하면 주소가 유지된다.

## 알려진 함정

- 스크립트는 한글 제목을 숫자 코드로 만든다. Windows PowerShell 5.1은 BOM 없는 `.ps1`을 ANSI로 읽어서 한글을 직접 쓰면 제목이 깨진다. 스크립트를 고칠 때 한글 리터럴을 넣지 말고, 넣는다면 파일을 UTF-8 BOM으로 저장한다.
- Artifact는 `<title>`을 이름(2~4단어)으로 쓰라고 한다. 앱의 원래 제목 "청년 경제생활 | 내 조건에 맞는 지원과 저축"은 설명이 붙은 형태라 `청년 경제생활`로 줄였다.
- `/asset-programs-public.json`처럼 절대 경로로 요청하는 코드가 앱에 있으나, 공개 화면 경로(홈·지원사업·상품 찾기·이용 안내)에서는 쓰이지 않는다.
