import releaseSummary from './public-data/release-summary.json';
/** Presentation only. No profile input, financial arithmetic, or policy decisions. */
export function BrandMark() {
  // A roof over three rising savings bars; the tallest is the goal (gold).
  return <svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M3.5 14.5 16 5l12.5 9.5" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round"/><rect x="8" y="19.5" width="4.2" height="8" rx="1.2" fill="currentColor"/><rect x="13.9" y="15.5" width="4.2" height="12" rx="1.2" fill="currentColor"/><rect x="19.8" y="11.8" width="4.2" height="15.7" rx="1.2" fill="#f0b429"/><path d="M5 28.6h22" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>;
}

function Arrow() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}

export function SiteHeader() {
  return <>
    <a className="skip-link" href="#input-heading">계산 입력으로 바로가기</a>
    <header className="site-header"><div className="topbar">
      <a className="brand" href="#main" aria-label="청년 경제생활 의사결정 시뮬레이터 홈"><span className="brand-mark"><BrandMark /></span><span>청년 경제생활<small>의사결정 시뮬레이터</small></span></a>
      <nav className="primary-nav" aria-label="주요 메뉴"><a href="#asset-programs">청년 지원사업</a><a href="#input-heading">생활비 계산</a><a href="#result-heading">나의 결과</a><a href="#asset-alerts">모집 알림</a></nav>
      <span className="demo-pill"><span aria-hidden="true"/>공식 정보 · 계산 시연</span>
    </div></header>
  </>;
}

export function ServiceIntro() {
  return <>
    <section className="intro" aria-labelledby="intro-title">
      <div className="intro-copy"><p className="hero-kicker">나의 생활에서 시작하는 경제 계획</p>
        <h1 id="intro-title">오늘의 생활을 살피고,<br/><span>내일의 선택을 준비해요.</span></h1>
        <p className="lead">정부·지자체 지원부터 한 달 예산, 저축 계획까지.<br/>내 상황이 달라졌을 때의 변화도 함께 확인하세요.</p>
        <a className="hero-action" href="#input-heading">내 생활비 계산하기<Arrow /></a>
        <p className="hero-privacy"><svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M10 2 4 4.5v5c0 4 6 7 6 7s6-3 6-7v-5L10 2Z" stroke="currentColor" strokeWidth="1.4"/><path d="m7.5 9.5 1.7 1.7 3.4-3.4" stroke="currentColor" strokeWidth="1.4"/></svg>로그인 없이, 소득·지출 저장 없이</p>
      </div>
      <div className="plan-visual" aria-hidden="true">
        <div className="visual-orbit orbit-one"/><div className="visual-orbit orbit-two"/>
        <div className="plan-sheet"><div className="plan-sheet-top"><span className="mini-logo"><BrandMark /></span><span>나의 생활 계획</span><span className="sheet-dots">•••</span></div>
          <p className="sheet-label">한눈에 살펴보는</p><strong className="sheet-title">나의 경제생활</strong>
          <div className="plan-bars"><div><span>소득</span><i/></div><div><span>지출</span><i/></div><div><span>저축 계획</span><i/></div></div>
          <div className="sheet-bottom"><span>오늘의 상황에서, 다음 가능성으로</span><Arrow /></div>
        </div>
        <div className="visual-tag tag-policy"><span className="tag-check">✓</span><span>정책 조건<small>확인할 근거를 명확하게</small></span></div>
        <div className="visual-tag tag-scenario"><span className="tag-change">↗</span><span>상황이 바뀐다면?<small>변경 전·후를 나란히</small></span></div>
      </div>
    </section>
    <div className="service-steps" aria-label="서비스 이용 순서">
      <div><span className="journey-number">01</span><span><strong>현재 상황 입력</strong><small>나이·지역과 월 수입·지출</small></span></div>
      <span className="journey-arrow" aria-hidden="true">›</span>
      <div><span className="journey-number">02</span><span><strong>정책·예산 확인</strong><small>조건별 판정과 저축 가능 금액</small></span></div>
      <span className="journey-arrow" aria-hidden="true">›</span>
      <div><span className="journey-number">03</span><span><strong>변화와 계획 비교</strong><small>What-if와 가상 적금 계산</small></span></div>
    </div>
  </>;
}

export function EmptyResult() {
  return <div className="empty-state">
    <div className="empty-ledger" aria-hidden="true"><div className="ledger-title"/><div className="ledger-row"><i/><b/></div><div className="ledger-row"><i/><b/></div><div className="ledger-divider"/><div className="ledger-total"><i/><b/></div><span className="ledger-check">✓</span></div>
    <p className="empty-kicker">나의 생활을 숫자로 이해하는 첫걸음</p><h3>입력한 상황에 맞춰<br/>결과를 정리해 드릴게요.</h3>
    <p>현재 상황을 입력하고 계산 버튼을 눌러 주세요.<br/>월 예산과 정책별 확인사항을 함께 보여드립니다.</p>
    <div className="empty-tags"><span>조건별 판정</span><span>월 예산 계산</span><span>추가 확인사항</span></div>
  </div>;
}

export function ServiceGuide() {
  return <section className="service-guide" id="service-guide" aria-labelledby="guide-heading"><div className="guide-heading"><p className="eyebrow">서비스 이용 안내</p><h2 id="guide-heading">내 조건으로 비교하고,<br/>근거를 확인하세요.</h2><p>전국 청년을 위한 공식 상품·지원정보 탐색.<br/>확인된 자료부터 차근차근 넓혀갑니다.</p></div><div className="guide-questions">
    <details><summary>내 조건에 맞는 지원은 어떻게 찾나요?</summary><p>‘내 조건으로 찾기’로 결과 창을 열고, 같은 창에서 사업 비교와 예·적금 탐색을 할 수 있습니다. 청년 지원사업에서 지역·현재 만 나이·취업 상태·월세 거주 여부를 입력하세요. 확인된 조건은 Python 비교표로 바로 비교하고, 생일 경계·소득·재산·예외는 추가 확인으로 남깁니다. 전국·해당 광역지역·해당 시군구 사업을 함께 찾고 월세·주거, 취업·면접, 교육·응시료 등 분야로 좁힐 수 있습니다. 입력 조건이 일치해도 공고 기준일·가구소득·재산·주민등록 이력·중복 지원·잔여예산은 추가 확인해야 합니다. 현재 확인한 사업 목록이며 전국 모든 시군구의 전수 목록이 아닙니다.</p></details><details><summary>내 조건에 맞는 상품은 어떻게 보나요?</summary><p>상품 찾기에 월 저축액과 목표 기간을 입력하세요. 정기예금은 이미 모아 둔 목돈을 별도로 입력합니다. 금액·기간이 맞는 상품, 일부 금액만 넣을 수 있는 상품, 일정·대상 확인이 필요한 상품을 구분합니다. 전체 목록을 보거나 은행·상품명으로 검색하고 최대 3개를 비교할 수 있습니다.</p></details>
    <details><summary>모든 금융상품을 볼 수 있나요?</summary><p>현재 공식 근거를 확보한 {releaseSummary.institutions}개 금융회사의 예·적금 상품·가입유형 상세 {releaseSummary.product_count}개와 주거·취업·교육·생활·문화·자산형성 지원사업·모집 안내 {releaseSummary.support_count}개를 제공합니다. 공시 더 보기에서는 97개 금융회사·299개 상품명 기준의 적금 참고 자료도 검색할 수 있습니다. 상세 목록과 중복될 수 있으며, 공시 참고 자료를 개인 조건 일치로 판정하지 않습니다. 모든 은행·저축은행·특판을 전수 수집한 목록은 아닙니다. 대출·주식·보험 추천은 제공하지 않습니다.</p></details>
    <details><summary>금리가 높으면 무조건 좋은 상품인가요?</summary><p>기본금리와 조건부 최고금리는 다릅니다. 가입 대상, 급여·카드·자동이체 등 우대조건, 납입 주기와 중도해지 조건을 함께 확인하세요. 과거 공시의 금리를 현재 금리로 바꾸지 않고, 실제 만기금액을 추정해 표시하지 않습니다.</p></details>
    <details><summary>조건 일치면 바로 가입할 수 있나요?</summary><p>금액·기간의 공시 범위를 비교한 결과입니다. 나이·소득·거래 실적 등 개인별 가입 자격은 추가 확인이 필요합니다. 청년 지원사업도 DRAFT / CONDITION_SLICE 범위의 정보이며, 가구소득·거주기간 등 UNKNOWN을 충족으로 간주하지 않습니다.</p></details>
    <details><summary>새 모집이나 금리는 자동으로 알려주나요?</summary><p>현재 공개 사이트에는 자동 갱신·브라우저 알림·이메일 구독이 없습니다. 유료 서버나 알림 요금제는 신청하지 않았습니다. 표시된 검토일 기준 자료이며, 오래된 자료는 조건 일치 표시를 보류합니다. 새 공고와 최신 조건은 공식 출처에서 확인하세요.</p></details>
    <details><summary>입력값은 저장되거나 외부로 전송되나요?</summary><p>공개 상품 비교는 Python으로 준비한 비교표를 이 화면에서 조회합니다. 입력값을 서버·외부 AI로 전송하거나 영구 저장하지 않습니다. 관심상품·관심사업 별표와 신청 준비 체크리스트는 사업·상품·확인항목 ID만, "내 조건 기억하기"를 켠 경우 지역·나이·취업 상태·월세 여부만 해당 브라우저에 저장하며, 로그인·기기 간 동기화·알림 구독은 아닙니다. 로컬 생활비 계산은 기존 Python 엔진을 사용하고 정책 지원금은 수입에 더하지 않습니다.</p></details>
  </div></section>;
}

export function SiteFooter() {
  return <footer><div className="footer-main"><a className="footer-brand" href="#main">청년 경제생활</a><p>내 상황을 이해하고, 다음 선택을 준비하는 곳.</p><a href="#service-guide">서비스 이용 안내 ↗</a></div><div className="footer-bottom"><p>AI+X · 청년 경제생활 의사결정 시뮬레이터</p><p>로컬 검증 시제품 · 실제 금융상품 가입 및 정책 신청 서비스가 아닙니다.</p></div></footer>;
}
