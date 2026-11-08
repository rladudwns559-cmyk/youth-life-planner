# M3.8E — 로컬 후보 Provider 연결 및 실제 고정30 검증

확인일: **2026-10-26 KST**. 최종 판단: **M3_LOCAL_CANDIDATE_LLM_VERIFIED**.

판단 범위는 **설치된 로컬 모델·합성 고정30·후보 정확 일치·기존 검사기·실제 로컬 API/화면 연결**이다. 실제30은30채택/0대체, Python원본불변30/30, warm p50 1.63초/p95 1.74초였다. 별도cold와모델재시작뒤화면cold는모두TIMEOUT→전체정형대체했다. **사람의 설명 유용성/사용자 이해도·실제 정책/상품·운영 일반화는 검증하지 않았다.** 기본설정은시험후NoProvider로복귀했다.

## 1. M3.8D 재사용 구조

[M3.8D 보고](M3_8D_NARRATIVE_CATALOG_CORE.md)의 prepare_catalog/model_input/catalog_output_schema/parse_catalog/assemble_catalog를 수정없이 재사용했다. 기존 로컬 전송/strict envelope를 상속한 OllamaCatalogProvider만 추가했다. 모델은 기존 summary/policy_texts 문장 JSON을 반환하고 현재 요청·정책slot의 후보와 정확히 맞아야 한다. 후보 ID선택·유사도·repair·정책별부분대체로 계약을 바꾸지 않았다.

## 2. 확인한 실행 환경

Windows11Home64/10.0.26300, AMD Ryzen7 260 8C/16T, 사용가능총RAM16052788KiB(약15.31GiB), RTX5050Laptop8151MiB, 드라이버572.97, Python3.12.14를 직접 확인했다. 확인시 C드라이브여유364188499968bytes(약339.18GiB), VRAM사용0MiB/모델서버미실행이었다. 고정30평가는 전체회귀가 끝난 뒤 실행했다. native CUDA호환성확인 경고는있었지만 실제GPU에37/37layer offload와생성완료를확인했다. 드라이버/보안설정은변경하지않았다.

## 3. Provider·모델·라이선스와 승인

Ollama **0.40.11**, `qwen3:4b-instruct-2507-q4_K_M`, GGUF4.0B/Q4_K_M, manifest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`를 기존 설치에서 확인했다. 기존ZIP/config/모든layerSHA256을검증하고설치목록과server version도대조했다. 모델 license layer의Apache2.0과M3.7의공식라이선스기록을재사용했다. [모델공식license](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/main/LICENSE), [Ollama MIT](https://raw.githubusercontent.com/ollama/ollama/v0.40.11/LICENSE). 새모델·다운로드·설치·유료API·외부전송0, 추가승인필요작업0이다. 바이너리를재배포하지않았다.

## 4. 실제 연결 API와 설정

고정 `http://127.0.0.1:11434/api/chat`, stream=false, format=현재후보enum schema, temperature0/num_predict256/num_ctx16384/truncate=false/shift=false다. ProxyHandler({})·redirect거부·모델일치/done/stop/remote/thinking/tools/images/metrics 검사는 기존 M3.8B 전송을 그대로 상속했다. 브라우저는 기존 FastAPI `/api/synthetic/explain`만 호출한다.

서버opt-in은 `AIX_EXPLANATION_PROVIDER=ollama_local`, `AIX_OLLAMA_MODEL=qwen3:4b-instruct-2507-q4_K_M`, `AIX_EXPLANATION_CONTRACT=narrative_catalog_v2`다. 미설정NoProvider/legacy/V1/알수없는계약의거부동작을보존했다. 실제시험env는프로세스단위이며영구설정0이다.

## 5. 입력 Projection과 출력 계약

실제30에서context535~609UTF8bytes, system/enum포함전체요청2053~2201bytes, 실제envelope672~707bytes였다. 정확금액·개인입력·정책/규칙ID·reason/source경로·전체정형문서는모델에보내지않았다. 모델에는서버가의미를정한각필드의후보2개만제공했다. 문장JSON은summary와정확히p01~p03이며각항목의후보문장을그대로반환했다. 모든raw envelope/문장/옵션선택번호(평가metadata만)를 [증거JSON](../evidence/m3_8e_actual_candidate_evaluation.json)에보관했다.

## 6. 검사·조립·Fallback

Python확정결과→불변후보준비→실제로컬Provider1회→기존strict envelope→M3.8D parse_catalog/exact membership→assemble_catalog→기존validate_output→기존서비스validator/API/화면이다. 후보밖문장·slot오류·금액/상태/UNKNOWN조작·JSON/크기/HTTP/연결/timeout은전체canonical대체다. 기존코어/validator수정0, 자동재시도/외부Provider/legacy추가호출0이다. 제품Provider에는요청/응답원문로그를추가하지않았다.

## 7. 실제 고정30 평가 방법

기존EX01~EX30입력을정확히재사용했고fault라벨은metadata만남겼다. mock/fault주입0이다. 같은Python결과로정형문서와실제후보선택문서를대조했다. raw수신/JSON구조/slot/정확일치/최종validator/원본보존/지연/사람미검토를각사례에기록했다. 고정30batch1회/Prompt·옵션변경0이며실패를숨기려고재평가하지않았다.

## 8. 실제30 결과

**실제30요청/완료원문30/구조·slot·후보정확일치·기존검증통과30/채택30/정형대체0**. 관측된상태·금액·UNKNOWN/rules/source/next_actions변경0, 후보밖추가정보0이다. 이채택률100%는후보선택성공률이며사람이판단한설명유용성비율이아니다. 아래문장평가는Codex대조검토이고사람검토는각행NOT_PERFORMED/비율null이다.

| ID | 전체ms | 요청/context bytes | 요약군 | 경로/후보 | Codex 의미·유용성 검토 |
|---|---:|---:|---|---|---|
| EX01 | 1728.40 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX02 | 1593.73 | 2061 / 539 | S4 | 채택/일치 | 변경된 입력 이름만 안내하고 정책 종합 판정과 입력 불변을 혼동하지 않았다. 구체적 상태 방향·이유는 기존 Python 상세를 읽어야 한다. |
| EX03 | 1537.29 | 2061 / 539 | S4 | 채택/일치 | 변경된 입력 이름만 안내하고 정책 종합 판정과 입력 불변을 혼동하지 않았다. 구체적 상태 방향·이유는 기존 Python 상세를 읽어야 한다. |
| EX04 | 1734.69 | 2185 / 601 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX05 | 1701.35 | 2165 / 591 | S4 | 채택/일치 | 변경된 입력 이름만 안내하고 정책 종합 판정과 입력 불변을 혼동하지 않았다. 구체적 상태 방향·이유는 기존 Python 상세를 읽어야 한다. |
| EX06 | 1816.71 | 2201 / 609 | S4 | 채택/일치 | 변경된 입력 이름만 안내하고 정책 종합 판정과 입력 불변을 혼동하지 않았다. 구체적 상태 방향·이유는 기존 Python 상세를 읽어야 한다. 미확인 해소는 해당 정책의 표시만 가리키며 다른 정책의 UNKNOWN을 지우지 않았다. |
| EX07 | 1735.12 | 2099 / 558 | S2 | 채택/일치 | 명시된 예산 지표와 여유자금의 방향이 Python 결과와 맞는다. 소득/월세 치환이나 정책 통과 인과를 추가하지 않았다. |
| EX08 | 1737.93 | 2099 / 558 | S2 | 채택/일치 | 명시된 예산 지표와 여유자금의 방향이 Python 결과와 맞는다. 소득/월세 치환이나 정책 통과 인과를 추가하지 않았다. |
| EX09 | 1645.73 | 2087 / 552 | S2 | 채택/일치 | 명시된 예산 지표와 여유자금의 방향이 Python 결과와 맞는다. 소득/월세 치환이나 정책 통과 인과를 추가하지 않았다. |
| EX10 | 1700.92 | 2087 / 552 | S2 | 채택/일치 | 명시된 예산 지표와 여유자금의 방향이 Python 결과와 맞는다. 소득/월세 치환이나 정책 통과 인과를 추가하지 않았다. |
| EX11 | 1579.19 | 2079 / 548 | S1 | 채택/일치 | 상한 설정 변경만 안내한다. 미입력과 영의 숫자 비교를 만들지 않았다. 구체적인 차이는 Python 숫자 행과 가정에 의존한다. |
| EX12 | 1685.24 | 2099 / 558 | S2 | 채택/일치 | 명시된 예산 지표와 여유자금의 방향이 Python 결과와 맞는다. 소득/월세 치환이나 정책 통과 인과를 추가하지 않았다. |
| EX13 | 1739.48 | 2157 / 587 | S4 | 채택/일치 | 변경된 입력 이름만 안내하고 정책 종합 판정과 입력 불변을 혼동하지 않았다. 구체적 상태 방향·이유는 기존 Python 상세를 읽어야 한다. |
| EX14 | 1652.64 | 2169 / 593 | S4 | 채택/일치 | 변경된 입력 이름만 안내하고 정책 종합 판정과 입력 불변을 혼동하지 않았다. 구체적 상태 방향·이유는 기존 Python 상세를 읽어야 한다. |
| EX15 | 1654.52 | 2053 / 535 | S4 | 채택/일치 | 변경된 입력 이름만 안내하고 정책 종합 판정과 입력 불변을 혼동하지 않았다. 구체적 상태 방향·이유는 기존 Python 상세를 읽어야 한다. |
| EX16 | 1619.14 | 2079 / 548 | S1 | 채택/일치 | 상한 설정 변경만 안내한다. 미입력과 영의 숫자 비교를 만들지 않았다. 구체적인 차이는 Python 숫자 행과 가정에 의존한다. |
| EX17 | 1619.84 | 2079 / 548 | S1 | 채택/일치 | 상한 설정 변경만 안내한다. 미입력과 영의 숫자 비교를 만들지 않았다. 구체적인 차이는 Python 숫자 행과 가정에 의존한다. |
| EX18 | 1653.73 | 2053 / 535 | S4 | 채택/일치 | 변경된 입력 이름만 안내하고 정책 종합 판정과 입력 불변을 혼동하지 않았다. 구체적 상태 방향·이유는 기존 Python 상세를 읽어야 한다. |
| EX19 | 1683.19 | 2071 / 544 | S4 | 채택/일치 | 변경된 입력 이름만 안내하고 정책 종합 판정과 입력 불변을 혼동하지 않았다. 구체적 상태 방향·이유는 기존 Python 상세를 읽어야 한다. FAIL 정책에도 추가 확인 문장이 남아 있다. |
| EX20 | 1617.95 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX21 | 1565.03 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX22 | 1602.76 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX23 | 1591.87 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX24 | 1636.02 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX25 | 1591.10 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX26 | 1582.28 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX27 | 1585.97 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX28 | 1616.89 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX29 | 1550.36 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |
| EX30 | 1610.01 | 2075 / 546 | S5 | 채택/일치 | 입력 불변과 비교 결과 동일을 안내한다. 정책별 미확인은 해당 슬롯에 남아 있으며 전역 UNKNOWN으로 단정하지 않았다. 반복 문장의 추가 효용은 미평가다. |

## 9. 의미적 품질·정형 설명 비교

Codex가실제30문장을입력·Python결과·정형문서와대조한범위에서중대한모순을발견하지못했다. EX10은월세감소와여유자금증가를각각정확히말했고소득증가로치환하지않았다. EX07은정책통과의원인을생활비소득으로만들지않았고, EX02/03은종합판정유지와취업입력불변을혼동하지않았다. EX06의미확인해소는해당정책표시범위이고EX19FAIL에는미확인이남았다.

다만S2예산방향5건외S1설정안내3/S4입력명안내9/S5동일결과13건은추가정보가적다. 종합판정/미확인문구는반복되고구체적원인·숫자·상태방향은기존Python화면을읽어야한다. “미확인표시해소”를공식증빙심사완료로오해하는지사람검토가필요하다. **더유용하다/더자연스럽다/이해도가향상됐다거나도움된비율을주장하지않는다.** 수정이필요하면후보계약을별도로개정하며이번후보문구는바꾸지않았다.

## 10. Warm 지연과 실용성

고정30전체평균**1645.64ms**, p50**1627.93ms**, p95 nearest-rank(29/30)**1739.48ms**. warm전송timeout0/서비스deadline0/fallback0이다. 모든표본이채택돼정상채택평균도같다. 반복입력·prompt cache가있으며독립30명의사용자/기기·동시부하·cold성능으로일반화하지않는다. 기존27/30warm목표는초기제안이었고이번관측30/30은그보다높았지만사용자유용성목표는아니다.

## 11. Cold 로딩 영향

별도첫cold요청은client6061.03ms/전송6024.22ms에TIMEOUT으로전체정형대체했다. raw최종응답/load_duration은수집하지못했다. native log의llama-server started in은4.07초이고화면cold재시작에서는3.79~3.80초였다. 이는runner시작관측이며순수weight읽기시간이나첫완성응답시간이아니다. 첫생성의로드+prompt처리+출력이기존6초안에끝난다고보장하지않는다.

고정30의warm결과에서cold실패를삭제하지않고별도보관했다. 모델종료→실제offlineUI검증→같은서버재시작→coldUI검증은명시적인별도시험이다. 두cold모두정형대체가작동했고제한을늘려통과시키지않았다. 모델size/생성옵션최적화나설정별재평가는하지않았다.

## 12. 실제 API

FastAPI에EX02/EX19를AI모드각1회/정형모드각1회로비교했다. AI는각1747.63/1593.71ms에llm채택, 정형은25.83/21.02ms에모델0회로반환했다. 네응답모두HTTP200/no-store/원본값·UNKNOWN·근거·행동불변이었다. 상세정형문서와선택문서둘을증거에남겼다. UI시험후NoProvider기본설정으로복귀하고기존products/savings/comparison/explanation/main 실제HTTP5경로도통과했다.

## 13. 실제 React·390px·늦은 응답

별도합성탭390×844에서UI01모델설명채택/로딩버튼disabled/Python숫자/정책상태/UNKNOWN을확인했다. UI02는이번모델을종료한뒤PROVIDER_UNAVAILABLE→정형, UI03은재시작cold의TIMEOUT→정형을확인했다. UI04는요청중월세입력을550000→600000으로바꾸었고native모델완료뒤에도이전설명이재표시되지않았다. 해당취소응답의최종문장은미수집이므로AI채택으로세지않는다.

스크린샷은 `<USER_HOME>\Documents\ChatGPT\AI+X채팅\output\m3.8e`의 browser-accepted/unknown/offline/timeout/stale-cleared-390.png다. UI실제rawHTTP본문/지연을모두수집한것은아니며화면관측과APIJSON증거를구분한다. 12초UIabort는기존코드/Frontend시험으로보존했고이번실제UI timeout은6초전송실패의서비스응답이다. 시험탭을닫고viewport를reset해원래탭은보존했다.

## 14. 호출 계수

**Provider요청37회 = 별도cold1 + 고정30 + 실제HTTP AI2 + UI요청4**. native new-prompt task는첫session34/재시작session2로총36개이며offline1은서버미도달이다. 관측채택33개(고정30+HTTP2+UI1),TIMEOUT정형2/연결실패정형1/취소후미표시1이다. 메타데이터GET·정형HTTP2·NoProvider회귀·mock시험은실제생성에합산하지않는다. 고정30수용률과전체시험표본을혼합하지않았다. 기존M3.7/M3.8B실적과도분리한다.

## 15. 자원 관측

warm후유휴스냅샷GPU사용4974MiB/8151MiB·사용률0%, runnerWorkingSet1163919360bytes/해당프로세스PeakWorkingSet1214160896bytes를확인했다. GPU값은전체GPU사용량이고실행전체최고치나모델단독사용량이아니다. RAM·VRAM을합산하지않았다. CUDA호환성경고를이유로새드라이버를설치하지않았고37/37layer offload/실제30성공을실측근거로남겼다.

## 16. 신규 연결 시험

신규**67passed(3.29초)**는전송모의시험이다. 고정30/service/원본불변, enum·최소입력/요청8KiB,후보밖문장·slot·공백·UNKNOWN부정·금액추가거부,strict envelope/JSON/32KiB,HTTP/offline/timeout·내부오류/자동재시도없음,기존validator호출/실패,동시요청격리,factory/legacy/V1보존을검증했다. 실제모델실적으로67회를더하지않는다. 기존테스트/fixture수정0이다.

## 17. 전체 회귀·최초 실패 이력

Backend **12162passed/1skipped/1warning(97.78초)** = 기존12095+신규67. Frontend**115passed(10.04초)**, TypeScript/Vite빌드성공(Vite2.09초). 신규/전체실행최초실패0,최종소스후추가수정0이다. skip은기존NTFS file symlink권한부족,warning은기존Starlette/httpx deprecation이다. 실제NTFS필수증거가새로확보된것이아니므로M2.77SYNTHETIC_ONLY를유지한다.

## 18. 기존 코드·동결 계약

기준선322기존파일중변경은**provider.py의명시적계약선택분기1개**,나머지321개는SHA256/크기/mtime불변이다. M3.8D후보정확일치·V1코어·기존OutputValidator·Facts·기존Provider/Prompt·엔진·API/React·기존tests/golden/GV01~GV15/BV01~BV16/Coveragefreeze를보존했다. 신규4코드/시험/도구와보고·증거2파일을추가했다.

## 19. 실제 release6 SHA256

| 파일 | SHA256 |
|---|---|
| `data/releases/ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json` | `9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025` |
| `data/releases/ansan-youth-2026-10-20-001/README.md` | `4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f` |
| `data/releases/ansan-youth-2026-10-20-001/sources.json` | `a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b` |
| `data/releases/ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json` | `d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92` |
| `data/releases/ansan-youth-2026-10-20-002/README.md` | `8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99` |
| `data/releases/ansan-youth-2026-10-20-002/sources.json` | `711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620` |

## 20. 실제 정책·금융 상태

실제상품만기계산**0개**, 검증되지않은실제지원금Cashflow반영**0원**, 실제정책DRAFT/CONDITION_SLICE, ResidenceHistory OFFICIAL_INQUIRY_REQUIRED, M2.77SYNTHETIC_ONLY를유지한다. 실제정책판정이나금융수익계산에LLM을사용하지않았다.

## 21. 개인정보·외부 전송·문의

모든실제요청/원문기록은고정공개합성자료또는같은합성UI입력뿐이다. 제품원문로그0/외부AI0/유료API0/새계좌연결0/실제개인입력저장0이다. IBK는사용자이메일발송보고·공식회신대기이며새은행문의/회신원문생성0이다. 모델과런타임을재배포하지않았다.

## 22. Obsidian

기존OBSIDIAN_WORKFLOW에따라M3.8E실행환경/라이선스/후보계약/실제30/채택·fallback·p50/p95/실패·다음작업을노트와대시보드에연결한다. M3.6/M3.8/M3.8D와Wikilink를연결하고GUI미확인·최신완료Bookmark M3.1구버전상태는유지한다. 실제게시후링크/보존검사수를추가한다.

## 23. 남은 위험·미구현

사람한국어의미/유용성평가0, 비율null이다. 후보를정확히복사한성공을새로운추론능력으로설명하지않는다. cold첫모델설명은여전히TIMEOUT이며항상모델설명제공을보장하지않는다. 동시사용·다른기기·최신실데이터/실상품/정책전체판정·배포검증은이번범위밖이다. 기존ai_executed는Provider정상반환후에만true라실제생성후거부/취소통계를이flag만으로계산하지않는다.

## 24. 실행 후 설정

시험용API는NoProvider기본설정으로복귀했고, 이번모델server/runner는경로·부모·소유를확인해종료했다. 설치/모델파일/보안·드라이버·시작프로그램은변경하지않았다. 새V2경로는명시적서버설정으로선택할수있지만기본활성화·운영노출승인은분리한다.

## 25. 재현

같은설치런타임·모델store와위고정옵션을사용한다. 기존project.venv에서 `python -B -m tools.evaluate_local_catalog --phase cold --output <별도cold파일>`, 이후 `--phase fixed30 --output <별도30파일>`로분리한다. 평가도구가버전·모델manifest를대조한다. 이전증거를덮어쓰거나실제개인입력을기록하지않는다. metadata조회/정형모드/mock은실제생성으로세지않는다.

## 26. 최종 판단

**M3_LOCAL_CANDIDATE_LLM_VERIFIED** — 로컬합성후보선택연결검증범위. 실제30개모두채택됐고후보/원본/UNKNOWN/기존검증기·실제API/390px·연결실패/시간초과대체/기존회귀를확인했다. Codex대조범위의중대한의미모순0이고기존warm목표도충족했다. **사용자용AI기능전체완료·사람이평가한유용성·운영품질/실정책검증을뜻하지않는다.** 초기cold대체와사람평가미실행을명시하고기본정형을유지한다.

## 27. 다음 최소 작업 하나

**M3.8F — 정형 설명과 후보 선택 설명의 사람 검토용 비교표 및 소규모 이해도 평가**를제안한다. 같은Python결과의두문서를보여주고변화원인/UNKNOWN이해·불필요문장·표현오해를평가해모델선택이유용한지확인하는범위다. 후보문구수정은별도계약개정으로분리한다. 참가자연락·외부전송·새기능구현은이번에수행하거나승인된것으로간주하지않는다.


## 28. 게시 후 감사 결과

기존322파일 중321개 SHA256·크기·mtime 불변, 기존변경은provider.py 선택분기1개이며 신규4코드/시험/도구와 보고/증거2개만 확인했다. M3.8D후보코어·기존validator·V1/legacy·엔진·API/UI·기존tests/golden·Coveragefreeze·실제release6 SHA256은 모두 보존했다. 최종회귀 이후 제품소스추가수정0이다.

Obsidian은 기존13노트 갱신/신규1노트다. Markdown74/Wikilink686(제목15·블록1)/source_paths412/로컬파일링크79, 깨진링크0이다. Bookmarks13·4그룹/Base1/Canvas1/템플릿5/앱설정은 보존했다. GUI미확인·최신완료Bookmark M3.1구버전 상태를 남겼다. 은행은 사용자발송보고/공식회신대기이고 새회신을 생성하지 않았다.

실제30개·별도cold/API/화면·실패대체·회귀를기술검증범위로완료했고 사람평가비율null/운영활성화분리를기록했다. 기본NoProvider복귀·이번시험모델종료·시험탭정리/viewport reset을마쳤다. **M3_LOCAL_CANDIDATE_LLM_VERIFIED**는 이 제한된 범위를 뜻한다.
