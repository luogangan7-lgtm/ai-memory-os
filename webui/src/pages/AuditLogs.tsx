import { useEffect, useState, useCallback } from "react";
import { getAuditLogs } from "../api/endpoints";
import type { AuditLog } from "../api/types";

export function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [action, setAction] = useState("");
  const [user, setUser] = useState("");

  const load = useCallback(async () => {
    try {
      const r = await getAuditLogs(action, user);
      setLogs(r.logs);
    } catch {
      console.error('audit load failed');
    }
  }, [action, user]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <h1 style={{ font: "600 22px var(--v6-font-sans)", color: "var(--v6-fg)", marginBottom: 4 }}>审计日志 Audit Logs</h1>
      <div style={{ color: "var(--v6-fg-muted)", fontSize: 13, marginBottom: 24 }}>系统操作行为的安全审计日志 · Security audit logs of system operations</div>

      <div className="v6-card">
        <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
          <select
            value={action}
            onChange={e => setAction(e.target.value)}
            className="v6-input-global"
            style={{ width: 160 }}
          >
            <option value="">全部操作 All Actions</option>
            <option value="store">存储记忆 Store Memory</option>
            <option value="delete">删除记忆 Delete Memory</option>
            <option value="login">用户登录 User Login</option>
          </select>
          <input
            placeholder="搜索用户名... Search username..."
            className="v6-input-global"
            style={{ flex: 1 }}
            value={user}
            onChange={e => setUser(e.target.value)}
          />
          <button className="v6-btn v6-btn--primary" onClick={load}>
            查询 Search
          </button>
        </div>

        <table className="v6-table">
          <thead>
            <tr>
              <th>时间 Time</th>
              <th>用户 User</th>
              <th>租户 Tenant</th>
              <th>操作 Action</th>
              <th>目标 Target ID</th>
              <th>IP IP Address</th>
              <th>结果 Result</th>
            </tr>
          </thead>
          <tbody>
            {(logs || []).length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: 40, color: "var(--v6-fg-muted)" }}>
                  暂无审计数据 · No audit logs yet
                </td>
              </tr>
            ) : (
              (logs || []).map((l, i) => (
                <tr key={i}>
                  <td className="v6-font-mono">{l.created_at || "-"}</td>
                  <td>{l.username || "-"}</td>
                  <td className="v6-font-mono">{(l.team_id || "").substring(0, 12)}</td>
                  <td>
                    <span className="v6-tag">
                      {l.action}
                    </span>
                  </td>
                  <td className="v6-font-mono">{(l.target_id || "").substring(0, 12) || "—"}</td>
                  <td className="v6-font-mono">{l.ip_address || "-"}</td>
                  <td>
                    <span className={`v6-tag ${l.success ? "" : "v6-tag-crimson"}`}>
                      {l.success ? "OK" : "FAIL"}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
