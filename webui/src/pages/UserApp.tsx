import { useState, useEffect, useRef, useCallback } from 'react';

function ChatPanel(){
const [msgs,setMsgs]=useState<{role:string;content:string}[]>([]);
const [input,setInput]=useState('');const [loading,setLoading]=useState(false);
const endRef=useRef<HTMLDivElement>(null);
async function send(){
if(!input.trim()||loading)return;
const m={role:'user',content:input};
setMsgs(p=>[...p,m]);setInput('');setLoading(true);
try{const res=await fetch('/v1/chat/completions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'deepseek-chat',messages:[...msgs,m]})});const d=await res.json();setMsgs(p=>[...p,{role:'assistant',content:d.choices?.[0]?.message?.content||'无响应'}])}catch{setMsgs(p=>[...p,{role:'assistant',content:'连接失败'}])}setLoading(false)}
useEffect(()=>{endRef.current?.scrollIntoView({behavior:'smooth'})},[msgs]);
return(<div className='card' style={{flex:2,display:'flex',flexDirection:'column',minHeight:500}}><div className='card-title'>💬 AI 对话</div><div style={{flex:1,overflow:'auto',maxHeight:400,marginBottom:12}}>{msgs.map((m,i)=><div key={i} style={{padding:'8px 12px',marginBottom:6,borderRadius:8,background:m.role==='user'?'rgba(0,240,212,.06)':'rgba(157,80,255,.06)',fontSize:13,lineHeight:1.7}}><span style={{color:m.role==='user'?'var(--teal)':'var(--violet)',fontWeight:600,fontSize:11}}>{m.role==='user'?'你':'AI'}: </span>{m.content}</div>)}<div ref={endRef}/></div><div style={{display:'flex',gap:8}}><input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&send()} placeholder='输入消息...' style={{flex:1}} disabled={loading}/><button className='btn btn-teal' onClick={send} disabled={loading}>{loading?'...':'发送'}</button></div></div>)}

function MemoryPanel(){
const [memories,setMemories]=useState<{title:string;content:string}[]>([]);
const [query,setQuery]=useState('');
const search=useCallback(async()=>{try{const r=await fetch('/memory/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:query||'*',limit:20})});const d=await r.json();setMemories(d.results||d.memories||[])}catch{setMemories([])}},[query]);
useEffect(()=>{search()},[search]);
return(<div className='card'><div className='card-title'>🧠 我的记忆</div><div style={{display:'flex',gap:8,marginBottom:12}}><input value={query} onChange={e=>setQuery(e.target.value)} placeholder='搜索记忆...' onKeyDown={e=>e.key==='Enter'&&search()}/><button className='btn btn-teal' onClick={search}>搜索</button></div><div style={{maxHeight:300,overflow:'auto'}}>{memories.map((m,i)=><div key={i} style={{padding:'8px 0',borderBottom:'1px solid var(--border)',fontSize:13}}><div style={{fontWeight:600}}>{m.title||'无标题'}</div><div style={{color:'var(--muted)',fontSize:12,marginTop:2}}>{m.content?.substring(0,150)}</div></div>)}</div></div>)}

function ConnectPanel(){
const[token]=useState(()=>'mos_'+Math.random().toString(36).slice(2,10)+'_'+Array.from({length:32},()=>Math.floor(Math.random()*16).toString(16)).join(''));
const[agent,setAgent]=useState<'cursor'|'claude'|'openclaw'|'cline'>('cursor');
const[tab,setTab]=useState<'config'|'prompt'>('config');
const[copied,setCopied]=useState(false);

const configs:Record<string,string>={
cursor:JSON.stringify({mcpServers:{"ai-memory-os":{command:"npx",args:["-y","@ai-memory-os/mcp","--token="+token,"--server=http://localhost:8003"]}}},null,2),
claude:JSON.stringify({mcpServers:{"ai-memory-os":{command:"npx",args:["-y","@ai-memory-os/mcp"],env:{MOS_TOKEN:token,MOS_SERVER:"http://localhost:8003"}}}},null,2),
openclaw:"SSE 远程接入 URL:\nhttp://localhost:8003/mcp?token="+token+"\n\n方式1: OpenClaw → MCP Servers → 添加 SSE → 粘贴上方 URL\n方式2: stdio 模式同上 Cursor 配置",
cline:JSON.stringify({"ai-memory-os":{command:"npx",args:["-y","@ai-memory-os/mcp","--token="+token,"--server=http://localhost:8003"],disabled:false,autoApprove:["memory_search","memory_list","memory_status"]}},null,2)};

const promptText='[自动记忆规则 — 粘贴到 Agent 的 System Prompt]\n\n1. 对话开始时用 memory_search 检索相关背景知识（静默）\n2. 获得重要信息时用 memory_store 自动写入（静默）\n3. 对话结束时保存有价值内容的摘要（静默）\n4. 用户说"记住/忘掉/搜索记忆"时执行对应操作\n5. 所有记忆操作无需向用户报告，除非操作失败';

const cfgFiles:Record<string,string>={cursor:'~/.cursor/mcp.json',claude:'~/Library/Application Support/Claude/claude_desktop_config.json',openclaw:'OpenClaw → Settings → MCP Servers → Add SSE',cline:'VS Code → Cline → MCP Servers (JSON)'};

return(<div className='card'><div className='card-title'>🔑 接入配置</div>

<div style={{marginBottom:20}}>
<div style={{fontSize:11,color:'var(--muted)',marginBottom:6}}>你的 MCP Token（用于 Agent 连接记忆系统）</div>
<div style={{display:'flex',gap:8,alignItems:'center'}}>
<code style={{flex:1,background:'rgba(0,0,0,.3)',padding:'10px 14px',borderRadius:8,fontSize:12,fontFamily:'var(--mono)',wordBreak:'break-all'}}>{token}</code>
<button className='btn btn-teal' onClick={()=>{navigator.clipboard.writeText(token);setCopied(true);setTimeout(()=>setCopied(false),2000)}}>{copied?'✅ 已复制':'📋 复制'}</button></div></div>

<div style={{marginBottom:16}}><div style={{fontSize:11,color:'var(--muted)',marginBottom:8}}>选择你的 Agent</div>
<div style={{display:'flex',gap:6,flexWrap:'wrap',marginBottom:12}}>
{['cursor','claude','openclaw','cline'].map(a=><button key={a} className={`btn ${agent===a?'btn-teal':'btn-ghost'}`} onClick={()=>setAgent(a as 'cursor'|'claude'|'openclaw'|'cline')} style={{fontSize:11}}>{a==='cursor'?'Cursor':a==='claude'?'Claude Desktop':a==='openclaw'?'OpenClaw (SSE)':'Cline'}</button>)}
</div></div>

<div style={{display:'flex',gap:8,marginBottom:12}}>
<button className={`btn ${tab==='config'?'btn-teal':'btn-ghost'}`} onClick={()=>setTab('config')} style={{fontSize:11}}>⚙️ 配置文件</button>
<button className={`btn ${tab==='prompt'?'btn-teal':'btn-ghost'}`} onClick={()=>setTab('prompt')} style={{fontSize:11}}>📝 系统提示词</button></div>

{tab==='config'&&<>
<div style={{fontSize:11,color:'var(--muted)',marginBottom:6}}>配置文件位置: {cfgFiles[agent]}</div>
<code style={{display:'block',background:'rgba(0,0,0,.3)',padding:'12px',borderRadius:8,fontSize:11,fontFamily:'var(--mono)',whiteSpace:'pre-wrap',maxHeight:250,overflow:'auto'}}>{configs[agent]||""}</code>
<button className='btn btn-ghost' style={{marginTop:8,fontSize:11}} onClick={()=>{navigator.clipboard.writeText(configs[agent]||"");setCopied(true);setTimeout(()=>setCopied(false),2000)}}>📋 复制配置</button></>}

{tab==='prompt'&&<>
<div style={{fontSize:11,color:'var(--muted)',marginBottom:6}}>粘贴到 Agent 的 System Prompt / 自定义指令中</div>
<code style={{display:'block',background:'rgba(0,0,0,.3)',padding:'12px',borderRadius:8,fontSize:11,fontFamily:'var(--mono)',whiteSpace:'pre-wrap',maxHeight:250,overflow:'auto',lineHeight:1.8}}>{promptText}</code>
<button className='btn btn-ghost' style={{marginTop:8,fontSize:11}} onClick={()=>{navigator.clipboard.writeText(promptText);setCopied(true);setTimeout(()=>setCopied(false),2000)}}>📋 复制提示词</button></>}
</div>)}

export function UserAppPage(){
const [tab,setTab]=useState<'chat'|'memory'|'connect'>('chat');
return(<div style={{maxWidth:900,margin:'0 auto',padding:'40px 24px'}}><div style={{textAlign:'center',marginBottom:32}}><div className='logo-orb' style={{margin:'0 auto 16px',width:56,height:56,fontSize:26,borderRadius:16}}>🧠</div><div className='page-title' style={{textAlign:'center'}}>我的记忆空间</div><div className='page-sub' style={{textAlign:'center'}}>AI 对话 · 记忆管理 · MCP 接入</div></div><div style={{display:'flex',gap:10,justifyContent:'center',marginBottom:24}}>{(['chat','memory','connect'] as const).map(t=><button key={t} className={`btn ${tab===t?'btn-teal':'btn-ghost'}`} onClick={()=>setTab(t)}>{t==='chat'?'💬 AI 对话':t==='memory'?'🧠 我的记忆':'🔑 接入配置'}</button>)}</div>{tab==='chat'&&<ChatPanel/>}{tab==='memory'&&<MemoryPanel/>}{tab==='connect'&&<ConnectPanel/>}</div>)}
