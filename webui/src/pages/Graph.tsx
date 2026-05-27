import { useRef, useEffect, useState } from 'react';
import { api } from '../api/client';

export function GraphPage(){
  const cr=useRef<HTMLCanvasElement>(null);
  const [stats, setStats] = useState({ nodes: 0, edges: 0, status: "loading" });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [graphData, setGraphData] = useState<any>(null);

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
    api.get<any>("/graph/visualization").then(setGraphData).catch(()=>{});
  }, []);

  useEffect(()=>{
    const c=cr.current;if(!c)return;
    const ctx=c.getContext('2d');if(!ctx)return;
    c.width=c.parentElement!.clientWidth||800;c.height=500;
    const rawNodes = graphData?.nodes || [];
    const rawEdges = graphData?.edges || [];
    const cx=c.width/2,cy=c.height/2,r2=Math.min(c.width,c.height)*0.38;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nodes:any[] = rawNodes.length > 0
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ? rawNodes.map((n:any,i:number)=>({x:cx+Math.cos(2*Math.PI*i/rawNodes.length)*r2,y:cy+Math.sin(2*Math.PI*i/rawNodes.length)*r2,r:5+Math.random()*3,label:(n.title||n.name||n.label||n.id||"").slice(0,18),vx:0,vy:0}))
      : Array.from({length:30},(_,i)=>({x:Math.random()*c.width,y:Math.random()*c.height,r:6+Math.random()*8,label:"Node "+(i+1),vx:0,vy:0}));
    const links:number[][]=[];
    if(rawEdges.length>0){
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const idMap=new Map(nodes.map((n:any,i:number)=>[n.id,i]));
      for(const e of rawEdges){const a=idMap.get(e.source),b=idMap.get(e.target);if(a!==null&&b!==null&&a!==b)links.push([a as number,b as number])}
    } else {for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){const dx=Number(nodes[i]!.x)-Number(nodes[j]!.x),dy=Number(nodes[i]!.y)-Number(nodes[j]!.y);if(Math.sqrt(dx*dx+dy*dy)<120)links.push([i,j])}}
    const W=c.width,H=c.height;
    function draw(){
      ctx!.clearRect(0,0,W,H);
      ctx!.strokeStyle='rgba(45, 191, 168, 0.12)';ctx!.lineWidth=.8;
      for(const[a,b]of links as [number,number][]){
        ctx!.beginPath();ctx!.moveTo(nodes[a]!.x,nodes[a]!.y);ctx!.lineTo(nodes[b]!.x,nodes[b]!.y);ctx!.stroke()
      }
      for(const n of nodes){
        ctx!.beginPath();ctx!.arc(n.x,n.y,n.r,0,Math.PI*2);
        ctx!.fillStyle='rgba(45, 191, 168, 0.4)';ctx!.fill();
        ctx!.strokeStyle='#2DBFA8';ctx!.lineWidth=1;ctx!.stroke();
        ctx!.font='10px Fira Code, Courier New, monospace';ctx!.fillStyle='var(--v6-fg-muted)';ctx!.textAlign='center';ctx!.fillText(n.label,n.x,n.y+n.r+14);
        n.vx+=(Math.random()-.5)*.02;n.vy+=(Math.random()-.5)*.02;n.vx*=.95;n.vy*=.95;
        n.x+=n.vx;n.y+=n.vy;
        n.x=Math.max(30,Math.min(W-30,n.x));n.y=Math.max(30,Math.min(H-30,n.y))
      }
      requestAnimationFrame(draw)
    }
    draw()
  },[graphData]);

  return (
    <div>
      <h1 style={{ font: "600 22px var(--v6-font-sans)", color: "var(--v6-fg)", marginBottom: 4 }}>知识图谱 Knowledge Graph</h1>
      <div style={{ color: "var(--v6-fg-muted)", fontSize: 13, marginBottom: 24 }}>Neo4j 语义神经网络关联可视化 · Neo4j semantic neural network visualization</div>
      <div className="v6-card" style={{ position: 'relative', overflow: 'hidden' }}>
        
        {/* Floating HUD Controller */}
        <div style={{
          position: 'absolute',
          top: 20,
          left: 20,
          background: 'var(--v6-bg-elev)',
          border: '1px solid var(--v6-border)',
          borderRadius: 12,
          padding: '16px 20px',
          color: 'var(--v6-fg)',
          fontFamily: 'var(--v6-font-mono), monospace',
          fontSize: 12,
          maxWidth: 380,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
          zIndex: 10
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <span style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: stats.nodes === 0 ? 'var(--v6-fg-muted)' : '#2DBFA8',
              display: 'inline-block'
            }} />
            <span style={{ fontWeight: 'bold', color: 'var(--v6-fg)', letterSpacing: 0.5 }}>NEO4J 神经网络控制器 Neural Controller</span>
          </div>
          
          <div className='v6-grid-2col' style={{ gap: 12, marginBottom: 12, borderBottom: '1px solid var(--v6-border)', paddingBottom: 12 }}>
            <div>
              <div style={{ color: 'var(--v6-fg-muted)', fontSize: 10 }}>实体节点数 Nodes</div>
              <div style={{ fontSize: 20, fontWeight: 'bold', color: stats.nodes === 0 ? 'var(--v6-fg-muted)' : 'var(--v6-fg)' }}>{stats.nodes}</div>
            </div>
            <div>
              <div style={{ color: 'var(--v6-fg-muted)', fontSize: 10 }}>关联关系数 Edges</div>
              <div style={{ fontSize: 20, fontWeight: 'bold', color: stats.nodes === 0 ? 'var(--v6-fg-muted)' : 'var(--v6-fg)' }}>{stats.edges}</div>
            </div>
          </div>
          
          <div style={{ fontSize: 11, color: 'var(--v6-fg-muted)', lineHeight: 1.5 }}>
            {stats.nodes === 0 ? (
              <span>
                ✨ <strong>数据已彻底净化 Empty State</strong>: 当前 Neo4j 底层存储为空。下方呈现的是神经网络算法的实时动画模拟。
                <br />
                The database is empty. Showing an animated network simulation.
              </span>
            ) : (
              <span>
                ✓ <strong>实时图谱已同步 Synced</strong>: 当前已加载 {stats.nodes} 个实体节点与 {stats.edges} 条关联。
                <br />
                Loaded {stats.nodes} nodes and {stats.edges} edges from Neo4j.
              </span>
            )}
          </div>
        </div>

        <canvas ref={cr} style={{width:'100%',borderRadius:12, display: 'block'}}/>
      </div>
    </div>
  );
}
