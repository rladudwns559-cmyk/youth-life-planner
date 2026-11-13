// After the Pages build: write program pages, the sitemap and region calendars into the output folder.
// Usage (frontend/): node scripts/static-pages.mts dist-pages [--today YYYY-MM-DD]
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {CALENDAR_FEEDS,SITE_BASE,indexPage,openPrograms,pageSlug,pageUrl,programPage,regionCalendar,sitemap,type StaticProgram} from '../src/static-site.ts';

const out=process.argv[2];
if(!out)throw new Error('usage: node scripts/static-pages.mts <outDir> [--today YYYY-MM-DD]');
const flag=process.argv.indexOf('--today');
const today=flag>0?process.argv[flag+1]:new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const stamp=new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z$/,'Z');
const data=JSON.parse(readFileSync(new URL('../src/public-data/current-support-web.json',import.meta.url),'utf8')) as {programs:StaticProgram[];updated_on?:string;built_on:string};
const updatedOn=data.updated_on??data.built_on;

const open=openPrograms(data.programs,today);
for(const p of open){
  const dir=join(out,'p',pageSlug(p.program_id));
  mkdirSync(dir,{recursive:true});
  writeFileSync(join(dir,'index.html'),programPage(p,{today,updatedOn}));
}
mkdirSync(join(out,'p'),{recursive:true});
writeFileSync(join(out,'p','index.html'),indexPage(open,{updatedOn}));
writeFileSync(join(out,'sitemap.xml'),sitemap([SITE_BASE,SITE_BASE+'p/',...open.map(p=>pageUrl(p.program_id))],today));
mkdirSync(join(out,'calendars'),{recursive:true});
for(const f of CALENDAR_FEEDS)writeFileSync(join(out,'calendars',f.slug+'.ics'),regionCalendar(data.programs,f.province,f.label,{today,stamp}));
console.log(JSON.stringify({today,pages:open.length,calendars:CALENDAR_FEEDS.length}));
