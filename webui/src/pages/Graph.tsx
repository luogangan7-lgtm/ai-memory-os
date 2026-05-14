import { useRef, useEffect } from 'react';
export function GraphPage(){
const cr=useRef<HTMLCanvasElement>(null);
useEffect(()=>{const c=cr.current;if(!c)return;const ctx=c.getContext('2d');if(!ctx)return;c.width=c.parentElement!.clientWidth||800;c.height=500;
const nodes=Array.from({length:20},(_,i)=>({x:Math.random()*c.width,y:Math.random()*c.height,r:8+Math.random()*6,label:'Node '+(i+1)}));
function draw(){ctx!.clearRect(0,0,c!.width,c!.height);
ctx!.strokeStyle='rgba(0,240,212,.2)';ctx!.lineWidth=1;
for(let i=0;i<30;i++){const a=nodes[Math.floor(Math.random()*20)]!,b=nodes[Math.floor(Math.random()*20)]!;ctx!.beginPath();ctx!.moveTo(a.x,a.y);ctx!.lineTo(b.x,b.y);ctx!.stroke()}
nodes.forEach(n=>{ctx!.beginPath();ctx!.arc(n.x,n.y,n.r,0,Math.PI*2);ctx!.fillStyle='rgba(0,240,212,.6)';ctx!.fill();ctx!.strokeStyle='#00f0d4';ctx!.stroke();
ctx!.font='10px Fira Code';ctx!.fillStyle='#e4eeff';ctx!.textAlign='center';ctx!.fillText(n.label,n.x,n.y+n.r+14);n.x+=(Math.random()-.5)*.5;n.y+=(Math.random()-.5)*.5;n.x=Math.max(20,Math.min(c!.width-20,n.x));n.y=Math.max(20,Math.min(c!.height-20,n.y))})
requestAnimationFrame(draw)}draw()},[]);
return(<div><div className='page-title'>Knowledge Graph</div><div className='page-sub'>Neo4j neural network visualization</div><div className='card'><canvas ref={cr} style={{width:'100%',borderRadius:12}}/></div></div>)}
