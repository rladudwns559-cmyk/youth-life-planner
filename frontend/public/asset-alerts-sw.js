/* No offline caching of economic inputs or API responses. */
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('push',event=>{
  event.waitUntil((async()=>{
    let data={};try{data=event.data?event.data.json():{};}catch{}
    const title=typeof data.title==='string'?data.title.slice(0,240):'청년 지원사업 새 소식';
    const body=typeof data.body==='string'?data.body.slice(0,600):'사이트 알림함에서 공식 공고를 확인해 주세요.';
    await self.registration.showNotification(title,{body,tag:typeof data.id==='string'?data.id:'aix-asset-update',data:{url:typeof data.url==='string'?data.url:'/#asset-alerts'},renotify:false});
  })());
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();
  event.waitUntil((async()=>{
    const allowed=['www.korea.kr','m.korea.kr','www.bokjiro.go.kr','account.gfgf.kr','news.seoul.go.kr','young.busan.go.kr','youth.incheon.go.kr','www.modadream.kr','daejeonyouthportal.kr','www.daejeonyouthportal.kr','double.jb2030.or.kr','obank.kbstar.com'];
    let url=new URL('/#asset-alerts',self.location.origin);
    try{const candidate=new URL(event.notification.data?.url,self.location.origin);if(candidate.origin===self.location.origin||(candidate.protocol==='https:'&&allowed.includes(candidate.hostname)))url=candidate;}catch{}
    const windows=await self.clients.matchAll({type:'window',includeUncontrolled:true});
    if(url.origin===self.location.origin&&windows.length){await windows[0].navigate(url.href);return windows[0].focus();}
    return self.clients.openWindow(url.href);
  })());
});
