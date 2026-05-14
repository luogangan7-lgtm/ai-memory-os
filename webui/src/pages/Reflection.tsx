import { useState } from 'react';
import { triggerReflection, saveReflectionConfig } from '../api/endpoints';
import { useToast } from '../contexts/ToastContext';

export function ReflectionPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [decay, setDecay] = useState(0.05);
  const [quality, setQuality] = useState(0.2);
  const [intervalH, setIntervalH] = useState(24);

  async function trigger() {
    setLoading(true); setStatus('running...');
    try {
      const r = await triggerReflection();
      toast(r.status === 'initiated' ? 'Reflection started' : (r.message || 'failed'));
      setStatus('triggered');
    } catch { toast('err', 'err'); setStatus(''); }
    setLoading(false);
  }

  async function save() {
    try {
      await saveReflectionConfig({ decay_rate: decay, quality_threshold: quality, interval_hours: intervalH });
      toast('Config saved');
    } catch { toast('err', 'err'); }
  }

  return (
    <div>
      <div className='page-title'>知识整合</div>
      <div className='page-sub'>全局知识整合</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <div className='card'>
          <div className='card-head'><div className='card-title'><div className='card-icon ci-violet'>K</div>Global Reflection</div></div>
          <button className='btn btn-teal w-full' onClick={trigger} disabled={loading}>{loading ? '运行中...' : '触发全局整合'}</button>
          {status && <p style={{ marginTop: 10, color: '#4A6080', fontSize: 12 }}>{status}</p>}
        </div>
        <div className='card'>
          <div className='card-head'><div className='card-title'><div className='card-icon ci-amber'>P</div>Parameters</div></div>
          <div className='form-group'><label>Decay Rate: {(decay * 100).toFixed(0)}%/day</label><input type='range' min={0} max={0.2} step={0.01} value={decay} onChange={e => setDecay(+e.target.value)} /></div>
          <div className='form-group'><label>Quality Threshold: {quality.toFixed(2)}</label><input type='range' min={0} max={1} step={0.05} value={quality} onChange={e => setQuality(+e.target.value)} /></div>
          <div className='form-group'><label>间隔(小时)</label><select value={intervalH} onChange={e => setIntervalH(+e.target.value)}><option value={0}>手动</option><option value={6}>6h</option><option value={12}>12h</option><option value={24}>24h</option></select></div>
          <button className='btn btn-teal w-full' onClick={save}>保存参数</button>
        </div>
      </div>
    </div>
  );
}
