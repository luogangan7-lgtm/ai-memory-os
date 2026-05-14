import { useState } from 'react';
import { PROVIDERS, getRecommendations, type ProviderInfo } from '../data/models';

interface PipeConfig { provider: string; apiKey: string; model: string; purpose: string; }
const DEFAULTS: PipeConfig[] = [
  { provider:'deepseek', apiKey:'', model:'deepseek-v4-flash', purpose:'classifier' },
  { provider:'deepseek', apiKey:'', model:'deepseek-v4-pro', purpose:'reflection' },
  { provider:'alibaba', apiKey:'', model:'text-embedding-v4', purpose:'embedding' },
  { provider:'alibaba', apiKey:'', model:'gte-rerank-v2', purpose:'rerank' },
];
const LABELS: Record<string,{name:string;desc:string;icon:string}> = {
  classifier:{name:'内容分类器',desc:'自动将记忆分为常识/人物/代码/任务等类型',icon:'🏷️'},
  reflection:{name:'知识整合引擎',desc:'定期分析全量记忆，合并重复、发现关联',icon:'🔮'},
  embedding:{name:'向量化模型',desc:'将文本转为高维向量用于语义检索',icon:'🔢'},
  rerank:{name:'重排序模型',desc:'对检索结果进行精排，提升准确率',icon:'🎯'},
};

function filterProviders(purpose:string){return PROVIDERS.filter(p=>{if(purpose==='embedding'||purpose==='rerank')return p.features.includes('Embedding')||p.features.includes('Rerank');return p.features.includes('Chat')||p.features.includes('Reasoning')})}

function PipeCard({cfg,onChange}:{cfg:PipeConfig;onChange:(c:PipeConfig)=>void}){
const meta=LABELS[cfg.purpose]||{name:cfg.purpose,desc:'',icon:'⚙️'};
const prov=PROVIDERS.find(p=>p.id===cfg.provider);
const [testing,setTesting]=useState(false);
const [status,setStatus]=useState<'idle'|'ok'|'err'>('idle');
async function test(){
setTesting(true);setStatus('idle');
try{const r=await fetch((prov?.baseUrl||'').replace(/\/+$/,'')+'/chat/completions',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+cfg.apiKey},body:JSON.stringify({model:cfg.model,messages:[{role:'user',content:'hi'}],max_tokens:5})});
setStatus(r.ok?'ok':'err');}catch{setStatus('err')}finally{setTesting(false)}}
return(<div className='pipe-card'>
<div className='pipe-header'><span className='pipe-icon'>{meta.icon}</span><div><div className='pipe-name'>{meta.name}</div><div className='pipe-desc'>{meta.desc}</div></div><div className={`pipe-status ${status}`}>{status==='ok'?'✅ 已连接':status==='err'?'❌ 连接失败':''}</div></div>
<div className='pipe-body'><div className='pipe-row'>
<label>模型厂商</label><select value={cfg.provider} onChange={e=>onChange({...cfg,provider:e.target.value,model:''})}>{filterProviders(cfg.purpose).map(p=><option key={p.id} value={p.id}>{p.region==='cn'?'🇨🇳':p.region==='local'?'💻':'🌐'} {p.name}</option>)}</select></div>
<div className='pipe-row'><label>模型</label><select value={cfg.model} onChange={e=>onChange({...cfg,model:e.target.value})}>{prov?.models.filter(m=>{if(cfg.purpose==='embedding')return m.type==='embedding';if(cfg.purpose==='rerank')return m.type==='rerank';return m.type==='chat'||m.type==='reasoning'}).map(m=><option key={m.id} value={m.id}>{m.name}{m.recommended?' ★':''}{m.price?' · '+m.price:''}{m.ctx?' · '+(m.ctx/1000).toFixed(0)+'k':''}</option>)}</select></div>
<div className='pipe-row'><label>API Key</label><input type='password' value={cfg.apiKey} onChange={e=>onChange({...cfg,apiKey:e.target.value})} placeholder='sk-...'/></div>
<div className='pipe-row' style={{justifyContent:'flex-end'}}><button className='btn btn-teal' onClick={test} disabled={testing||!cfg.apiKey}>{testing?'测试中...':'🔗 测试连接'}</button></div></div></div>)}


const FEATURE_ZH:Record<string,string>={'Chat':'对话','Vision':'视觉','Embedding':'向量化','Rerank':'重排序','Audio':'语音','Reasoning':'推理','Voice':'语音'};
export function ModelConfigPage(){
const[cfgs,setCfgs]=useState<PipeConfig[]>(DEFAULTS);
const[saved,setSaved]=useState(false);
async function saveAll(){
try{await fetch('/admin/providers/configure',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({configs:cfgs.map(c=>({purpose:c.purpose,provider:c.provider,model:c.model}))})});
setSaved(true);setTimeout(()=>setSaved(false),2000)}catch{setSaved(false)}}
const recs=getRecommendations('classifier').concat(getRecommendations('reflection'),getRecommendations('embedding'),getRecommendations('rerank'));
const cn=PROVIDERS.filter(p=>p.region==='cn');
const intl=PROVIDERS.filter(p=>p.region==='intl');
const local=PROVIDERS.filter(p=>p.region==='local');
const ProviderListItem=({p}:{p:ProviderInfo})=>(<div className='card' style={{padding:16}}><div style={{fontWeight:600,marginBottom:8}}><span>{p.region==='cn'?'🇨🇳':p.region==='local'?'💻':'🌐'}</span> {p.name} <span style={{fontSize:11,color:'var(--muted)'}}>{p.nameZh}</span></div><div style={{display:'flex',gap:4,flexWrap:'wrap',marginBottom:8}}>{p.features.map(f=><span key={f} className='badge badge-violet' style={{fontSize:9}}>{FEATURE_ZH[f]||f}</span>)}</div><div style={{fontSize:10,color:'var(--muted)',marginBottom:4,fontFamily:'var(--mono)'}}>{p.baseUrl}</div><div style={{fontSize:10,color:'var(--dim)'}}>{p.models.length} models</div></div>);
return(<div>
<div className='page-header'><div><div className='page-title'>模型配置中心</div><div className='page-sub'>配置 AI Memory OS 各管线的底层大模型——分类、反思、向量化、重排序</div></div>
<button className={`btn ${saved?'btn-emerald':'btn-teal'}`} onClick={saveAll} style={{fontSize:14,padding:'10px 24px'}}>{saved?'✅ 已保存':'💾 保存全部配置'}</button></div>
<div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(380px,1fr))',gap:20,marginBottom:30}}>
{cfgs.map((cfg,i)=><PipeCard key={i} cfg={cfg} onChange={(c)=>{const n=[...cfgs];n[i]=c;setCfgs(n)}}/>)}
</div>
<div className="card" style={{marginTop:20,marginBottom:20}}><div className="card-title">💡 推荐配置组合</div><div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))",gap:12}}>{recs.map(r=>{const prov=PROVIDERS.find(p=>p.id===r.p);return(<div key={r.m} className="card" style={{padding:16,cursor:"pointer",borderColor:"var(--border)"}} onClick={()=>{const n=[...cfgs];const idx=n.findIndex(c=>c.purpose===n[idx]?.purpose||"classifier");if(idx>=0)n[idx]={provider:r.p,model:r.m,apiKey:n[idx]?.apiKey||"",purpose:n[idx]?.purpose||"classifier"};setCfgs(n)}}><div style={{fontSize:12,color:"var(--teal)",marginBottom:4}}>{r.label}</div><div style={{fontSize:13,fontWeight:600}}>{prov?.name||r.p}</div><div style={{fontSize:11,color:"var(--muted)",fontFamily:"var(--mono)"}}>{r.m}</div></div>)})}</div></div><div className="card" style={{marginTop:20}}><div className="card-title">📋 可用模型清单</div>
<div style={{marginTop:16}}><div style={{fontSize:13,fontWeight:600,marginBottom:10}}>🇨🇳 中国厂商 ({cn.length})</div><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:14}}>{cn.map(p=><ProviderListItem key={p.id} p={p}/>)}</div></div>
<div style={{marginTop:16}}><div style={{fontSize:13,fontWeight:600,marginBottom:10}}>🌐 海外厂商 ({intl.length})</div><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:14}}>{intl.map(p=><ProviderListItem key={p.id} p={p}/>)}</div></div>
{local.length>0&&<div style={{marginTop:16}}><div style={{fontSize:13,fontWeight:600,marginBottom:10}}>💻 本地模型 ({local.length})</div><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:14}}>{local.map(p=><ProviderListItem key={p.id} p={p}/>)}</div></div>}
</div>
<LocalDetect/></div>)}

function LocalDetect(){
const[scanning,setScanning]=useState(false);const[results,setResults]=useState<string[]>([]);
async function scan(){setScanning(true);setResults([]);const f:string[]=[];
for(const u of['http://localhost:11434/v1','http://localhost:1234/v1','http://localhost:4891/v1']){try{const r=await fetch(u+'/models',{signal:AbortSignal.timeout(3000)});const d=await r.json();const m=d.data||d.models||[];f.push(u+' OK ('+m.length+' models)')}catch{f.push(u+' offline')}}
setResults(f);setScanning(false)}
return(<div className='card' style={{marginTop:20}}><div className='card-head'><div className='card-title'>💻 本地模型检测</div><button className='btn btn-teal' onClick={scan} disabled={scanning}>{scanning?'扫描中...':'🔍 扫描'}</button></div>
{results.length>0&&<div style={{fontFamily:'var(--mono)',fontSize:12,lineHeight:2}}>{results.map((r,i)=><div key={i}>{r}</div>)}</div>}
<div style={{marginTop:8,fontSize:11,color:'var(--muted)'}}>Ollama(11434) · LM Studio(1234) · vLLM(4891)</div></div>)}
