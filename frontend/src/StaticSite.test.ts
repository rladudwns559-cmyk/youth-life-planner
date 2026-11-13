import {it,expect,describe} from 'vitest';
import web from './public-data/current-support-web.json';
import {CALENDAR_FEEDS,indexPage,openPrograms,pageSlug,pageUrl,programPage,regionCalendar,sitemap,type StaticProgram} from './static-site';

const programs=web.programs as unknown as StaticProgram[];
const TODAY='2026-11-14';
const sample=programs.find(p=>p.intake_mode==='WINDOW'&&p.ends_on&&p.ends_on>=TODAY)!;

describe('program pages',()=>{
  it('leave out closed rounds and past deadlines',()=>{
    const open=openPrograms(programs,TODAY);
    expect(open.length).toBeGreaterThan(100);
    for(const p of open){expect(['CLOSED','NO_INTAKE']).not.toContain(p.intake_mode);if(p.ends_on)expect(p.ends_on>=TODAY).toBe(true);}
    expect(new Set(open.map(p=>pageSlug(p.program_id))).size).toBe(open.length);  // no two pages share a folder
  });
  it('carry the title, description, canonical link, deadline and a way back into the app',()=>{
    const html=programPage(sample,{today:TODAY,updatedOn:'2026-11-13'});
    expect(html).toContain('<html lang="ko">');
    expect(html).toContain(`<link rel="canonical" href="${pageUrl(sample.program_id)}">`);
    expect(html).toContain('<meta name="description"');
    expect(html).toContain('공고에 적힌 신청 마감');
    expect(html).toContain(`href="../../#/programs/item/${encodeURIComponent(sample.program_id)}"`);
    expect(html).toContain('신청·수급 자격을 확정하지 않습니다');
  });
  it('escape text so a notice cannot inject markup',()=>{
    const html=programPage({...sample,title:'<script>alert(1)</script>',benefit_summary:'"&'},{today:TODAY,updatedOn:TODAY});
    expect(html).not.toContain('<script>alert(1)</script>');
    expect(html).toContain('&lt;script&gt;');
  });
  it('lists every page in the index and the sitemap',()=>{
    const open=openPrograms(programs,TODAY);
    const index=indexPage(open,{updatedOn:TODAY});
    for(const p of open.slice(0,20))expect(index).toContain(`href="./${pageSlug(p.program_id)}/"`);
    const map=sitemap(open.map(p=>pageUrl(p.program_id)),TODAY);
    expect(map.match(/<url>/g)).toHaveLength(open.length);
  });
});

describe('region calendars',()=>{
  const stamp='20261114T000000Z';
  it('cover the region plus nationwide programs, only with deadlines still ahead',()=>{
    const ics=regionCalendar(programs,'경기','경기',{today:TODAY,stamp});
    const events=ics.split('BEGIN:VEVENT').length-1;
    expect(events).toBeGreaterThan(0);
    const expected=openPrograms(programs,TODAY).filter(p=>p.intake_mode==='WINDOW'&&p.ends_on&&p.ends_on>=TODAY&&(p.provinces.length===0||p.provinces.includes('경기'))).length;
    expect(events).toBe(expected);
    expect(ics).toContain('X-WR-CALNAME:청년 지원사업 마감 · 경기');
    expect(ics).toContain('REFRESH-INTERVAL;VALUE=DURATION:PT12H');
    for(const line of ics.split('\r\n'))expect(new TextEncoder().encode(line).length).toBeLessThanOrEqual(75);
  });
  it('the nationwide feed holds every region and no feed holds another region',()=>{
    const all=regionCalendar(programs,'','전국 전체',{today:TODAY,stamp}).split('BEGIN:VEVENT').length-1;
    for(const f of CALENDAR_FEEDS.slice(1)){
      const n=regionCalendar(programs,f.province,f.label,{today:TODAY,stamp}).split('BEGIN:VEVENT').length-1;
      expect(n).toBeLessThanOrEqual(all);
    }
    const busan=regionCalendar(programs,'부산','부산',{today:TODAY,stamp});
    const seoulOnly=programs.find(p=>p.provinces.length===1&&p.provinces[0]==='서울'&&p.intake_mode==='WINDOW'&&p.ends_on&&p.ends_on>=TODAY)!;
    expect(busan).not.toContain(`UID:${seoulOnly.program_id}@`);
  });
});
