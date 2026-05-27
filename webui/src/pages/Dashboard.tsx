import { useEffect, useState, useRef, useCallback } from 'react';
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { getStats, getThroughput, getRouting, testEngine, getLLMEngineConfig } from '../api/endpoints';
import type { DashboardStats, ServiceHealth } from '../api/types';
import { PROVIDERS } from '../data/models';

Chart.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler);

function MetricTile({ label, value, sub, done }: { label: string; value: string; sub: string; done?: boolean }) {
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
  return (
    <div className="v6-metric-tile" onPointerMove={handleTilt} onPointerLeave={resetTilt}>
      <div className="v6-metric-tile__label">{label}</div>
      <div className={`v6-metric-tile__value${done ? ' v6-metric-tile__value--done' : ''}`}>{value}</div>
      <div className="v6-metric-tile__sub">{sub}</div>
    </div>
  );
}

const SVCS: { key: keyof ServiceHealth; label: string }[] = [
  { key: 'postgres', label: 'PostgreSQL' },
  { key: 'qdrant', label: 'Qdrant' },
  { key: 'neo4j', label: 'Neo4j' },
  { key: 'redis', label: 'Redis' },
  { key: 'minio', label: 'MinIO' }
];

export function DashboardPage() {
  const [s, setStats] = useState<DashboardStats | null>(null);
  const [tl, setTpL] = useState<string[]>([]);
  const [tv, setTpV] = useState<number[]>([]);
  const [svc, setSvc] = useState<ServiceHealth | null>(null);
  const [log, setLog] = useState<string[]>(['[SYS] Online.']);
  const lr = useRef<HTMLDivElement>(null);

  // Model & Compute Routing Status
  interface TestState {
    testing: boolean;
    status: 'idle' | 'ok' | 'err';
    error?: string;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [routing, setRouting] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [llmEngine, setLlmEngine] = useState<any>(null);
  const [testStates, setTestStates] = useState<Record<'classifier' | 'reflection' | 'embedding' | 'rerank', TestState>>({
    classifier: { testing: false, status: 'idle' },
    reflection: { testing: false, status: 'idle' },
    embedding: { testing: false, status: 'idle' },
    rerank: { testing: false, status: 'idle' }
  });

  const runEngineTest = useCallback(async (type: 'classifier' | 'reflection' | 'embedding' | 'rerank') => {
    setTestStates(p => ({
      ...p,
      [type]: { testing: true, status: p[type].status, error: p[type].error }
    }));
    try {
      const res = await testEngine(type);
      if (res.status === 'success') {
        setTestStates(p => ({
          ...p,
          [type]: { testing: false, status: 'ok' }
        }));
      } else {
        // Clean up long error URLs – keep only the key status part
        const rawErr = res.error || '测试失败';
        const cleanErr = rawErr
          .replace(/For more information.*$/s, '')
          .replace(/Client error '(\d+ [^']+)' for url '([^']+)'/,
            (_: string, status: string) => status)
          .trim();
        setTestStates(p => ({
          ...p,
          [type]: { testing: false, status: 'err', error: cleanErr }
        }));
      }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (e: any) {
      setTestStates(p => ({
        ...p,
        [type]: { testing: false, status: 'err', error: e.message || '网络异常' }
      }));
    }
  }, []);

  const runAllTests = useCallback(() => {
    runEngineTest('classifier');
    runEngineTest('reflection');
    runEngineTest('embedding');
    runEngineTest('rerank');
  }, [runEngineTest]);

const ld = useCallback(async () => {
    // Health: direct fetch, independent
    const token = localStorage.getItem('admin_token') || localStorage.getItem('mos_admin_token') || '';
    fetch('/admin/health', { headers: token ? { Authorization: 'Bearer ' + token } : {} })
      .then(r => r.json()).then(d => { if (d.services) setSvc(d.services); }).catch(() => {});
    // Stats + throughput (main data)
    try {
      const [sr, tp] = await Promise.all([getStats(), getThroughput()]);
      setStats(sr);
      setTpL(tp.labels || []); setTpV(tp.values || []);
      setLog(p => [...p, '[' + new Date().toLocaleTimeString() + '] ' + (sr.total||0) + ' mems | ' + (sr.active_users||0) + ' users'].slice(-50));
    } catch {}
    // Routing + LLM engine (non-critical, async)
    getRouting().then(r => { if (r) setRouting(r); }).catch(() => {});
    getLLMEngineConfig().then(e => { if (e) setLlmEngine(e); }).catch(() => {});
  }, []);

  useEffect(() => {
    ld();
    const i = setInterval(ld, 6000);
    return () => clearInterval(i);
  }, [ld]);

  // Auto-run tests only after data is loaded AND user is on this page
  const hasTested = useRef(false);
  useEffect(() => {
    if (routing && llmEngine && !hasTested.current) {
      hasTested.current = true;
      // Small delay to ensure auth token is settled in localStorage
      setTimeout(() => runAllTests(), 800);
    }
  }, [routing, llmEngine, runAllTests]);

  useEffect(() => {
    if (lr.current) lr.current.scrollTop = lr.current.scrollHeight;
  }, [log]);

  const co = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: 'var(--v6-fg-muted)', font: { size: 10 } }, grid: { color: 'rgba(45,191,168,0.05)' } },
      y: { ticks: { color: 'var(--v6-fg-muted)', font: { size: 10 } }, grid: { color: 'rgba(45,191,168,0.05)' } }
    }
  };

  const td = {
    labels: tl,
    datasets: [
      {
        data: tv,
        borderColor: '#2DBFA8',
        backgroundColor: 'rgba(45,191,168,0.05)',
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        pointBackgroundColor: '#2DBFA8'
      }
    ]
  };

  return (
    <div>
      <h1 style={{font:"600 22px var(--v6-font-sans)",color:"var(--v6-fg)",marginBottom:4}}>控制台 Dashboard</h1>
      <div style={{color:"var(--v6-fg-muted)",fontSize:13,marginBottom:24}}>系统状态监测与引擎测试 · System status and engine diagnostics</div>

      <div className="v6-metric-grid">
        <MetricTile label='总记忆 Memories' value={s?.total?.toLocaleString() ?? "—"} sub={s?.memory_growth ?? '加载中 Loading'} done />
        <MetricTile label='活跃租户 Tenants' value={s?.active_users?.toLocaleString() ?? "—"} sub='注册总数 Total' />
        <MetricTile label='今日写入 Today' value={s?.today_writes?.toLocaleString() ?? "—"} sub='实时频率 Rate' />
        <MetricTile label='已省 Token Saved' value={s?.tokens_saved?.toLocaleString() ?? "—"} sub='全局 RAG 减免' />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 18, marginBottom: 22 }}>
        <div className="v6-card" style={{ marginBottom: 0 }}>
          <div className="v6-card__head">
            <div className="v6-card__title">
              写入吞吐 Throughput
            </div>
          </div>
          <div className='chart-wrap'>
            <Line options={co} data={td} />
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div className="v6-card" style={{ marginBottom: 0 }}>
            <div className="v6-card__head">
              <div className="v6-card__title">
                服务健康 Health
              </div>
            </div>
            <div>
              {SVCS.map(v => (
                <div key={v.key} className='v6-health-item'>
                  <div className='v6-health-item__label'>
                    <div className={`v6-health-item__dot ${svc?.[v.key] ? 'v6-health-item__dot--ok' : 'v6-health-item__dot--err'}`} />
                    {v.label}
                  </div>
                  <span style={{
                    fontSize: 10,
                    fontFamily: 'var(--v6-font-mono)',
                    letterSpacing: '0.06em',
                    color: svc?.[v.key] ? '#2DBFA8' : 'var(--v6-danger)',
                  }}>
                    {svc?.[v.key] ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="v6-card" style={{ marginBottom: 0 }}>
            <div className="v6-card__head">
              <div className="v6-card__title">
                模型算力 Engines
              </div>
              <button
                className='v6-btn v6-btn--primary'
                style={{ padding: '4px 8px', fontSize: 10 }}
                onClick={runAllTests}
                disabled={testStates.classifier.testing || testStates.reflection.testing || testStates.embedding.testing || testStates.rerank.testing}
              >
                检测全部 Test all
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {(['classifier', 'reflection', 'embedding', 'rerank'] as const).map(type => {
                const route = (type === 'classifier' || type === 'reflection') 
                  ? llmEngine?.config?.[type] 
                  : routing?.[type];
                const provName = route ? (PROVIDERS.find(p => p.id === route.provider)?.nameZh || route.provider) : '未配置';
                const modelName = route ? route.model : '—';
                const state = testStates[type];
                const label = {
                  classifier: '内容分类器 (Classifier)',
                  reflection: '知识整合引擎 (Reflection)',
                  embedding: '向量化模型 (Embedding)',
                  rerank: '重排序模型 (Rerank)'
                }[type];

                // dot class
                const dotCls = state.testing
                  ? 'v6-health-item__dot v6-health-item__dot--testing'
                  : state.status === 'ok'
                  ? 'v6-health-item__dot v6-health-item__dot--ok'
                  : state.status === 'err'
                  ? 'v6-health-item__dot v6-health-item__dot--err'
                  : 'v6-health-item__dot';

                return (
                  <div key={type} style={{ padding: '10px 0', borderBottom: '1px solid var(--v6-border)' }}>
                    {/* Row 1: dot + name + test button */}
                    <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:5 }}>
                      <div className={dotCls} style={{ flexShrink:0 }} />
                      <div style={{ flex:1, fontWeight:600, fontSize:12, color:'var(--v6-fg)' }}>{label}</div>
                      <button
                        className='v6-btn v6-btn--ghost v6-btn--xs'
                        style={{ padding:'2px 8px', fontSize:9, flexShrink:0 }}
                        onClick={() => runEngineTest(type)}
                        disabled={state.testing}
                      >
                        {state.testing ? '检测中…' : '检测 Test'}
                      </button>
                    </div>
                    {/* Row 2: provider/model + status label */}
                    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', paddingLeft:16 }}>
                      <div style={{ fontSize:11, fontFamily:'var(--v6-font-mono)', color:'var(--v6-fg-muted)' }}>
                        {provName}
                        {modelName !== '—' && (
                          <span style={{ color:'var(--v6-fg-faint)' }}> ({modelName})</span>
                        )}
                      </div>
                      <span style={{
                        fontSize:10, fontFamily:'var(--v6-font-mono)', letterSpacing:'0.06em',
                        color: state.testing ? '#E5A23B'
                          : state.status==='ok' ? '#2DBFA8'
                          : state.status==='err' ? 'var(--v6-danger)'
                          : 'var(--v6-fg-faint)',
                      }}>
                        {state.testing ? 'TESTING…'
                          : state.status==='ok' ? 'ONLINE'
                          : state.status==='err' ? 'OFFLINE'
                          : '—'}
                      </span>
                    </div>
                    {/* Row 3: error message */}
                    {state.status==='err' && state.error && (
                      <div style={{
                        marginTop:5, marginLeft:16,
                        fontSize:9, fontFamily:'var(--v6-font-mono)',
                        color:'var(--v6-danger)',
                        background:'rgba(255,77,109,0.05)',
                        padding:'4px 8px', borderRadius:5,
                        border:'1px solid rgba(255,77,109,0.12)',
                        wordBreak:'break-all', lineHeight:1.5,
                      }}>
                        {state.error}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="v6-card">
        <div className="v6-card__head">
          <div className="v6-card__title">
            实时写入 Log stream
          </div>
        </div>
        <div className='log-stream' ref={lr} style={{ background: 'var(--v6-bg-sunken)', borderColor: 'var(--v6-border)', fontFamily: 'var(--v6-font-mono)' }}>
          {log.map((l, i) => {
            const isErr = l.includes('[ERROR]') || l.includes('fail') || l.includes('error') || l.includes('OFFLINE');
            return (
              <div key={i} style={{ color: isErr ? 'var(--v6-danger)' : 'var(--v6-fg)', padding: '2px 0', fontFamily: 'var(--v6-font-mono)' }}>
                {l}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
