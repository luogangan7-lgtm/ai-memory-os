import { useEffect, useState, useRef, useCallback } from 'react';
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { getStats, getThroughput, getHealth } from '../api/endpoints';
import type { DashboardStats, ServiceHealth } from '../api/types';
import { useToast } from '../contexts/ToastContext';
Chart.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler);
type StatColor = 'teal' | 'violet' | 'emerald' | 'amber';
function StatCard({color,label,value,sub}:{color:StatColor;label:string;value:string;sub:string}){return <div className={`stat-card ${color}`}><div className='stat-label'>{label}</div><div className='stat-value'>{value}</div><div className='stat-sub'>{sub}</div></div>}
const SVCS:{key:keyof ServiceHealth;label:string}[]=[{key:'postgres',label:'PostgreSQL'},{key:'qdrant',label:'Qdrant'},{key:'neo4j',label:'Neo4j'},{key:'redis',label:'Redis'},{key:'minio',label:'MinIO'}];
export function DashboardPage(){const{toast}=useToast();const[s,setStats]=useState<DashboardStats|null>(null);const[tl,setTpL]=useState<string[]>([]);const[tv,setTpV]=useState<number[]>([]);const[svc,setSvc]=useState<ServiceHealth|null>(null);const[log,setLog]=useState<string[]>(['[SYS] Online.']);const lr=useRef<HTMLDivElement>(null);
const ld=useCallback(async()=>{try{const[sr,tp,h]=await Promise.all([getStats(),getThroughput(),getHealth()]);setStats(sr);setTpL(tp.labels);setTpV(tp.values);setSvc(h.services as ServiceHealth);setLog(p=>[...p,`[${new Date().toLocaleTimeString()}] ${sr.total} mems | ${sr.active_users} users`].slice(-50))}catch{toast('Load failed','err')}},[toast]);
useEffect(()=>{ld();const i=setInterval(ld,6000);return()=>clearInterval(i)},[ld]);useEffect(()=>{if(lr.current)lr.current.scrollTop=lr.current.scrollHeight},[log]);
const co={responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#4A6080',font:{size:10}},grid:{color:'rgba(0,229,255,0.05)'}},y:{ticks:{color:'#4A6080',font:{size:10}},grid:{color:'rgba(0,229,255,0.05)'}}}};
const td={labels:tl,datasets:[{data:tv,borderColor:'#00E5FF',backgroundColor:'rgba(0,229,255,0.05)',tension:0.4,fill:true,pointRadius:3,pointBackgroundColor:'#00E5FF'}]};
return(<div><div className='page-title'>COMMAND DECK</div><div className='page-sub'>实时系统状态监控</div>
<div className='stats-grid'><StatCard color='teal' label='GLOBAL MEMORIES' value={s?.total?.toLocaleString()??'—'} sub={s?.memory_growth??'加载中...'}/><StatCard color='violet' label='ACTIVE TENANTS' value={s?.active_users?.toLocaleString()??'—'} sub='注册租户总数'/><StatCard color='emerald' label='TODAY WRITES' value={s?.today_writes?.toLocaleString()??'—'} sub='实时写入频率'/><StatCard color='amber' label='TOKENS SAVED' value={s?.tokens_saved?.toLocaleString()??'—'} sub='全局 RAG 减免'/></div>
<div style={{display:'grid',gridTemplateColumns:'2fr 1fr',gap:18}}><div className='card'><div className='card-head'><div className='card-title'><div className='card-icon ci-teal'>📈</div>写入吞吐趋势</div></div><div className='chart-wrap'><Line options={co} data={td}/></div></div><div className='card'><div className='card-head'><div className='card-title'><div className='card-icon ci-emerald'>💚</div>服务健康</div></div><div>{SVCS.map(v=>(<div key={v.key} className='service-row'><div className='service-name'><div className={`status-dot ${svc?.[v.key]?'status-ok':'status-err'}`}/>{v.label}</div><span className={`badge ${svc?.[v.key]?'badge-emerald':'badge-red'}`}>{svc?.[v.key]?'ONLINE':'OFFLINE'}</span></div>))}</div></div></div>
<div className='card'><div className='card-head'><div className='card-title'><div className='card-icon ci-teal'>📡</div>实时写入日志</div></div><div className='log-stream' ref={lr}>{log.map((l,i)=><div key={i} className='log-info'>{l}</div>)}</div></div></div>);
}
