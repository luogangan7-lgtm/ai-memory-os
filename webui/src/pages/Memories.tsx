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

  const categoriesDisplay = [
    { value: '自然科学', label: '自然科学 Natural Sci' },
    { value: '社会科学', label: '社会科学 Social Sci' },
    { value: '数学科学', label: '数学科学 Math Sci' },
    { value: '系统科学', label: '系统科学 System Sci' },
    { value: '工程技术', label: '工程技术 Engineering' },
    { value: '人体科学', label: '人体科学 Life Sci' },
    { value: '思维科学', label: '思维科学 Cognitive Sci' },
    { value: '人文艺术', label: '人文艺术 Humanities' },
    { value: '个人记忆', label: '个人记忆 Personal' },
    { value: '未分类', label: '未分类 Unclassified' }
  ];

  const sourceTypes = [
    { value: 'document', label: '文档 Document' },
    { value: 'knowledge', label: '整合知识 Reflection' },
    { value: 'human', label: '用户聊天 Chat' },
    { value: 'agent', label: 'AI记忆/MCP Agent/MCP' },
    { value: 'image', label: '图片/OCR Image/OCR' }
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
      toast('加载记忆失败 Load memories failed', 'err');
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
      toast('加载文档失败 Load documents failed', 'err');
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
    if (!window.confirm('确定要永久删除此条记忆吗？对应向量索引和关系将一并清除。\nAre you sure you want to delete this memory? Vector index and relations will be removed.')) {
      return;
    }
    try {
      await deleteAdminMemory(id);
      toast('记忆删除成功 Memory deleted');
      loadMemories();
      if (activeMemory?.id === id) {
        setActiveMemory(null);
      }
    } catch {
      toast('删除失败 Delete failed', 'err');
    }
  };

  const handleDeleteDocument = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('确定要永久删除此文档吗？这将级联删除对应的解析记忆、向量数据以及底层存储文件！\nAre you sure you want to delete this document? This will delete all parsed memories, vectors, and files!')) {
      return;
    }
    try {
      await deleteAdminDocument(id);
      toast('文档级联删除成功 Document deleted');
      loadDocuments();
      if (subTab === 'memories') {
        loadMemories();
      }
    } catch {
      toast('删除失败 Delete failed', 'err');
    }
  };

  const getSourceBadge = (source: string) => {
    switch (source) {
      case 'document':
        return <span className="v6-tag">文档 Doc</span>;
      case 'knowledge':
        return <span className="v6-tag v6-tag--accent">整合 Reflection</span>;
      case 'human':
        return <span className="v6-tag">聊天 Chat</span>;
      case 'agent':
        return <span className="v6-tag">AI/MCP</span>;
      case 'image':
        return <span className="v6-tag">OCR</span>;
      default:
        return <span className="v6-tag">{source || '未知 Unknown'}</span>;
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
      <h1 style={{ font: "600 22px var(--v6-font-sans)", color: "var(--v6-fg)", marginBottom: 4 }}>数据与知识 Data & Knowledge</h1>
      <div style={{ color: "var(--v6-fg-muted)", fontSize: 13, marginBottom: 24 }}>查看、检索和管理系统内的所有知识、多级记忆与上传文档数据 · Browse and manage database knowledge, memories, and files</div>

      {/* Sub-tab navigation */}
      <div style={{ marginBottom: 16 }}>
        <div className="v6-subtabs">
          <button
            className="v6-subtab"
            aria-current={subTab === 'memories' ? 'page' : undefined}
            onClick={() => setSubTab('memories')}
          >
            记忆管理 Memories
          </button>
          <button
            className="v6-subtab"
            aria-current={subTab === 'documents' ? 'page' : undefined}
            onClick={() => setSubTab('documents')}
          >
            文档管理 Documents
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="v6-card" style={{ padding: 18, marginBottom: 18 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          <div>
            <label style={{ fontSize: 11, color: 'var(--v6-fg-muted)', display: 'block', marginBottom: 4 }}>租户过滤 Tenant</label>
            <select
              className="v6-input-global"
              style={{ width: '100%' }}
              value={selectedTenant}
              onChange={e => setSelectedTenant(e.target.value)}
            >
              <option value="">全部租户 All Tenants</option>
              {tenants.map(t => (
                <option key={t.team_id} value={t.team_id}>{t.name || t.team_id}</option>
              ))}
            </select>
          </div>

          {subTab === 'memories' && (
            <>
              <div>
                <label style={{ fontSize: 11, color: 'var(--v6-fg-muted)', display: 'block', marginBottom: 4 }}>科学分类 Category</label>
                <select
                  className="v6-input-global"
                  style={{ width: '100%' }}
                  value={selectedCategory}
                  onChange={e => setSelectedCategory(e.target.value)}
                >
                  <option value="">全部类别 All Categories</option>
                  {categoriesDisplay.map(c => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: 11, color: 'var(--v6-fg-muted)', display: 'block', marginBottom: 4 }}>记忆来源 Source</label>
                <select
                  className="v6-input-global"
                  style={{ width: '100%' }}
                  value={selectedSourceType}
                  onChange={e => setSelectedSourceType(e.target.value)}
                >
                  <option value="">全部来源 All Sources</option>
                  {sourceTypes.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
            </>
          )}

          <div style={{ gridColumn: subTab === 'memories' ? 'span 2' : 'span 4' }}>
            <label style={{ fontSize: 11, color: 'var(--v6-fg-muted)', display: 'block', marginBottom: 4 }}>
              {subTab === 'memories' ? '搜索内容/标题 Search Content / Title' : '搜索文档名称 Search Filename'}
            </label>
            <input
              placeholder="输入关键词搜索... Search keywords..."
              className="v6-input-global"
              style={{ width: '100%' }}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      {subTab === 'memories' ? (
        /* Memories Table */
        <div className="v6-card">
          <table className="v6-table" style={{ cursor: 'pointer' }}>
            <thead>
              <tr>
                <th>标题 Title</th>
                <th>租户 Tenant</th>
                <th>分类 Category</th>
                <th>主题 Topic</th>
                <th>来源 Source</th>
                <th>创建时间 Created At</th>
                <th>操作 Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--v6-fg-muted)' }}>
                    加载中... Loading...
                  </td>
                </tr>
              ) : memories.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--v6-fg-muted)' }}>
                    暂无匹配的知识记忆 No matching memories
                  </td>
                </tr>
              ) : (
                memories.map(m => (
                  <tr key={m.id} onClick={() => setActiveMemory(m)}>
                    <td style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                      {m.title || '无标题 Untitled'}
                    </td>
                    <td className="v6-font-mono">{m.team_id}</td>
                    <td>{m.category || '未分类 Unclassified'}</td>
                    <td style={{ color: '#2DBFA8' }}>{m.topic || '—'}</td>
                    <td>{getSourceBadge(m.source_type)}</td>
                    <td className="v6-font-mono" style={{ fontSize: 11, color: 'var(--v6-fg-muted)' }}>{formatDate(m.created_at)}</td>
                    <td>
                      <button
                        className="v6-btn v6-btn--danger v6-btn--xs"
                        onClick={e => handleDelete(e, m.id)}
                      >
                        删除 Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--v6-border)' }}>
              <span style={{ fontSize: 12, color: 'var(--v6-fg-muted)' }}>
                共 <strong>{currentTotal}</strong> 条记录 Total {currentTotal} (第 {currentPage} / {totalPages} 页 Page {currentPage} of {totalPages})
              </span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="v6-btn v6-btn--ghost v6-btn--xs"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                >
                  上一页 Prev
                </button>
                <button
                  className="v6-btn v6-btn--ghost v6-btn--xs"
                  disabled={currentPage >= totalPages}
                  onClick={() => setOffset(offset + limit)}
                >
                  下一页 Next
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Documents Table */
        <div className="v6-card">
          <table className="v6-table">
            <thead>
              <tr>
                <th>文件名 Filename</th>
                <th>租户 Tenant</th>
                <th>文件大小 Size</th>
                <th>分块数 Chunks</th>
                <th>上传时间 Uploaded At</th>
                <th style={{ textAlign: 'right' }}>操作 Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--v6-fg-muted)' }}>
                    加载中... Loading...
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--v6-fg-muted)' }}>
                    暂无匹配的文档文件 No matching documents
                  </td>
                </tr>
              ) : (
                documents.map(d => (
                  <tr key={d.id}>
                    <td style={{ fontWeight: 500 }}>{d.filename}</td>
                    <td className="v6-font-mono">{d.team_id}</td>
                    <td className="v6-font-mono">{formatSize(d.file_size)}</td>
                    <td>
                      <span className="v6-tag">{d.chunk_count} Chunks</span>
                    </td>
                    <td className="v6-font-mono" style={{ fontSize: 11, color: 'var(--v6-fg-muted)' }}>{formatDate(d.created_at)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="v6-btn v6-btn--danger v6-btn--xs"
                        onClick={e => handleDeleteDocument(e, d.id)}
                      >
                        删除 Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--v6-border)' }}>
              <span style={{ fontSize: 12, color: 'var(--v6-fg-muted)' }}>
                共 <strong>{currentTotal}</strong> 个文档 Total {currentTotal} (第 {currentPage} / {totalPages} 页 Page {currentPage} of {totalPages})
              </span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="v6-btn v6-btn--ghost v6-btn--xs"
                  disabled={docsOffset === 0}
                  onClick={() => setDocsOffset(Math.max(0, docsOffset - limit))}
                >
                  上一页 Prev
                </button>
                <button
                  className="v6-btn v6-btn--ghost v6-btn--xs"
                  disabled={currentPage >= totalPages}
                  onClick={() => setDocsOffset(docsOffset + limit)}
                >
                  下一页 Next
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
            background: 'rgba(0,0,0,0.7)',
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
              background: 'var(--v6-bg-elev)',
              border: '1px solid var(--v6-border)',
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
                borderBottom: '1px solid var(--v6-border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--v6-fg)' }}>
                  {activeMemory.title || '知识详情 Knowledge Details'}
                </h3>
                <div style={{ display: 'flex', gap: 8, marginTop: 6, fontSize: 11, color: 'var(--v6-fg-muted)' }}>
                  <span>租户 Tenant: <strong>{activeMemory.team_id}</strong></span>
                  <span style={{ color: 'var(--v6-fg-faint)' }}>|</span>
                  <span>分类 Category: <strong>{activeMemory.category || '未分类 Unclassified'}</strong></span>
                  {activeMemory.subcategory && (
                    <>
                      <span style={{ color: 'var(--v6-fg-faint)' }}>|</span>
                      <span>子类 Subcategory: <strong>{activeMemory.subcategory}</strong></span>
                    </>
                  )}
                  {activeMemory.topic && (
                    <>
                      <span style={{ color: 'var(--v6-fg-faint)' }}>|</span>
                      <span>主题 Topic: <strong>{activeMemory.topic}</strong></span>
                    </>
                  )}
                </div>
              </div>
              <button
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--v6-fg-muted)',
                  fontSize: 24,
                  cursor: 'pointer',
                  padding: 4,
                  lineHeight: 1
                }}
                onClick={() => setActiveMemory(null)}
              >
                &times;
              </button>
            </div>

            {/* Content */}
            <div style={{ padding: 20, overflowY: 'auto', flex: 1 }}>
              <div
                style={{
                  background: 'var(--v6-bg-sunken)',
                  border: '1px solid var(--v6-border)',
                  borderRadius: 'var(--v6-radius-md)',
                  padding: 16,
                  color: 'var(--v6-fg)',
                  fontSize: 13,
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'var(--v6-font-mono)'
                }}
              >
                {activeMemory.content || '(无内容 No content)'}
              </div>
            </div>

            {/* Footer */}
            <div
              style={{
                padding: '12px 20px',
                borderTop: '1px solid var(--v6-border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'var(--v6-bg-sunken)'
              }}
            >
              <div style={{ fontSize: 11, color: 'var(--v6-fg-muted)' }} className="v6-font-mono">
                创建时间 Created At: {formatDate(activeMemory.created_at)}
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  className="v6-btn v6-btn--danger v6-btn--xs"
                  onClick={e => handleDelete(e, activeMemory.id)}
                >
                  删除记忆 Delete
                </button>
                <button
                  className="v6-btn v6-btn--ghost v6-btn--xs"
                  onClick={() => setActiveMemory(null)}
                >
                  关闭 Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
