import { useState, useEffect, useCallback } from 'react';
import { PROVIDERS, type ProviderInfo, type ModelInfo } from '../data/models';
import { api } from '../api/client';

// ── Types ──────────────────────────────────────────────────────────────────
interface ProviderSavedCfg { api_key: string; }
type SavedMap = Record<string, ProviderSavedCfg>;
type TestStatus = 'idle' | 'testing' | 'ok' | 'err';
interface RoleAssignment { provider: string; model: string; }
type RoleMap = Record<string, RoleAssignment>;

const ROLES = [
  { key: 'classifier', nameZh: '内容分类器',   nameEn: 'Classifier', desc: '自动将记忆分类为常识/人物/代码/任务', modelTypes: ['chat','reasoning'] as ModelInfo['type'][] },
  { key: 'reflection', nameZh: '知识整合引擎', nameEn: 'Reflection', desc: '定期分析全量记忆，合并重复、发现关联', modelTypes: ['chat','reasoning'] as ModelInfo['type'][] },
  { key: 'embedding',  nameZh: '向量化模型',   nameEn: 'Embedding',  desc: '将文本转为高维向量用于语义检索',       modelTypes: ['embedding'] as ModelInfo['type'][] },
  { key: 'rerank',     nameZh: '重排序模型',   nameEn: 'Rerank',     desc: '对检索结果进行精排，提升准确率',       modelTypes: ['rerank'] as ModelInfo['type'][] },
];

const REGION_LABEL: Record<string,string> = { cn:'CN', intl:'INTL', local:'LOCAL' };
function countChat(p: ProviderInfo) { return p.models.filter(m=>m.type==='chat'||m.type==='reasoning').length; }
function countFree(p: ProviderInfo) { return p.models.filter(m=>m.free).length; }
function getToken() { return localStorage.getItem('admin_token')||localStorage.getItem('mos_admin_token')||''; }

// ── Model Picker Drawer ────────────────────────────────────────────────────
function ModelPickerDrawer({
  role, current, savedMap, onSelect, onClose,
}: {
  role: typeof ROLES[number];
  current: RoleAssignment | undefined;
  savedMap: SavedMap;
  onSelect: (a: RoleAssignment) => void;
  onClose: () => void;
}) {
  const eligible = PROVIDERS.filter(p =>
    savedMap[p.id]?.api_key &&
    p.models.some(m => role.modelTypes.includes(m.type))
  );

  const [selProvider, setSelProvider] = useState(current?.provider || eligible[0]?.id || '');
  const [selModel, setSelModel]       = useState(current?.model || '');
  const [saving, setSaving]           = useState(false);
  const [msg, setMsg]                 = useState('');

  const provObj = PROVIDERS.find(p => p.id === selProvider);
  const models  = provObj?.models.filter(m => role.modelTypes.includes(m.type)) || [];

  // Auto-select recommended or first model when provider changes
  useEffect(() => {
    if (!selProvider) return;
    const curValid = models.find(m => m.id === selModel);
    if (!curValid) {
      const rec = models.find(m => m.recommended) || models[0];
      setSelModel(rec?.id || '');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selProvider]);

  useEffect(() => {
    const fn = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', fn);
    return () => window.removeEventListener('keydown', fn);
  }, [onClose]);

  async function confirm() {
    if (!selProvider || !selModel) return;
    setSaving(true); setMsg('');
    try {
      // public_router has prefix="/admin" in admin.py, so real path is /admin/providers/configure
      const res = await fetch('/admin/providers/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({
          configs: [{ purpose: role.key, provider: selProvider, model: selModel, apiKey: '' }],
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      onSelect({ provider: selProvider, model: selModel });
      setTimeout(onClose, 400);
    } catch (e: unknown) {
      setMsg('保存失败: ' + (e instanceof Error ? e.message : String(e)));
      setSaving(false);
    }
  }

  return (
    <>
      <div onClick={onClose} style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.4)', zIndex:48 }} />
      <div style={{
        position:'fixed', top:0, right:0, width:400, height:'100%',
        background:'var(--v6-bg-elev)', borderLeft:'1px solid var(--v6-border)',
        zIndex:49, display:'flex', flexDirection:'column',
        animation:'slideIn .2s cubic-bezier(.16,1,.3,1)',
      }}>
        <style>{`@keyframes slideIn{from{transform:translateX(100%)}to{transform:translateX(0)}}`}</style>

        {/* Header */}
        <div style={{ padding:'18px 20px 14px', borderBottom:'1px solid var(--v6-border)' }}>
          <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', marginBottom:4 }}>
            <div style={{ fontWeight:600, fontSize:15, color:'var(--v6-fg)' }}>
              {role.nameZh}
              <span style={{ marginLeft:8, fontSize:10, fontFamily:'var(--v6-font-mono)', color:'var(--v6-fg-muted)', textTransform:'uppercase', letterSpacing:'.05em' }}>
                {role.nameEn}
              </span>
            </div>
            <button className="v6-btn v6-btn--ghost" onClick={onClose} style={{ fontSize:16, padding:'2px 7px' }}>✕</button>
          </div>
          <div style={{ fontSize:12, color:'var(--v6-fg-muted)' }}>{role.desc}</div>
        </div>

        {/* Body */}
        <div style={{ flex:1, overflowY:'auto', padding:'16px 20px', display:'flex', flexDirection:'column', gap:16 }}>
          {eligible.length === 0 ? (
            <div className="v6-empty" style={{ marginTop:40 }}>
              请先在下方录入至少一个支持此类型的厂商 API Key
            </div>
          ) : (
            <>
              {/* Provider pills */}
              <div>
                <div style={{ fontSize:11, fontFamily:'var(--v6-font-mono)', color:'var(--v6-fg-faint)', letterSpacing:'.07em', textTransform:'uppercase', marginBottom:8 }}>
                  选择厂商 Provider
                </div>
                <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
                  {eligible.map(p => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setSelProvider(p.id)}
                      style={{
                        padding:'6px 12px',
                        borderRadius:'var(--v6-radius-sm)',
                        border:`1px solid ${selProvider===p.id ? 'var(--v6-fg)' : 'var(--v6-border)'}`,
                        background: selProvider===p.id ? 'var(--v6-bg-sunken)' : 'var(--v6-bg)',
                        fontSize:12.5, fontFamily:'var(--v6-font-sans)', color:'var(--v6-fg)',
                        cursor:'pointer', transition:'border-color .15s, background .15s',
                      }}
                    >
                      {p.region==='cn' ? p.nameZh : p.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Model list — immediately visible below provider pills */}
              {selProvider && models.length > 0 && (
                <div>
                  <div style={{ fontSize:11, fontFamily:'var(--v6-font-mono)', color:'var(--v6-fg-faint)', letterSpacing:'.07em', textTransform:'uppercase', marginBottom:8 }}>
                    选择模型 Model
                  </div>
                  <div style={{ border:'1px solid var(--v6-border)', borderRadius:'var(--v6-radius-md)', overflow:'hidden' }}>
                    {models.map((m, i) => (
                      <div
                        key={m.id}
                        onClick={() => setSelModel(m.id)}
                        style={{
                          display:'flex', alignItems:'center', justifyContent:'space-between', gap:10,
                          padding:'11px 14px',
                          borderTop: i>0 ? '1px solid var(--v6-border)' : 'none',
                          background: selModel===m.id ? 'var(--v6-bg-sunken)' : 'var(--v6-bg)',
                          cursor:'pointer', transition:'background .12s',
                        }}
                      >
                        <div style={{ minWidth:0, flex:1 }}>
                          <div style={{ fontSize:13, fontWeight:500, color:'var(--v6-fg)', display:'flex', alignItems:'center', gap:5 }}>
                            {selModel===m.id && <span style={{ color:'#2DBFA8', fontSize:9 }}>●</span>}
                            {m.name}
                            {m.recommended && <span style={{ color:'var(--v6-fg-faint)', fontSize:10 }}>★</span>}
                          </div>
                          {m.note && <div style={{ fontSize:11, color:'var(--v6-fg-muted)', fontFamily:'var(--v6-font-mono)', marginTop:2 }}>{m.note}</div>}
                        </div>
                        <div style={{ display:'flex', gap:5, alignItems:'center', flexShrink:0 }}>
                          {m.ctx && <span style={{ fontSize:10, fontFamily:'var(--v6-font-mono)', color:'var(--v6-fg-muted)' }}>{Math.round(m.ctx/1000)}K</span>}
                          {m.free ? <span className="v6-freebadge">FREE</span> : <span className="v6-pricebadge">{m.price||'paid'}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding:'14px 20px', borderTop:'1px solid var(--v6-border)', display:'flex', gap:8, alignItems:'center' }}>
          <button className="v6-btn v6-btn--primary" onClick={confirm} disabled={saving||!selProvider||!selModel}>
            {saving ? '保存中…' : '确认 Confirm'}
          </button>
          <button className="v6-btn" onClick={onClose}>取消 Cancel</button>
          {msg && <span style={{ fontSize:11.5, color:'var(--v6-danger)', fontFamily:'var(--v6-font-mono)' }}>{msg}</span>}
        </div>
      </div>
    </>
  );
}

// ── Provider API Key Panel ─────────────────────────────────────────────────
function ProviderKeyPanel({
  provider, savedCfg, onSaved, onDeleted,
}: {
  provider: ProviderInfo;
  savedCfg: ProviderSavedCfg | undefined;
  onSaved: (pid:string, cfg:ProviderSavedCfg) => void;
  onDeleted: (pid:string) => void;
}) {
  const [apiKey, setApiKey]         = useState('');
  const [testStatus, setTestStatus] = useState<TestStatus>('idle');
  const [msg, setMsg]               = useState('');
  const [saving, setSaving]         = useState(false);
  const [deleting, setDeleting]     = useState(false);
  const hasKey = !!savedCfg?.api_key;

  // Find best model to test: prefer chat, fallback to embedding
  const testModelId =
    provider.models.find(m => m.type==='chat'||m.type==='reasoning')?.id ||
    provider.models.find(m => m.type==='embedding')?.id ||
    provider.models[0]?.id || '';

  async function handleTest() {
    const key = apiKey || savedCfg?.api_key || '';
    if (!key) { setMsg('请先输入 API Key'); setTestStatus('err'); return; }
    setTestStatus('testing'); setMsg('');
    try {
      // api client adds /admin prefix — POST /admin/providers/test
      const res = await api.post<{ok:boolean;error?:string}>('/providers/test', {
        provider: provider.id,
        apiKey: key,
        model: testModelId,
      });
      setTestStatus(res.ok ? 'ok' : 'err');
      setMsg(res.ok ? '连接成功 Connected ✓' : '连接失败: ' + (res.error || 'error'));
    } catch (e: unknown) {
      setTestStatus('err');
      setMsg('连接失败: ' + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function handleSave() {
    if (!apiKey) return;
    setSaving(true); setMsg('');
    try {
      // api client adds /admin prefix — PUT /admin/providers/{id}
      const res = await fetch(`/admin/providers/${provider.id}`, {
        method: 'PUT',
        headers: { 'Content-Type':'application/json', Authorization:`Bearer ${getToken()}` },
        body: JSON.stringify({ api_key: apiKey, api_base: provider.baseUrl }),
      });
      if (!res.ok) throw new Error(await res.text());
      onSaved(provider.id, { api_key: apiKey.slice(0,8)+'...' });
      setMsg('已保存 Saved ✓');
      setApiKey('');
    } catch (e: unknown) {
      setMsg('保存失败: ' + (e instanceof Error ? e.message : String(e)));
    } finally { setSaving(false); }
  }

  async function handleDelete() {
    if (!window.confirm(`确认删除 ${provider.name} 的 API Key？删除后关联的引擎角色也会被重置。`)) return;
    setDeleting(true); setMsg('');
    try {
      // DELETE /admin/providers/{id}
      const res = await fetch(`/admin/providers/${provider.id}`, {
        method: 'DELETE',
        headers: { Authorization:`Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error(await res.text());
      onDeleted(provider.id);
    } catch (e: unknown) {
      setMsg('删除失败: ' + (e instanceof Error ? e.message : String(e)));
      setDeleting(false);
    }
  }

  const msgOk = msg.startsWith('已保存') || msg.startsWith('连接成功');

  return (
    <div style={{ padding:'12px 14px', background:'var(--v6-bg-sunken)', borderTop:'1px solid var(--v6-border)' }}>
      {hasKey && (
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:8 }}>
          <span style={{ fontSize:11, fontFamily:'var(--v6-font-mono)', color:'#2DBFA8' }}>
            ● 已配置 {savedCfg!.api_key}
          </span>
          <button
            className="v6-btn v6-btn--danger v6-btn--xs"
            onClick={handleDelete}
            disabled={deleting}
          >
            {deleting ? '删除中…' : '删除 Key'}
          </button>
        </div>
      )}
      <div style={{ display:'flex', gap:6, alignItems:'center', flexWrap:'wrap' }}>
        <input
          className="v6-input-global"
          type="password"
          value={apiKey}
          onChange={e => setApiKey(e.target.value)}
          onKeyDown={e => e.key==='Enter' && handleSave()}
          placeholder={hasKey ? '输入新 Key 以覆盖…' : `${provider.name} API Key…`}
          style={{ flex:1, minWidth:160, margin:0 }}
        />
        <button
          className="v6-btn v6-btn--primary"
          onClick={handleSave}
          disabled={saving || !apiKey}
          style={{ whiteSpace:'nowrap' }}
        >
          {saving ? '保存中…' : '保存 Save'}
        </button>
        <button
          className="v6-btn"
          onClick={handleTest}
          disabled={testStatus==='testing' || (!apiKey && !hasKey)}
          style={{ whiteSpace:'nowrap' }}
        >
          {testStatus==='testing' ? '测试中…' : '测试 Test'}
        </button>
        {provider.signupUrl && (
          <a
            href={provider.signupUrl} target="_blank" rel="noreferrer"
            style={{ fontSize:11, fontFamily:'var(--v6-font-mono)', color:'var(--v6-fg-muted)', textDecoration:'none', borderBottom:'1px dotted var(--v6-border-strong)', whiteSpace:'nowrap' }}
          >
            Get key ↗
          </a>
        )}
      </div>
      {msg && (
        <div
          className={msgOk ? 'v6-statusbar v6-statusbar--ok' : 'v6-statusbar v6-statusbar--err'}
          style={{ marginTop:8, marginBottom:0 }}
        >
          {msg}
        </div>
      )}
    </div>
  );
}

// ── 4 Role Cards ──────────────────────────────────────────────────────────
function RoleCards({ roleMap, savedMap, onOpen }: {
  roleMap: RoleMap;
  savedMap: SavedMap;
  onOpen: (key:string) => void;
}) {
  return (
    <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(210px,1fr))', gap:10, marginBottom:28 }}>
      {ROLES.map(role => {
        const assigned = roleMap[role.key];
        const prov  = assigned ? PROVIDERS.find(p => p.id===assigned.provider) : null;
        const model = prov?.models.find(m => m.id===assigned?.model);
        const canConfigure = PROVIDERS.some(p =>
          savedMap[p.id]?.api_key && p.models.some(m => role.modelTypes.includes(m.type))
        );

        return (
          <button
            key={role.key}
            type="button"
            onClick={() => canConfigure && onOpen(role.key)}
            title={!canConfigure ? '请先录入支持此类型的厂商 API Key' : ''}
            style={{
              padding:'14px 16px',
              background: assigned ? 'var(--v6-bg-elev)' : 'var(--v6-bg)',
              border:`1px solid ${assigned ? 'var(--v6-border-strong)' : 'var(--v6-border)'}`,
              borderRadius:'var(--v6-radius-md)',
              cursor: canConfigure ? 'pointer' : 'not-allowed',
              opacity: canConfigure ? 1 : 0.5,
              textAlign:'left', fontFamily:'var(--v6-font-sans)', color:'inherit',
              transition:'border-color .2s, background .2s',
              display:'flex', flexDirection:'column', gap:6,
            }}
          >
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
              <span style={{ fontSize:13, fontWeight:600, color:'var(--v6-fg)' }}>{role.nameZh}</span>
              <span style={{ fontSize:9, fontFamily:'var(--v6-font-mono)', color:'var(--v6-fg-muted)', letterSpacing:'.05em', textTransform:'uppercase' }}>
                {role.nameEn}
              </span>
            </div>
            <div style={{ fontSize:11.5, color:'var(--v6-fg-muted)' }}>{role.desc}</div>
            <div style={{ marginTop:4 }}>
              {assigned && prov && model ? (
                <>
                  <div style={{ fontSize:11, fontFamily:'var(--v6-font-mono)', color:'#2DBFA8', marginBottom:2 }}>
                    ● {prov.region==='cn' ? prov.nameZh : prov.name}
                  </div>
                  <div style={{ fontSize:11, fontFamily:'var(--v6-font-mono)', color:'var(--v6-fg-muted)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                    {model.name}
                  </div>
                </>
              ) : (
                <div style={{ fontSize:11, fontFamily:'var(--v6-font-mono)', color: canConfigure ? 'var(--v6-fg-muted)' : 'var(--v6-fg-faint)' }}>
                  {canConfigure ? '点击选择模型 →' : '请先配置 API Key'}
                </div>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ── Provider Section (defined outside ModelConfigPage to avoid re-creation) ─
function ProviderSection({
  title, count, providers, savedMap, expandedId, onToggle, onSaved, onDeleted,
}: {
  title: string;
  count: number;
  providers: ProviderInfo[];
  savedMap: SavedMap;
  expandedId: string | null;
  onToggle: (id:string) => void;
  onSaved: (pid:string, cfg:ProviderSavedCfg) => void;
  onDeleted: (pid:string) => void;
}) {
  const expandedProvider = providers.find(p => p.id === expandedId);
  return (
    <>
      <div className="v6-section-label">
        <span>{title}</span>
        <span className="v6-section-label__count">{count}</span>
      </div>

      <div className="v6-provider-grid" style={{ marginBottom: expandedProvider ? 8 : 20 }}>
        {providers.map(p => {
          const hasKey = !!savedMap[p.id]?.api_key;
          const isExpanded = expandedId===p.id;
          return (
            <button
              key={p.id}
              className="v6-provider-card"
              aria-current={isExpanded ? 'page' : undefined}
              onClick={() => onToggle(p.id)}
              type="button"
            >
              <div className="v6-provider-card__name">
                {p.region==='cn' ? p.nameZh : p.name}
                <span className="v6-provider-card__region">{REGION_LABEL[p.region]}</span>
              </div>
              <div className="v6-provider-card__meta">
                {countChat(p)} models
                {countFree(p)>0 && <> · <b>{countFree(p)} free</b></>}
              </div>
              {hasKey && (
                <div style={{ fontSize:10, fontFamily:'var(--v6-font-mono)', color:'#2DBFA8', marginTop:2 }}>● 已配置</div>
              )}
            </button>
          );
        })}
      </div>

      {expandedProvider && (
        <div style={{ border:'1px solid var(--v6-border-strong)', borderRadius:'var(--v6-radius-md)', marginBottom:20, overflow:'hidden' }}>
          <div style={{ padding:'10px 14px', background:'var(--v6-bg-elev)', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
            <span style={{ fontWeight:600, fontSize:13.5, color:'var(--v6-fg)' }}>
              {expandedProvider.region==='cn' ? expandedProvider.nameZh : expandedProvider.name}
              <span style={{ marginLeft:8, fontSize:10, fontFamily:'var(--v6-font-mono)', color:'var(--v6-fg-muted)' }}>{expandedProvider.baseUrl}</span>
            </span>
            <button className="v6-btn v6-btn--ghost" style={{ fontSize:12 }} onClick={() => onToggle(expandedProvider.id)}>
              收起 ✕
            </button>
          </div>
          <ProviderKeyPanel
            provider={expandedProvider}
            savedCfg={savedMap[expandedProvider.id]}
            onSaved={onSaved}
            onDeleted={onDeleted}
          />
        </div>
      )}
    </>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────
export function ModelConfigPage() {
  const [savedMap, setSavedMap]     = useState<SavedMap>({});
  const [roleMap, setRoleMap]       = useState<RoleMap>({});
  const [loading, setLoading]       = useState(true);
  const [expandedId, setExpandedId] = useState<string|null>(null);
  const [pickerRole, setPickerRole] = useState<string|null>(null);

  useEffect(() => {
    async function load() {
      try {
        type RoutingMap = Record<string,{provider:string;model:string}>;
        type EngineResp = {config:Record<string,{provider:string;model:string}>};
        const [providers, routing, engine] = await Promise.all([
          api.get<SavedMap>('/providers'),
          api.get<RoutingMap>('/routing').catch(() => ({} as RoutingMap)),
          api.get<EngineResp>('/providers/llm-engine').catch(() => ({ config:{} } as EngineResp)),
        ]);
        setSavedMap(providers || {});
        const rm: RoleMap = {};
        const r = routing as RoutingMap;
        const e = engine  as EngineResp;
        if (r?.embedding)          rm.embedding  = r.embedding;
        if (r?.rerank)             rm.rerank     = r.rerank;
        if (e?.config?.classifier) rm.classifier = e.config.classifier;
        if (e?.config?.reflection) rm.reflection = e.config.reflection;
        setRoleMap(rm);
      } catch (err) { console.error(err); }
      finally { setLoading(false); }
    }
    load();
  }, []);

  const handleSaved = useCallback((pid:string, cfg:ProviderSavedCfg) => {
    setSavedMap(prev => ({ ...prev, [pid]: { ...prev[pid], ...cfg } }));
  }, []);

  const handleDeleted = useCallback((pid:string) => {
    setSavedMap(prev => { const next={...prev}; delete next[pid]; return next; });
    setExpandedId(prev => prev===pid ? null : prev);
    setRoleMap(prev => {
      const next = {...prev};
      ROLES.forEach(r => { if (next[r.key]?.provider===pid) delete next[r.key]; });
      return next;
    });
  }, []);

  const handleToggle = useCallback((id:string) => {
    setExpandedId(prev => prev===id ? null : id);
  }, []);

  const activeRole = pickerRole ? ROLES.find(r => r.key===pickerRole) : null;

  const cnProviders    = PROVIDERS.filter(p => p.region==='cn');
  const intlProviders  = PROVIDERS.filter(p => p.region==='intl');
  const localProviders = PROVIDERS.filter(p => p.region==='local');

  if (loading) return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', minHeight:'60vh', gap:14, color:'var(--v6-fg-muted)', fontSize:14, fontFamily:'var(--v6-font-sans)' }}>
      <div style={{ width:32, height:32, borderRadius:'50%', border:'3px solid var(--v6-border-strong)', borderTopColor:'var(--v6-fg-muted)', animation:'spin .9s linear infinite' }} />
      加载中 Loading…
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  const sectionProps = { savedMap, expandedId, onToggle:handleToggle, onSaved:handleSaved, onDeleted:handleDeleted };

  return (
    <div>
      <div style={{ marginBottom:24 }}>
        <h1 style={{ font:'600 22px var(--v6-font-sans)', color:'var(--v6-fg)', margin:0, letterSpacing:'-0.02em' }}>
          模型配置 Providers
        </h1>
        <div style={{ fontSize:13, color:'var(--v6-fg-muted)', marginTop:4 }}>
          先录入厂商 API Key · 再为 4 个引擎角色分配模型
        </div>
      </div>

      {/* 4 Role Cards */}
      <div className="v6-section-label">
        <span>引擎角色 · Engine Roles</span>
        <span className="v6-section-label__count">需先配置 API Key 才可选择</span>
      </div>
      <RoleCards roleMap={roleMap} savedMap={savedMap} onOpen={setPickerRole} />

      {/* Provider Sections */}
      <ProviderSection title="中国厂商 · China"        count={cnProviders.length}    providers={cnProviders}    {...sectionProps} />
      <ProviderSection title="海外厂商 · International" count={intlProviders.length}  providers={intlProviders}  {...sectionProps} />
      {localProviders.length > 0 && (
        <ProviderSection title="本地模型 · Local"       count={localProviders.length} providers={localProviders} {...sectionProps} />
      )}

      <LocalDetect />

      {/* Model Picker Drawer */}
      {pickerRole && activeRole && (
        <ModelPickerDrawer
          role={activeRole}
          current={roleMap[pickerRole]}
          savedMap={savedMap}
          onSelect={a => { setRoleMap(prev => ({ ...prev, [pickerRole!]: a })); }}
          onClose={() => setPickerRole(null)}
        />
      )}
    </div>
  );
}

// ── Local Scanner ──────────────────────────────────────────────────────────
function LocalDetect() {
  const [scanning, setScanning] = useState(false);
  const [results, setResults]   = useState<string[]>([]);

  async function scan() {
    setScanning(true); setResults([]);
    const out: string[] = [];
    for (const u of ['http://localhost:11434/v1','http://localhost:1234/v1','http://localhost:4891/v1']) {
      try {
        const r = await fetch(u+'/models', { signal:AbortSignal.timeout(3000) });
        const d = await r.json();
        out.push(`${u}  ✓  ${(d.data||d.models||[]).length} models`);
      } catch { out.push(`${u}  ✗  offline`); }
    }
    setResults(out); setScanning(false);
  }

  return (
    <div className="v6-card" style={{ marginTop:12 }}>
      <div className="v6-card__head">
        <div className="v6-card__title">
          本地模型检测 Local Scan
          <span className="v6-card__title-hint">Ollama · LM Studio · vLLM</span>
        </div>
        <button className="v6-btn" onClick={scan} disabled={scanning}>
          {scanning ? '扫描中…' : '🔍 扫描 Scan'}
        </button>
      </div>
      {results.length > 0 && (
        <div style={{ fontFamily:'var(--v6-font-mono)', fontSize:12, lineHeight:2, marginTop:8 }}>
          {results.map((r,i) => (
            <div key={i} style={{ color:r.includes('✓') ? '#2DBFA8' : 'var(--v6-fg-faint)' }}>{r}</div>
          ))}
        </div>
      )}
    </div>
  );
}
