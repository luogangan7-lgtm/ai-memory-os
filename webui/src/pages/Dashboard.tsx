import { useEffect, useState, useRef, useCallback } from 'react';
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { getStats, getThroughput, getHealth, getRouting, testEngine, getLLMEngineConfig } from '../api/endpoints';
import type { DashboardStats, ServiceHealth } from '../api/types';
import { PROVIDERS } from '../data/models';

Chart.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler);

type StatColor = 'teal' | 'violet' | 'emerald' | 'amber';

function StatCard({ color, label, value, sub }: { color: StatColor; label: string; value: string; sub: string }) {
  return (
    <div className={`stat-card ${color}`}>
      <div className='stat-label'>{label}</div>
      <div className='stat-value'>{value}</div>
      <div className='stat-sub'>{sub}</div>
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

  const [routing, setRouting] = useState<any>(null);
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
        setTestStates(p => ({
          ...p,
          [type]: { testing: false, status: 'err', error: res.error || '测试失败' }
        }));
      }
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
    try {
      const [sr, tp, h, rt, eng] = await Promise.all([
        getStats(),
        getThroughput(),
        getHealth(),
        getRouting(),
        getLLMEngineConfig()
      ]);
      setStats(sr);
      setTpL(tp.labels);
      setTpV(tp.values);
      setSvc(h.services as ServiceHealth);
      setRouting(rt);
      setLlmEngine(eng);
      setLog(p => [...p, `[${new Date().toLocaleTimeString()}] ${sr.total} mems | ${sr.active_users} users`].slice(-50));
    } catch {
      /* API unavailable, silent */
    }
  }, []);

  useEffect(() => {
    ld();
    const i = setInterval(ld, 6000);
    return () => clearInterval(i);
  }, [ld]);

  // Auto-run connection diagnostic test on load
  const hasTested = useRef(false);
  useEffect(() => {
    if (routing && llmEngine && !hasTested.current) {
      hasTested.current = true;
      runAllTests();
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
      x: { ticks: { color: '#4A6080', font: { size: 10 } }, grid: { color: 'rgba(0,229,255,0.05)' } },
      y: { ticks: { color: '#4A6080', font: { size: 10 } }, grid: { color: 'rgba(0,229,255,0.05)' } }
    }
  };

  const td = {
    labels: tl,
    datasets: [
      {
        data: tv,
        borderColor: '#00E5FF',
        backgroundColor: 'rgba(0,229,255,0.05)',
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        pointBackgroundColor: '#00E5FF'
      }
    ]
  };

  return (
    <div>
      <div className='page-title'>控制台</div>
      <div className='page-sub'>实时系统状态监控</div>

      <div className='stats-grid'>
        <StatCard color='teal' label='全局记忆' value={s?.total?.toLocaleString() ?? '—'} sub={s?.memory_growth ?? '加载中...'} />
        <StatCard color='violet' label='活跃租户' value={s?.active_users?.toLocaleString() ?? '—'} sub='注册租户总数' />
        <StatCard color='emerald' label='今日写入' value={s?.today_writes?.toLocaleString() ?? '—'} sub='实时写入频率' />
        <StatCard color='amber' label='已省 Token' value={s?.tokens_saved?.toLocaleString() ?? '—'} sub='全局 RAG 减免' />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 18, marginBottom: 22 }}>
        <div className='card' style={{ marginBottom: 0 }}>
          <div className='card-head'>
            <div className='card-title'>
              <div className='card-icon ci-teal'>📈</div>
              写入吞吐趋势
            </div>
          </div>
          <div className='chart-wrap'>
            <Line options={co} data={td} />
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div className='card' style={{ marginBottom: 0 }}>
            <div className='card-head'>
              <div className='card-title'>
                <div className='card-icon ci-emerald'>💚</div>
                服务健康
              </div>
            </div>
            <div>
              {SVCS.map(v => (
                <div key={v.key} className='service-row'>
                  <div className='service-name'>
                    <div className={`status-dot ${svc?.[v.key] ? 'status-ok' : 'status-err'}`} />
                    {v.label}
                  </div>
                  <span className={`badge ${svc?.[v.key] ? 'badge-emerald' : 'badge-red'}`}>
                    {svc?.[v.key] ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className='card' style={{ marginBottom: 0 }}>
            <div className='card-head'>
              <div className='card-title'>
                <div className='card-icon ci-violet'>🤖</div>
                模型与算力状态
              </div>
              <button
                className='btn btn-teal'
                style={{ padding: '4px 8px', fontSize: 10 }}
                onClick={runAllTests}
                disabled={testStates.classifier.testing || testStates.reflection.testing || testStates.embedding.testing || testStates.rerank.testing}
              >
                🔄 一键检测
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

                return (
                  <div key={type} className='service-row' style={{ display: 'flex', flexDirection: 'column', alignItems: 'stretch', gap: 4, paddingBottom: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontWeight: 600, fontSize: 12, color: 'var(--text)' }}>{label}</div>
                      <button
                        className='btn btn-ghost'
                        style={{ padding: '2px 6px', fontSize: 9 }}
                        onClick={() => runEngineTest(type)}
                        disabled={state.testing}
                      >
                        {state.testing ? '检测中...' : '⚡ 检测'}
                      </button>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11 }}>
                      <div style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11 }}>
                        {provName} <span style={{ color: 'var(--dim)' }}>({modelName})</span>
                      </div>
                      <div>
                        {state.status === 'idle' && <span className='badge badge-violet'>未检测</span>}
                        {state.status === 'ok' && <span className='badge badge-emerald'>ONLINE</span>}
                        {state.status === 'err' && <span className='badge badge-crimson' title={state.error}>OFFLINE</span>}
                      </div>
                    </div>
                    {state.status === 'err' && state.error && (
                      <div
                        style={{
                          fontSize: 9,
                          color: 'var(--crimson)',
                          fontFamily: 'var(--mono)',
                          marginTop: 2,
                          background: 'rgba(255,77,109,0.05)',
                          padding: '4px 8px',
                          borderRadius: 6,
                          border: '1px solid rgba(255,77,109,0.1)',
                          wordBreak: 'break-all'
                        }}
                      >
                        [ERROR]: {state.error}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div className='card'>
        <div className='card-head'>
          <div className='card-title'>
            <div className='card-icon ci-teal'>📡</div>
            实时写入日志
          </div>
        </div>
        <div className='log-stream' ref={lr}>
          {log.map((l, i) => (
            <div key={i} className='log-info'>
              {l}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
