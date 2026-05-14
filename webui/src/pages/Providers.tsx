import { useState } from 'react';
import { PROVIDERS, getRecommendations, getLocalProviders, type ProviderInfo, type ModelInfo } from '../data/models';

function ProviderCard({p,selected,onToggle}:{p:ProviderInfo;selected:boolean;onToggle:()=>void}){
return(<div className={`card ${selected?'card-selected':''}`} style={{cursor:'pointer'}} onClick={onToggle}>
<div className='card-head'><div className='card-title'>
<span>{p.region==='cn'?'🇨🇳':p.region==='local'?'💻':'🌐'}</span> {p.name} <span style={{fontSize:11,color:'var(--muted)',fontWeight:400}}>{p.nameZh}</span>
{selected&&<span className='badge badge-teal' style={{marginLeft:8}}>ACTIVE</span>}
</div></div>
{p.features&&<div style={{display:'flex',gap:6,flexWrap:'wrap',marginBottom:12}}>{p.features.map(f=><span key={f} className='badge badge-violet'>{f}</span>)}</div>}
{selected&&<div style={{marginTop:12}}><div style={{fontSize:11,color:'var(--muted)',marginBottom:8,fontFamily:'var(--mono)'}}>Models:</div>
{p.models.map(m=><ModelBadge key={m.id} model={m}/>)}</div>}
</div>)}
function ModelBadge({model}:{model:ModelInfo}){
return(<div style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'6px 10px',marginBottom:4,background:'rgba(0,240,212,.04)',borderRadius:8,fontSize:12}}>
<div style={{display:'flex',alignItems:'center',gap:6}}><span style={{color:'var(--text)',fontFamily:'var(--mono)'}}>{model.name}</span>{model.recommended&&<span className='badge badge-amber'>REC</span>}{model.ctx&&<span style={{color:'var(--dim)',fontSize:10}}>{Math.round(model.ctx/1000)}k</span>}{model.size&&<span style={{color:'var(--dim)',fontSize:10}}>{model.size}</span>}</div>
<span style={{color:'var(--muted)',fontSize:10}}>{model.type}</span></div>)}

export function ProvidersPage(){
const[sel,setSel]=useState<string|null>(null);
const[tab,setTab]=useState<'all'|'cn'|'intl'|'local'>('all');
const recs=getRecommendations('classifier');
const local=getLocalProviders();
const filtered=PROVIDERS.filter(p=>tab==='all'||p.region===tab);
return(<div>
<div className='page-header'><div><div className='page-title'>System Compute</div><div className='page-sub'>LLM Provider Configuration — select models for classifier, reflection, embedding and rerank</div></div></div>
<div style={{display:'flex',gap:10,marginBottom:24}}>
{['all','cn','intl','local'].map(t=><button key={t} className={`btn ${tab===t?'btn-teal':'btn-ghost'}`} onClick={()=>setTab(t as "all"|"cn"|"intl"|"local")}>{t==='all'?'All':t==='cn'?'China':'International'}{t==='local'?' Local':''}</button>)}
</div>
<div className='card' style={{borderColor:'rgba(0,240,212,.25)',background:'linear-gradient(135deg,rgba(10,18,36,.95),rgba(0,240,212,.03))'}}>
<div className='card-title'><span>Recommended for Classifier</span></div>
<div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(240px,1fr))',gap:10}}>
{recs.map((r)=>{const prov=PROVIDERS.find(p=>p.id===r.p);return prov?<div key={r.p} className='card' style={{padding:14,cursor:'pointer',borderColor:sel===r.p?'var(--teal)':'var(--border)'}} onClick={()=>setSel(sel===r.p?null:r.p)}><div style={{fontSize:13,fontWeight:600,color:'var(--text)'}}>{prov.name}</div><div style={{fontSize:11,color:'var(--muted)',fontFamily:'var(--mono)',marginTop:4}}>{r.m}</div></div>:null})}
</div></div>
<div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:16,marginTop:24}}>
{filtered.map(p=><ProviderCard key={p.id} p={p} selected={sel===p.id} onToggle={()=>setSel(sel===p.id?null:p.id)}/>)}
</div>
{local.length>0&&<div className='card' style={{marginTop:24}}><div className='card-title'>Local Models Detected</div>
{local.map(p=><div key={p.id}><ProviderCard p={p} selected={sel===p.id} onToggle={()=>setSel(sel===p.id?null:p.id)}/></div>)}</div>}
</div>)}
