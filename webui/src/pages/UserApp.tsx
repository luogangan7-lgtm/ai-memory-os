import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api/client';

function Dashboard() {
  const [tab, setTab] = useState<"memory" | "connect" | "persona">("memory");
  const { logout, token, mcpKey } = useAuth();
  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "40px 24px" }}>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <div className="logo-orb" style={{ margin: "0 auto 16px", width: 56, height: 56, fontSize: 26, borderRadius: 16 }}>🧠</div>
        <div className="page-title" style={{ textAlign: "center" }}>我的记忆空间</div>
        <div className="page-sub" style={{ textAlign: "center" }}>记忆管理 · MCP 接入</div>
        <button className="btn btn-ghost btn-sm" style={{ marginTop: 8 }} onClick={logout}>退出登录</button>
      </div>
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginBottom: 24 }}>
        <button className={`btn ${tab === "memory" ? "btn-teal" : "btn-ghost"}`} onClick={() => setTab("memory")}>知识库</button>
        <button className={`btn ${tab === "connect" ? "btn-teal" : "btn-ghost"}`} onClick={() => setTab("connect")}>接入大模型</button>
      </div>
      {tab === "memory" && <MemoryPanel />}
      {tab === "connect" && <ConnectPanel token={mcpKey || token} />}
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
  const [memories,setMemories]=useState<{title:string;content:string;score:number}[]>([]);
  const [query,setQuery]=useState('');
  const [loading,setLoading]=useState(false);

  const search=useCallback(async()=>{
    if(loading)return;
    setLoading(true);
    try{
      const d = await api.post<any[]>('/memory/search', { query: query || "*", top_k: 20 });
      setMemories(d.map((x:any)=>({
        title: x.memory?.title || '无标题',
        content: x.chunk_text || x.memory?.content || '',
        score: x.score || 0
      })));
    }catch(e){
      console.error(e);
      setMemories([]);
    }finally{
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[query]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(()=>{search()},[]);

  return(
    <div className='card'>
      <div className='card-title'>🧠 我的记忆</div>
      <div style={{display:'flex',gap:8,marginBottom:12}}>
        <input value={query} onChange={e=>setQuery(e.target.value)} style={{flex:1,background:'rgba(4,8,16,.85)',border:'1px solid var(--border)',borderRadius:10,padding:'10px 14px',color:'var(--text)',fontSize:13,outline:'none'}} placeholder='搜索记忆...' onKeyDown={e=>e.key==='Enter'&&search()}/>
        <button className='btn btn-teal' onClick={search} disabled={loading}>{loading?'搜索中...':'搜索'}</button>
      </div>
      <div style={{maxHeight:400,overflow:'auto'}}>
        {memories.length === 0 && !loading && <div style={{padding:20,textAlign:'center',color:'var(--muted)',fontSize:13}}>暂无记忆数据或未搜索到结果</div>}
        {memories.map((m,i)=>(
          <div key={i} style={{padding:'12px 0',borderBottom:'1px solid var(--border)',fontSize:13}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
              <div style={{fontWeight:600,color:'var(--teal)'}}>{m.title}</div>
              <div style={{fontSize:10,color:'var(--muted)'}}>相关度: {(m.score*100).toFixed(1)}%</div>
            </div>
            <div style={{color:'var(--text)',fontSize:12,marginTop:6,lineHeight:1.6}}>{m.content}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ConnectPanel({token:propToken}:{token?:string}){

const[connected,setConnected]=useState<'checking'|'online'|'offline'>('checking');
useEffect(()=>{function check(){fetch(window.location.origin+'/').then(r=>setConnected(r.ok?'online':'offline')).catch(()=>setConnected('offline'))};check();const i=setInterval(check,8000);return ()=>clearInterval(i)},[]);
const[token]=useState(()=>propToken||'mos_'+Math.random().toString(36).slice(2,10)+'_'+Array.from({length:32},()=>Math.floor(Math.random()*16).toString(16)).join(''));
const[agent,setAgent]=useState<'cursor'|'claude'|'openclaw'|'cline'|'continue'|'roo'|'codex'>('cursor');
const[copied,setCopied]=useState(false);

const configs={cursor:JSON.stringify({mcpServers:{"ai-memory-os":{command:"npx",args:["-y","@ai-memory-os/mcp","--token="+token,"--server=http://localhost:8003"],env:{}}}},null,2),
claude:JSON.stringify({mcpServers:{"ai-memory-os":{command:"npx",args:["-y","@ai-memory-os/mcp"],env:{MOS_TOKEN:token,MOS_SERVER:"http://localhost:8003"}}}},null,2),
openclaw:"SSE 地址: http://localhost:8003/mcp?token="+token,
cline:JSON.stringify({"ai-memory-os":{command:"npx",args:["-y","@ai-memory-os/mcp","--token="+token,"--server=http://localhost:8003"],disabled:false,autoApprove:["memory_search","memory_list","memory_status"]}},null,2),
continue:JSON.stringify({experimental:{modelContextProtocolServers:[{transport:{type:"stdio",command:"npx",args:["-y","@ai-memory-os/mcp","--token="+token,"--server=http://localhost:8003"]}}]}},null,2),
roo:JSON.stringify({"ai-memory-os":{command:"npx",args:["-y","@ai-memory-os/mcp","--token="+token,"--server=http://localhost:8003"],alwaysAllow:["memory_search","memory_store"]}},null,2),
codex:"# ~/.codex/config.toml\n[[mcp_servers]]\nname = \"ai-memory-os\"\ncommand = \"npx\"\nargs = [\"-y\", \"@ai-memory-os/mcp\", \"--token="+token+"\", \"--server=http://localhost:8003\"]"};

const FILE_PATHS={cursor:'~/.cursor/mcp.json',claude:'~/Library/Application Support/Claude/claude_desktop_config.json',openclaw:'OpenClaw → Settings → MCP Servers',cline:'VS Code → Cline → MCP Servers',continue:'~/.continue/config.json',roo:'VS Code → Roo Code → MCP Servers',codex:'~/.codex/config.toml'};

const AGENTS=[{id:'cursor',name:'Cursor'},{id:'claude',name:'Claude Desktop'},{id:'openclaw',name:'OpenClaw (SSE)'},{id:'cline',name:'Cline'},{id:'continue',name:'Continue'},{id:'roo',name:'Roo Code'},{id:'codex',name:'Codex CLI'}];

const SETUP_STEPS={cursor:['1. 打开 Cursor → Settings → MCP','2. 点击 Add Server → 选择 Command','3. 复制上方 JSON 粘贴到配置框','4. 点击 Save，重启 Cursor','5. 在聊天框输入"检索我的记忆"测试'],
claude:['1. 打开文件: ~/Library/Application Support/Claude/claude_desktop_config.json','2. 复制上方 JSON，粘贴到 mcpServers 字段','3. 保存文件，完全退出 Claude Desktop','4. 重新打开 Claude，发送新对话测试'],
openclaw:['1. 打开 OpenClaw → Agent 设置','2. 找到 MCP Servers → 添加 SSE','3. 粘贴上方 SSE URL','4. 保存后对话自动识别记忆工具'],
cline:['1. 打开 VS Code → 扩展 → Cline 设置','2. 找到 MCP Servers 配置 (JSON 格式)','3. 复制上方 JSON 粘贴到配置','4. 重启 VS Code，新对话自动加载'],
continue:['1. 打开文件: ~/.continue/config.json','2. 在 experimental.modelContextProtocolServers 数组中粘贴上方 JSON','3. 保存文件，重启 Continue 扩展'],
roo:['1. 打开 VS Code → Roo Code 扩展','2. Settings → MCP Servers → Add','3. 粘贴上方 JSON 配置','4. 保存后新对话即可使用'],
codex:['1. 打开文件: ~/.codex/config.toml','2. 复制上方配置粘贴到文件末尾','3. 保存文件','4. 运行 codex 命令，工具自动加载']};
const SYSTEM_PROMPTS={standard:'你已连接 AI Memory OS V6.0 长期记忆系统（8个工具）。\n\n【对话开始时，静默执行以下操作】：\n1. 调用 memory_get_persona → 了解用户背景和偏好\n2. 调用 memory_task_canvas_get → 恢复未完成任务（如有）\n3. 调用 memory_search(用户问题关键词) → 检索相关知识\n\n【对话中，发现以下内容时立即调用 memory_store】：\n- 用户偏好、习惯、要求\n- 技术决策及原因\n- 项目结构、约定、配置\n- 用户说"记住"的任何内容\n- 解决的复杂问题（问题+方案）\n\n【长任务进行中】：\n每完成一个重要阶段，调用 memory_task_canvas_update 更新 Mermaid 任务画布\n\n【对话结束时】：\n若对话产生了有价值的结论或方案，调用 memory_store 保存摘要\n\n所有上述操作静默完成，不向用户报告，除非操作失败',concise:'[记忆规则] ①开始→persona+search+canvas_get ②重要信息→store ③进展→canvas_update ④记住/忘掉/搜索→对应操作。静默执行。',dev:'你是连接了 AI Memory OS 的开发助手。记忆工具是你感知能力的延伸。\n\n【每次对话开始】静默执行：\n① memory_get_persona 了解技术栈和项目背景\n② memory_task_canvas_get 恢复上次未完成的开发任务\n③ memory_search(项目名/功能关键词) 检索相关代码约定\n\n【代码工作中】：\n- 确定了技术方案 → memory_store（tags: [\"架构决策\"]）\n- 解决了 Bug → memory_store（title: \"Bug修复: xxx\"，tags: [\"bug\", \"技术栈\"]）\n- 完成了功能阶段 → memory_task_canvas_update（更新进度图）\n\n【存储代码记忆时】：\n只存逻辑摘要和关键决策，不存完整大段代码。\n格式：问题背景 + 解决思路 + 关键代码片段（< 20行）\n\n所有操作静默完成。'};

const[pType,setPType]=useState<'standard'|'concise'|'dev'>('standard');

return(<div className='card'><div className='card-title'>🔑 接入配置</div>
<div style={{marginBottom:16,display:'flex',alignItems:'center',gap:8}}><div style={{width:8,height:8,borderRadius:'50%',background:connected==='online'?'var(--emerald)':connected==='offline'?'var(--crimson)':'var(--amber)',boxShadow:connected==='online'?'0 0 8px var(--emerald)':connected==='offline'?'0 0 8px var(--crimson)':'none'}}/><span style={{fontSize:13,color:connected==='online'?'var(--emerald)':connected==='offline'?'var(--crimson)':'var(--amber)'}}>{connected==='online'?'已连接到服务器':connected==='offline'?'服务器不可达':'检测中...'}</span></div>
<div style={{marginBottom:20,padding:"10px 14px",background:"rgba(255,179,71,.08)",borderRadius:10,border:"1px solid rgba(255,179,71,.2)",fontSize:12,color:"var(--amber)"}}>⚠️ 部署到服务器后，请将下方配置中的 <code style={{color:"var(--teal)",fontSize:11}}>localhost:8003</code> 替换为实际服务器地址。<hr style={{borderColor:"var(--border)",margin:"10px 0"}}/></div><div style={{marginBottom:20}}>
<div style={{fontSize:11,color:'var(--muted)',marginBottom:6}}>你的 MCP Token（Agent 连接记忆系统的凭证）</div>
<div style={{display:'flex',gap:8,alignItems:'center'}}>
<code style={{flex:1,background:'rgba(0,240,212,.05)',padding:'12px 16px',borderRadius:10,fontSize:13,fontFamily:'var(--mono)',wordBreak:'break-all',border:'1px solid rgba(0,240,212,.15)'}}>{token}</code>
<button className='btn btn-teal' onClick={()=>{navigator.clipboard.writeText(token);setCopied(true);setTimeout(()=>setCopied(false),2000)}}>{copied?'✅ 已复制':'📋 复制'}</button></div></div>

<div style={{marginBottom:16}}><div style={{fontSize:11,color:'var(--muted)',marginBottom:8}}>选择你的 Agent（{AGENTS.length} 种）</div>
<div style={{display:'flex',gap:6,flexWrap:'wrap',marginBottom:12}}>
{AGENTS.map(a=><button key={a.id} className={`btn ${agent===a.id?'btn-teal':'btn-ghost'}`} onClick={()=>setAgent(a.id as 'cursor'|'claude'|'openclaw'|'cline'|'continue'|'roo'|'codex')} style={{fontSize:11,padding:'8px 14px'}}>{a.name}</button>)}
</div></div>

<div style={{fontSize:10,color:'var(--muted)',marginBottom:4,fontFamily:'var(--mono)'}}>📁 保存位置:: {FILE_PATHS[agent]||'N/A'}</div>
<code style={{display:'block',background:'rgba(0,0,0,.45)',padding:'12px',borderRadius:8,fontSize:11,fontFamily:'var(--mono)',whiteSpace:'pre-wrap',maxHeight:220,overflow:'auto',marginBottom:8}}>{configs[agent]||''}</code>
<button className='btn btn-teal btn-sm' style={{fontSize:11,marginBottom:20}} onClick={()=>{navigator.clipboard.writeText(configs[agent]||'');setCopied(true);setTimeout(()=>setCopied(false),2000)}}>📋 复制配置</button>
<div style={{marginTop:14,padding:"12px 14px",background:"rgba(0,240,212,.04)",borderRadius:10,border:"1px solid var(--border)"}}><div style={{fontSize:11,fontWeight:600,color:"var(--teal)",marginBottom:8}}>📋 设置步骤</div>{SETUP_STEPS[agent]?.map((s,i)=><div key={i} style={{fontSize:12,color:"var(--text)",padding:"4px 0",lineHeight:1.6}}>{s}</div>)}</div>

<div style={{borderTop:'1px solid var(--border)',paddingTop:20,marginTop:4}}><div style={{fontSize:11,color:'var(--muted)',marginBottom:8}}>系统提示词（粘贴到 Agent 的 System Prompt）</div>
<div style={{display:'flex',gap:6,marginBottom:10}}>{Object.keys(SYSTEM_PROMPTS).map(k=><button key={k} className={`btn ${pType===k?'btn-teal':'btn-ghost'}`} onClick={()=>setPType(k as 'standard'|'concise'|'dev')} style={{fontSize:10}}>{k==='standard'?'📝 完整版':k==='concise'?'⚡ 精简版':'💻 开发版'}</button>)}</div>
<code style={{display:'block',background:'rgba(0,0,0,.45)',padding:'12px',borderRadius:8,fontSize:11,fontFamily:'var(--mono)',whiteSpace:'pre-wrap',lineHeight:1.8,maxHeight:200,overflow:'auto',marginBottom:8}}>{SYSTEM_PROMPTS[pType]}</code>
<button className='btn btn-teal btn-sm' style={{fontSize:11}} onClick={()=>{navigator.clipboard.writeText(SYSTEM_PROMPTS[pType]);setCopied(true);setTimeout(()=>setCopied(false),2000)}}>📋 复制提示词</button></div>
</div>)}
