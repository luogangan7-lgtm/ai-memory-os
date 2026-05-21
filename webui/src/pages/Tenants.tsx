import { useEffect, useState } from "react";
import { getTenants, deleteTenant } from "../api/endpoints";
import { useToast } from "../contexts/ToastContext";

export function TenantsPage() {
  const { toast } = useToast();
  const [tenants, setTenants] = useState<{team_id:string;name:string;user_count:number;memory_count:number;active:boolean}[]>([]);
  const [err, setErr] = useState("");

  const load = () => {
    getTenants().then(r => setTenants(r.tenants || [])).catch(() => setErr("加载失败 — 后端未连接"));
  };
  useEffect(() => { load(); }, []);

  async function remove(team_id: string) {
    if (team_id === "default" || team_id === "admin") {
      toast("无法删除系统内置租户", "err");
      return;
    }
    if (!window.confirm(`确定要永久删除租户 "${team_id}" 及其所有数据吗？此操作无法撤销！`)) return;
    try {
      await deleteTenant(team_id);
      toast(`租户 ${team_id} 已删除`);
      load();
    } catch {
      toast("删除失败", "err");
    }
  }

  return (
    <div>
      <h1 style={{ font: "600 22px var(--v6-font-sans)", color: "var(--v6-fg)", marginBottom: 4 }}>租户管理 Tenants</h1>
      <div style={{ color: "var(--v6-fg-muted)", fontSize: 13, marginBottom: 24 }}>管理系统中的所有租户（团队）及其资源配额 · Manage tenant workspace allocations and resource quotas</div>
      {err && <div className="v6-statusbar v6-statusbar--err" style={{ marginBottom: 16 }}>{err}</div>}
      <div className="v6-card">
        <table className="v6-table">
          <thead>
            <tr>
              <th>标识 ID</th>
              <th>名称 Name</th>
              <th>用户数 Users</th>
              <th>记忆数 Memories</th>
              <th>状态 Status</th>
              <th>操作 Actions</th>
            </tr>
          </thead>
          <tbody>
            {tenants.length === 0 && !err && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: 40, color: "var(--v6-fg-muted)" }}>
                  暂无数据 · No data yet
                </td>
              </tr>
            )}
            {tenants.map((t, i) => (
              <tr key={i}>
                <td className="v6-font-mono">{t.team_id}</td>
                <td>{t.name}</td>
                <td>{t.user_count}</td>
                <td className="v6-font-mono">{t.memory_count?.toLocaleString()}</td>
                <td>
                  <span className="v6-tag">
                    {t.active ? "活跃 Active" : "已暂停 Paused"}
                  </span>
                </td>
                <td>
                  {t.team_id !== "default" && t.team_id !== "admin" ? (
                    <button
                      className="v6-btn v6-btn--danger v6-btn--xs"
                      onClick={() => remove(t.team_id)}
                    >
                      删除 Delete
                    </button>
                  ) : (
                    <span style={{ color: "var(--v6-fg-faint)", fontSize: 12 }}>系统租户 System</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
