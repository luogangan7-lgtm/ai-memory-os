import { useState, useEffect, useCallback, useRef } from 'react';
import { PROVIDERS as ALL_PROVIDERS } from "../data/models";
import { useAuth } from '../contexts/AuthContext';
import { PlanPanel } from "./PlanPanel";
import { api } from '../api/client';
import { getUserPipelineStatus, getUserDocuments, deleteUserDocument, UserDocument } from '../api/endpoints';
import type { PipelineStatus, PipelineJob } from '../api/types';
import { CortexMark } from '../components/CortexMark';

type DashTab = "overview" | "memory" | "connect" | "myllm" | "canvas" | "persona" | "plan";
const DASH_TABS: { id: DashTab; label: string }[] = [
  { id: "overview", label: "概览 Overview" },
  { id: "memory",   label: "知识库 Library" },
  { id: "connect",  label: "接入 Connect" },
  { id: "myllm",    label: "LLM 模型" },
  { id: "canvas",   label: "画布 Canvas" },
  { id: "plan",     label: "订阅 Plan" },
  { id: "persona",  label: "画像 Persona" },
];

function Dashboard() {
  const [tab, setTab] = useState<DashTab>("overview");
  const { logout, token, mcpKey } = useAuth();

  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (document.documentElement.getAttribute('data-theme') as 'light' | 'dark') || 'dark';
  });

  const toggleTheme = useCallback(() => {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme') || 'dark';
    const next = current === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', next);
    setTheme(next);
  }, []);

  // Allow child panels to trigger navigation without prop drilling
  useEffect(() => {
    const handler = (e: Event) => {
      const dest = (e as CustomEvent).detail as DashTab;
      if (dest) setTab(dest);
    };
    window.addEventListener('cortex-nav', handler);
    return () => window.removeEventListener('cortex-nav', handler);
  }, []);

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
            <button
              onClick={toggleTheme}
              title="切换主题 Theme"
              style={{
                appearance: 'none',
                background: 'transparent',
                border: '1px solid var(--v6-border)',
                color: 'var(--v6-fg-muted)',
                fontFamily: 'var(--v6-font-mono)',
                fontSize: 16,
                width: 34,
                height: 34,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 'var(--v6-radius-md)',
                cursor: 'pointer',
                transition: 'all 0.15s',
                padding: 0,
                marginRight: 8,
              }}
            >
              {theme === 'light' ? '🌙' : '☀'}
            </button>
            <button className="v6-btn v6-btn--ghost" onClick={logout}>
              退出 Sign out
            </button>
          </div>
        </nav>
        <main className="v6-app__main">
          {tab === "overview" && <OverviewPanel onNavigate={setTab} />}
          {tab === "memory" && <MemoryPanel />}
          {tab === "connect" && <ConnectPanel token={mcpKey || token} />}
          {tab === "myllm" && <MyLLMPanel />}
          {tab === "canvas" && <CanvasPanel />}
          {tab === "persona" && <PersonaPanel />}
          {tab === "plan" && <PlanPanel />}
        </main>
      </div>
    </div>
  );
}

// ── Overview (default post-login dashboard) ────────────────────────────────
function OverviewPanel({ onNavigate }: { onNavigate: (tab: DashTab) => void }) {
  const getToken = () => localStorage.getItem('admin_token') || localStorage.getItem('mos_admin_token') || '';
  const authHeader = () => ({ Authorization: 'Bearer ' + getToken() });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [stats, setStats] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [llm, setLlm] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [pipeline, setPipeline] = useState<any>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, l, p] = await Promise.all([
        fetch('/stats', { headers: authHeader() }).then((r) => r.json()),
        fetch('/api/user/llm', { headers: authHeader() }).then((r) => r.json()),
        fetch('/api/user/llm/pipeline/status', { headers: authHeader() }).then((r) => r.json()).catch(() => null),
      ]);
      setStats(s);
      setLlm(l);
      setPipeline(p);
    } catch { /* non-fatal */ }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  const fmt = (n: number) => n >= 1000 ? (n / 1000).toFixed(1) + 'K' : String(n || 0);
  const fmtDate = (s: string) => {
    if (!s) return '—';
    try { return new Date(s).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }); }
    catch { return s; }
  };

  const llmOk = llm?.provider && llm?.model;
  const agentCount = stats?.active_agents?.length ?? 0;
  const pipelineCounts = pipeline?.counts || {};
  const pipelineRecent = (pipeline?.recent || []).slice(0, 5);

  // 3D tilt handler for metric tiles
  const handleTilt = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    el.style.transform = `perspective(700px) rotateX(${y * -6}deg) rotateY(${x * 6}deg) translateY(-4px)`;
  };
  const resetTilt = (e: React.PointerEvent<HTMLDivElement>) => {
    e.currentTarget.style.transform = '';
  };

  const isNew = !llmOk && (stats?.total_memories ?? 0) < 3;

  return (
    <div className="v6-card v6-overview-card">
      {/* ambient decorative highlight layer */}
      <div className="v6-overview__glow" aria-hidden="true" />

      <div className="v6-card__head" style={{ position: 'relative', zIndex: 1 }}>
        <div className="v6-card__title">
          系统概览 Overview
          <span className="v6-card__title-hint">每 5 秒自动刷新</span>
        </div>
        <button className="v6-btn v6-btn--xs" onClick={refresh}>刷新</button>
      </div>

      {isNew ? (
        /* ── Onboarding 空状态 ── */
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ marginBottom: 18, fontSize: 13.5, color: 'var(--v6-fg-muted)' }}>
            3 步让 Cortex 跑起来：
          </div>
          <div className="v6-onboarding">
            <div className={`v6-onboarding__step ${llmOk ? 'v6-onboarding__step--done' : ''}`}>
              <span className="v6-onboarding__num">{llmOk ? '✓' : '1'}</span>
              <div className="v6-onboarding__body">
                <div className="v6-onboarding__title">配置 LLM（你的 key，你的账单）</div>
                <div className="v6-onboarding__desc">选一个 provider，填入 API key。可选带 FREE 标识的模型，零成本启动。</div>
                {!llmOk && <button className="v6-btn v6-btn--xs" style={{ marginTop: 10 }} onClick={() => onNavigate('myllm')}>前往配置 →</button>}
              </div>
            </div>
            <div className="v6-onboarding__step">
              <span className="v6-onboarding__num">2</span>
              <div className="v6-onboarding__body">
                <div className="v6-onboarding__title">接入 AI Agent（MCP 协议）</div>
                <div className="v6-onboarding__desc">在 Cursor / Claude Desktop / Cline 中添加 MCP 配置，Agent 就能自动把知识写入记忆。</div>
                <button className="v6-btn v6-btn--xs" style={{ marginTop: 10 }} onClick={() => onNavigate('connect')}>前往接入 →</button>
              </div>
            </div>
            <div className="v6-onboarding__step">
              <span className="v6-onboarding__num">3</span>
              <div className="v6-onboarding__body">
                <div className="v6-onboarding__title">写入第一条记忆</div>
                <div className="v6-onboarding__desc">让 Agent 在对话中自动调用 memory_store，或在知识库页面上传文档。</div>
                <button className="v6-btn v6-btn--xs" style={{ marginTop: 10 }} onClick={() => onNavigate('memory')}>前往知识库 →</button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ position: 'relative', zIndex: 1 }}>
          {/* ── 4 个核心指标 ── */}
          <div className="v6-metric-grid">
            <div className="v6-metric-tile" onPointerMove={handleTilt} onPointerLeave={resetTilt}>
              <div className="v6-metric-tile__label">总记忆 Memories</div>
              <div className="v6-metric-tile__value">{fmt(stats?.total_memories ?? 0)}</div>
              <div className="v6-metric-tile__sub">{fmt(stats?.total_documents ?? 0)} 份文档</div>
            </div>
            <div className="v6-metric-tile" onPointerMove={handleTilt} onPointerLeave={resetTilt}>
              <div className="v6-metric-tile__label">今日新增 Today</div>
              <div className="v6-metric-tile__value v6-metric-tile__value--accent">{fmt(stats?.new_today ?? 0)}</div>
              <div className="v6-metric-tile__sub">过去 24 小时</div>
            </div>
            <div className="v6-metric-tile" onPointerMove={handleTilt} onPointerLeave={resetTilt}>
              <div className="v6-metric-tile__label">活跃 Agents</div>
              <div className="v6-metric-tile__value">{agentCount}</div>
              <div className="v6-metric-tile__sub">
                {agentCount > 0 ? stats.active_agents.slice(0, 2).join(' · ') : '7 天内暂无'}
              </div>
            </div>
            <div className="v6-metric-tile" onPointerMove={handleTilt} onPointerLeave={resetTilt}>
              <div className="v6-metric-tile__label">管线完成 Done</div>
              <div className="v6-metric-tile__value v6-metric-tile__value--done">
                {fmt((pipelineCounts as Record<string, number>)['done'] ?? 0)}
              </div>
              <div className="v6-metric-tile__sub">
                <span style={{ color: pipelineCounts['failed'] ? 'var(--v6-danger)' : undefined }}>
                  {pipelineCounts['failed'] ?? 0} 失败
                </span>
                {' · '}{pipelineCounts['pending'] ?? 0} 排队中
              </div>
            </div>
          </div>

          {/* ── 管线任务列表 ── */}
          <div className="v6-section-label" style={{ marginBottom: 10 }}>
            <span>记忆管线 · Pipeline</span>
            <span className="v6-section-label__count">
              {pipeline?.in_flight ?? 0} 正在处理
            </span>
          </div>
          {pipelineRecent.length === 0 ? (
            <div className="v6-empty" style={{ padding: '24px 0' }}>暂无管线任务 — 接入 Agent 后自动触发</div>
          ) : (
            <div className="v6-modellist" style={{ marginBottom: 20 }}>
              {pipelineRecent.map((j: { id: string; status: string; task_type: string; created_at: string; started_at: string; completed_at: string; error_msg: string }) => (
                <div key={j.id} className="v6-usage-row">
                  <div className="v6-usage-row__label" style={{ fontFamily: 'var(--v6-font-mono)', fontSize: 12 }}>
                    <span className="v6-tag" style={{ marginRight: 6 }}>{j.status}</span>
                    {j.task_type}
                  </div>
                  <div className="v6-usage-row__nums">
                    {j.error_msg && <span style={{ color: 'var(--v6-danger)' }}>{j.error_msg.slice(0, 30)}</span>}
                    <span>{fmtDate(j.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── 管道层级呼吸灯 ── */}
          <div className="v6-section-label" style={{ marginBottom: 10 }}>
            <span>管道层级 · Layers</span>
          </div>
          <div className="v6-metric-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 16 }}>
            {[
              { label: 'L1 知识提取 Extract', key: 'l1_total', color: '#7A7A82' },
              { label: 'L2 场景聚合 Synthesis', key: 'l2_total', color: '#E5A23B' },
              { label: 'L3 画像生成 Persona', key: 'l3_total', color: '#2DBFA8' }
            ].map(layer => {
              const count = (pipeline?.[layer.key] as number) ?? 0;
              const pc = pipelineCounts as Record<string,number>;
              const recentCompleted = pipelineRecent.length > 0 && pipelineRecent[0]?.completed_at
                ? (Date.now() - new Date(pipelineRecent[0].completed_at).getTime()) < 300000
                : false;
              const active = (pc['processing'] ?? 0) > 0 || (pc['pending'] ?? 0) > 0 || recentCompleted;
              return (
                <div key={layer.key} className="v6-metric-tile">
                  <div className="v6-metric-tile__label">{layer.label}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div className="v6-metric-tile__value" style={{ fontSize: 28 }}>{count}</div>
                    <div style={{
                      width: 12, height: 12, borderRadius: '50%',
                      background: layer.color,
                      opacity: active ? 1 : 0.3,
                      animation: active ? 'pulse-breath 1.5s ease-in-out infinite' : 'none'
                    }} />
                  </div>
                  <div className="v6-metric-tile__sub">{active ? '工作中' : '待命中'}</div>
                </div>
              );
            })}
          </div>
          {/* ── 系统健康 ── */}
          <div className="v6-section-label"><span>系统健康 · Health</span></div>
          <div className="v6-health-list">
            <div className="v6-health-item">
              <span className={`v6-health-item__dot ${llmOk ? 'v6-health-item__dot--ok' : 'v6-health-item__dot--warn'}`} />
              <span className="v6-health-item__label">LLM</span>
              <span className="v6-health-item__detail">
                {llmOk ? `${llm.provider} / ${llm.model}` : '未配置 — '}
                {!llmOk && (
                  <button style={{ background: 'none', border: 'none', color: 'var(--v6-fg)', cursor: 'pointer', textDecoration: 'underline', fontSize: 12, fontFamily: 'var(--v6-font-mono)', padding: 0 }} onClick={() => onNavigate('myllm')}>前往配置 →</button>
                )}
              </span>
            </div>
            <div className="v6-health-item">
              <span className={`v6-health-item__dot ${agentCount > 0 ? 'v6-health-item__dot--ok' : 'v6-health-item__dot--warn'}`} />
              <span className="v6-health-item__label">MCP</span>
              <span className="v6-health-item__detail">
                {agentCount > 0
                  ? `${agentCount} 个 Agent 活跃（7 天内）`
                  : '暂无活跃 Agent '}
                {agentCount === 0 && (
                  <button style={{ background: 'none', border: 'none', color: 'var(--v6-fg)', cursor: 'pointer', textDecoration: 'underline', fontSize: 12, fontFamily: 'var(--v6-font-mono)', padding: 0 }} onClick={() => onNavigate('connect')}>前往接入 →</button>
                )}
              </span>
            </div>
            <div className="v6-health-item">
              <span className="v6-health-item__dot v6-health-item__dot--ok" />
              <span className="v6-health-item__label">Backend</span>
              <span className="v6-health-item__detail">服务正常</span>
            </div>
          </div>
        </div>
      )}
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
  const [code, setCode] = useState("");
  const [sendingCode, setSendingCode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  if (isAuthenticated) return <Dashboard />;

  async function sendCode(){
    if(!email){setLocalError("请先输入邮箱");return;}
    setSendingCode(true);setLocalError(null);
    try{
      const r=await fetch("/auth/send-code",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email})});
      const d=await r.json();
      setLocalError(d.sent?"验证码已发送到邮箱":"发送失败");
    }catch{setLocalError("发送失败");}
    setSendingCode(false);
  }

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
        await signup(username, email, password, code);
        setLocalError(null);
        alert("注册成功！请使用邮箱登录。");
        setMode("signin");
      } else {
        const id = email;
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
            {!isUserApp && <span className="v6-tag" style={{ marginLeft: 8 }}>管理后台 Admin</span>}
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
            <section className="v6-hero" style={{position:'relative',overflow:'hidden'}}>
              {/* 3D decoration — Spline 待接入 */}
              <div className="v6-hero__geo" aria-hidden="true">
                <div className="v6-hero__geo-ring" />
                <div className="v6-hero__geo-sphere" />
                <span className="v6-hero__geo-label">Spline 待接入</span>
              </div>
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
                {mode === "signup" ? "创建账号 Create your account" : isUserApp ? "欢迎回来 Welcome back" : "管理员登录 Admin sign in"}
              </h2>
              <p className="v6-authcard__sub">
                {mode === "signup"
                  ? "注册账号以接入 Cortex 记忆 · Sign up for Cortex memory"
                  : isUserApp
                  ? "登录 Cortex 进入你的记忆空间 · Sign in to your memory space"
                  : "使用管理员账户登录 Command Deck · Sign in to Command Deck"}
              </p>
              <form onSubmit={handleSubmit}>
                {mode === "signup" && (
                  <div className="v6-field">
                    <label className="v6-field__label">用户名 Username</label>
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
                  <label className="v6-field__label">{isUserApp ? "邮箱 Email" : "管理员账号 Admin Account"}</label>
                  <input
                    className="v6-input"
                    type={isUserApp ? "email" : "text"}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={isUserApp ? "mail@example.com" : "admin"}
                    autoComplete={isUserApp ? "email" : "username"}
                  />
                </div>
                {mode === "signup" && (
                  <div className="v6-field">
                    <label className="v6-field__label">验证码 Verification Code</label>
                    <div style={{display:"flex",gap:8}}>
                      <input className="v6-input" type="text" value={code} onChange={e=>setCode(e.target.value)} placeholder="6位数字" maxLength={6} style={{flex:1}}/>
                      <button type="button" className="v6-btn v6-btn--ghost" onClick={sendCode} disabled={sendingCode} style={{whiteSpace:"nowrap"}}>{sendingCode?"发送中...":"获取验证码"}</button>
                    </div>
                  </div>
                )}
                <div className="v6-field">
                  <label className="v6-field__label">密码 Password</label>
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
                  {loading ? "..." : mode === "signup" ? "创建账号 Create account" : "登录 Sign in"}
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

const CATEGORY_LABELS: Record<string, string> = {
  '全部': 'All',
  '文档知识': 'Docs',
  '整合知识': 'Knowledge',
  '工程技术': 'Engineering',
  '个人记忆': 'Personal',
  '自然科学': 'Science',
  '社会科学': 'Social',
  '其他': 'Other',
};

const SOURCE_LABELS: Record<string, string> = {
  document: 'doc',
  knowledge: 'knowledge',
  human: 'chat',
  agent: 'agent',
  image: 'ocr',
};

function MemoryPanel() {
  const [memories, setMemories] = useState<UserMemory[]>([]);
  const [documents, setDocuments] = useState<UserDocument[]>([]);
  const [subTab, setSubTab] = useState<'memories' | 'documents' | 'public'>('memories');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');
  const [publicCount, setPublicCount] = useState(0);

  const [activeCategory, setActiveCategory] = useState('全部');
  const [drawer, setDrawer] = useState<any>(null);  // null | { id, title, content, chunk_count, category, source_type, created_at }
  const [drawerChunks, setDrawerChunks] = useState<any[]>([]);

  const categories = ['全部', '文档知识', '整合知识', '工程技术', '个人记忆', '自然科学', '社会科学', '其他'];

  const fetchPublic = useCallback(async()=>{
    setLoading(true);
    try{
      const d = await api.get<any[]>("/memory/recent?limit=100&team_id=public&source_type=knowledge");
      const pub = d.map((x:any)=>({
        id:x.id, title:x.title||"无标题", content:x.content||"",
        category:x.category||"未分类", subcategory:x.subcategory||"", topic:x.topic||"",
        source_type:x.source_type||"knowledge", created_at:x.created_at||"",
      }));
      setMemories(pub);
      setPublicCount(pub.length);
      setDocuments([]);
    }catch(e){
      console.error(e);
      setMemories([]);
      setPublicCount(0);
    }finally{
      setLoading(false);
    }
  },[loading]);

  const fetchMemories = useCallback(async()=>{
    if(loading)return;
    setLoading(true);
    try{
      if (query.trim() === '') {
        // Query recent memories
        let url = '/memory/public';
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

  const openDrawer = async (mem: UserMemory) => {
    if (!mem.id) return;
    setDrawer({ id: mem.id, title: mem.title, content: mem.content, category: mem.category, source_type: mem.source_type, created_at: mem.created_at, score: mem.score });
    try {
      const detail = await api.get<any>(`/memory/${mem.id}`);
      setDrawer({ id: detail.id, title: detail.title, content: detail.content, category: detail.category, source_type: detail.source_type, created_at: detail.created_at, chunk_count: detail.chunk_count });
      const chunks = await api.get<any[]>(`/memory/${mem.id}/chunks`);
      setDrawerChunks(chunks || []);
    } catch { setDrawerChunks([]); }
  };

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
    if (subTab === 'public') fetchPublic();
    else { fetchMemories(); fetchDocuments(); }
  },[fetchMemories, fetchDocuments, fetchPublic, subTab]);

  // Esc to close drawer
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawer(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

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

  const getSourceTag = (source: string) => SOURCE_LABELS[source] || source || 'chat';

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

  const runUpload = async (files: File[], onDone?: () => void) => {
    if (files.length === 0) return;
    setUploading(true);
    setUploadMsg(`Uploading ${files.length} file${files.length > 1 ? 's' : ''}...`);
    const tokenHeader = localStorage.getItem('mos_token') || localStorage.getItem('admin_token') || localStorage.getItem('mos_admin_token') || '';
    let ok = 0;
    let fail = 0;
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (!f) continue;
      setUploadMsg(`Parsing (${i + 1}/${files.length}) ${f.name}…`);
      try {
        const fd = new FormData();
        fd.append('file', f);
        const r = await fetch('/memory/upload', {
          method: 'POST',
          headers: { Authorization: 'Bearer ' + tokenHeader },
          body: fd,
        });
        const d = await r.json();
        if (d.id) ok++; else fail++;
      } catch (err) {
        console.error(err);
        fail++;
      }
    }
    setUploadMsg(`Imported ${ok}${fail > 0 ? ` · failed ${fail}` : ''}`);
    setTimeout(() => {
      fetchMemories();
      fetchDocuments();
      onDone?.();
    }, 400);
    setUploading(false);
  };

  const uploadStatusKind = uploadMsg.startsWith('Imported')
    ? (uploadMsg.includes('failed') ? 'err' : 'ok')
    : '';

  return (
    <div className="v6-card">
      <div className="v6-card__head">
        <div className="v6-card__title">
          {subTab === 'public' ? '公共知识 Public' : subTab === 'memories' ? '知识库 Memories' : '文档库 Files'}
          <span className="v6-card__title-hint">
            {subTab === 'memories' ? `${filteredMemories.length} 条` : `${documents.length} 份`}
          </span>
        </div>
        <div className="v6-subtabs" role="tablist">
          <button
            className="v6-subtab"
            aria-current={subTab === 'memories' ? 'page' : undefined}
            onClick={() => setSubTab('memories')}
          >
            Memories
          </button>
          <button
            className="v6-subtab"
            aria-current={subTab === 'documents' ? 'page' : undefined}
            onClick={() => setSubTab('documents')}
          >
            Files
          </button>
          <button
            className="v6-subtab"
            aria-current={subTab === 'public' ? 'page' : undefined}
            onClick={() => setSubTab('public')}
          >
            Public · {publicCount}
          </button>
        </div>
      </div>

      <div className="v6-toolbar">
        {subTab !== 'documents' && (
          <>
            <input
              className="v6-input-global"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search memories…"
              onKeyDown={(e) => e.key === 'Enter' && fetchMemories()}
            />
            <button className="v6-btn" onClick={fetchMemories} disabled={loading}>
              {loading ? '…' : 'Search'}
            </button>
          </>
        )}
        <label className={`v6-btn ${subTab === 'documents' ? 'v6-btn--primary' : ''}`} style={{ cursor: 'pointer' }}>
          Upload
          <input
            type="file"
            accept=".txt,.md,.pdf"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => {
              const files = Array.from(e.target.files || []);
              runUpload(files);
              e.target.value = '';
            }}
            disabled={uploading}
          />
        </label>
      </div>

      {(uploading || uploadMsg) && (
        <div className={`v6-statusbar ${uploadStatusKind === 'ok' ? 'v6-statusbar--ok' : uploadStatusKind === 'err' ? 'v6-statusbar--err' : ''}`}>
          {uploadMsg}
        </div>
      )}

      {subTab !== 'documents' ? (
        <>
          <div className="v6-chips">
            {categories.map((c) => (
              <button
                key={c}
                className="v6-chip"
                aria-current={activeCategory === c ? 'page' : undefined}
                onClick={() => setActiveCategory(c)}
              >
                {CATEGORY_LABELS[c] || c}
              </button>
            ))}
          </div>
          {filteredMemories.length === 0 && !loading ? (
            <div className="v6-empty">{subTab === 'public' ? '暂无公共知识' : 'No memories in this category yet.'}</div>
          ) : (
            <div className="v6-list" style={{ maxHeight: 500, overflow: 'auto' }}>
              {filteredMemories.map((m, i) => (
                <div key={i} className="v6-list__item" onClick={() => openDrawer(m)} style={{ cursor: 'pointer' }}>
                  <div className="v6-list__item-head">
                    <div className="v6-list__item-main">
                      <div className="v6-list__item-title">{m.title}</div>
                      <div className="v6-list__item-meta">
                        <span className="v6-tag">{getSourceTag(m.source_type)}</span>
                        <span className="v6-tag">{CATEGORY_LABELS[m.category] || m.category}</span>
                        {m.subcategory && <span className="v6-tag">{m.subcategory}</span>}
                        {m.topic && (
                          <span style={{ fontSize: 11, color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)' }}>
                            #{m.topic}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="v6-list__item-aside">
                      {m.score !== undefined && <span>{(m.score * 100).toFixed(0)}%</span>}
                      <span>{formatDate(m.created_at)}</span>
                      <button
                        className="v6-btn v6-btn--ghost v6-btn--danger v6-btn--xs"
                        onClick={() => handleDelete(m.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="v6-list__item-body">{m.content}</div>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <>
          {documents.length === 0 ? (
            <div className="v6-empty">No files uploaded yet. Use Upload above.</div>
          ) : (
            <div style={{ maxHeight: 500, overflow: 'auto' }}>
              <table className="v6-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Chunks</th>
                    <th>Uploaded</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id}>
                      <td style={{ fontWeight: 500 }}>{doc.filename}</td>
                      <td style={{ color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)' }}>
                        {formatSize(doc.file_size)}
                      </td>
                      <td>
                        <span className="v6-tag">{doc.chunk_count}</span>
                      </td>
                      <td style={{ color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)' }}>
                        {formatDate(doc.created_at)}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="v6-btn v6-btn--ghost v6-btn--danger v6-btn--xs"
                          onClick={() => handleDeleteDocument(doc.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Memory Detail Drawer */}
      {drawer && (
        <>
          <div className="v6-drawer-overlay" onClick={() => setDrawer(null)} />
          <div className={`v6-drawer${drawer ? ' v6-drawer--open' : ''}`}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:16}}>
              <div>
                <div style={{fontSize:16,fontWeight:600,color:'var(--v6-fg)',marginBottom:4}}>{drawer.title}</div>
                <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
                  <span className="v6-tag">{drawer.category}</span>
                  <span className="v6-tag">{drawer.source_type}</span>
                  {drawer.chunk_count > 0 && <span className="v6-tag">{drawer.chunk_count} chunks</span>}
                  {drawer.score !== undefined && <span className="v6-tag">{(drawer.score*100).toFixed(0)}% match</span>}
                </div>
              </div>
              <button className="v6-btn v6-btn--ghost v6-btn--xs" onClick={() => setDrawer(null)}>✕</button>
            </div>
            <div className="v6-card__body" style={{marginBottom:16,whiteSpace:'pre-wrap',lineHeight:1.7,fontSize:13,maxHeight:400,overflow:'auto',background:'var(--v6-bg-sunken)',border:'1px solid var(--v6-border)',borderRadius:'var(--v6-radius-md)',padding:'14px 16px'}}>
              {drawer.content || '(empty)'}
            </div>
            {drawerChunks.length > 0 && (
              <div className="v6-card" style={{marginBottom:16,background:'var(--v6-bg-sunken)'}}>
                <div className="v6-card__title" style={{fontSize:12,marginBottom:8}}>Chunks <span className="v6-card__title-hint">{drawerChunks.length}</span></div>
                {drawerChunks.map((ch: any, i: number) => (
                  <div key={i} style={{fontSize:11,fontFamily:'var(--v6-font-mono)',color:'var(--v6-fg-muted)',padding:'4px 0',borderBottom:'1px solid var(--v6-border)'}}>
                    [{ch.chunk_index}] ({ch.token_count} tokens) {ch.content?.substring(0,120)}
                  </div>
                ))}
              </div>
            )}
            <div style={{display:'flex',gap:8}}>
              <button className="v6-btn v6-btn--xs" onClick={() => { navigator.clipboard.writeText(drawer.id).catch(()=>{}); }}>
                Copy ID
              </button>
              <button className="v6-btn v6-btn--danger v6-btn--xs" onClick={() => { handleDelete(drawer.id); setDrawer(null); }}>
                Delete
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ConnectPanel({ token: propToken }: { token?: string }) {
  const [connected, setConnected] = useState<'checking' | 'online' | 'offline'>('checking');
  useEffect(() => {
    function check() {
      fetch(window.location.origin + '/')
        .then((r) => setConnected(r.ok ? 'online' : 'offline'))
        .catch(() => setConnected('offline'));
    }
    check();
    const i = setInterval(check, 8000);
    return () => clearInterval(i);
  }, []);

  const [token] = useState(
    () =>
      propToken ||
      'mos_' +
        Math.random().toString(36).slice(2, 10) +
        '_' +
        Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('')
  );
  const getServerUrl = () =>
    window.location.origin;
  const [agent, setAgent] = useState<'cursor' | 'claude' | 'openclaw' | 'cline' | 'continue' | 'roo' | 'codex'>('cursor');
  const [copiedKey, setCopiedKey] = useState<string>('');
  const copy = async (key: string, text: string) => {
    // navigator.clipboard requires a secure context — fails silently on plain
    // http://192.168.x.x deployments. Fall back to the legacy textarea trick.
    let ok = false;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        ok = true;
      }
    } catch { /* fall through */ }
    if (!ok) {
      try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        ta.style.top = '0';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ok = document.execCommand('copy');
        document.body.removeChild(ta);
      } catch { /* nothing else to try */ }
    }
    if (ok) {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(''), 1500);
    } else {
      setCopiedKey('error');
      setTimeout(() => setCopiedKey(''), 2000);
    }
  };

  const configs: Record<string, string> = {
    cursor: JSON.stringify({ mcpServers: { 'ai-memory-os': { command: 'npx', args: ['-y', 'ai-memory-os-mcp', '--token=' + token, '--server=' + getServerUrl()], env: {} } } }, null, 2),
    claude: JSON.stringify({ mcpServers: { 'ai-memory-os': { command: 'npx', args: ['-y', 'ai-memory-os-mcp'], env: { MOS_TOKEN: token, MOS_SERVER: getServerUrl() } } } }, null, 2),
    openclaw: 'SSE endpoint: ' + getServerUrl() + '/mcp?token=' + token,
    cline: JSON.stringify({ 'ai-memory-os': { command: 'npx', args: ['-y', 'ai-memory-os-mcp', '--token=' + token, '--server=' + getServerUrl()], disabled: false, autoApprove: ['memory_search', 'memory_list', 'memory_status'] } }, null, 2),
    continue: JSON.stringify({ experimental: { modelContextProtocolServers: [{ transport: { type: 'stdio', command: 'npx', args: ['-y', 'ai-memory-os-mcp', '--token=' + token, '--server=' + getServerUrl()] } }] } }, null, 2),
    roo: JSON.stringify({ 'ai-memory-os': { command: 'npx', args: ['-y', 'ai-memory-os-mcp', '--token=' + token, '--server=' + getServerUrl()], alwaysAllow: ['memory_search', 'memory_store'] } }, null, 2),
    codex: '# ~/.codex/config.toml\n[[mcp_servers]]\nname = "ai-memory-os"\ncommand = "npx"\nargs = ["-y", "ai-memory-os-mcp", "--token=' + token + '", "--server=' + getServerUrl() + '"]',
  };

  const FILE_PATHS: Record<string, string> = {
    cursor: '~/.cursor/mcp.json',
    claude: '~/Library/Application Support/Claude/claude_desktop_config.json',
    openclaw: 'OpenClaw → Settings → MCP Servers',
    cline: 'VS Code → Cline → MCP Servers',
    continue: '~/.continue/config.json',
    roo: 'VS Code → Roo Code → MCP Servers',
    codex: '~/.codex/config.toml',
  };

  const AGENTS = [
    { id: 'cursor', name: 'Cursor' },
    { id: 'claude', name: 'Claude Desktop' },
    { id: 'openclaw', name: 'OpenClaw' },
    { id: 'cline', name: 'Cline' },
    { id: 'continue', name: 'Continue' },
    { id: 'roo', name: 'Roo Code' },
    { id: 'codex', name: 'Codex CLI' },
  ];

  const SETUP_STEPS: Record<string, string[]> = {
    cursor: ['Cursor → Settings → MCP', 'Add Server → Command', 'Paste JSON above', 'Save, restart Cursor'],
    claude: ['Open ~/Library/Application Support/Claude/claude_desktop_config.json', 'Paste into mcpServers', 'Save, fully quit Claude Desktop', 'Reopen'],
    openclaw: ['OpenClaw → Agent settings', 'Add SSE under MCP Servers', 'Paste URL above', 'Save'],
    cline: ['VS Code → Cline settings', 'Paste JSON into MCP Servers', 'Restart VS Code'],
    continue: ['Open ~/.continue/config.json', 'Append JSON to experimental.modelContextProtocolServers', 'Save, restart extension'],
    roo: ['VS Code → Roo Code → MCP Servers → Add', 'Paste JSON above', 'Save'],
    codex: ['Open ~/.codex/config.toml', 'Append config above', 'Save'],
  };

  // eslint-disable-next-line
  const SYSTEM_PROMPTS: Record<string, string> = { standard: '你已连接 Cortex 长期记忆系统（9个工具）。\n\n【对话开始时，静默执行以下操作】：\n1. 调用 memory_get_persona → 了解用户背景和偏好\n2. 调用 memory_task_canvas_get → 恢复未完成任务（如有）\n3. 调用 memory_search(用户问题关键词) → 检索相关知识\n\n【对话中，发现以下内容时立即调用 memory_store】：\n- 用户偏好、习惯、要求\n- 技术决策及原因\n- 项目结构、约定、配置\n- 用户说"记住"的任何内容\n- 解决的复杂问题（问题+方案）\n\n【长任务进行中】：\n每完成一个重要阶段，调用 memory_task_canvas_update 更新 Mermaid 任务画布\n\n【对话结束时】：\n若对话产生了有价值的结论或方案，调用 memory_store 保存摘要\n\n所有上述操作静默完成，不向用户报告，除非操作失败', concise: '[记忆规则] ①开始→persona+search+canvas_get ②重要信息→store ③进展→canvas_update ④记住/忘掉/搜索→对应操作。静默执行。', dev: '你是连接了 AI Memory OS 的开发助手。记忆工具是你感知能力的延伸。\n\n【每次对话开始】静默执行：\n① memory_get_persona 了解技术栈和项目背景\n② memory_task_canvas_get 恢复上次未完成的开发任务\n③ memory_search(项目名/功能关键词) 检索相关代码约定\n\n【代码工作中】：\n- 确定了技术方案 → memory_store（tags: ["架构决策"]）\n- 解决了 Bug → memory_store（title: "Bug修复: xxx"，tags: ["bug", "技术栈"]）\n- 完成了功能阶段 → memory_task_canvas_update（更新进度图）\n\n【存储代码记忆时】：\n只存逻辑摘要和关键决策，不存完整大段代码。\n格式：问题背景 + 解决思路 + 关键代码片段（< 20行）\n\n所有操作静默完成。' };
  const [pType, setPType] = useState<'standard' | 'concise' | 'dev'>('standard');

  const status = {
    online: { label: 'Connected', cls: 'v6-llmpill__dot--ok' },
    offline: { label: 'Offline', cls: 'v6-llmpill__dot--warn' },
    checking: { label: 'Checking…', cls: '' },
  }[connected];

  return (
    <div className="v6-card">
      <div className="v6-card__head">
        <div className="v6-card__title">
          接入配置 Connect
          <span className="v6-card__title-hint">MCP 网关 · 连接你的 AI Agent</span>
        </div>
        <span className="v6-llmpill">
          <span className={`v6-llmpill__dot ${status.cls}`} />
          {status.label}
        </span>
      </div>


      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 11, color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 8 }}>
          MCP Token 凭证
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'stretch' }}>
          <code style={{ flex: 1, minWidth: 0, background: 'var(--v6-bg-sunken)', border: '1px solid var(--v6-border)', borderRadius: 'var(--v6-radius-md)', padding: '10px 14px', fontSize: 12.5, fontFamily: 'var(--v6-font-mono)', wordBreak: 'break-all', color: 'var(--v6-fg)' }}>
            {token}
          </code>
          <button className="v6-btn" onClick={() => copy('token', token)}>
            {copiedKey === 'token' ? '已复制 ✓' : '复制 Copy'}
          </button>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 8 }}>
          选择 Agent 客户端
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {AGENTS.map((a) => (
            <button
              key={a.id}
              className="v6-chip"
              aria-current={agent === a.id ? 'page' : undefined}
              onClick={() => setAgent(a.id as typeof agent)}
            >
              {a.name}
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)' }}>
            {FILE_PATHS[agent] || 'N/A'}
          </span>
          <button className="v6-btn v6-btn--xs" onClick={() => copy('config', configs[agent] || '')}>
            {copiedKey === 'config' ? '已复制 ✓' : '复制配置 Copy'}
          </button>
        </div>
        <pre style={{ margin: 0, background: 'var(--v6-bg-sunken)', border: '1px solid var(--v6-border)', borderRadius: 'var(--v6-radius-md)', padding: 14, fontSize: 11.5, fontFamily: 'var(--v6-font-mono)', color: 'var(--v6-fg)', whiteSpace: 'pre-wrap', maxHeight: 240, overflow: 'auto' }}>
          {configs[agent] || ''}
        </pre>
      </div>

      <div style={{ marginBottom: 24, padding: '14px 16px', background: 'var(--v6-bg-sunken)', border: '1px solid var(--v6-border)', borderRadius: 'var(--v6-radius-md)' }}>
        <div style={{ fontSize: 11, color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
          接入步骤 Setup
        </div>
        <ol style={{ paddingLeft: 18, margin: 0, fontSize: 12.5, color: 'var(--v6-fg)', lineHeight: 1.75 }}>
          {SETUP_STEPS[agent]?.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
      </div>

      <div style={{ borderTop: '1px solid var(--v6-border)', paddingTop: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, flexWrap: 'wrap', gap: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            系统提示词 System Prompt
          </span>
          <div className="v6-subtabs">
            {(['standard', 'concise', 'dev'] as const).map((k) => (
              <button
                key={k}
                className="v6-subtab"
                aria-current={pType === k ? 'page' : undefined}
                onClick={() => setPType(k)}
              >
                {k}
              </button>
            ))}
          </div>
        </div>
        <pre style={{ margin: 0, background: 'var(--v6-bg-sunken)', border: '1px solid var(--v6-border)', borderRadius: 'var(--v6-radius-md)', padding: 14, fontSize: 11.5, fontFamily: 'var(--v6-font-mono)', color: 'var(--v6-fg)', whiteSpace: 'pre-wrap', lineHeight: 1.7, maxHeight: 220, overflow: 'auto', marginBottom: 8 }}>
          {SYSTEM_PROMPTS[pType]}
        </pre>
        <button className="v6-btn v6-btn--xs" onClick={() => copy('prompt', SYSTEM_PROMPTS[pType] || '')}>
          {copiedKey === 'prompt' ? '已复制 ✓' : '复制提示词 Copy'}
        </button>
      </div>
    </div>
  );
}

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
        用户画像 Persona
        <span className="v6-card__title-hint">长期用户档案 · long-term profile</span>
      </div>
      <div className="v6-card__body">
        {loading ? <div style={{ color: "var(--v6-fg-muted)" }}>Loading…</div> : <pre>{persona}</pre>}
      </div>
      <div className="v6-card__actions">
        <button className="v6-btn" onClick={load}>刷新 Refresh</button>
      </div>
    </div>
  );
}

function MyLLMPanel() {
  const getToken = () => localStorage.getItem('admin_token') || localStorage.getItem('mos_admin_token') || '';
  const authHeaders = () => ({ 'Content-Type': 'application/json', Authorization: 'Bearer ' + getToken() });
  // Hide local-only providers (Ollama etc.) from a hosted product perspective.
  const PROVIDERS = ALL_PROVIDERS.filter((x) => !x.region || x.region !== 'local');

  const [p, setP] = useState('');
  const [k, setK] = useState('');
  const [m, setM] = useState('');
  const [b, setB] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const prov = PROVIDERS.find((x) => x.id === p);
  const chatModels = (prov?.models || []).filter((mm) => mm.type === 'chat' || mm.type === 'reasoning');
  const freeChatCount = (px: typeof PROVIDERS[number]) =>
    px.models.filter((mm) => (mm.type === 'chat' || mm.type === 'reasoning') && mm.free).length;
  const chatCount = (px: typeof PROVIDERS[number]) =>
    px.models.filter((mm) => mm.type === 'chat' || mm.type === 'reasoning').length;

  const savedCfg = useRef<{provider:string; model:string; base:string}>({provider:'', model:'', base:''});

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    fetch('/api/user/llm', { headers: authHeaders() })
      .then((r) => r.json())
      .then((d) => {
        savedCfg.current = { provider: d.provider || '', model: d.model || '', base: d.base_url || '' };
        if (d.has_key) setK('••••••••');
        // Don't auto-expand — user clicks to select
      });
  }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (p && prov) {
      setB(prov.baseUrl);
      const chatIds = chatModels.map((cm) => cm.id);
      if (!m || !chatIds.includes(m)) setM(chatIds[0] || '');
    }
    if (!p) setM('');
  }, [p]);

  async function save() {
    if (!p || !m) { setMsg('Pick a provider and model first'); return; }
    setBusy(true);
    try {
      await fetch('/api/user/llm', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ provider: p, api_key: k, model: m, base_url: b }),
      });
      setMsg('已保存 Saved');
    } catch { setMsg('保存失败 Save failed'); }
    setBusy(false);
  }
  async function test() {
    setBusy(true);
    try {
      const r = await fetch('/api/user/llm/test', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ provider: p, api_key: k, base_url: b, model: m }),
      });
      const d = await r.json();
      setMsg(d.connected ? '连接成功 Connected ✓' : '连接失败 Failed: ' + (d.error || d.status));
    } catch { setMsg('Test failed'); }
    setBusy(false);
  }

  const msgKind = msg.startsWith('已保存') || msg.startsWith('连接成功') ? 'ok' : msg ? 'err' : '';
  const cnProviders = PROVIDERS.filter((x) => x.region === 'cn');
  const intlProviders = PROVIDERS.filter((x) => x.region === 'intl');

  return (
    <div className="v6-card">
      <div className="v6-card__head">
        <div className="v6-card__title">
          LLM 大模型配置
          <span className="v6-card__title-hint">你的 Key，你的账单 · BYOK</span>
        </div>
      </div>

      {/* BYOK: keep the commercial model transparent up front */}
      <div className="v6-byok">
        <span className="v6-byok__icon">i</span>
        <div>
          <strong>你的 key，你的账单 — Cortex 不抽成。</strong>
          {" "}请求直发你选择的 provider，费用由你向 provider 直接结算。
          需要零成本？选下方带 <span className="v6-freebadge" style={{ margin: '0 3px' }}>FREE</span> 标识的模型即可。
        </div>
      </div>

      {/* Provider grid — China */}
      <div className="v6-section-label">
        <span>中国厂商 · China</span>
        <span className="v6-section-label__count">{cnProviders.length}</span>
      </div>
      <div className="v6-provider-grid">
        {cnProviders.map((x) => (
          <button
            key={x.id}
            className="v6-provider-card"
            aria-current={p === x.id ? 'page' : undefined}
            onClick={() => {
                if (p === x.id) { setP(''); setK(''); setM(''); }
                else {
                  setP(x.id);
                  setK('');
                  if (x.id === savedCfg.current.provider) {
                    setM(savedCfg.current.model);
                    setB(savedCfg.current.base);
                  }
                }
              }}
            type="button"
          >
            <div className="v6-provider-card__name">
              {x.nameZh}
              <span className="v6-provider-card__region">CN</span>
            </div>
            <div className="v6-provider-card__meta">
              {chatCount(x)} models{freeChatCount(x) > 0 && <> · <b>{freeChatCount(x)} free</b></>}
            </div>
            {x.signupUrl && (
              <a
                className="v6-provider-card__signup"
                href={x.signupUrl}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
              >
                Get key ↗
              </a>
            )}
          </button>
        ))}
      </div>

      {/* Provider grid — Intl */}
      <div className="v6-section-label">
        <span>海外厂商 · International</span>
        <span className="v6-section-label__count">{intlProviders.length}</span>
      </div>
      <div className="v6-provider-grid">
        {intlProviders.map((x) => (
          <button
            key={x.id}
            className="v6-provider-card"
            aria-current={p === x.id ? 'page' : undefined}
            onClick={() => {
                if (p === x.id) { setP(''); setK(''); setM(''); }
                else {
                  setP(x.id);
                  setK('');
                  if (x.id === savedCfg.current.provider) {
                    setM(savedCfg.current.model);
                    setB(savedCfg.current.base);
                  }
                }
              }}
            type="button"
          >
            <div className="v6-provider-card__name">
              {x.name}
              <span className="v6-provider-card__region">INTL</span>
            </div>
            <div className="v6-provider-card__meta">
              {chatCount(x)} models{freeChatCount(x) > 0 && <> · <b>{freeChatCount(x)} free</b></>}
            </div>
            {x.signupUrl && (
              <a
                className="v6-provider-card__signup"
                href={x.signupUrl}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
              >
                Get key ↗
              </a>
            )}
          </button>
        ))}
      </div>

      {/* Model list of selected provider */}
      {prov && chatModels.length > 0 && (
        <>
          <div className="v6-section-label">
            <span>{prov.nameZh} · models</span><button onClick={() => setP('')} style={{marginLeft:8,background:"none",border:"1px solid var(--v6-border)",borderRadius:4,color:"var(--v6-fg-muted)",cursor:"pointer",fontSize:11,padding:"1px 6px"}}>×</button>
            <span className="v6-section-label__count">
              {chatModels.filter((mm) => mm.free).length} free · {chatModels.length} total
            </span>
          </div>
          <div className="v6-modellist">
            {chatModels.map((mm) => (
              <div
                key={mm.id}
                className="v6-model-row"
                aria-current={m === mm.id ? 'true' : undefined}
                onClick={() => setM(mm.id)}
              >
                <div className="v6-model-row__main">
                  <div className="v6-model-row__name">
                    {mm.name}
                    {mm.recommended && <span className="v6-modelrow-star">★</span>}
                  </div>
                  {mm.note && <div className="v6-model-row__note">{mm.note}</div>}
                </div>
                <div className="v6-model-row__aside">
                  {mm.ctx && <span>{Math.round(mm.ctx / 1000)}K ctx</span>}
                  {mm.free ? <span className="v6-freebadge">FREE</span> : <span className="v6-pricebadge">{mm.price || 'paid'}</span>}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* API key + actions */}
      {prov && (
        <>
          <div className="v6-section-label">
            <span>API Key 密钥</span>
          </div>
          <input
            className="v6-input-global"
            type="password"
            value={k}
            onChange={(e) => setK(e.target.value)}
            placeholder={`Paste your ${prov.name} API key`}
            style={{ width: '100%', marginBottom: 12 }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="v6-btn v6-btn--primary" onClick={save} disabled={busy || !m}>
              {busy ? '…' : '保存 Save'}
            </button>
            <button className="v6-btn" onClick={test} disabled={busy || !k || !m}>
              测试连接 Test
            </button>
            <span style={{ flex: 1 }} />
            <span style={{ fontSize: 11.5, fontFamily: 'var(--v6-font-mono)', color: 'var(--v6-fg-muted)', alignSelf: 'center' }}>
              endpoint: {b || prov.baseUrl}
            </span>
          </div>
          {msg && (
            <div className={`v6-statusbar ${msgKind === 'ok' ? 'v6-statusbar--ok' : msgKind === 'err' ? 'v6-statusbar--err' : ''}`} style={{ marginTop: 14, marginBottom: 0 }}>
              {msg}
            </div>
          )}
        </>
      )}

      <UsagePanel />
    </div>
  );
}

function UsagePanel() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [usage, setUsage] = useState<any>(null);
  const getToken = () => localStorage.getItem('admin_token') || localStorage.getItem('mos_admin_token') || '';
  useEffect(() => {
    const fetchStats = () => {
      fetch('/user/stats', { headers: { Authorization: 'Bearer ' + getToken() } })
        .then((r) => r.json())
        .then(setUsage)
        .catch(() => {});
    };
    fetchStats();
    const id = setInterval(fetchStats, 5000);
    return () => clearInterval(id);
  }, []);

  if (!usage) return null;
  const models: { provider_name: string; model_name: string; prompt: number; completion: number; total: number }[] =
    (usage.usage_by_model || []).map((m: any) => ({
      provider_name: m.provider_name || '',
      model_name: m.model_name || '',
      prompt: m.prompt_tokens ?? m.prompt ?? 0,
      completion: m.completion_tokens ?? m.completion ?? 0,
      total: m.total_tokens ?? m.total ?? 0,
    })).filter((m: any) => m.total > 0);
  const totalPrompt = models.reduce((s, m) => s + (m.prompt || 0), 0);
  const totalCompletion = models.reduce((s, m) => s + (m.completion || 0), 0);

  const pipe = usage.pipeline_stats || {
    l1_calls: 0,
    l2_calls: 0,
    l3_calls: 0,
    l1_tokens: 0,
    l2_tokens: 0,
    l3_tokens: 0,
    total_tokens: 0
  };
  const hasPipelineData = (
    pipe.l1_calls > 0 || pipe.l2_calls > 0 || pipe.l3_calls > 0 ||
    pipe.l1_tokens > 0 || pipe.l2_tokens > 0 || pipe.l3_tokens > 0
  );

  const hasData = (totalPrompt + totalCompletion > 0) || hasPipelineData;
  const fmt = (n: number) => n >= 1000 ? (n / 1000).toFixed(1) + 'K' : String(n);

  return (
    <div style={{ marginTop: 24, paddingTop: 20, borderTop: '1px solid var(--v6-border)' }}>
      <div className="v6-section-label">
        <span>用量与计费 · Usage & Billing（今日）</span>
        <span className="v6-section-label__count" style={{ fontWeight: 400 }}>
          费用直接结算给 provider
        </span>
      </div>

      {!hasData ? (
        <div className="v6-empty" style={{ padding: '20px 0', textAlign: 'left' }}>
          <div style={{ fontSize: 13, color: 'var(--v6-fg-muted)' }}>
            暂无使用记录 · No usage yet
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--v6-fg-faint)', marginTop: 4, fontFamily: 'var(--v6-font-mono)' }}>
            通过 MCP 接入 Agent 或使用 completions 代理后，Token 消耗会在此实时显示。
          </div>
        </div>
      ) : (
        <>
          {(totalPrompt + totalCompletion > 0) && (
            <>
              <div className="v6-metric-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 16 }}>
                <div className="v6-metric-tile">
                  <div className="v6-metric-tile__label">输入 Prompt Tokens</div>
                  <div className="v6-metric-tile__value">{fmt(totalPrompt)}</div>
                </div>
                <div className="v6-metric-tile">
                  <div className="v6-metric-tile__label">输出 Completion Tokens</div>
                  <div className="v6-metric-tile__value">{fmt(totalCompletion)}</div>
                </div>
                <div className="v6-metric-tile">
                  <div className="v6-metric-tile__label">预估费用 Est. Cost</div>
                  <div className="v6-metric-tile__value">
                    {(()=>{const p=usage.usage_by_model||[];let t=0;for(const m of p){const k=(m.prompt_tokens||0)+(m.completion_tokens||0);t+=m.model_name?.includes('free')||m.provider_name==='ollama'||m.provider_name==='groq'?0:k/1e6*(m.provider_name==='alibaba'?0.5:m.provider_name==='zhipu'?1.0:m.provider_name==='deepseek'?1.0:2.0)};return t>0.001?'¥'+t.toFixed(3):t>0?'<¥0.001':'—'})()}
                  </div>
                  <div className="v6-metric-tile__sub">直接结算给 provider</div>
                </div>
              </div>

              <div className="v6-modellist" style={{ marginBottom: hasPipelineData ? 24 : 0 }}>
                {models.map((m, i) => (
                  <div key={i} className="v6-usage-row">
                    <div className="v6-usage-row__label">{m.model_name || m.provider_name}</div>
                    <div className="v6-usage-row__nums">
                      <span>输入 <b>{fmt(m.prompt || 0)}</b></span>
                      <span>输出 <b>{fmt(m.completion || 0)}</b></span>
                      <span>合计 <b>{fmt(m.total || 0)}</b> tokens</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {hasPipelineData && (
            <div style={{ marginTop: (totalPrompt + totalCompletion > 0) ? 20 : 0, paddingTop: (totalPrompt + totalCompletion > 0) ? 16 : 0, borderTop: (totalPrompt + totalCompletion > 0) ? '1px dashed var(--v6-border)' : 'none' }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--v6-fg-muted)', marginBottom: 12 }}>
                记忆处理管道 · Memory Processing Pipelines
              </div>
              <div className="v6-metric-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                <div className="v6-metric-tile">
                  <div className="v6-metric-tile__label">L1 事实提取 (L1 Fact Extraction)</div>
                  <div className="v6-metric-tile__value">{fmt(pipe.l1_tokens)}</div>
                  <div className="v6-metric-tile__sub">{pipe.l1_calls} 次调用 · calls</div>
                </div>
                <div className="v6-metric-tile">
                  <div className="v6-metric-tile__label">L2 场景合成 (L2 Scene Synthesis)</div>
                  <div className="v6-metric-tile__value">{fmt(pipe.l2_tokens)}</div>
                  <div className="v6-metric-tile__sub">{pipe.l2_calls} 次调用 · calls</div>
                </div>
                <div className="v6-metric-tile">
                  <div className="v6-metric-tile__label">L3 画像生成 (L3 Persona Generation)</div>
                  <div className="v6-metric-tile__value">{fmt(pipe.l3_tokens)}</div>
                  <div className="v6-metric-tile__sub">{pipe.l3_calls} 次调用 · calls</div>
                </div>
                <div className="v6-metric-tile" style={{ borderLeft: '2px solid var(--v6-primary, #6366f1)' }}>
                  <div className="v6-metric-tile__label">管道总消耗 Total Pipeline</div>
                  <div className="v6-metric-tile__value" style={{ color: 'var(--v6-primary, #6366f1)' }}>{fmt(pipe.total_tokens)}</div>
                  <div className="v6-metric-tile__sub">Tokens</div>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      <div style={{ marginTop: 12, fontSize: 11.5, color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)' }}>
        Pipeline status → <button
          style={{ background: 'none', border: 'none', color: 'var(--v6-fg)', cursor: 'pointer', fontFamily: 'inherit', fontSize: 'inherit', textDecoration: 'underline', padding: 0 }}
          onClick={() => {
            // Signal parent to navigate to overview — use custom event
            window.dispatchEvent(new CustomEvent('cortex-nav', { detail: 'overview' }));
          }}
        >Overview tab</button>
      </div>
    </div>
  );
}

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

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: 'pending',
    processing: 'running',
    done: 'done',
    failed: 'failed',
    dead: 'dead',
  };
  return <span className="v6-tag">{map[status] || status}</span>;
}

export function PipelineStatusPanel() {
  const [data, setData] = useState<PipelineStatus | null>(null);
  const [err, setErr] = useState<string>('');
  const [expanded, setExpanded] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const d = await getUserPipelineStatus();
      setData(d);
      setErr('');
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Load failed');
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  const c = data?.counts || { pending: 0, processing: 0, done: 0, failed: 0, dead: 0 };
  const inFlight = data?.in_flight ?? 0;
  const recent: PipelineJob[] = data?.recent || [];

  const tileStyle: React.CSSProperties = {
    background: 'var(--v6-bg-sunken)',
    border: '1px solid var(--v6-border)',
    borderRadius: 'var(--v6-radius-md)',
    padding: '10px 8px',
    textAlign: 'center',
  };
  const tileLabel: React.CSSProperties = {
    fontSize: 10,
    color: 'var(--v6-fg-muted)',
    fontFamily: 'var(--v6-font-mono)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  };
  const tileValue: React.CSSProperties = {
    fontSize: 22,
    fontWeight: 600,
    color: 'var(--v6-fg)',
    letterSpacing: '-0.02em',
    marginTop: 2,
    fontVariantNumeric: 'tabular-nums',
  };

  return (
    <div style={{ marginTop: 24, paddingTop: 20, borderTop: '1px solid var(--v6-border)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
        <div className="v6-card__title" style={{ marginBottom: 0 }}>
          管线状态 Pipeline
          <span className="v6-card__title-hint">24h · 每 5 秒自动刷新</span>
        </div>
        <button className="v6-btn v6-btn--xs" onClick={refresh}>刷新 Refresh</button>
      </div>

      {!data?.configured && (
        <div className="v6-statusbar v6-statusbar--err" style={{ marginBottom: 12 }}>
          尚未配置 LLM — 请先在上方选择厂商并保存 API Key，才能运行记忆管线。
        </div>
      )}
      {err && (
        <div className="v6-statusbar v6-statusbar--err" style={{ marginBottom: 12 }}>{err}</div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginBottom: 14 }}>
        {[
          { key: 'pending', label: 'pending' },
          { key: 'processing', label: 'running' },
          { key: 'done', label: 'done' },
          { key: 'failed', label: 'failed' },
          { key: 'dead', label: 'dead' },
        ].map((s) => (
          <div key={s.key} style={tileStyle}>
            <div style={tileLabel}>{s.label}</div>
            <div style={tileValue}>{(c as Record<string, number>)[s.key] ?? 0}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', fontSize: 11.5, color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)', marginBottom: 12 }}>
        <div>in-flight: <span style={{ color: 'var(--v6-fg)' }}>{inFlight}</span></div>
        <div>last ok: <span style={{ color: 'var(--v6-fg)' }}>{fmtTime(data?.last_completed_at || null)}</span></div>
        {data?.last_failed_at && (
          <div>last fail: <span style={{ color: 'var(--v6-danger)' }}>{fmtTime(data.last_failed_at)}</span></div>
        )}
      </div>

      <button className="v6-btn v6-btn--xs" onClick={() => setExpanded((v) => !v)} style={{ marginBottom: 10 }}>
        {expanded ? '收起' : '展开'} 最近 {recent.length} 条任务
      </button>

      {expanded &&
        (recent.length === 0 ? (
          <div className="v6-empty">暂无管线任务 · No pipeline jobs yet</div>
        ) : (
          <div style={{ maxHeight: 260, overflow: 'auto' }}>
            <table className="v6-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Task</th>
                  <th>Created</th>
                  <th>Duration</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((j) => (
                  <tr key={j.id}>
                    <td><StatusBadge status={j.status} /></td>
                    <td style={{ fontFamily: 'var(--v6-font-mono)' }}>{j.task_type}</td>
                    <td style={{ color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)' }}>{fmtTime(j.created_at)}</td>
                    <td style={{ fontFamily: 'var(--v6-font-mono)' }}>{fmtDuration(j.started_at, j.completed_at)}</td>
                    <td style={{ color: 'var(--v6-danger)', maxWidth: 240, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontFamily: 'var(--v6-font-mono)' }} title={j.error_msg || ''}>
                      {j.error_msg || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
    </div>
  );
}

function CanvasPanel() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [canvases, setCanvases] = useState<any[]>([]);
  const [activeAgent, setActiveAgent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const svgRef = useRef<HTMLDivElement>(null);

  async function load() {
    setLoading(true);
    try {
      const r = await fetch('/canvas', {
        headers: { Authorization: 'Bearer ' + (localStorage.getItem('admin_token') || localStorage.getItem('mos_admin_token') || '') },
      });
      const d = await r.json();
      const arr = Array.isArray(d) ? d : d.task_id ? [d] : [];
      setCanvases(arr);
      if (arr.length > 0 && !arr.find((x) => x.agent_id === activeAgent)) {
        setActiveAgent(arr[0].agent_id || 'default');
      } else if (arr.length === 0) {
        setActiveAgent('');
      }
    } catch {
      setCanvases([]);
    }
    setLoading(false);
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, []);

  // 5s auto-refresh
  useEffect(() => {
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);
  // eslint-disable-next-line react-hooks/exhaustive-deps

  useEffect(() => {
    let md = 'graph TD\n  A[No tasks yet] --> B[Will appear here]';
    if (canvases.length > 0 && activeAgent) {
      const c = canvases.find((x) => x.agent_id === activeAgent) || canvases[0];
      if (c && c.canvas_mermaid) md = c.canvas_mermaid;
    }
    let isCancelled = false;
    setTimeout(async () => {
      if (svgRef.current && !isCancelled) {
        try {
          const mermaid = (await import('mermaid')).default;
          mermaid.initialize({
            startOnLoad: false,
            theme: 'base',
            themeVariables: {
              primaryColor: '#101013',
              primaryTextColor: '#ECECF0',
              primaryBorderColor: '#26262C',
              lineColor: '#7A7A82',
              secondaryColor: '#1A1A1F',
              tertiaryColor: '#050507',
              background: '#08080B',
              mainBkg: '#101013',
              nodeBorder: '#26262C',
              fontFamily: 'Geist, sans-serif',
            },
          });
          const { svg } = await mermaid.render('mermaid-canvas-' + Date.now(), md);
          if (!isCancelled) svgRef.current.innerHTML = svg;
        } catch {
          if (!isCancelled) svgRef.current.innerHTML = '<div style="color:var(--v6-fg-muted);font-family:var(--v6-font-mono);font-size:12px">Render failed</div>';
        }
      }
    }, 100);
    return () => { isCancelled = true; };
  }, [canvases, activeAgent]);

  return (
    <div className="v6-card">
      <div className="v6-card__head">
        <div className="v6-card__title">
          任务画布 Canvas
          <span className="v6-card__title-hint">多 Agent 协作视图 · multi-agent</span>
        </div>
      </div>

      <div className="v6-toolbar">
        <button className="v6-btn" onClick={load} disabled={loading}>
          {loading ? '…' : '刷新 Refresh'}
        </button>
      </div>

      {canvases.length > 0 && (
        <div className="v6-chips">
          {canvases.map((c) => (
            <button
              key={c.agent_id}
              className="v6-chip"
              aria-current={activeAgent === c.agent_id ? 'page' : undefined}
              onClick={() => setActiveAgent(c.agent_id)}
            >
              {c.agent_id || 'default'}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="v6-empty">Loading…</div>
      ) : (
        <div
          ref={svgRef}
          style={{
            background: 'var(--v6-bg-sunken)',
            border: '1px solid var(--v6-border)',
            borderRadius: 'var(--v6-radius-md)',
            padding: 18,
            minHeight: 120,
            overflow: 'auto',
          }}
        />
      )}
      {/* Checklist: completed + next steps */}
      {canvases.length > 0 && activeAgent && (() => {
        const canvas = canvases.find(c => c.agent_id === activeAgent);
        if (!canvas) return null;
        let completed: string[] = [];
        let nextSteps: string[] = [];
        try { completed = JSON.parse(canvas.completed_steps || '[]'); } catch {}
        try { nextSteps = JSON.parse(canvas.next_steps || '[]'); } catch {}
        if (completed.length === 0 && nextSteps.length === 0) return null;
        return (
          <div className="v6-card" style={{ marginTop: 14 }}>
            <div className="v6-card__head">
              <div className="v6-card__title">任务进度 Progress <span className="v6-card__title-hint">{completed.length} done / {nextSteps.length} todo</span></div>
            </div>
            <div className="v6-canvas-checklist">
              {completed.map((s, i) => (
                <div key={`done${i}`} className="v6-canvas-step done">✓ {s}</div>
              ))}
              {nextSteps.map((s, i) => (
                <div key={`todo${i}`} className="v6-canvas-step todo">○ {s}</div>
              ))}
            </div>
          </div>
        );
      })()}
      <div style={{ fontSize: 11, color: 'var(--v6-fg-muted)', fontFamily: 'var(--v6-font-mono)', marginTop: 10 }}>
        Each agent under the same task keeps an isolated canvas.
      </div>
    </div>
  );
}

// Exported for the admin Audit page; no longer rendered from the user dashboard.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function AuditPanel() {
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
        操作记录 Activity
        <span className="v6-card__title-hint">最近 30 条 · latest events</span>
      </div>
      {loading ? (
        <div className="v6-empty">Loading…</div>
      ) : logs.length === 0 ? (
        <div className="v6-empty">暂无操作记录 · No activity yet</div>
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
