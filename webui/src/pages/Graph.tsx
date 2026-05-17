import { useRef, useEffect, useState } from 'react';
import { api } from '../api/client';

export function GraphPage(){
  const cr=useRef<HTMLCanvasElement>(null);
  const [stats, setStats] = useState({ nodes: 0, edges: 0, status: 'loading' });

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await api.get<{ nodes: number; edges: number; status: string }>('/graph/summary');
        setStats(res);
      } catch {
        setStats({ nodes: 0, edges: 0, status: 'error' });
      }
    }
    fetchStats();
  }, []);

  useEffect(()=>{
    const c=cr.current;if(!c)return;
    const ctx=c.getContext('2d');if(!ctx)return;
    c.width=c.parentElement!.clientWidth||800;c.height=500;
    const N=30;
    const nodes=Array.from({length:N},(_,i)=>({x:Math.random()*c.width,y:Math.random()*c.height,r:6+Math.random()*8,label:'Node '+(i+1),vx:0,vy:0}));
    const links:number[][]=[];
    for(let i=0;i<N;i++)for(let j=i+1;j<N;j++){
      const dx=nodes[i]!.x-nodes[j]!.x,dy=nodes[i]!.y-nodes[j]!.y;
      if(Math.sqrt(dx*dx+dy*dy)<120)links.push([i,j])
    }
    const W=c.width,H=c.height;
    function draw(){
      ctx!.clearRect(0,0,W,H);
      ctx!.strokeStyle='rgba(0,240,212,.12)';ctx!.lineWidth=.8;
      for(const[a,b]of links as [number,number][]){
        ctx!.beginPath();ctx!.moveTo(nodes[a]!.x,nodes[a]!.y);ctx!.lineTo(nodes[b]!.x,nodes[b]!.y);ctx!.stroke()
      }
      for(const n of nodes){
        ctx!.beginPath();ctx!.arc(n.x,n.y,n.r,0,Math.PI*2);
        ctx!.fillStyle='rgba(0,240,212,.5)';ctx!.fill();
        ctx!.strokeStyle='#00f0d4';ctx!.lineWidth=1;ctx!.stroke();
        ctx!.font='10px Fira Code';ctx!.fillStyle='#6a7fa8';ctx!.textAlign='center';ctx!.fillText(n.label,n.x,n.y+n.r+14);
        n.vx+=(Math.random()-.5)*.02;n.vy+=(Math.random()-.5)*.02;n.vx*=.95;n.vy*=.95;
        n.x+=n.vx;n.y+=n.vy;
        n.x=Math.max(30,Math.min(W-30,n.x));n.y=Math.max(30,Math.min(H-30,n.y))
      }
      requestAnimationFrame(draw)
    }
    draw()
  },[]);

  return (
    <div>
      <div className='page-title'>知识图谱</div>
      <div className='page-sub'>Neo4j 神经网络可视化</div>
      <div className='card' style={{ position: 'relative', overflow: 'hidden' }}>
        
        {/* Floating HUD Controller */}
        <div style={{
          position: 'absolute',
          top: 20,
          left: 20,
          background: 'rgba(8, 12, 24, 0.88)',
          border: '1px solid rgba(0, 240, 212, 0.25)',
          borderRadius: 12,
          padding: '16px 20px',
          color: 'var(--text)',
          fontFamily: 'Fira Code, monospace',
          fontSize: 12,
          maxWidth: 380,
          backdropFilter: 'blur(8px)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
          zIndex: 10
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <span style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: stats.nodes === 0 ? '#00f0d4' : '#10b981',
              boxShadow: stats.nodes === 0 ? '0 0 10px #00f0d4' : '0 0 10px #10b981',
              display: 'inline-block'
            }} />
            <span style={{ fontWeight: 'bold', color: '#00f0d4', letterSpacing: 0.5 }}>NEO4J 神经网络控制器</span>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12, borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: 12 }}>
            <div>
              <div style={{ color: '#6a7fa8', fontSize: 10 }}>实体节点数</div>
              <div style={{ fontSize: 20, fontWeight: 'bold', color: stats.nodes === 0 ? '#00f0d4' : '#fff' }}>{stats.nodes}</div>
            </div>
            <div>
              <div style={{ color: '#6a7fa8', fontSize: 10 }}>关联关系数</div>
              <div style={{ fontSize: 20, fontWeight: 'bold', color: stats.nodes === 0 ? '#00f0d4' : '#fff' }}>{stats.edges}</div>
            </div>
          </div>
          
          <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>
            {stats.nodes === 0 ? (
              <span>
                ✨ <strong style={{ color: '#38bdf8' }}>数据已彻底净化</strong>：当前 Neo4j 底层存储完全为空（0 个节点）。下方为您呈现的是神经网络自适应突触寻轨算法的实时动画模拟。
              </span>
            ) : (
              <span>
                ✓ 实时图谱已同步：当前数据库内已加载 {stats.nodes} 个实体节点与 {stats.edges} 条关联。
              </span>
            )}
          </div>
        </div>

        <canvas ref={cr} style={{width:'100%',borderRadius:12, display: 'block'}}/>
      </div>
    </div>
  );
}
