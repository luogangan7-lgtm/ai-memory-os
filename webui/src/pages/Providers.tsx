import { useState } from 'react';
import { PROVIDERS, getRecommendations } from '../data/models';

interface ActiveConfig { provider: string; apiKey: string; model: string; purpose: string; }
const DEFAULT_CONFIGS: ActiveConfig[] = [
  { provider:'deepseek', apiKey:'', model:'deepseek-chat', purpose:'classifier' },
  { provider:'deepseek', apiKey:'', model:'deepseek-reasoner', purpose:'reflection' },
  { provider:'alibaba', apiKey:'', model:'text-embedding-v3', purpose:'embedding' },
  { provider:'alibaba', apiKey:'', model:'gte-rerank', purpose:'rerank' },
];

function ConfigRow({cfg,onChange}:{cfg:ActiveConfig;onChange:(c:ActiveConfig)=>void}){
const currentProvider = PROVIDERS.find(p=>p.id===cfg.provider);
return(<div style={{display:'grid',gridTemplateColumns:'1fr 1fr 2fr auto',gap:10,alignItems:'center',padding:'10px 14px',marginBottom:8,background:'rgba(0,240,212,.04)',borderRadius:10,border:'1px solid var(--border)'}}>
<div style={{fontSize:12,fontWeight:600,color:'var(--text)'}}>{cfg.purpose.toUpperCase()}</div>
<select value={cfg.provider} onChange={e=>onChange({...cfg,provider:e.target.value,model:''})} style={{fontSize:12}}>
{PROVIDERS.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
</select>
<div style={{display:'flex',gap:8}}>
<select value={cfg.model} onChange={e=>onChange({...cfg,model:e.target.value})} style={{flex:1,fontSize:12}}>
{currentProvider?.models.map(m=><option key={m.id} value={m.id}>{m.name}{m.recommended?' ★':''}</option>)}
</select>
<input type="password" value={cfg.apiKey} onChange={e=>onChange({...cfg,apiKey:e.target.value})} placeholder="API Key" style={{flex:1,fontSize:11}}/>
</div>
<button className='btn btn-ghost' onClick={async()=>{
const prov=PROVIDERS.find(p=>p.id===cfg.provider);
if(!cfg.apiKey||!prov){alert('Enter API key');return}
try{const res=await fetch(prov.baseUrl.replace(/\/+$/,'')+'/chat/completions',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+cfg.apiKey},body:JSON.stringify({model:cfg.model,messages:[{role:'user',content:'hi'}],max_tokens:5})});
const d=await res.json().catch(()=>({}));
alert(res.ok?'CONNECTED - '+cfg.model:'FAILED: '+(d.error?.message||res.status))
}catch(e: unknown){alert("Connection error: " + (e instanceof Error ? e.message : String(e)))}
}} style={{fontSize:11,padding:'4px 10px'}}>TEST</button>
</div>)}
export function ProvidersPage(){
const [configs,setConfigs]=useState<ActiveConfig[]>(DEFAULT_CONFIGS);
const [activeTab,setActiveTab]=useState<'config'|'browse'>('config');
const recs=getRecommendations('classifier');
const [saved,setSaved]=useState(false);
async function saveAll(){
try{
const payload=configs.map(c=>({purpose:c.purpose,provider:c.provider,model:c.model}));
await fetch('/admin/providers/configure',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({configs:payload})});
setSaved(true);setTimeout(()=>setSaved(false),2000);
}catch{alert('Save failed - backend offline')}
}
return(<div>
<div className='page-header'><div><div className='page-title'>System Compute</div><div className='page-sub'>Configure LLMs for each pipeline function</div></div>
<div style={{display:'flex',gap:8}}>
<button className={`btn ${activeTab==='config'?'btn-teal':'btn-ghost'}`} onClick={()=>setActiveTab('config')}>Configuration</button>
<button className={`btn ${activeTab==='browse'?'btn-teal':'btn-ghost'}`} onClick={()=>setActiveTab('browse')}>Browse Models</button>
</div></div>
{activeTab==='config'&&<>
<div className='card' style={{borderColor:'rgba(0,240,212,.2)'}}>
<div className='card-head'><div className='card-title'>Pipeline Configuration</div>
<button className='btn btn-teal' onClick={saveAll}>{saved?'✅ Saved':'💾 Save Config'}</button></div>
{configs.map((cfg,i)=><ConfigRow key={i} cfg={cfg} onChange={(c)=>{const n=[...configs];n[i]=c;setConfigs(n)}} />)}
</div>
<div className='card' style={{background:'linear-gradient(135deg,rgba(10,18,36,.95),rgba(0,240,212,.02))'}}>
<div className='card-title'>Recommended Configurations</div><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(220px,1fr))',gap:10}}>
{recs.map(r=>{const p=PROVIDERS.find(pp=>pp.id===r.p);return p?<div key={r.p} className='card' style={{padding:14,cursor:'pointer'}} onClick={()=>{const n=[...configs];n[0]={provider:r.p,model:r.m,apiKey:'',purpose:'classifier'};setConfigs(n)}}><div style={{fontSize:13,fontWeight:600}}>{p.name}</div><div style={{fontSize:11,color:'var(--muted)',fontFamily:'var(--mono)'}}>{r.m}</div></div>:null})}
</div></div></>}
{activeTab==='browse'&&<div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:16}}>
{PROVIDERS.map(p=><div key={p.id} className='card' style={{padding:18}}>
<div style={{fontSize:14,fontWeight:700,marginBottom:10}}><span>{p.region==='cn'?'🇨🇳':p.region==='local'?'💻':'🌐'}</span> {p.name} <span style={{fontSize:11,color:'var(--muted)',fontWeight:400}}>{p.nameZh}</span></div>
<div style={{display:'flex',gap:4,flexWrap:'wrap',marginBottom:10}}>{p.features.map(f=><span key={f} className='badge badge-violet' style={{fontSize:9}}>{f}</span>)}</div>
<div style={{fontSize:10,color:'var(--muted)',marginBottom:10}}>Base: <code style={{color:'var(--teal)',fontSize:10}}>{p.baseUrl}</code></div>
{p.models.slice(0,5).map(m=><div key={m.id} style={{display:'flex',justifyContent:'space-between',padding:'4px 0',fontSize:11,borderBottom:'1px solid rgba(40,65,110,.1)'}}><span style={{fontFamily:'var(--mono)',color:'var(--text)'}}>{m.name}</span><span style={{color:'var(--muted)'}}>{m.type}{m.ctx?' · '+Math.round(m.ctx/1000)+'k':''}{m.recommended?' ★':''}</span></div>)}
{p.models.length>5&&<div style={{fontSize:10,color:'var(--muted)',marginTop:6}}>+{p.models.length-5} more models</div>}
</div>)}</div>}
</div>)}
