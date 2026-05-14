import { useState } from 'react';
import { saveRAGConfig, saveSecurityConfig } from '../api/endpoints';
import { useToast } from '../contexts/ToastContext';

export function ConfigPage() {
  const { toast } = useToast();
  const [topk, setTopk] = useState(5);
  const [sim, setSim] = useState(0.6);
  const [ctxTokens, setCtxTokens] = useState(2000);
  const [history, setHistory] = useState(10);
  const [rateWrite, setRateWrite] = useState(60);
  const [rateRead, setRateRead] = useState(120);
  const [maxMemLen, setMaxMemLen] = useState(10000);
  const [jwtExpire, setJwtExpire] = useState(43200);

  async function saveRAG() {
    try { await saveRAGConfig({ top_k: topk, min_similarity: sim, max_context_tokens: ctxTokens, history_count: history }); toast('RAG saved'); }
    catch { toast('err', 'err'); }
  }

  async function saveSec() {
    try { await saveSecurityConfig({ rate_write: rateWrite, rate_read: rateRead, max_mem_len: maxMemLen, jwt_expire: jwtExpire }); toast('Security saved'); }
    catch { toast('err', 'err'); }
  }

  return (
    <div>
      <div className='page-title'>系统配置</div>
      <div className='page-sub'>RAG 参数与安全设置</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <div className='card'>
          <div className='card-head'><div className='card-title'><div className='card-icon ci-teal'>R</div>RAG 参数</div></div>
          <div className='form-group'><label>Top-K</label><input type='text' value={topk} onChange={e => setTopk(+e.target.value)} /></div>
          <div className='form-group'><label>Min Similarity: {sim.toFixed(2)}</label><input type='range' min={0} max={1} step={0.05} value={sim} onChange={e => setSim(+e.target.value)} /></div>
          <div className='form-group'><label>Max Context Tokens</label><input type='text' value={ctxTokens} onChange={e => setCtxTokens(+e.target.value)} /></div>
          <div className='form-group'><label>History Messages</label><input type='text' value={history} onChange={e => setHistory(+e.target.value)} /></div>
          <button className='btn btn-teal w-full' onClick={saveRAG}>保存 RAG</button>
        </div>
        <div className='card'>
          <div className='card-head'><div className='card-title'><div className='card-icon ci-red'>S</div>安全与限速</div></div>
          <div className='form-group'><label>Write Rate (per min)</label><input type='text' value={rateWrite} onChange={e => setRateWrite(+e.target.value)} /></div>
          <div className='form-group'><label>Read Rate (per min)</label><input type='text' value={rateRead} onChange={e => setRateRead(+e.target.value)} /></div>
          <div className='form-group'><label>Max Memory Length (chars)</label><input type='text' value={maxMemLen} onChange={e => setMaxMemLen(+e.target.value)} /></div>
          <div className='form-group'><label>JWT Expire (minutes)</label><input type='text' value={jwtExpire} onChange={e => setJwtExpire(+e.target.value)} /></div>
          <button className='btn btn-teal w-full' onClick={saveSec}>保存安全</button>
        </div>
      </div>
    </div>
  );
}
