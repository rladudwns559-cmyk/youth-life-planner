// Example people for a quick demo of the support finder. They are made-up profiles,
// shown as "예시", and never saved as the visitor's own conditions.
export type SupportExample={id:string;label:string;detail:string;province:string;city:string;age:string;employment:string;rent:string};

export const SUPPORT_EXAMPLES:SupportExample[]=[
  {id:'ansan',label:'안산 · 25세 · 구직 중 · 월세',detail:'경기 안산시 단원구에 살며 일자리를 찾는 청년',province:'경기',city:'안산시 단원구',age:'25',employment:'unemployed',rent:'yes'},
  {id:'seoul',label:'서울 마포 · 29세 · 직장인 · 전세',detail:'서울 마포구에서 회사에 다니며 전세로 사는 청년',province:'서울',city:'마포구',age:'29',employment:'employed',rent:'no'},
  {id:'busan',label:'부산 · 22세 · 대학생 아르바이트 · 월세',detail:'부산진구에서 아르바이트를 하며 월세로 사는 대학생',province:'부산',city:'부산진구',age:'22',employment:'employed',rent:'yes'},
];

export function exampleById(id:string|null|undefined){return SUPPORT_EXAMPLES.find(e=>e.id===id)??null;}

/** "#/programs?example=ansan" → "ansan" */
export function exampleFromHash(hash:string){
  const q=hash.split('?')[1];if(!q)return null;
  return exampleById(new URLSearchParams(q).get('example'));
}
