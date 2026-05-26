import { useState, useEffect } from "react";
import { api } from "../api/client";

interface CategoryStat {
  category: string;
  count: number;
  latest_at: string | null;
  contributing_agents: string[];
}

interface MemoryItem {
  id: string;
  title: string;
  content: string;
  layer: string;
  category: string;
  agent_source: string;
  created_at: string | null;
}

export function KnowledgeMap() {
  const [stats, setStats] = useState<CategoryStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [selectedCat, setSelectedCat] = useState<string | null>(null);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [modalLoading, setModalLoading] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<CategoryStat[]>("/memory/categories");
      setStats(data || []);
    } catch (e: any) {
      setError(e?.message || "无法加载知识地图统计信息");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const openCategory = async (category: string) => {
    setSelectedCat(category);
    setModalLoading(true);
    setMemories([]);
    try {
      const data = await api.get<MemoryItem[]>(`/memory/categories/${encodeURIComponent(category)}`);
      setMemories(data || []);
    } catch (e) {
      console.error("加载分类数据失败", e);
    } finally {
      setModalLoading(false);
    }
  };

  const formatDate = (s: string | null) => {
    if (!s) return "—";
    try {
      return new Date(s).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return s;
    }
  };

  const totalCount = stats.reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="v6-card" style={{ position: "relative", overflow: "hidden" }}>
      <div className="v6-card__head">
        <div className="v6-card__title">
          🗺️ 知识地图 Knowledge Map
          <span className="v6-card__title-hint">可视化查看所有记忆分类与贡献来源</span>
        </div>
        <button className="v6-btn v6-btn--xs" onClick={fetchStats}>
          刷新
        </button>
      </div>

      {loading ? (
        <div className="v6-empty" style={{ padding: "40px 0" }}>
          加载地图数据中...
        </div>
      ) : error ? (
        <div className="v6-authcard__error" style={{ margin: "20px 0" }}>
          {error}
        </div>
      ) : stats.length === 0 ? (
        <div className="v6-empty" style={{ padding: "40px 0" }}>
          暂无知识分类数据，请写入更多记忆。
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Overview Stat Row */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              background: "var(--v6-bg-elevated)",
              padding: "16px 20px",
              borderRadius: "var(--v6-radius-md)",
              border: "1px solid var(--v6-border)",
            }}
          >
            <div>
              <div style={{ fontSize: 13, color: "var(--v6-fg-muted)" }}>总提取节点数</div>
              <div style={{ fontSize: 28, fontWeight: "bold", color: "var(--color-primary, #00d4ff)", fontFamily: "var(--v6-font-mono)" }}>
                {totalCount}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 13, color: "var(--v6-fg-muted)" }}>分类总数</div>
              <div style={{ fontSize: 28, fontWeight: "bold", color: "var(--v6-fg)", fontFamily: "var(--v6-font-mono)" }}>
                {stats.length}
              </div>
            </div>
          </div>

          {/* Grid Layout */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 16,
            }}
          >
            {stats.map((item) => {
              const percentage = totalCount > 0 ? ((item.count / totalCount) * 100).toFixed(0) : "0";
              return (
                <div
                  key={item.category}
                  onClick={() => openCategory(item.category)}
                  className="v6-metric-tile"
                  style={{
                    cursor: "pointer",
                    transition: "transform 0.2s, box-shadow 0.2s",
                    border: "1px solid var(--v6-border)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = "translateY(-4px)";
                    e.currentTarget.style.boxShadow = "0 8px 24px rgba(0, 212, 255, 0.15)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = "none";
                    e.currentTarget.style.boxShadow = "none";
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                    <div style={{ fontSize: 16, fontWeight: "bold", color: "var(--v6-fg)" }}>
                      {item.category}
                    </div>
                    <span className="v6-tag" style={{ background: "rgba(0, 212, 255, 0.1)", color: "var(--color-primary, #00d4ff)" }}>
                      {percentage}%
                    </span>
                  </div>

                  <div style={{ fontSize: 24, fontWeight: "bold", margin: "10px 0", fontFamily: "var(--v6-font-mono)", color: "var(--v6-fg)" }}>
                    {item.count} <span style={{ fontSize: 13, fontWeight: "normal", color: "var(--v6-fg-muted)" }}>个节点</span>
                  </div>

                  <div style={{ fontSize: 12, color: "var(--v6-fg-muted)", marginTop: 12, display: "flex", flexDirection: "column", gap: 4 }}>
                    <div>🕒 最新更新: {formatDate(item.latest_at)}</div>
                    <div>🤖 贡献智能体: {item.contributing_agents.length > 0 ? item.contributing_agents.join(", ") : "无"}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Details Modal */}
      {selectedCat && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.6)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setSelectedCat(null)}
        >
          <div
            style={{
              background: "var(--v6-bg-elevated)",
              width: "90%",
              maxWidth: 700,
              maxHeight: "80vh",
              borderRadius: "var(--v6-radius-lg)",
              border: "1px solid var(--v6-border)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                padding: "16px 20px",
                borderBottom: "1px solid var(--v6-border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div style={{ fontSize: 18, fontWeight: "bold", color: "var(--v6-fg)" }}>
                📁 分类详情: {selectedCat}
              </div>
              <button
                className="v6-btn v6-btn--ghost v6-btn--xs"
                onClick={() => setSelectedCat(null)}
                style={{ fontSize: 18, padding: "0 6px" }}
              >
                ✕
              </button>
            </div>

            <div style={{ flex: 1, overflowY: "auto", padding: 20 }}>
              {modalLoading ? (
                <div className="v6-empty" style={{ padding: "30px 0" }}>
                  加载记忆列表中...
                </div>
              ) : memories.length === 0 ? (
                <div className="v6-empty" style={{ padding: "30px 0" }}>
                  本分类下暂无已 crystallized 节点
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {memories.map((m) => (
                    <div
                      key={m.id}
                      style={{
                        background: "rgba(255,255,255,0.02)",
                        padding: "14px 16px",
                        borderRadius: "var(--v6-radius-sm)",
                        border: "1px solid var(--v6-border)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                        <div style={{ fontWeight: "bold", fontSize: 14, color: "var(--v6-fg)" }}>{m.title}</div>
                        <span className="v6-tag">{m.agent_source}</span>
                      </div>
                      <p style={{ fontSize: 13, color: "var(--v6-fg-muted)", margin: "8px 0", lineHeight: 1.4 }}>
                        {m.content}
                      </p>
                      <div style={{ fontSize: 11, color: "var(--v6-fg-muted)", textAlign: "right" }}>
                        创建时间: {formatDate(m.created_at)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div
              style={{
                padding: "12px 20px",
                borderTop: "1px solid var(--v6-border)",
                textAlign: "right",
                background: "rgba(255,255,255,0.01)",
              }}
            >
              <button className="v6-btn v6-btn--ghost v6-btn--xs" onClick={() => setSelectedCat(null)}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
