import { useRef, useEffect } from 'react';
export function GraphPage(){
const cr=useRef<HTMLCanvasElement>(null);
useEffect(()=>{
const c=cr.current;if(!c)return;
const ctx=c.getContext('2d');if(!ctx)return;
c.width=c.parentElement!.clientWidth||800;c.height=500;
const N=30;
const nodes=Array.from({length:N},(_,i)=>({x:Math.random()*c.width,y:Math.random()*c.height,r:6+Math.random()*8,label:'Node '+(i+1),vx:0,vy:0}));
const links:number[][]=[];
for(let i=0;i<N;i++)for(let j=i+1;j<N;j++){
const dx=nodes[i]!.x-nodes[j]!.x,dy=nodes[i]!.y-nodes[j]!.y;
if(Math.sqrt(dx*dx+dy*dy)<120)links.push([i,j])}
const W=c.width,H=c.height;
function draw(){
ctx!.clearRect(0,0,W,H);
ctx!.strokeStyle='rgba(0,240,212,.12)';ctx!.lineWidth=.8;
for(const[a,b]of links as [number,number][]){ctx!.beginPath();ctx!.moveTo(nodes[a]!.x,nodes[a]!.y);ctx!.lineTo(nodes[b]!.x,nodes[b]!.y);ctx!.stroke()}
for(const n of nodes){
ctx!.beginPath();ctx!.arc(n.x,n.y,n.r,0,Math.PI*2);
ctx!.fillStyle='rgba(0,240,212,.5)';ctx!.fill();
ctx!.strokeStyle='#00f0d4';ctx!.lineWidth=1;ctx!.stroke();
ctx!.font='10px Fira Code';ctx!.fillStyle='#6a7fa8';ctx!.textAlign='center';ctx!.fillText(n.label,n.x,n.y+n.r+14);
n.vx+=(Math.random()-.5)*.02;n.vy+=(Math.random()-.5)*.02;n.vx*=.95;n.vy*=.95;
n.x+=n.vx;n.y+=n.vy;
n.x=Math.max(30,Math.min(W-30,n.x));n.y=Math.max(30,Math.min(H-30,n.y))
}
requestAnimationFrame(draw)}draw()},[]);
return(<div><div className='page-title'>知识图谱</div><div className='page-sub'>Neo4j 神经网络可视化</div><div className='card'><canvas ref={cr} style={{width:'100%',borderRadius:12}}/></div></div>)}
