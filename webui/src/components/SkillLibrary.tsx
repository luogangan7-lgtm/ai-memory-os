import { useState, useEffect } from "react";
import { api } from "../api/client";

interface SkillItem {
  id: string;
  skill_name: string;
  skill_content: string;
  trigger_pattern: string | null;
  usage_count: number;
  fail_count?: number;
  effectiveness: number;
  source_agents?: string[];
  last_used_at?: string | null;
  created_at: string | null;
}

export function SkillLibrary() {
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [crystallizing, setCrystallizing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const fetchSkills = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<{ skills: SkillItem[] }>("/api/skills");
      setSkills(data?.skills || []);
    } catch (e: any) {
      setError(e?.message || "无法加载技能库信息");
    } finally {
      setLoading(false);
    }
  };

  const triggerCrystallize = async () => {
    setCrystallizing(true);
    setMsg(null);
    try {
      await api.post("/api/skills/crystallize", {});
      setMsg("🧠 技能固化提取任务已启动，请稍后刷新查看。");
      setTimeout(() => setMsg(null), 5000);
    } catch (e: any) {
      setError(e?.message || "触发技能固化失败");
    } finally {
      setCrystallizing(false);
    }
  };

  useEffect(() => {
    fetchSkills();
  }, []);

  const formatDate = (s: string | null | undefined) => {
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

  return (
    <div className="v6-card" style={{ position: "relative", overflow: "hidden" }}>
      <div className="v6-card__head">
        <div className="v6-card__title">
          💎 智能体技能库 Skill Library (L4)
          <span className="v6-card__title-hint">查看由 L1 记忆固化、演化出的核心技能模式</span>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button 
            className="v6-btn v6-btn--xs v6-btn--secondary" 
            onClick={triggerCrystallize}
            disabled={crystallizing}
          >
            {crystallizing ? "提取中..." : "🧠 固化技能"}
          </button>
          <button className="v6-btn v6-btn--xs" onClick={fetchSkills} disabled={loading}>
            刷新
          </button>
        </div>
      </div>

      {msg && (
        <div className="v6-authcard__success" style={{ margin: "10px 0" }}>
          {msg}
        </div>
      )}

      {loading ? (
        <div className="v6-empty" style={{ padding: "40px 0" }}>
          正在加载技能库数据...
        </div>
      ) : error ? (
        <div className="v6-authcard__error" style={{ margin: "20px 0" }}>
          {error}
        </div>
      ) : skills.length === 0 ? (
        <div className="v6-empty" style={{ padding: "40px 0" }}>
          暂无已固化的 L4 技能。可点击右上角「固化技能」手动提取。
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {skills.map((skill) => {
            const effPercentage = (skill.effectiveness * 100).toFixed(0);
            let progressBarColor = "var(--color-success, #00ff88)";
            if (skill.effectiveness < 0.4) {
              progressBarColor = "var(--color-danger, #ff4455)";
            } else if (skill.effectiveness < 0.7) {
              progressBarColor = "var(--color-warning, #ffb800)";
            }

            return (
              <div
                key={skill.id}
                style={{
                  background: "var(--v6-bg-elevated)",
                  padding: "20px",
                  borderRadius: "var(--v6-radius-md)",
                  border: "1px solid var(--v6-border)",
                  transition: "transform 0.15s, border-color 0.15s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--color-primary, #00d4ff)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--v6-border)";
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: 16, fontWeight: "bold", color: "var(--v6-fg)" }}>
                      {skill.skill_name}
                    </h3>
                    {skill.trigger_pattern && (
                      <code
                        style={{
                          display: "inline-block",
                          marginTop: 6,
                          padding: "2px 6px",
                          background: "rgba(0,0,0,0.3)",
                          borderRadius: 4,
                          fontSize: 11,
                          color: "var(--color-primary, #00d4ff)",
                          fontFamily: "var(--v6-font-mono)",
                        }}
                      >
                        ⚡ 触发模式: {skill.trigger_pattern}
                      </code>
                    )}
                  </div>
                  
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 12, color: "var(--v6-fg-muted)", marginBottom: 4 }}>
                      有效性: <strong style={{ color: progressBarColor }}>{effPercentage}%</strong>
                    </div>
                    {/* Progress Bar */}
                    <div
                      style={{
                        width: 100,
                        height: 6,
                        background: "rgba(255,255,255,0.1)",
                        borderRadius: 3,
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${effPercentage}%`,
                          height: "100%",
                          background: progressBarColor,
                        }}
                      />
                    </div>
                  </div>
                </div>

                <div 
                  style={{ 
                    fontSize: 13, 
                    color: "var(--v6-fg-muted)", 
                    lineHeight: 1.5, 
                    marginBottom: 16,
                    whiteSpace: "pre-wrap"
                  }}
                >
                  {skill.skill_content}
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    borderTop: "1px solid rgba(255,255,255,0.05)",
                    paddingTop: 12,
                    fontSize: 11,
                    color: "var(--v6-fg-muted)",
                  }}
                >
                  <div style={{ display: "flex", gap: 16 }}>
                    <span>📊 调用次数: <strong>{skill.usage_count}</strong></span>
                    {skill.fail_count !== undefined && (
                      <span>❌ 失败次数: <strong>{skill.fail_count}</strong></span>
                    )}
                    {skill.source_agents && skill.source_agents.length > 0 && (
                      <span>🤖 关联智能体: <strong>{skill.source_agents.join(", ")}</strong></span>
                    )}
                  </div>
                  <div>
                    <span>🕒 创建时间: {formatDate(skill.created_at)}</span>
                    {skill.last_used_at && (
                      <span style={{ marginLeft: 16 }}>⚡ 上次使用: {formatDate(skill.last_used_at)}</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
