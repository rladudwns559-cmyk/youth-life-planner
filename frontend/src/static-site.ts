/* Static files generated after the Pages build (scripts/static-pages.mts):
   - p/<slug>/index.html : one crawlable, shareable page per open program
   - p/index.html        : list of those pages
   - calendars/<slug>.ics: subscribable deadline calendars per region
   - sitemap.xml
   Pure functions only (no file system), so tests can check the output directly. */

export const SITE_BASE='https://rladudwns559-cmyk.github.io/youth-life-planner/';
export const CALENDAR_FEEDS:{province:string;slug:string;label:string}[]=[
  {province:'',slug:'all',label:'전국 전체'},
  {province:'서울',slug:'seoul',label:'서울'},{province:'부산',slug:'busan',label:'부산'},{province:'대구',slug:'daegu',label:'대구'},
  {province:'인천',slug:'incheon',label:'인천'},{province:'광주',slug:'gwangju',label:'광주'},{province:'대전',slug:'daejeon',label:'대전'},
  {province:'울산',slug:'ulsan',label:'울산'},{province:'세종',slug:'sejong',label:'세종'},{province:'경기',slug:'gyeonggi',label:'경기'},
  {province:'강원',slug:'gangwon',label:'강원'},{province:'충북',slug:'chungbuk',label:'충북'},{province:'충남',slug:'chungnam',label:'충남'},
  {province:'전북',slug:'jeonbuk',label:'전북'},{province:'전남',slug:'jeonnam',label:'전남'},{province:'경북',slug:'gyeongbuk',label:'경북'},
  {province:'경남',slug:'gyeongnam',label:'경남'},{province:'제주',slug:'jeju',label:'제주'},
];
export const calendarUrl=(slug:string)=>`${SITE_BASE}calendars/${slug}.ics`;
export const pageSlug=(id:string)=>id.toLowerCase().replace(/[^a-z0-9-]+/g,'-');
export const pageUrl=(id:string)=>`${SITE_BASE}p/${pageSlug(id)}/`;

export type StaticProgram={program_id:string;title:string;authority:string;edition:string;category:string;provinces:string[];city:string|null;
  benefit_summary:string;age_note:string;income_note:string;schedule_note:string;required_checks:string[];
  starts_on:string|null;ends_on:string|null;intake_mode:string;sources:{url:string;title:string;verified_on:string}[]};

const CATEGORY:Record<string,string>={HOUSING:'월세·주거',EMPLOYMENT:'취업·면접',EDUCATION:'교육·응시료',LIVING:'생활·복지',CULTURE:'문화',ASSET:'청년통장·자산형성'};
const esc=(s:string)=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const place=(p:StaticProgram)=>p.provinces.length?p.provinces.join('·')+(p.city?' '+p.city:''):'전국';
const deadline=(p:StaticProgram,today:string)=>p.intake_mode==='WINDOW'&&p.ends_on&&/^\d{4}-\d{2}-\d{2}$/.test(p.ends_on)&&p.ends_on>=today?p.ends_on:null;
const korean=(iso:string)=>{const [y,m,d]=iso.split('-').map(Number);return `${y}년 ${m}월 ${d}일`;};

/** Programs worth a public page today: not marked closed and not past their published deadline. */
export function openPrograms<T extends StaticProgram>(programs:T[],today:string):T[]{
  return programs.filter(p=>!['CLOSED','NO_INTAKE'].includes(p.intake_mode)&&!(p.ends_on&&p.ends_on<today));
}

const STYLE='body{margin:0;background:#f6f4ef;color:#0e1a2b;font:16px/1.7 system-ui,-apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif}main{max-width:760px;margin:0 auto;padding:24px 16px 48px}a{color:#1f57d8}h1{font-size:28px;line-height:1.3;margin:8px 0 12px}h2{font-size:18px;margin:24px 0 8px}.meta{color:#5b6676;font-size:14px}.box{background:#fff;border:1px solid #e4e1d8;border-radius:14px;padding:16px 18px;margin:14px 0}.cta{display:inline-block;margin:6px 8px 6px 0;padding:12px 20px;border-radius:999px;background:#1f57d8;color:#fff;font-weight:700;text-decoration:none}.cta.alt{background:#fff;color:#1f57d8;border:1px solid #cfd6e2}.note{font-size:13px;color:#5b6676}dt{font-weight:700;margin-top:8px}dd{margin:0}ul{padding-left:20px}';

/** A crawlable page for one program. `appBase` is the path from this page back to the app. */
export function programPage(p:StaticProgram,{today,updatedOn}:{today:string;updatedOn:string}):string{
  const end=deadline(p,today);
  const description=`${place(p)} · ${p.benefit_summary}`.slice(0,150);
  const app=`../../#/programs/item/${encodeURIComponent(p.program_id)}`;
  return `<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(p.title)} | 청년 경제생활</title>
<meta name="description" content="${esc(description)}">
<link rel="canonical" href="${pageUrl(p.program_id)}">
<meta property="og:type" content="article"><meta property="og:title" content="${esc(p.title)}"><meta property="og:description" content="${esc(description)}"><meta property="og:url" content="${pageUrl(p.program_id)}"><meta property="og:locale" content="ko_KR">
<link rel="icon" href="../../favicon.svg"><style>${STYLE}</style></head>
<body><main>
<p class="meta"><a href="../../#/">청년 경제생활</a> · <a href="../">지원사업 모아보기</a></p>
<p class="meta">${esc(CATEGORY[p.category]??'지원사업')} · ${esc(p.authority)} · ${esc(place(p))}</p>
<h1>${esc(p.title)}</h1>
<p>${esc(p.benefit_summary)}</p>
${end?`<p><strong>공고에 적힌 신청 마감: ${korean(end)}</strong></p>`:''}
<p><a class="cta" href="${app}">내 조건과 비교하기</a><a class="cta alt" href="${esc(p.sources[0].url)}" rel="noopener">공식 안내 보기</a></p>
<div class="box"><h2>지원 조건과 일정</h2><dl><dt>연령·대상</dt><dd>${esc(p.age_note)}</dd><dt>소득 기준</dt><dd>${esc(p.income_note)}</dd><dt>모집 안내</dt><dd>${esc(p.schedule_note)}</dd></dl></div>
<div class="box"><h2>신청 전에 확인할 것</h2><ul>${p.required_checks.map(t=>`<li>${esc(t)}</li>`).join('')}</ul></div>
<div class="box"><h2>근거 자료</h2><ul>${p.sources.map(s=>`<li><a href="${esc(s.url)}" rel="noopener">${esc(s.title)}</a> <span class="note">확인 ${esc(s.verified_on)}</span></li>`).join('')}</ul></div>
<p class="note">자료 확인 ${esc(updatedOn)}. 이 페이지는 공식 공고를 요약한 안내이며 신청·수급 자격을 확정하지 않습니다. 모집 여부·예산·최종 자격은 공식 안내에서 확인하세요.</p>
</main></body></html>
`;
}

export function indexPage(programs:StaticProgram[],{updatedOn}:{updatedOn:string}):string{
  const rows=[...programs].sort((a,b)=>place(a).localeCompare(place(b),'ko')||a.title.localeCompare(b.title,'ko'))
    .map(p=>`<li><a href="./${pageSlug(p.program_id)}/">${esc(p.title)}</a> <span class="note">${esc(place(p))}</span></li>`).join('');
  return `<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>청년 지원사업 모아보기 | 청년 경제생활</title>
<meta name="description" content="공식 공고를 바탕으로 정리한 청년 지원사업 ${programs.length}개. 지역·나이·취업·월세 조건과 비교해 보세요.">
<link rel="canonical" href="${SITE_BASE}p/"><link rel="icon" href="../favicon.svg"><style>${STYLE}</style></head>
<body><main><p class="meta"><a href="../#/">청년 경제생활</a></p><h1>청년 지원사업 모아보기</h1>
<p>공식 공고를 바탕으로 정리한 지원사업 ${programs.length}개예요. <a href="../#/programs">내 조건으로 찾기</a>에서 조건과 비교할 수 있어요.</p>
<ul>${rows}</ul><p class="note">자료 확인 ${esc(updatedOn)}</p></main></body></html>
`;
}

export function sitemap(urls:string[],lastmod:string):string{
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map(u=>`<url><loc>${esc(u)}</loc><lastmod>${lastmod}</lastmod></url>`).join('\n')}\n</urlset>\n`;
}

const icsText=(s:string)=>s.replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,');
function fold(line:string){const enc=new TextEncoder();let out='',chunk='',size=0;for(const c of line){const n=enc.encode(c).length;if(size+n>75){out+=chunk+'\r\n';chunk=' ';size=1;}chunk+=c;size+=n;}return out+chunk;}

/** Subscribable calendar: one all-day event on each published deadline. Empty province = every program. */
export function regionCalendar(programs:StaticProgram[],province:string,label:string,{today,stamp}:{today:string;stamp:string}):string{
  const events=openPrograms(programs,today).filter(p=>!province||p.provinces.length===0||p.provinces.includes(province))
    .flatMap(p=>{const end=deadline(p,today);if(!end)return [];const d=new Date(end+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+1);
      return ['BEGIN:VEVENT',`UID:${p.program_id}@youth-life-planner`,`DTSTAMP:${stamp}`,`DTSTART;VALUE=DATE:${end.replace(/-/g,'')}`,`DTEND;VALUE=DATE:${d.toISOString().slice(0,10).replace(/-/g,'')}`,
        `SUMMARY:${icsText('[마감] '+p.title)}`,`DESCRIPTION:${icsText(`${place(p)} · ${p.benefit_summary}\n${p.schedule_note}\n자세히: ${pageUrl(p.program_id)}\n공고에 적힌 마감일이에요. 실제 마감 시각·예산 소진·자격은 공식 안내에서 확인하세요.`)}`,
        `URL:${p.sources[0].url}`,'TRANSP:TRANSPARENT','END:VEVENT'];});
  const name=`청년 지원사업 마감 · ${label}`;
  return ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//youth-life-planner//deadlines//KO','CALSCALE:GREGORIAN','METHOD:PUBLISH',
    `X-WR-CALNAME:${icsText(name)}`,`NAME:${icsText(name)}`,'X-WR-TIMEZONE:Asia/Seoul','REFRESH-INTERVAL;VALUE=DURATION:PT12H','X-PUBLISHED-TTL:PT12H',
    ...events,'END:VCALENDAR'].map(fold).join('\r\n')+'\r\n';
}
