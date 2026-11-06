import {Component,type PropsWithChildren} from 'react';

/** Render/chunk failures get a recovery screen instead of an empty page. */
export default class ErrorBoundary extends Component<PropsWithChildren,{failed:boolean}>{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 render(){
  if(this.state.failed)return <main className="app-recovery" role="alert"><span aria-hidden="true">!</span><h1>화면을 불러오지 못했어요.</h1><p>연결 상태를 확인한 뒤 다시 열어 주세요. 새로고침하면 입력한 조건은 초기화됩니다.</p><button type="button" onClick={()=>window.location.reload()}>화면 다시 불러오기</button><a href="https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch" target="_blank" rel="noopener noreferrer">온통청년 공식 정책 검색으로 이동 ↗</a></main>;
  return this.props.children;
 }
}
