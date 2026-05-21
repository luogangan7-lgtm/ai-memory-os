import { useState, useEffect, useCallback, useRef } from 'react';
import { PROVIDERS as ALL_PROVIDERS } from "../data/models";
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api/client';
import { getUserPipelineStatus, getUserDocuments, deleteUserDocument, UserDocument } from '../api/endpoints';
import type { PipelineStatus, PipelineJob } from '../api/types';
import { CortexMark } from '../components/CortexMark';

type DashTab = "memory" | "connect" | "persona" | "myllm" | "canvas" | "audit";
const DASH_TABS: { id: DashTab; label: string }[] = [
  { id: "memory", label: "知识库" },
  { id: "connect", label: "接入" },
  { id: "myllm", label: "LLM" },
  { id: "persona", label: "画像" },
  { id: "canvas", label: "画布" },
  { id: "audit", label: "操作记录" },
];

function Dashboard() {
  const [tab, setTab] = useState<DashTab>("memory");
  const { logout, token, mcpKey } = useAuth();
  return (
    <div className="v6-app">
      <div className="v6-app__shell">
        <nav className="v6-app__nav">
          <div className="v6-app__nav-brand">
            <CortexMark size={26} breathing />
            <span>Cortex</span>
          </div>
          <div className="v6-app__tabs">
            {DASH_TABS.map((t) => (
              <button
                key={t.id}
                className="v6-app__tab"
                aria-current={tab === t.id ? "page" : undefined}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="v6-app__nav-right">
            <LLMStatusBar />
            <button className="v6-btn v6-btn--ghost" onClick={logout}>
              Sign out
            </button>
          </div>
        </nav>
        <main className="v6-app__main">
          {tab === "memory" && <MemoryPanel />}
          {tab === "connect" && <ConnectPanel token={mcpKey || token} />}
          {tab === "myllm" && <MyLLMPanel />}
          {tab === "persona" && <PersonaPanel />}
          {tab === "canvas" && <CanvasPanel />}
          {tab === "audit" && <AuditPanel />}
        </main>
      </div>
    </div>
  );
}

// ── Login & Register Overlay (Premium Edition) ─────────────────────────────────────────────
import "../css/login.css";

export function LoginOverlay() {
  const { login, signup, error: authError, isAuthenticated } = useAuth();
  const isUserApp = window.location.hash.includes("/app") || window.location.pathname.startsWith("/app");
  const [mode, setMode] = useState<"landing" | "signin" | "signup">(isUserApp ? "landing" : "signin");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  if (isAuthenticated) return <Dashboard />;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalError(null);
    setLoading(true);
    try {
      if (mode === "signup") {
        if (!email || !username || !password) {
          setLocalError("请填写所有字段");
          setLoading(false);
          return;
        }
        await signup(username, email, password);
        setLocalError(null);
        alert("注册成功！请使用邮箱登录。");
        setMode("signin");
      } else {
        const id = isUserApp ? email : "admin";
        if (!id || !password) {
          setLocalError("请输入完整凭据");
          setLoading(false);
          return;
        }
        await login(id, password);
        window.location.href = isUserApp ? "/app/#/app" : "/manage/#/";
      }
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : String(err) || "操作失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="v6-auth">
      <div className="v6-auth__page">
        <nav className="v6-nav">
          <div className="v6-nav__brand">
            <CortexMark size={28} breathing />
            <span>Cortex</span>
          </div>
          <div className="v6-nav__actions">
            {isUserApp ? (
              <>
                {mode !== "signin" && (
                  <button className="v6-btn v6-btn--ghost" onClick={() => setMode("signin")}>
                    Sign in
                  </button>
                )}
                {mode !== "signup" && (
                  <button className="v6-btn" onClick={() => setMode("signup")}>
                    Sign up
                  </button>
                )}
                {mode !== "landing" && (
                  <button className="v6-btn v6-btn--ghost" onClick={() => setMode("landing")}>
                    ← Home
                  </button>
                )}
              </>
            ) : (
              <span className="v6-btn v6-btn--ghost" style={{ pointerEvents: "none" }}>
                Command Deck
              </span>
            )}
          </div>
        </nav>

        {mode === "landing" && (
          <>
            <section className="v6-hero">
              <span className="v6-hero__tag">long-term memory for AI agents</span>
              <h1 className="v6-hero__title">
                Memory that <em>lasts</em>, across every agent.
              </h1>
              <p className="v6-hero__sub">
                Cortex 通过 MCP 协议为 Cursor / Claude Desktop / Cline 等 AI Agent 提供一个永久的、加密的、可检索的共享记忆库。
              </p>
              <div className="v6-hero__cta">
                <button className="v6-btn v6-btn--primary" onClick={() => setMode("signup")}>
                  Get started →
                </button>
                <button className="v6-btn" onClick={() => setMode("signin")}>
                  I have an account
                </button>
              </div>
            </section>
            <section className="v6-features">
              <article className="v6-feature">
                <div className="v6-feature__icon" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 17H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h4M15 7h4a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-4M9 12h6" />
                  </svg>
                </div>
                <h3 className="v6-feature__title">Cross-Agent MCP Gateway</h3>
                <p className="v6-feature__desc">
                  兼容 Anthropic MCP 协议。一键接入 Cursor / Claude Desktop / Cline / Continue 等 AI 智能体。
                </p>
              </article>
              <article className="v6-feature">
                <div className="v6-feature__icon" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="3" />
                    <circle cx="6" cy="6" r="2" />
                    <circle cx="18" cy="6" r="2" />
                    <circle cx="6" cy="18" r="2" />
                    <circle cx="18" cy="18" r="2" />
                    <path d="M8 7l3 3M16 7l-3 3M8 17l3-3M16 17l-3-3" />
                  </svg>
                </div>
                <h3 className="v6-feature__title">Hybrid Retrieval & Reflection</h3>
                <p className="v6-feature__desc">
                  向量 + 知识图谱 + BM25 三位一体混合检索；L0→L3 反射引擎自动整合长期记忆。
                </p>
              </article>
              <article className="v6-feature">
                <div className="v6-feature__icon" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="11" width="18" height="11" rx="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <h3 className="v6-feature__title">Encrypted Multi-Tenancy</h3>
                <p className="v6-feature__desc">
                  每个租户的向量集合物理隔离；Provider API Key 通过 AES-256-GCM 加密落盘存储。
                </p>
              </article>
            </section>
          </>
        )}

        {(mode === "signin" || mode === "signup") && (
          <div className="v6-authcard-wrap">
            <div className="v6-authcard">
              <h2 className="v6-authcard__title">
                {mode === "signup" ? "Create your account" : isUserApp ? "Welcome back" : "Admin sign in"}
              </h2>
              <p className="v6-authcard__sub">
                {mode === "signup"
                  ? "注册账号以接入 Cortex 记忆"
                  : isUserApp
                  ? "登录 Cortex 进入你的记忆空间"
                  : "使用管理员账户登录 Command Deck"}
              </p>
              <form onSubmit={handleSubmit}>
                {mode === "signup" && (
                  <div className="v6-field">
                    <label className="v6-field__label">用户名</label>
                    <input
                      className="v6-input"
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="your_username"
                      autoComplete="username"
                    />
                  </div>
                )}
                <div className="v6-field">
                  <label className="v6-field__label">{isUserApp ? "邮箱" : "管理员账号"}</label>
                  <input
                    className="v6-input"
                    type={isUserApp ? "email" : "text"}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={isUserApp ? "mail@example.com" : "admin"}
                    autoComplete={isUserApp ? "email" : "username"}
                  />
                </div>
                <div className="v6-field">
                  <label className="v6-field__label">密码</label>
                  <input
                    className="v6-input"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete={mode === "signup" ? "new-password" : "current-password"}
                  />
                </div>
                <button type="submit" className="v6-btn v6-btn--primary v6-btn--block" disabled={loading}>
                  {loading ? "..." : mode === "signup" ? "Create account" : "Sign in"}
                </button>
              </form>
              {isUserApp && (
                <div className="v6-authcard__switch">
                  {mode === "signup" ? (
                    <>
                      Already have an account?
                      <button onClick={() => setMode("signin")}>Sign in</button>
                    </>
                  ) : (
                    <>
                      Don&apos;t have an account?
                      <button onClick={() => setMode("signup")}>Sign up</button>
                    </>
                  )}
                </div>
              )}
              {(localError || authError) && (
                <div className="v6-authcard__error">{localError || authError}</div>
              )}
            </div>
          </div>
        )}

        <footer className="v6-foot">
          <span>
            backend healthy ·{" "}
            <a href="/health" target="_blank" rel="noreferrer">
              /health
            </a>
          </span>
          <span>
            <a href="https://github.com/luogangan7-lgtm/ai-memory-os" target="_blank" rel="noreferrer">
              source
            </a>
          </span>
        </footer>
      </div>
    </div>
  );
}

interface UserMemory {
  id: string;
  title: string;
  content: string;
  category: string;
  subcategory: string;
  topic: string;
  source_type: string;
  created_at: string;
  score?: number;
}

function MemoryPanel(){
  const [memories,setMemories]=useState<UserMemory[]>([]);
  const [documents,setDocuments]=useState<UserDocument[]>([]);
  const [subTab,setSubTab]=useState<'memories' | 'documents'>('memories');
  const [query,setQuery]=useState('');
  const [loading,setLoading]=useState(false);
  const [uploading,setUploading]=useState(false);
  const [uploadMsg,setUploadMsg]=useState('');
  const [activeCategory,setActiveCategory]=useState('全部');

  const categories = ['全部', '文档知识', '整合知识', '工程技术', '个人记忆', '自然科学', '社会科学', '其他'];

  const fetchMemories = useCallback(async()=>{
    if(loading)return;
    setLoading(true);
    try{
      if (query.trim() === '') {
        // Query recent memories
        let url = '/memory/recent?limit=100';
        if (activeCategory === '文档知识') {
          url += '&source_type=document';
        } else if (activeCategory === '整合知识') {
          url += '&source_type=knowledge';
        } else if (activeCategory !== '全部') {
          url += `&category=${encodeURIComponent(activeCategory)}`;
        }
        const d = await api.get<any[]>(url);
        setMemories(d.map((x: any)=>({
          id: x.id,
          title: x.title || '无标题',
          content: x.content || '',
          category: x.category || '未分类',
          subcategory: x.subcategory || '',
          topic: x.topic || '',
          source_type: x.source_type || 'chat',
          created_at: x.created_at || '',
        })));
      } else {
        // Semantic search
        const d = await api.post<any[]>('/memory/search', { query, top_k: 20 });
        setMemories(d.map((x: any)=>({
          id: x.memory?.id || '',
          title: x.memory?.title || x.chunk_text?.slice(0, 20) || '无标题',
          content: x.chunk_text || x.memory?.content || '',
          category: x.memory?.category || '未分类',
          subcategory: x.memory?.subcategory || '',
          topic: x.memory?.topic || '',
          source_type: x.memory?.source_type || 'chat',
          created_at: x.memory?.created_at || '',
          score: x.score || 0
        })));
      }
    }catch(e){
      console.error(e);
      setMemories([]);
    }finally{
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[query, activeCategory]);

  const fetchDocuments = useCallback(async()=>{
    try {
      const d = await getUserDocuments();
      setDocuments(d || []);
    } catch(e) {
      console.error(e);
    }
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(()=>{
    fetchMemories();
    fetchDocuments();
  },[fetchMemories, fetchDocuments]);

  const handleDelete = async (id: string) => {
    if (!id) return;
    if (!window.confirm('确定要删除这条记忆吗？')) return;
    try {
      await api.delete(`/memory/${id}`);
      fetchMemories();
    } catch (e) {
      console.error(e);
      alert('删除失败');
    }
  };

  const handleDeleteDocument = async (id: string) => {
    if (!id) return;
    if (!window.confirm('确定要删除这个文档吗？这将级联删除它关联的所有提取记忆和向量索引。')) return;
    try {
      await deleteUserDocument(id);
      fetchDocuments();
      fetchMemories();
    } catch (e) {
      console.error(e);
      alert('删除失败');
    }
  };

  const getSourceBadge = (source: string) => {
    switch (source) {
      case 'document':
        return <span className="badge badge-emerald" style={{marginLeft: 6, fontSize: 10, padding: '2px 6px'}}>📄 文档</span>;
      case 'knowledge':
        return <span className="badge badge-premium" style={{marginLeft: 6, fontSize: 10, padding: '2px 6px', background: 'rgba(124, 58, 237, 0.15)', border: '1px solid rgba(124, 58, 237, 0.4)', color: '#a78bfa'}}>🧠 整合知识</span>;
      case 'human':
        return <span className="badge badge-teal" style={{marginLeft: 6, fontSize: 10, padding: '2px 6px'}}>💬 聊天</span>;
      case 'agent':
        return <span className="badge badge-violet" style={{marginLeft: 6, fontSize: 10, padding: '2px 6px'}}>🤖 AI/MCP</span>;
      case 'image':
        return <span className="badge badge-amber" style={{marginLeft: 6, fontSize: 10, padding: '2px 6px'}}>🖼️ OCR</span>;
      default:
        return <span className="badge badge-ghost" style={{marginLeft: 6, fontSize: 10, padding: '2px 6px'}}>💬 {source}</span>;
    }
  };

  const formatSize = (bytes: number) => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  // Filter memories by category
  const filteredMemories = memories.filter(m => {
    if (activeCategory === '全部') return true;
    if (activeCategory === '文档知识') return true;
    if (activeCategory === '整合知识') return true;
    if (activeCategory === '其他') {
      return !['工程技术', '个人记忆', '自然科学', '社会科学'].includes(m.category);
    }
    return m.category === activeCategory;
  });

  return(
    <div className='card'>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16}}>
        <div className='card-title' style={{margin: 0}}>🧠 我的知识空间</div>
        <div style={{display: 'flex', gap: 6}}>
          <button 
            className={`btn btn-sm ${subTab === 'memories' ? 'btn-teal' : 'btn-ghost'}`}
            style={{fontSize: 11, padding: '6px 12px'}}
            onClick={() => setSubTab('memories')}
          >
            📋 记忆与知识
          </button>
          <button 
            className={`btn btn-sm ${subTab === 'documents' ? 'btn-teal' : 'btn-ghost'}`}
            style={{fontSize: 11, padding: '6px 12px'}}
            onClick={() => setSubTab('documents')}
          >
            📁 我的文档库 ({documents.length})
          </button>
        </div>
      </div>

      {subTab === 'memories' ? (
        <>
          <div style={{display:'flex',gap:8,marginBottom:16}}>
            <input value={query} onChange={e=>setQuery(e.target.value)} style={{flex:1,background:'rgba(4,8,16,.85)',border:'1px solid var(--border)',borderRadius:10,padding:'10px 14px',color:'var(--text)',fontSize:13,outline:'none'}} placeholder='搜索记忆...' onKeyDown={e=>e.key==='Enter'&&fetchMemories()}/>
            <button className='btn btn-teal' onClick={fetchMemories} disabled={loading}>{loading?'搜索中...':'搜索'}</button>
            <label className='btn btn-ghost' style={{cursor:'pointer',fontSize:12,padding:'10px 14px',whiteSpace:'nowrap'}}>
              📄 批量上传
              <input type='file' accept='.txt,.md,.pdf' multiple style={{display:'none'}} onChange={async(e)=>{
                const files = Array.from(e.target.files || []);
                if (files.length === 0) return;
                setUploading(true);
                setUploadMsg(`📤 准备上传 ${files.length} 个文件...`);
                const tokenHeader = localStorage.getItem('mos_token') || localStorage.getItem('admin_token') || localStorage.getItem('mos_admin_token') || '';
                
                let successCount = 0;
                let failCount = 0;
                
                for (let i = 0; i < files.length; i++) {
                  const f = files[i];
                  if (!f) continue;
                  setUploadMsg(`📤 正在解析并分类 (${i + 1}/${files.length}): ${f.name}...`);
                  try {
                    const fd = new FormData();
                    fd.append('file', f);
                    const r = await fetch('/memory/upload', {
                      method: 'POST',
                      headers: { "Authorization": "Bearer " + tokenHeader },
                      body: fd
                    });
                    const d = await r.json();
                    if (d.id) {
                      successCount++;
                    } else {
                      failCount++;
                    }
                  } catch (err) {
                    console.error(err);
                    failCount++;
                  }
                }
                
                setUploadMsg(`✅ 成功导入 ${successCount} 个文件` + (failCount > 0 ? `，❌ 失败 ${failCount} 个` : ''));
                setTimeout(() => {
                  fetchMemories();
                  fetchDocuments();
                }, 500);
                setUploading(false);
                e.target.value = '';
              }}/>
            </label>
          </div>
          {(uploading||uploadMsg)&&<div style={{marginBottom:12,fontSize:12,color:uploadMsg.includes('❌')?'var(--crimson)':uploadMsg.includes('✅')?'var(--emerald)':'var(--text)'}}>{uploadMsg}</div>}

          {/* Category Tabs */}
          <div style={{display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16, borderBottom: '1px solid var(--border)', paddingBottom: 10}}>
            {categories.map(c => (
              <button 
                key={c} 
                className={`btn ${activeCategory === c ? 'btn-teal' : 'btn-ghost'}`} 
                style={{padding: '4px 10px', fontSize: 11, minWidth: 'auto', height: 'auto'}}
                onClick={() => setActiveCategory(c)}
              >
                {c}
              </button>
            ))}
          </div>

          <div style={{maxHeight:450,overflow:'auto'}}>
            {filteredMemories.length === 0 && !loading && <div style={{padding:20,textAlign:'center',color:'var(--muted)',fontSize:13}}>暂无该类别的记忆数据</div>}
            {filteredMemories.map((m,i)=>(
              <div key={i} style={{padding:'14px 0',borderBottom:'1px solid var(--border)',fontSize:13}}>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start'}}>
                  <div>
                    <div style={{display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4}}>
                      <span style={{fontWeight:600,color:'var(--teal)',fontSize:13}}>{m.title}</span>
                      {getSourceBadge(m.source_type)}
                      <span className="badge badge-violet" style={{fontSize: 10, padding: '2px 6px'}}>{m.category}</span>
                      {m.subcategory && <span className="badge badge-ghost" style={{fontSize: 10, padding: '2px 6px'}}>{m.subcategory}</span>}
                      {m.topic && <span style={{fontSize: 10, color: 'var(--muted)', marginLeft: 4}}>#{m.topic}</span>}
                    </div>
                  </div>
                  <div style={{display: 'flex', alignItems: 'center', gap: 10}}>
                    {m.score !== undefined && <div style={{fontSize:10,color:'var(--muted)'}}>相关度: {(m.score*100).toFixed(1)}%</div>}
                    <button 
                      onClick={() => handleDelete(m.id)} 
                      style={{
                        background: 'none', 
                        border: 'none', 
                        color: 'var(--crimson)', 
                        fontSize: 11, 
                        cursor: 'pointer',
                        padding: 0
                      }}
                    >
                      删除
                    </button>
                  </div>
                </div>
                <div style={{color:'var(--text)',fontSize:12,marginTop:6,lineHeight:1.6,whiteSpace: 'pre-wrap'}}>{m.content}</div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <>
          <div style={{display:'flex',justifyContent: 'space-between',alignItems:'center',marginBottom:16}}>
            <div style={{fontSize:12,color:'var(--muted)'}}>在这里查看你通过批量上传或MCP录入的原始文档以及它们的解析状态。</div>
            <label className='btn btn-teal' style={{cursor:'pointer',fontSize:12,padding:'8px 16px',whiteSpace:'nowrap',margin:0}}>
              ➕ 上传新文档
              <input type='file' accept='.txt,.md,.pdf' multiple style={{display:'none'}} onChange={async(e)=>{
                const files = Array.from(e.target.files || []);
                if (files.length === 0) return;
                setUploading(true);
                setUploadMsg(`📤 准备上传 ${files.length} 个文件...`);
                const tokenHeader = localStorage.getItem('mos_token') || localStorage.getItem('admin_token') || localStorage.getItem('mos_admin_token') || '';
                
                let successCount = 0;
                let failCount = 0;
                
                for (let i = 0; i < files.length; i++) {
                  const f = files[i];
                  if (!f) continue;
                  setUploadMsg(`📤 正在解析并分类 (${i + 1}/${files.length}): ${f.name}...`);
                  try {
                    const fd = new FormData();
                    fd.append('file', f);
                    const r = await fetch('/memory/upload', {
                      method: 'POST',
                      headers: { "Authorization": "Bearer " + tokenHeader },
                      body: fd
                    });
                    const d = await r.json();
                    if (d.id) {
                      successCount++;
                    } else {
                      failCount++;
                    }
                  } catch (err) {
                    console.error(err);
                    failCount++;
                  }
                }
                
                setUploadMsg(`✅ 成功导入 ${successCount} 个文件` + (failCount > 0 ? `，❌ 失败 ${failCount} 个` : ''));
                setTimeout(() => {
                  fetchDocuments();
                  fetchMemories();
                }, 500);
                setUploading(false);
                e.target.value = '';
              }}/>
            </label>
          </div>
          {(uploading||uploadMsg)&&<div style={{marginBottom:12,fontSize:12,color:uploadMsg.includes('❌')?'var(--crimson)':uploadMsg.includes('✅')?'var(--emerald)':'var(--text)'}}>{uploadMsg}</div>}

          <div style={{maxHeight:450,overflow:'auto'}}>
            <table className="table" style={{width:'100%',borderCollapse:'collapse'}}>
              <thead>
                <tr style={{textAlign:'left',borderBottom:'1px solid var(--border)',color:'var(--muted)',fontSize:11}}>
                  <th style={{padding:'10px 8px'}}>文件名</th>
                  <th style={{padding:'10px 8px'}}>大小</th>
                  <th style={{padding:'10px 8px'}}>分块数量</th>
                  <th style={{padding:'10px 8px'}}>上传时间</th>
                  <th style={{padding:'10px 8px',textAlign:'right'}}>操作</th>
                </tr>
              </thead>
              <tbody>
                {documents.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{padding:30,textAlign:'center',color:'var(--muted)',fontSize:12}}>暂无已上传的文档</td>
                  </tr>
                ) : (
                  documents.map((doc)=>(
                    <tr key={doc.id} style={{borderBottom:'1px solid var(--border)',fontSize:12}}>
                      <td style={{padding:'12px 8px',fontWeight:500,color:'var(--text)'}}>{doc.filename}</td>
                      <td style={{padding:'12px 8px',color:'var(--muted)'}}>{formatSize(doc.file_size)}</td>
                      <td style={{padding:'12px 8px'}}><span className="badge badge-violet" style={{fontSize:10,padding:'2px 6px'}}>{doc.chunk_count} Chunks</span></td>
                      <td style={{padding:'12px 8px',color:'var(--muted)',fontSize:11}}>{formatDate(doc.created_at)}</td>
                      <td style={{padding:'12px 8px',textAlign:'right'}}>
                        <button 
                          className="btn btn-ghost btn-sm"
                          style={{color:'var(--crimson)',padding:'4px 8px',fontSize:11}}
                          onClick={() => handleDeleteDocument(doc.id)}
                        >
                          删除
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

function ConnectPanel({token:propToken}:{token?:string}){

const[connected,setConnected]=useState<'checking'|'online'|'offline'>('checking');
useEffect(()=>{function check(){fetch(window.location.origin+'/').then(r=>setConnected(r.ok?'online':'offline')).catch(()=>setConnected('offline'))};check();const i=setInterval(check,8000);return ()=>clearInterval(i)},[]);
const[token]=useState(()=>propToken||'mos_'+Math.random().toString(36).slice(2,10)+'_'+Array.from({length:32},()=>Math.floor(Math.random()*16).toString(16)).join(''));
const getServerUrl=()=>window.location.hostname+(window.location.port?':'+window.location.port:':8003');
const[agent,setAgent]=useState<'cursor'|'claude'|'openclaw'|'cline'|'continue'|'roo'|'codex'>('cursor');
const[copied,setCopied]=useState(false);

const configs={cursor:JSON.stringify({mcpServers:{"ai-memory-os":{command:"npx",args:["-y","ai-memory-os-mcp","--token="+token,"--server=http://"+getServerUrl()+""],env:{}}}},null,2),
claude:JSON.stringify({mcpServers:{"ai-memory-os":{command:"npx",args:["-y","ai-memory-os-mcp"],env:{MOS_TOKEN:token,MOS_SERVER:"http://"+getServerUrl()}}}},null,2),
openclaw:"SSE 地址: http://"+getServerUrl()+"/mcp?token="+token,
cline:JSON.stringify({"ai-memory-os":{command:"npx",args:["-y","ai-memory-os-mcp","--token="+token,"--server=http://"+getServerUrl()+""],disabled:false,autoApprove:["memory_search","memory_list","memory_status"]}},null,2),
continue:JSON.stringify({experimental:{modelContextProtocolServers:[{transport:{type:"stdio",command:"npx",args:["-y","ai-memory-os-mcp","--token="+token,"--server=http://"+getServerUrl()+""]}}]}},null,2),
roo:JSON.stringify({"ai-memory-os":{command:"npx",args:["-y","ai-memory-os-mcp","--token="+token,"--server=http://"+getServerUrl()+""],alwaysAllow:["memory_search","memory_store"]}},null,2),
codex:"# ~/.codex/config.toml\n[[mcp_servers]]\nname = \"ai-memory-os\"\ncommand = \"npx\"\nargs = [\"-y\", \"ai-memory-os-mcp\", \"--token="+token+"\", \"--server=http://"+getServerUrl()+"\"]"};

const FILE_PATHS={cursor:'~/.cursor/mcp.json',claude:'~/Library/Application Support/Claude/claude_desktop_config.json',openclaw:'OpenClaw → Settings → MCP Servers',cline:'VS Code → Cline → MCP Servers',continue:'~/.continue/config.json',roo:'VS Code → Roo Code → MCP Servers',codex:'~/.codex/config.toml'};

const AGENTS=[{id:'cursor',name:'Cursor'},{id:'claude',name:'Claude Desktop'},{id:'openclaw',name:'OpenClaw (SSE)'},{id:'cline',name:'Cline'},{id:'continue',name:'Continue'},{id:'roo',name:'Roo Code'},{id:'codex',name:'Codex CLI'}];

const SETUP_STEPS={cursor:['1. 打开 Cursor → Settings → MCP','2. 点击 Add Server → 选择 Command','3. 复制上方 JSON 粘贴到配置框','4. 点击 Save，重启 Cursor','5. 在聊天框输入"检索我的记忆"测试'],
claude:['1. 打开文件: ~/Library/Application Support/Claude/claude_desktop_config.json','2. 复制上方 JSON，粘贴到 mcpServers 字段','3. 保存文件，完全退出 Claude Desktop','4. 重新打开 Claude，发送新对话测试'],
openclaw:['1. 打开 OpenClaw → Agent 设置','2. 找到 MCP Servers → 添加 SSE','3. 粘贴上方 SSE URL','4. 保存后对话自动识别记忆工具'],
cline:['1. 打开 VS Code → 扩展 → Cline 设置','2. 找到 MCP Servers 配置 (JSON 格式)','3. 复制上方 JSON 粘贴到配置','4. 重启 VS Code，新对话自动加载'],
continue:['1. 打开文件: ~/.continue/config.json','2. 在 experimental.modelContextProtocolServers 数组中粘贴上方 JSON','3. 保存文件，重启 Continue 扩展'],
roo:['1. 打开 VS Code → Roo Code 扩展','2. Settings → MCP Servers → Add','3. 粘贴上方 JSON 配置','4. 保存后新对话即可使用'],
codex:['1. 打开文件: ~/.codex/config.toml','2. 复制上方配置粘贴到文件末尾','3. 保存文件','4. 运行 codex 命令，工具自动加载']};
// eslint-disable-next-line
const SYSTEM_PROMPTS={standard:'你已连接 AI Memory OS V6.0 长期记忆系统（8个工具）。\n\n【对话开始时，静默执行以下操作】：\n1. 调用 memory_get_persona → 了解用户背景和偏好\n2. 调用 memory_task_canvas_get → 恢复未完成任务（如有）\n3. 调用 memory_search(用户问题关键词) → 检索相关知识\n\n【对话中，发现以下内容时立即调用 memory_store】：\n- 用户偏好、习惯、要求\n- 技术决策及原因\n- 项目结构、约定、配置\n- 用户说"记住"的任何内容\n- 解决的复杂问题（问题+方案）\n\n【长任务进行中】：\n每完成一个重要阶段，调用 memory_task_canvas_update 更新 Mermaid 任务画布\n\n【对话结束时】：\n若对话产生了有价值的结论或方案，调用 memory_store 保存摘要\n\n所有上述操作静默完成，不向用户报告，除非操作失败',concise:'[记忆规则] ①开始→persona+search+canvas_get ②重要信息→store ③进展→canvas_update ④记住/忘掉/搜索→对应操作。静默执行。',dev:'你是连接了 AI Memory OS 的开发助手。记忆工具是你感知能力的延伸。\n\n【每次对话开始】静默执行：\n① memory_get_persona 了解技术栈和项目背景\n② memory_task_canvas_get 恢复上次未完成的开发任务\n③ memory_search(项目名/功能关键词) 检索相关代码约定\n\n【代码工作中】：\n- 确定了技术方案 → memory_store（tags: [\"架构决策\"]）\n- 解决了 Bug → memory_store（title: \"Bug修复: xxx\"，tags: [\"bug\", \"技术栈\"]）\n- 完成了功能阶段 → memory_task_canvas_update（更新进度图）\n\n【存储代码记忆时】：\n只存逻辑摘要和关键决策，不存完整大段代码。\n格式：问题背景 + 解决思路 + 关键代码片段（< 20行）\n\n所有操作静默完成。'};

const[pType,setPType]=useState<'standard'|'concise'|'dev'>('standard');

return(<div className='card'><div className='card-title'>🔑 接入配置</div>
<div style={{marginBottom:16,display:'flex',alignItems:'center',gap:8}}><div style={{width:8,height:8,borderRadius:'50%',background:connected==='online'?'var(--emerald)':connected==='offline'?'var(--crimson)':'var(--amber)',boxShadow:connected==='online'?'0 0 8px var(--emerald)':connected==='offline'?'0 0 8px var(--crimson)':'none'}}/><span style={{fontSize:13,color:connected==='online'?'var(--emerald)':connected==='offline'?'var(--crimson)':'var(--amber)'}}>{connected==='online'?'已连接到服务器':connected==='offline'?'服务器不可达':'检测中...'}</span></div>
<div style={{marginBottom:20,padding:"10px 14px",background:"rgba(255,179,71,.08)",borderRadius:10,border:"1px solid rgba(255,179,71,.2)",fontSize:12,color:"var(--amber)"}}>⚠️ 部署到服务器后，配置已自动检测当前服务器地址，可直接复制使用。<hr style={{borderColor:"var(--border)",margin:"10px 0"}}/></div><div style={{marginBottom:20}}>
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

function PersonaPanel() {
  const [persona, setPersona] = useState("");
  const [loading, setLoading] = useState(false);
  async function load() {
    setLoading(true);
    try {
      const r = await fetch("/persona/default", {
        headers: { Authorization: "Bearer " + (localStorage.getItem("admin_token") || localStorage.getItem("mos_admin_token") || "") },
      });
      const d = await r.json();
      setPersona(d.persona_md || "暂无画像 — 多使用系统后自动生成");
    } catch {
      setPersona("加载失败");
    }
    setLoading(false);
  }
  useEffect(() => { load(); }, []);
  return (
    <div className="v6-card">
      <div className="v6-card__title">
        Persona
        <span className="v6-card__title-hint">long-term user profile</span>
      </div>
      <div className="v6-card__body">
        {loading ? <div style={{ color: "var(--v6-fg-muted)" }}>Loading…</div> : <pre>{persona}</pre>}
      </div>
      <div className="v6-card__actions">
        <button className="v6-btn" onClick={load}>Refresh</button>
      </div>
    </div>
  );
}

function MyLLMPanel(){
const getToken=()=>localStorage.getItem("admin_token")||localStorage.getItem("mos_admin_token")||"";
const authHeaders=()=>({"Content-Type":"application/json","Authorization":"Bearer "+getToken()});
const PROVIDERS = ALL_PROVIDERS.filter(x=>!x.region||x.region!=="local").map(x=>({id:x.id,name:x.name,region:x.region,base:x.baseUrl,models:x.models.map(m=>m.id)})); // auto from models.ts


const[p,setP]=useState("");const[k,setK]=useState("");const[m,setM]=useState("");const[b,setB]=useState("");
const[r,setR]=useState("");const[l,setL]=useState(false);
const prov=PROVIDERS.find(x=>x.id===p);
// eslint-disable-next-line react-hooks/exhaustive-deps
useEffect(()=>{fetch("/api/user/llm",{headers:authHeaders()}).then(r=>r.json()).then(d=>{setP(d.provider||"");setM(d.model||"");setB(d.base_url||"")})},[]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
useEffect(()=>{if(p&&prov){setB(prov.base);if(!m||!prov.models.includes(m)){setM(prov.models[0]||"")}}if(!p){setM("")}},[p]);
async function save(){setL(true);try{await fetch("/api/user/llm",{method:"POST",headers:authHeaders(),body:JSON.stringify({provider:p,api_key:k,model:m,base_url:b})});setR("✅ 已保存")}catch{setR("保存失败")}setL(false)}
async function test(){setL(true);try{const r=await fetch("/api/user/llm/test",{method:"POST",headers:authHeaders(),body:JSON.stringify({api_key:k,base_url:b,model:m})});const d=await r.json();setR(d.connected?"✅ 连接成功":"❌ "+ (d.error||d.status))}catch{setR("测试失败")}setL(false)}
return(<div className="card" style={{borderColor:"rgba(0,240,212,.2)"}}><div className="card-title">🤖 我的 LLM</div><div style={{fontSize:12,color:"var(--muted)",marginBottom:16}}>配置你自己的大模型，驱动记忆管线（L1/L2/L3 蒸馏）</div>
<div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:12}}>
<div className="form-group"><label>厂商</label><select value={p} onChange={e=>setP(e.target.value)} style={{background:"rgba(0,0,0,.3)",color:"var(--text)",border:"1px solid var(--border)",borderRadius:10,padding:"10px 12px",fontSize:13}}><optgroup label="🇨🇳 中国厂商">
{PROVIDERS.filter(x=>x.region==="cn").map(x=><option key={x.id} value={x.id}>{x.name} ({x.models.length} 模型)</option>)}
</optgroup>
<optgroup label="🌐 海外厂商">
{PROVIDERS.filter(x=>x.region==="intl").map(x=><option key={x.id} value={x.id}>{x.name} ({x.models.length} 模型)</option>)}
</optgroup></select></div>
<div className="form-group"><label>模型</label><select value={m} onChange={e=>setM(e.target.value)} disabled={!p} style={{background:"rgba(0,0,0,.3)",color:"var(--text)",border:"1px solid var(--border)",borderRadius:10,padding:"10px 12px",fontSize:13}}>{prov?.models.map(x=><option key={x} value={x}>{x}</option>)}</select></div></div>
<div className="form-group"><label>API Key</label><input type="password" value={k} onChange={e=>setK(e.target.value)} placeholder="sk-..." style={{background:"rgba(0,0,0,.3)",color:"var(--text)",border:"1px solid var(--border)",borderRadius:10,padding:"10px 14px",fontSize:13}}/></div>
<div style={{display:"flex",gap:8}}><button className="btn btn-teal" onClick={save} disabled={l}>💾 保存</button><button className="btn btn-ghost" onClick={test} disabled={l||!k}>🔗 测试连接</button></div>
{r&&<div style={{marginTop:12,fontSize:12,color:r.includes("✅")?"var(--emerald)":"var(--crimson)"}}>{r}</div>}
<PipelineStatusPanel />
</div>)}

function fmtTime(s: string|null): string {
  if(!s) return "-";
  const d = new Date(s);
  if(isNaN(d.getTime())) return s;
  return d.toLocaleString();
}

function fmtDuration(start: string|null, end: string|null): string {
  if(!start || !end) return "-";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if(isNaN(ms) || ms < 0) return "-";
  if(ms < 1000) return ms + "ms";
  if(ms < 60_000) return (ms/1000).toFixed(1) + "s";
  return Math.round(ms/1000) + "s";
}

function StatusBadge({status}:{status:string}){
  const map: Record<string,{label:string;color:string;bg:string}> = {
    pending:    {label:"⏳ 等待", color:"#facc15", bg:"rgba(250,204,21,.12)"},
    processing: {label:"🔄 处理中", color:"#38bdf8", bg:"rgba(56,189,248,.12)"},
    done:       {label:"✅ 完成", color:"var(--emerald)", bg:"rgba(34,197,94,.12)"},
    failed:     {label:"❌ 失败", color:"var(--crimson)", bg:"rgba(248,113,113,.12)"},
    dead:       {label:"💀 死信", color:"#f87171", bg:"rgba(248,113,113,.18)"},
  };
  const s = map[status] || {label: status, color: "var(--muted)", bg: "rgba(255,255,255,.06)"};
  return <span style={{display:"inline-block",padding:"2px 8px",borderRadius:6,fontSize:10,color:s.color,background:s.bg,fontFamily:"var(--mono)"}}>{s.label}</span>;
}

function PipelineStatusPanel(){
  const [data,setData]=useState<PipelineStatus|null>(null);
  const [err,setErr]=useState<string>("");
  const [expanded,setExpanded]=useState(false);

  const refresh = useCallback(async ()=>{
    try {
      const d = await getUserPipelineStatus();
      setData(d);
      setErr("");
    } catch(e:unknown) {
      setErr(e instanceof Error ? e.message : "加载失败");
    }
  },[]);

  useEffect(()=>{
    refresh();
    const id = setInterval(refresh, 5000);
    return ()=>clearInterval(id);
  },[refresh]);

  const c = data?.counts || {pending:0,processing:0,done:0,failed:0,dead:0};
  const inFlight = data?.in_flight ?? 0;
  const recent: PipelineJob[] = data?.recent || [];

  return (
    <div style={{marginTop:16,borderTop:"1px solid var(--border)",paddingTop:12}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
        <div style={{fontSize:11,color:"var(--muted)"}}>🔄 记忆管线状态（24h，每 5s 自动刷新）</div>
        <button className="btn btn-ghost btn-sm" style={{fontSize:10}} onClick={refresh}>↻ 立即刷新</button>
      </div>

      {!data?.configured && (
        <div style={{padding:"10px 12px",background:"rgba(255,179,71,.08)",border:"1px solid rgba(255,179,71,.2)",borderRadius:8,fontSize:11,color:"var(--amber)",marginBottom:10}}>
          ⚠️ 尚未保存自己的 LLM 配置，管线将无法运行 — 先保存上方的厂商/Key/模型再触发记忆写入。
        </div>
      )}

      {err && <div style={{fontSize:11,color:"var(--crimson)",marginBottom:8}}>⚠️ {err}</div>}

      <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:6,marginBottom:10}}>
        {[
          {key:"pending",label:"等待",color:"#facc15"},
          {key:"processing",label:"处理中",color:"#38bdf8"},
          {key:"done",label:"完成",color:"var(--emerald)"},
          {key:"failed",label:"失败",color:"var(--crimson)"},
          {key:"dead",label:"死信",color:"#f87171"},
        ].map(s=>(
          <div key={s.key} style={{background:"rgba(0,0,0,.2)",padding:"8px",borderRadius:8,textAlign:"center"}}>
            <div style={{fontSize:9,color:"var(--muted)"}}>{s.label}</div>
            <div style={{fontSize:16,fontWeight:700,color:s.color}}>{(c as Record<string,number>)[s.key] ?? 0}</div>
          </div>
        ))}
      </div>

      <div style={{display:"flex",gap:14,flexWrap:"wrap",fontSize:11,color:"var(--muted)",marginBottom:10}}>
        <div>当前在途: <span style={{color:inFlight>0?"#38bdf8":"var(--muted)",fontWeight:600}}>{inFlight}</span></div>
        <div>上次成功: <span style={{color:"var(--text)"}}>{fmtTime(data?.last_completed_at||null)}</span></div>
        {data?.last_failed_at && <div>上次失败: <span style={{color:"var(--crimson)"}}>{fmtTime(data.last_failed_at)}</span></div>}
      </div>

      <button className="btn btn-ghost btn-sm" style={{fontSize:10,marginBottom:8}} onClick={()=>setExpanded(v=>!v)}>
        {expanded ? "▼ 收起" : "▶ 展开"} 最近 {recent.length} 条任务
      </button>

      {expanded && (
        recent.length === 0 ? (
          <div style={{padding:"10px",color:"var(--muted)",fontSize:12,textAlign:"center"}}>暂无管线任务记录</div>
        ) : (
          <div style={{maxHeight:260,overflow:"auto",background:"rgba(0,0,0,.25)",borderRadius:8,padding:"4px 8px"}}>
            <table style={{width:"100%",fontSize:11,fontFamily:"var(--mono)",borderCollapse:"collapse"}}>
              <thead>
                <tr style={{color:"var(--muted)",textAlign:"left"}}>
                  <th style={{padding:"6px 4px"}}>状态</th>
                  <th style={{padding:"6px 4px"}}>类型</th>
                  <th style={{padding:"6px 4px"}}>创建时间</th>
                  <th style={{padding:"6px 4px"}}>耗时</th>
                  <th style={{padding:"6px 4px"}}>错误</th>
                </tr>
              </thead>
              <tbody>
                {recent.map(j=>(
                  <tr key={j.id} style={{borderTop:"1px solid var(--border)"}}>
                    <td style={{padding:"6px 4px"}}><StatusBadge status={j.status}/></td>
                    <td style={{padding:"6px 4px",color:"var(--text)"}}>{j.task_type}</td>
                    <td style={{padding:"6px 4px",color:"var(--muted)"}}>{fmtTime(j.created_at)}</td>
                    <td style={{padding:"6px 4px",color:"var(--text)"}}>{fmtDuration(j.started_at, j.completed_at)}</td>
                    <td style={{padding:"6px 4px",color:"var(--crimson)",maxWidth:240,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}} title={j.error_msg||""}>{j.error_msg||"-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}

function CanvasPanel(){
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [canvases,setCanvases]=useState<any[]>([]);
  const [activeAgent,setActiveAgent]=useState<string>("");
  const [loading,setLoading]=useState(false);
  const [taskId,setTaskId]=useState("main");
  const svgRef=useRef<HTMLDivElement>(null);
  
  async function load(){
    setLoading(true);
    try{
      const r=await fetch("/canvas/"+taskId,{headers:{"Authorization":"Bearer "+(localStorage.getItem('admin_token')||localStorage.getItem('mos_admin_token')||'')}});
      const d=await r.json();
      const arr = Array.isArray(d) ? d : (d.task_id ? [d] : []);
      setCanvases(arr);
      if (arr.length > 0 && !arr.find(x => x.agent_id === activeAgent)) {
        setActiveAgent(arr[0].agent_id || "default");
      } else if (arr.length === 0) {
        setActiveAgent("");
      }
    }catch{
      setCanvases([]);
    }
    setLoading(false);
  }
  
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(()=>{load()},[taskId]);

  useEffect(() => {
    let md = "graph TD\n  A[暂无任务] --> B[开始使用后自动生成]";
    if (canvases.length > 0 && activeAgent) {
      const c = canvases.find(x => x.agent_id === activeAgent) || canvases[0];
      if (c && c.canvas_mermaid) md = c.canvas_mermaid;
    }
    let isCancelled = false;
    setTimeout(async ()=>{
      if(svgRef.current && !isCancelled){
        try{
          const mermaid=(await import("mermaid")).default;
          mermaid.initialize({startOnLoad:false,theme:"dark",themeVariables:{primaryColor:"#00f0d4",primaryTextColor:"#e0e0e0",lineColor:"#4A6080"}});
          const{svg}=await mermaid.render("mermaid-canvas-"+Date.now(),md);
          if(!isCancelled) svgRef.current.innerHTML=svg;
        }catch{if(!isCancelled) svgRef.current.innerHTML='<div style=color:var(--muted)>图谱渲染失败</div>'}
      }
    },100);
    return () => { isCancelled = true; };
  }, [canvases, activeAgent]);

  return(<div className="card"><div className="card-title">📋 任务画布 (多Agent协作)</div>
    <div style={{display:"flex",gap:8,marginBottom:12}}>
      <input value={taskId} onChange={e=>setTaskId(e.target.value)} style={{flex:1,background:"rgba(4,8,16,.85)",border:"1px solid var(--border)",borderRadius:10,padding:"10px 14px",color:"var(--text)",fontSize:13}} placeholder="任务ID (默认: main)"/>
      <button className="btn btn-teal" onClick={load} disabled={loading}>刷新</button>
    </div>
    
    {canvases.length > 0 && (
      <div style={{display:'flex',gap:6,marginBottom:12,borderBottom:'1px solid var(--border)',paddingBottom:8,overflowX:'auto'}}>
        {canvases.map(c => (
          <button 
            key={c.agent_id} 
            className={`btn ${activeAgent===c.agent_id ? 'btn-teal' : 'btn-ghost'}`} 
            style={{padding:'4px 12px',fontSize:11,whiteSpace:'nowrap'}}
            onClick={() => setActiveAgent(c.agent_id)}
          >
            🤖 {c.agent_id || 'default'}
          </button>
        ))}
      </div>
    )}

    {loading?<div style={{color:"var(--muted)",fontSize:13}}>加载中...</div>:
    <div ref={svgRef} style={{background:"rgba(0,0,0,.3)",borderRadius:10,padding:16,minHeight:100,overflow:"auto"}}/>}
    <div style={{fontSize:10,color:"var(--muted)",marginTop:8}}>同一 Task 下的不同 Agent 画布互相隔离，互不干扰</div>
  </div>)
}

function AuditPanel() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  async function load() {
    setLoading(true);
    try {
      const r = await fetch("/audit-logs?limit=30", {
        headers: { Authorization: "Bearer " + (localStorage.getItem("admin_token") || localStorage.getItem("mos_admin_token") || "") },
      });
      const d = await r.json();
      setLogs(d.logs || []);
    } catch { setLogs([]); }
    setLoading(false);
  }
  useEffect(() => { load(); }, []);
  return (
    <div className="v6-card">
      <div className="v6-card__title">
        Activity
        <span className="v6-card__title-hint">latest 30 events</span>
      </div>
      {loading ? (
        <div className="v6-empty">Loading…</div>
      ) : logs.length === 0 ? (
        <div className="v6-empty">No activity yet.</div>
      ) : (
        <div style={{ maxHeight: 480, overflow: "auto" }}>
          <table className="v6-table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Time</th>
                <th>Target</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l, i) => (
                <tr key={i}>
                  <td style={{ fontFamily: "var(--v6-font-mono)" }}>{l.action || "?"}</td>
                  <td style={{ color: "var(--v6-fg-muted)", fontFamily: "var(--v6-font-mono)" }}>{l.created_at || ""}</td>
                  <td style={{ color: "var(--v6-fg-muted)", fontFamily: "var(--v6-font-mono)", fontSize: 11.5 }}>
                    {l.target_id ? l.target_id.slice(0, 24) : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function LLMStatusBar() {
  const [llm, setLlm] = useState<{ provider: string; model: string; connected: boolean } | null>(null);
  useEffect(() => {
    fetch("/api/user/llm", { headers: { Authorization: "Bearer " + (localStorage.getItem("admin_token") || "") } })
      .then((r) => r.json())
      .then((d) => {
        if (!d.provider) { setLlm(null); return; }
        setLlm({ provider: d.provider, model: d.model, connected: true });
      })
      .catch(() => setLlm(null));
  }, []);
  const provInfo = ALL_PROVIDERS.find((x) => x.id === llm?.provider);
  const provName = provInfo?.name || llm?.provider || "";
  if (!llm) {
    return (
      <span className="v6-llmpill">
        <span className="v6-llmpill__dot v6-llmpill__dot--warn" />
        No LLM configured
      </span>
    );
  }
  return (
    <span className="v6-llmpill" title={`${provName} / ${llm.model}`}>
      <span className={`v6-llmpill__dot ${llm.connected ? "v6-llmpill__dot--ok" : "v6-llmpill__dot--warn"}`} />
      <strong>{provName}</strong>
      <span>/ {llm.model}</span>
    </span>
  );
}
