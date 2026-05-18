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
      <div className="page-title">租户管理</div>
      <div className="page-sub">管理系统中的所有租户（团队）及其资源配额</div>
      {err && <div style={{color:"var(--crimson)",marginBottom:16,fontSize:13}}>{err}</div>}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>用户数</th>
              <th>记忆数</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {tenants.length === 0 && !err && (
              <tr><td colSpan={6} style={{textAlign:"center",padding:40,color:"var(--muted)"}}>暂无数据</td></tr>
            )}
            {tenants.map((t, i) => (
              <tr key={i}>
                <td>{t.team_id}</td>
                <td>{t.name}</td>
                <td>{t.user_count}</td>
                <td>{t.memory_count?.toLocaleString()}</td>
                <td>
                  <span className={`badge ${t.active ? "badge-emerald" : "badge-amber"}`}>
                    {t.active ? "活跃" : "已暂停"}
                  </span>
                </td>
                <td>
                  {t.team_id !== "default" && t.team_id !== "admin" ? (
                    <button
                      className="btn btn-danger"
                      onClick={() => remove(t.team_id)}
                    >
                      删除
                    </button>
                  ) : (
                    <span style={{color:"var(--muted)",fontSize:12}}>系统租户</span>
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
