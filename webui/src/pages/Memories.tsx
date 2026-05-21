import { useEffect, useState, useCallback } from 'react';
import { 
  getAdminMemories, 
  deleteAdminMemory, 
  getTenants, 
  AdminMemory,
  getAdminDocuments,
  deleteAdminDocument,
  AdminDocument
} from '../api/endpoints';
import { useToast } from '../contexts/ToastContext';

export function MemoriesPage() {
  const { toast } = useToast();
  const [subTab, setSubTab] = useState<'memories' | 'documents'>('memories');
  const [memories, setMemories] = useState<AdminMemory[]>([]);
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [tenants, setTenants] = useState<{ team_id: string; name: string }[]>([]);
  
  // Memories Pagination
  const [total, setTotal] = useState(0);
  const [limit] = useState(25);
  const [offset, setOffset] = useState(0);

  // Documents Pagination
  const [docsTotal, setDocsTotal] = useState(0);
  const [docsOffset, setDocsOffset] = useState(0);
  
  const [loading, setLoading] = useState(false);

  // Filters
  const [selectedTenant, setSelectedTenant] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedSourceType, setSelectedSourceType] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected memory for Modal
  const [activeMemory, setActiveMemory] = useState<AdminMemory | null>(null);

  const categories = [
    '自然科学', '社会科学', '数学科学', '系统科学',
    '工程技术', '人体科学', '思维科学', '人文艺术',
    '个人记忆', '未分类'
  ];

  const sourceTypes = [
    { value: 'document', label: '📄 文档' },
    { value: 'knowledge', label: '🧠 整合知识' },
    { value: 'human', label: '💬 用户聊天' },
    { value: 'agent', label: '🤖 AI记忆/Mcp' },
    { value: 'image', label: '🖼️ 图片/OCR' }
  ];

  const loadTenants = useCallback(async () => {
    try {
      const res = await getTenants();
      setTenants(res.tenants || []);
    } catch {
      /* Silent */
    }
  }, []);

  const loadMemories = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getAdminMemories({
        team_id: selectedTenant || undefined,
        category: selectedCategory || undefined,
        source_type: selectedSourceType || undefined,
        q: searchQuery || undefined,
        limit,
        offset
      });
      setMemories(res.memories || []);
      setTotal(res.total || 0);
    } catch {
      toast('加载记忆失败', 'err');
    } finally {
      setLoading(false);
    }
  }, [selectedTenant, selectedCategory, selectedSourceType, searchQuery, limit, offset, toast]);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getAdminDocuments({
        team_id: selectedTenant || undefined,
        q: searchQuery || undefined,
        limit,
        offset: docsOffset
      });
      setDocuments(res.documents || []);
      setDocsTotal(res.total || 0);
    } catch {
      toast('加载文档失败', 'err');
    } finally {
      setLoading(false);
    }
  }, [selectedTenant, searchQuery, docsOffset, limit, toast]);

  useEffect(() => {
    loadTenants();
  }, [loadTenants]);

  useEffect(() => {
    if (subTab === 'memories') {
      loadMemories();
    } else {
      loadDocuments();
    }
  }, [loadMemories, loadDocuments, subTab]);

  // Reset offset on filter changes
  useEffect(() => {
    setOffset(0);
    setDocsOffset(0);
  }, [selectedTenant, selectedCategory, selectedSourceType, searchQuery]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('确定要永久删除此条记忆吗？对应向量索引和关系将一并清除。')) {
      return;
    }
    try {
      await deleteAdminMemory(id);
      toast('记忆删除成功');
      loadMemories();
      if (activeMemory?.id === id) {
        setActiveMemory(null);
      }
    } catch {
      toast('删除失败', 'err');
    }
  };

  const handleDeleteDocument = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('确定要永久删除此文档吗？这将级联删除对应的解析记忆、向量数据以及底层存储文件！')) {
      return;
    }
    try {
      await deleteAdminDocument(id);
      toast('文档级联删除成功');
      loadDocuments();
      if (subTab === 'memories') {
        loadMemories();
      }
    } catch {
      toast('删除失败', 'err');
    }
  };

  const getSourceBadge = (source: string) => {
    switch (source) {
      case 'document':
        return <span className="badge badge-emerald">📄 文档</span>;
      case 'knowledge':
        return <span className="badge badge-premium" style={{background: 'rgba(124, 58, 237, 0.15)', border: '1px solid rgba(124, 58, 237, 0.4)', color: '#a78bfa'}}>🧠 整合</span>;
      case 'human':
        return <span className="badge badge-teal">💬 聊天</span>;
      case 'agent':
        return <span className="badge badge-violet">🤖 AI/MCP</span>;
      case 'image':
        return <span className="badge badge-amber">🖼️ OCR</span>;
      default:
        return <span className="badge badge-ghost">{source || '未知'}</span>;
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '—';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  const formatSize = (bytes: number) => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // Pagination Calculations
  const totalPages = subTab === 'memories' ? Math.ceil(total / limit) : Math.ceil(docsTotal / limit);
  const currentPage = subTab === 'memories' ? Math.floor(offset / limit) + 1 : Math.floor(docsOffset / limit) + 1;
  const currentTotal = subTab === 'memories' ? total : docsTotal;

  return (
    <div>
      <div className="page-title">数据与知识管理</div>
      <div className="page-sub">查看、检索和管理系统内的所有知识、多级记忆与上传文档数据</div>

      {/* Sub-tab navigation */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button
          className={`btn ${subTab === 'memories' ? 'btn-teal' : 'btn-ghost'}`}
          style={{ padding: '8px 16px', fontSize: 12 }}
          onClick={() => setSubTab('memories')}
        >
          📋 记忆管理
        </button>
        <button
          className={`btn ${subTab === 'documents' ? 'btn-teal' : 'btn-ghost'}`}
          style={{ padding: '8px 16px', fontSize: 12 }}
          onClick={() => setSubTab('documents')}
        >
          📁 文档管理
        </button>
      </div>

      {/* Filter Bar */}
      <div className="card" style={{ padding: 18, marginBottom: 18 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          <div>
            <label style={{ fontSize: 11, color: 'var(--muted)', display: 'block', marginBottom: 4 }}>租户过滤</label>
            <select
              style={{
                width: '100%',
                background: 'rgba(4,8,16,.85)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: '8px 12px',
                color: 'var(--text)',
                fontSize: 12,
                outline: 'none'
              }}
              value={selectedTenant}
              onChange={e => setSelectedTenant(e.target.value)}
            >
              <option value="">全部租户</option>
              {tenants.map(t => (
                <option key={t.team_id} value={t.team_id}>{t.name || t.team_id}</option>
              ))}
            </select>
          </div>

          {subTab === 'memories' && (
            <>
              <div>
                <label style={{ fontSize: 11, color: 'var(--muted)', display: 'block', marginBottom: 4 }}>科学分类</label>
                <select
                  style={{
                    width: '100%',
                    background: 'rgba(4,8,16,.85)',
                    border: '1px solid var(--border)',
                    borderRadius: 8,
                    padding: '8px 12px',
                    color: 'var(--text)',
                    fontSize: 12,
                    outline: 'none'
                  }}
                  value={selectedCategory}
                  onChange={e => setSelectedCategory(e.target.value)}
                >
                  <option value="">全部类别</option>
                  {categories.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: 11, color: 'var(--muted)', display: 'block', marginBottom: 4 }}>记忆来源</label>
                <select
                  style={{
                    width: '100%',
                    background: 'rgba(4,8,16,.85)',
                    border: '1px solid var(--border)',
                    borderRadius: 8,
                    padding: '8px 12px',
                    color: 'var(--text)',
                    fontSize: 12,
                    outline: 'none'
                  }}
                  value={selectedSourceType}
                  onChange={e => setSelectedSourceType(e.target.value)}
                >
                  <option value="">全部来源</option>
                  {sourceTypes.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
            </>
          )}

          <div style={{ gridColumn: subTab === 'memories' ? 'span 2' : 'span 4' }}>
            <label style={{ fontSize: 11, color: 'var(--muted)', display: 'block', marginBottom: 4 }}>
              {subTab === 'memories' ? '搜索内容/标题' : '搜索文档名称'}
            </label>
            <input
              placeholder="输入关键词搜索..."
              style={{
                width: '100%',
                background: 'rgba(4,8,16,.85)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: '8px 12px',
                color: 'var(--text)',
                fontSize: 12,
                outline: 'none'
              }}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      {subTab === 'memories' ? (
        /* Memories Table */
        <div className="card">
          <table className="table" style={{ cursor: 'pointer' }}>
            <thead>
              <tr>
                <th>标题</th>
                <th>租户</th>
                <th>分类</th>
                <th>主题</th>
                <th>来源</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
                    ⏳ 数据加载中...
                  </td>
                </tr>
              ) : memories.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
                    暂无匹配的知识记忆
                  </td>
                </tr>
              ) : (
                memories.map(m => (
                  <tr key={m.id} onClick={() => setActiveMemory(m)}>
                    <td style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                      {m.title || '无标题'}
                    </td>
                    <td>{m.team_id}</td>
                    <td>{m.category || '未分类'}</td>
                    <td style={{ color: 'var(--teal)' }}>{m.topic || '—'}</td>
                    <td>{getSourceBadge(m.source_type)}</td>
                    <td style={{ fontSize: 11, color: 'var(--muted)' }}>{formatDate(m.created_at)}</td>
                    <td>
                      <button
                        className="btn btn-danger"
                        style={{ padding: '4px 8px', fontSize: 11 }}
                        onClick={e => handleDelete(e, m.id)}
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                共 <strong>{currentTotal}</strong> 条记录 (第 {currentPage} / {totalPages} 页)
              </span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="btn btn-ghost"
                  style={{ padding: '6px 12px', fontSize: 11 }}
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                >
                  ◀ 上一页
                </button>
                <button
                  className="btn btn-ghost"
                  style={{ padding: '6px 12px', fontSize: 11 }}
                  disabled={currentPage >= totalPages}
                  onClick={() => setOffset(offset + limit)}
                >
                  下一页 ▶
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Documents Table */
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>文件名</th>
                <th>租户</th>
                <th>文件大小</th>
                <th>分块数</th>
                <th>上传时间</th>
                <th style={{ textAlign: 'right' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
                    ⏳ 数据加载中...
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
                    暂无匹配的文档文件
                  </td>
                </tr>
              ) : (
                documents.map(d => (
                  <tr key={d.id}>
                    <td style={{ fontWeight: 500 }}>{d.filename}</td>
                    <td>{d.team_id}</td>
                    <td>{formatSize(d.file_size)}</td>
                    <td>
                      <span className="badge badge-violet">{d.chunk_count} Chunks</span>
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--muted)' }}>{formatDate(d.created_at)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-danger"
                        style={{ padding: '4px 8px', fontSize: 11 }}
                        onClick={e => handleDeleteDocument(e, d.id)}
                      >
                        级联删除
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                共 <strong>{currentTotal}</strong> 个文档 (第 {currentPage} / {totalPages} 页)
              </span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="btn btn-ghost"
                  style={{ padding: '6px 12px', fontSize: 11 }}
                  disabled={docsOffset === 0}
                  onClick={() => setDocsOffset(Math.max(0, docsOffset - limit))}
                >
                  ◀ 上一页
                </button>
                <button
                  className="btn btn-ghost"
                  style={{ padding: '6px 12px', fontSize: 11 }}
                  disabled={currentPage >= totalPages}
                  onClick={() => setDocsOffset(docsOffset + limit)}
                >
                  下一页 ▶
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Memory Detail Modal */}
      {activeMemory && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.6)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: 20
          }}
          onClick={() => setActiveMemory(null)}
        >
          <div
            style={{
              background: 'rgba(10,18,32,0.95)',
              border: '1px solid var(--border)',
              borderRadius: 16,
              maxWidth: 700,
              width: '100%',
              maxHeight: '85vh',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
              overflow: 'hidden'
            }}
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div
              style={{
                padding: '16px 20px',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>
                  {activeMemory.title || '知识详情'}
                </h3>
                <div style={{ display: 'flex', gap: 8, marginTop: 6, fontSize: 11 }}>
                  <span>租户: <strong>{activeMemory.team_id}</strong></span>
                  <span style={{ color: 'var(--dim)' }}>|</span>
                  <span>分类: <strong>{activeMemory.category}</strong></span>
                  {activeMemory.subcategory && (
                    <>
                      <span style={{ color: 'var(--dim)' }}>|</span>
                      <span>子类: <strong>{activeMemory.subcategory}</strong></span>
                    </>
                  )}
                  {activeMemory.topic && (
                    <>
                      <span style={{ color: 'var(--dim)' }}>|</span>
                      <span>主题: <strong>{activeMemory.topic}</strong></span>
                    </>
                  )}
                </div>
              </div>
              <button
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--muted)',
                  fontSize: 20,
                  cursor: 'pointer',
                  padding: 4
                }}
                onClick={() => setActiveMemory(null)}
              >
                ×
              </button>
            </div>

            {/* Content */}
            <div style={{ padding: 20, overflowY: 'auto', flex: 1 }}>
              <div
                style={{
                  background: 'rgba(0,0,0,0.2)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  borderRadius: 10,
                  padding: 16,
                  color: '#CBD5E1',
                  fontSize: 13,
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'var(--mono)'
                }}
              >
                {activeMemory.content || '(无内容)'}
              </div>
            </div>

            {/* Footer */}
            <div
              style={{
                padding: '12px 20px',
                borderTop: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'rgba(0,0,0,0.1)'
              }}
            >
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                创建时间: {formatDate(activeMemory.created_at)}
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  className="btn btn-danger"
                  style={{ padding: '6px 14px', fontSize: 12 }}
                  onClick={e => handleDelete(e, activeMemory.id)}
                >
                  删除记忆
                </button>
                <button
                  className="btn btn-ghost"
                  style={{ padding: '6px 14px', fontSize: 12 }}
                  onClick={() => setActiveMemory(null)}
                >
                  关闭
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
