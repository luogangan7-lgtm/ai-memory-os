import { useState, useEffect } from 'react';
import { triggerReflection, saveReflectionConfig, getReflectionConfig } from '../api/endpoints';
import { useToast } from '../contexts/ToastContext';

export function ReflectionPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [decay, setDecay] = useState(0.05);
  const [quality, setQuality] = useState(0.2);
  const [intervalH, setIntervalH] = useState(24);

  useEffect(() => {
    async function loadConfig() {
      try {
        const cfg = await getReflectionConfig();
        if (cfg) {
          setDecay(cfg.decay_rate);
          setQuality(cfg.quality_threshold);
          setIntervalH(cfg.interval_hours);
        }
      } catch (e) {
        console.error('Failed to load reflection config', e);
      }
    }
    loadConfig();
  }, []);

  async function trigger() {
    setLoading(true); setStatus('running...');
    try {
      const r = await triggerReflection();
      toast(r.status === 'initiated' ? 'Reflection started' : (r.message || 'failed'));
      setStatus('triggered');
    } catch { console.error('reflection failed'); setStatus(''); }
    setLoading(false);
  }

  async function save() {
    try {
      await saveReflectionConfig({ decay_rate: decay, quality_threshold: quality, interval_hours: intervalH });
      toast('Config saved');
    } catch { console.error('reflection failed'); }
  }

  return (
    <div>
      <h1 style={{ font: "600 22px var(--v6-font-sans)", color: "var(--v6-fg)", marginBottom: 4 }}>知识整合 Reflection</h1>
      <div style={{ color: "var(--v6-fg-muted)", fontSize: 13, marginBottom: 24 }}>全局知识的语义网络重构与记忆衰减调度 · Semantic network restructuring and memory decay scheduling</div>
      <div className='v6-grid-2col'>
        <div className="v6-card">
          <div className="v6-card__head">
            <div className="v6-card__title">
              全局知识整合 Global Reflection
            </div>
          </div>
          <button className='v6-btn v6-btn--primary w-full' onClick={trigger} disabled={loading}>
            {loading ? '运行中... Running...' : '触发全局整合 Trigger Reflection'}
          </button>
          {status && <p style={{ marginTop: 10, color: 'var(--v6-fg-muted)', fontSize: 12 }}>{status}</p>}
        </div>
        <div className="v6-card">
          <div className="v6-card__head">
            <div className="v6-card__title">
              参数配置 Parameters Configuration
            </div>
          </div>
          <div className='form-group' style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, color: 'var(--v6-fg-muted)' }}>
              衰减率 Decay Rate: <span style={{ color: '#2DBFA8', fontFamily: 'var(--v6-font-mono)' }}>{(decay * 100).toFixed(0)}%/day</span>
            </label>
            <input type='range' className="v6-input-global" style={{ width: '100%', padding: '4px 8px' }} min={0} max={0.2} step={0.01} value={decay} onChange={e => setDecay(+e.target.value)} />
          </div>
          <div className='form-group' style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, color: 'var(--v6-fg-muted)' }}>
              质量阈值 Quality Threshold: <span style={{ color: '#2DBFA8', fontFamily: 'var(--v6-font-mono)' }}>{quality.toFixed(2)}</span>
            </label>
            <input type='range' className="v6-input-global" style={{ width: '100%', padding: '4px 8px' }} min={0} max={1} step={0.05} value={quality} onChange={e => setQuality(+e.target.value)} />
          </div>
          <div className='form-group' style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, color: 'var(--v6-fg-muted)' }}>
              时间间隔 Interval (Hours)
            </label>
            <select className="v6-input-global" style={{ width: '100%' }} value={intervalH} onChange={e => setIntervalH(+e.target.value)}>
              <option value={0}>手动 Manual</option>
              <option value={6}>6h</option>
              <option value={12}>12h</option>
              <option value={24}>24h</option>
            </select>
          </div>
          <button className='v6-btn v6-btn--primary w-full' onClick={save}>
            保存参数 Save Parameters
          </button>
        </div>
      </div>
    </div>
  );
}
