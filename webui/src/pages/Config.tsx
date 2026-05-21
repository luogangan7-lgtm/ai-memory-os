import { useState, useEffect } from 'react';
import { saveRAGConfig, saveSecurityConfig, getRAGConfig, getSecurityConfig } from '../api/endpoints';
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

  useEffect(() => {
    async function loadConfigs() {
      try {
        const rag = await getRAGConfig();
        if (rag) {
          setTopk(rag.top_k);
          setSim(rag.min_similarity);
          setCtxTokens(rag.max_context_tokens);
          setHistory(rag.history_count);
        }
      } catch (e) {
        console.error('Failed to load RAG config', e);
      }
      try {
        const sec = await getSecurityConfig();
        if (sec) {
          setRateWrite(sec.rate_write);
          setRateRead(sec.rate_read);
          setMaxMemLen(sec.max_mem_len);
          setJwtExpire(sec.jwt_expire);
        }
      } catch (e) {
        console.error('Failed to load security config', e);
      }
    }
    loadConfigs();
  }, []);

  async function saveRAG() {
    try {
      await saveRAGConfig({ top_k: topk, min_similarity: sim, max_context_tokens: ctxTokens, history_count: history });
      toast('保存成功 Saved');
    } catch {
      toast('保存失败 Save failed', 'err');
    }
  }
  async function saveSec() {
    try {
      await saveSecurityConfig({ rate_write: rateWrite, rate_read: rateRead, max_mem_len: maxMemLen, jwt_expire: jwtExpire });
      toast('保存成功 Saved');
    } catch {
      toast('保存失败 Save failed', 'err');
    }
  }

  const field = (label:string, desc:string, value:number, set:(v:number)=>void, unit:string='', type:string='number') => (
    <div className='form-group' style={{ marginBottom: 16 }}>
      <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--v6-fg)', display: 'block', marginBottom: 4 }}>
        {label} {unit && <span style={{ color: '#2DBFA8', fontWeight: 400 }}>— {unit}</span>}
      </label>
      <div style={{ fontSize: 11, color: 'var(--v6-fg-muted)', marginBottom: 6 }}>{desc}</div>
      {type === 'range' ? (
        <input
          type='range'
          style={{ width: '100%', accentColor: '#2DBFA8' }}
          min={0}
          max={1}
          step={0.05}
          value={value}
          onChange={e => set(+e.target.value)}
        />
      ) : (
        <input
          type='text'
          className="v6-input-global"
          style={{ width: '100%' }}
          value={value}
          onChange={e => set(+e.target.value)}
        />
      )}
    </div>
  );

  return (
    <div>
      <h1 style={{ font: "600 22px var(--v6-font-sans)", color: "var(--v6-fg)", marginBottom: 4 }}>系统配置 Configuration</h1>
      <div style={{ color: "var(--v6-fg-muted)", fontSize: 13, marginBottom: 24 }}>RAG 检索参数 · 安全策略 · 限速规则 · RAG retrieval parameters, security policies, and rate limits</div>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <div className="v6-card">
          <div className="v6-card__head">
            <div className="v6-card__title">RAG 检索参数 RAG Parameters</div>
          </div>
          {field('Top-K', '向量检索时返回的最相似记忆条数，越大召回越多但可能引入噪声 · Number of most similar memories returned during vector retrieval', topk, setTopk, '条 records')}
          {field('最小相似度阈值 Min Similarity Threshold', '只返回相似度高于此值的记忆，过滤低质量结果 · Only return memories with similarity score higher than this value', sim, setSim, sim.toFixed(2), 'range')}
          {field('上下文最大 Token Max Context Tokens', '注入到 LLM 对话上下文中的最大 Token 数量 · Maximum token count injected into LLM conversation context', ctxTokens, setCtxTokens, 'tokens')}
          {field('历史消息条数 Chat History Count', '注入到 LLM 对话中的最近历史消息数量 · Number of recent messages injected into LLM conversation', history, setHistory, '条 messages')}
          <button className='v6-btn v6-btn--primary' onClick={saveRAG} style={{ marginTop: 8, width: '100%' }}>保存 RAG 参数 Save RAG Parameters</button>
        </div>

        <div className="v6-card">
          <div className="v6-card__head">
            <div className="v6-card__title">安全与限速 Security & Rate Limits</div>
          </div>
          {field('每分钟写入限制 Rate Limit (Write)', '单个用户每分钟最多可写入的记忆条数，防止滥用 · Maximum memory write count per user per minute', rateWrite, setRateWrite, '次/分钟 writes/min')}
          {field('每分钟读取限制 Rate Limit (Read)', '单个用户每分钟最多可检索的次数 · Maximum memory read/query count per user per minute', rateRead, setRateRead, '次/分钟 queries/min')}
          {field('单条记忆最大长度 Max Memory Length', '单条记忆内容的字符上限，超过将被截断 · Maximum character limit per single memory content', maxMemLen, setMaxMemLen, '字符 chars')}
          {field('JWT 过期时间 JWT Token Expiration', '登录凭证的有效时长，超时后需重新登录 · Token validity duration before re-authentication is required', jwtExpire, setJwtExpire, '秒 seconds')}
          <button className='v6-btn v6-btn--primary' onClick={saveSec} style={{ marginTop: 8, width: '100%' }}>保存安全参数 Save Security Parameters</button>
        </div>
      </div>
    </div>
  );
}
