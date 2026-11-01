export type LocalCounts = { city: string; total: number; open: number };

export default function LocalNotice({city,total,open}:LocalCounts) {
  return <div className="local-notice" role="status" aria-label={city+' 공고 요약'}>
    <svg className="local-notice-pin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.4"/>
    </svg>
    <div><p className="local-notice-title">{city} 대상 공고 <strong>{total}건</strong></p>
    <p className="local-notice-detail">이 중 공식 접수 중이며 입력 조건과 충돌하지 않는 공고 <b>{open}건</b></p></div>
  </div>;
}
