import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';

function Dashboard() {
  const [tab, setTab] = useState<"memory" | "connect">("memory");
  const { logout } = useAuth();
  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "40px 24px" }}>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <div className="logo-orb" style={{ margin: "0 auto 16px", width: 56, height: 56, fontSize: 26, borderRadius: 16 }}>🧠</div>
        <div className="page-title" style={{ textAlign: "center" }}>我的记忆空间</div>
        <div className="page-sub" style={{ textAlign: "center" }}>记忆管理 · MCP 接入</div>
        <button className="btn btn-ghost btn-sm" style={{ marginTop: 8 }} onClick={logout}>退出登录</button>
      </div>
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginBottom: 24 }}>
        <button className={`btn ${tab === "memory" ? "btn-teal" : "btn-ghost"}`} onClick={() => setTab("memory")}>🧠 我的记忆</button>
        <button className={`btn ${tab === "connect" ? "btn-teal" : "btn-ghost"}`} onClick={() => setTab("connect")}>🔑 接入配置</button>
      </div>
      {tab === "memory" && <MemoryPanel />}
      {tab === "connect" && <ConnectPanel />}
    </div>
  );
}

// ── Login & Register Overlay (Premium Edition) ─────────────────────────────────────────────
import "../css/login.css";

export function LoginOverlay() {
  const { login, signup, error: authError, isAuthenticated } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const isUserApp = window.location.hash.includes("/app") || window.location.pathname.startsWith("/app");

  if (isAuthenticated) { return (<Dashboard />); }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalError(null);
    setLoading(true);
    
    try {
      if (isRegister) {
        if (!email || !username || !password) {
          setLocalError("请填写所有字段");
          setLoading(false);
          return;
        }
        await signup(username, email, password);
        setIsRegister(false);
        setLocalError(null);
        alert("注册成功！请使用邮箱登录。验证码已发送至控制台。");
      } else {
        const id = isUserApp ? email : "admin";
        if (!id || !password) {
          setLocalError("请输入完整凭据");
          setLoading(false);
          return;
        }
        await login(id, password);
        // Precise redirect for immediate access
        window.location.href = isUserApp ? "/app/#/app" : "/manage/#/";
      }
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : String(err) || "操作失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-overlay">
      <div className="login-box">
        <div className="login-logo">🧠</div>
        <div className="login-title">
          {isUserApp ? (isRegister ? "创建数字凭证" : "验证记忆权限") : "管理中心授权"}
        </div>
        <div className="login-sub">
          {isUserApp 
            ? (isRegister ? "正在为您建立个人记忆隔离区..." : "正在尝试连接您的加密记忆节点...")
            : "请输入管理员指令集以进入 Command Deck"}
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-5 mt-8">
          {isUserApp && isRegister && (
            <div className="form-group">
              <label>Node Identity (用户名)</label>
              <div className="input-wrapper">
                <span className="input-icon">👤</span>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="User_Name..."
                  className="form-input"
                  autoComplete="off"
                />
              </div>
            </div>
          )}
          
          {isUserApp && (
            <div className="form-group">
              <label>Communication Link (电子邮箱)</label>
              <div className="input-wrapper">
                <span className="input-icon">📧</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="mail@memory-os.com"
                  className="form-input"
                  autoComplete="email"
                />
              </div>
            </div>
          )}

          <div className="form-group">
            <label>Security Key (访问密码)</label>
            <div className="input-wrapper">
              <span className="input-icon">🔐</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="form-input"
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-premium w-full py-4 text-sm tracking-widest mt-2"
            disabled={loading}
          >
            {loading ? "AUTHENTICATING..." : (isRegister ? "INITIALIZE NODE" : "ESTABLISH LINK")}
          </button>
        </form>

        {isUserApp && (
          <div className="mt-6 text-center">
            <button 
              className="text-muted hover:text-teal-400 transition-colors text-xs font-mono uppercase tracking-tighter"
              onClick={() => setIsRegister(!isRegister)}
            >
              {isRegister ? "// ALREADY HAVE ACCESS" : "// NEED NEW CREDENTIALS"}
            </button>
          </div>
        )}

        {(localError || authError) && (
          <div className="login-error mt-6 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-xs font-mono animate-pulse">
            [ERROR]: {localError || authError}
          </div>
        )}
      </div>
    </div>
  );
}

function MemoryPanel(){
const [memories,setMemories]=useState<{title:string;content:string}[]>([]);
const [query,setQuery]=useState('');
const search=useCallback(async()=>{try{const r=await fetch('/memory/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:query||'*',limit:20})});const d=await r.json();setMemories(d.results||d.memories||[])}catch{setMemories([])}},[query]);
useEffect(()=>{search()},[search]);
return(<div className='card'><div className='card-title'>🧠 我的记忆</div><div style={{display:'flex',gap:8,marginBottom:12}}><input value={query} onChange={e=>setQuery(e.target.value)} style={{flex:1,background:'rgba(4,8,16,.85)',border:'1px solid var(--border)',borderRadius:10,padding:'10px 14px',color:'var(--text)',fontSize:13,outline:'none'}} placeholder='搜索记忆...' onKeyDown={e=>e.key==='Enter'&&search()}/><button className='btn btn-teal' onClick={search}>搜索</button></div><div style={{maxHeight:300,overflow:'auto'}}>{memories.map((m,i)=><div key={i} style={{padding:'8px 0',borderBottom:'1px solid var(--border)',fontSize:13}}><div style={{fontWeight:600}}>{m.title||'无标题'}</div><div style={{color:'var(--muted)',fontSize:12,marginTop:2}}>{m.content?.substring(0,150)}</div></div>)}</div></div>)}

function ConnectPanel(){
const [connected,setConnected]=useState("checking");
useEffect(()=>{function c(){fetch(window.location.origin+"/").then(r=>setConnected(r.ok?"online":"offline")).catch(()=>setConnected("offline"))};c();const i=setInterval(c,8e3);return()=>clearInterval(i)},[]);
const [token]=useState("mos_"+Math.random().toString(36).slice(2,10)+"_"+Array.from({length:32},()=>Math.floor(Math.random()*16).toString(16)).join(""));
const [copied,setCopied]=useState(false);
return(<div className="card"><div className="card-title">🔑 接入配置</div>
<div style={{marginBottom:16,display:"flex",alignItems:"center",gap:8}}><div style={{width:8,height:8,borderRadius:"50%",background:connected==="online"?"var(--emerald)":"var(--crimson)"}}/><span style={{fontSize:13,color:connected==="online"?"var(--emerald)":"var(--crimson)"}}>{connected==="online"?"已连接到服务器":"服务器不可达"}</span></div>
<div style={{marginBottom:16}}><div style={{fontSize:11,color:"var(--muted)",marginBottom:6}}>你的 MCP Token</div>
<code style={{display:"block",background:"rgba(0,0,0,.45)",padding:"12px",borderRadius:10,fontSize:12,fontFamily:"var(--mono)",wordBreak:"break-all",marginBottom:8}}>{token}</code>
<button className="btn btn-teal" onClick={()=>{navigator.clipboard.writeText(token);setCopied(true);setTimeout(()=>setCopied(false),2000)}}>{copied?"已复制":"📋 复制 Token"}</button></div></div>)}
