import type {CSSProperties, ReactNode} from 'react';
import './home-orbit.css';

/* A slowly turning miniature "life block": a home (support for housing), three savings columns
   that grow, and two cards that always face the viewer (a coin and a checked notice).
   Pure CSS 3D. Decorative only: aria-hidden, no information lives here. */

type BoxProps = {x: number; y: number; w: number; d: number; h: number; tone: string; className?: string; children?: ReactNode};

function Box({x, y, w, d, h, tone, className = '', children}: BoxProps) {
  const style = {left: x, top: y, width: w, height: d, '--h': `${h}px`, '--w': `${w}px`, '--d': `${d}px`} as CSSProperties;
  return <div className={`orbit-box tone-${tone} ${className}`} style={style}>
    <i className="f-top"/><i className="f-s"/><i className="f-n"/><i className="f-e"/><i className="f-w"/>
    {children}
  </div>;
}

function Billboard({x, y, z, children, className = ''}: {x: number; y: number; z: number; children: ReactNode; className?: string}) {
  return <div className={`orbit-billboard ${className}`} style={{left: x, top: y, '--z': `${z}px`} as CSSProperties}><div className="orbit-bob">{children}</div></div>;
}

export function HomeOrbit() {
  return <div className="home-orbit" aria-hidden="true">
    <div className="orbit-shadow"/>
    <div className="orbit-stage">
      <Box x={0} y={0} w={240} d={240} h={18} tone="base" className="orbit-base">
        <div className="orbit-deck">
          <div className="orbit-path"/>
          <Box x={26} y={30} w={64} d={58} h={46} tone="home" className="orbit-home">
            <div className="roof">
              <i className="r-n"/><i className="r-s"/><i className="g-e"/><i className="g-w"/>
            </div>
            <i className="door"/>
          </Box>
          <Box x={128} y={150} w={24} d={24} h={34} tone="save" className="orbit-col c1"/>
          <Box x={160} y={150} w={24} d={24} h={62} tone="save" className="orbit-col c2"/>
          <Box x={192} y={150} w={24} d={24} h={96} tone="save2" className="orbit-col c3"/>
          <Box x={40} y={150} w={58} d={40} h={8} tone="pad"/>
          <Billboard x={196} y={162} z={150} className="bb-coin">
            <svg viewBox="0 0 48 48"><circle cx="24" cy="24" r="21" className="coin-rim"/><circle cx="24" cy="24" r="15.5" className="coin-face"/><path d="M15.5 19h17M17.5 19l3.2 11 3.3-9 3.3 9 3.2-11" className="coin-mark"/></svg>
          </Billboard>
          <Billboard x={60} y={46} z={132} className="bb-note">
            <svg viewBox="0 0 64 76"><rect x="3" y="3" width="58" height="70" rx="8" className="note-paper"/><path d="M15 22h24M15 34h34M15 46h20" className="note-line"/><circle cx="46" cy="56" r="11" className="note-badge"/><path d="m40.5 56 4 4 7-8" className="note-check"/></svg>
          </Billboard>
        </div>
      </Box>
    </div>
  </div>;
}
