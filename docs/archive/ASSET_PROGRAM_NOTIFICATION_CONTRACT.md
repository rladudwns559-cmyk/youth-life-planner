# 자산형성사업 알림 연결 계약

2026-10-30 / 아래 기존 본문은 이전 단계 EVENT_READY_DELIVERY_NOT_IMPLEMENTED의 설계 이력입니다. 최신 구현 상태는 마지막 「공식 모집 자동 확인·관심 알림」 절과 OFFICIAL_INTAKE_MONITORING_AND_ALERTS.md를 따릅니다.

## 구현된 경계

diff_catalogs(previous,current,previous_at,current_at)는 timezone-aware 시각과 검증된 Catalog를 받는다. PROGRAM_ADDED / PROGRAM_REMOVED / PROGRAM_UPDATED / INTAKE_STATUS_CHANGED를 반환한다. payload는 program_id, edition, previous/current_revision, previous/current_status, observed_at, 안정적인 event_id, delivery_status=NOT_SENT다. 개인 프로필·소득은 이벤트에 없다. 두 시각이 역순이거나 naive면 거부한다.

공식 원문 바이트 변화만으로 이벤트를 발송하지 않는다. check_asset_program_sources.py는 HTTP 상태/크기/원문 SHA를 수집해 검토 후보만 만든다. 원문 변경에는 메뉴·카운터 변화도 포함될 수 있다. 원문은 수동 확인 후 공식 내용과 시각을 검증해 새 edition/스냅샷으로 반영해야 한다. 공고·신청·심사·계좌개설은 다른 상태다.

## 후속 연결 제안 — 아직 구현/운영하지 않음

1. 공공 출처 확인 작업의 실행 주기·실패 기록·점검자를 정한다. 7일 freshness는 임시 서비스 가정이며 실제 수집 SLA가 아니다.
2. 사용자 명시 동의로 관심 지역/사업·변경 종류·전달 수단만 구독한다. 소득·월세 저장은 기본값으로 추가하지 않는다. 연락처가 필요하면 프로필과 분리하고 목적·보유기간·해지/삭제 방식을 먼저 정의한다.
3. 검토 완료 이벤트만 outbox에 적재하고 subscriber_id + event_id로 중복 전달을 막는다. 발송 오류는 원문 상태와 분리하고 무한 재시도하지 않는다.
4. 만료/철회/삭제·정책 정정 공지와 알림 해지 기능을 시험한다. 선호 지역 일치 알림은 가입 자격 확정 알림이 아니다.
5. 전달 기록이 있을 때만 SENT로 표시한다. 브라우저 권한 요청·푸시·이메일·외부 예약 서비스를 임의 활성화하지 않는다.

현재 사용자 구독0, 알림 발송0, 상주 감시/예약 작업0. 실제 최신 운영을 약속하지 않는다. 모집 정보는 공식 페이지 재확인을 안내한다.

## 2026-10-30 공식 모집 자동 확인·관심 알림

사용자의 후속 요청으로 등록 공식 출처 자동 확인·관심 지역/사업 구독·사이트 알림함·브라우저 Web Push를 연결했다. 이메일은 사용자 결정으로 제외했다. 서버 실행 중6시간 확인이며 상시 운영/전국 완전 수집은 별도 단계다. 단순200·본문 동일 검증·일정 추출·푸시 서버 접수·기기 표시는 구분한다.

알림 전용 저장소는 관심 지역/사업·수신 설정·필요한 browser subscription/기기 식별자/알림 기록만 저장한다. 소득·월세·생년월일·계좌정보는 저장하지 않는다. 구독90일 만료·정기 삭제·즉시 구독 삭제를 지원한다. 원본 금융·정책 규칙은 자동 생성하지 않고 신규 공고 전체 자격 UNKNOWN을 유지한다.

실제 공식25주소 확인·일정3건 추출(모두마감), 새 API17사례, 전체 Backend12562/1skip/1warning·Frontend161·TS/build 통과. 브라우저 기기 표시는 사용자 직접 확인이며 자동 OS 검증과 구분한다. release6/GV/BV·기존 core 보존. 상세: [구현·검증](OFFICIAL_INTAKE_MONITORING_AND_ALERTS.md), [운영](ASSET_ALERTS_OPERATIONS.md).
