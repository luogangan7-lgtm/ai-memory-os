import { useEffect, useState, useCallback } from 'react';
import { getUsers, toggleUserStatus, deleteUser } from '../api/endpoints';
import { useToast } from '../contexts/ToastContext';

type User = {
  user_id: string;
  username: string;
  team_id: string;
  memory_count: number;
  token_usage: number;
  active: boolean;
  role?: string;
  created?: string;
  api_key_prefix?: string;
};

export function UsersPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    try { const r = await getUsers(q); setUsers(r.users); }
    catch { toast('加载失败 Load failed', 'err'); }
  }, [q, toast]);
  useEffect(() => { load(); }, [load]);

  async function toggle(uid: string, isActive: boolean) {
    setBusy(b => ({ ...b, [uid]: true }));
    try {
      await toggleUserStatus(uid, isActive);
      toast(isActive ? '已暂停 Suspended' : '已激活 Activated');
      load();
    } catch {
      toast('操作失败 Operation failed', 'err');
    } finally {
      setBusy(b => ({ ...b, [uid]: false }));
    }
  }

  async function remove(uid: string, username: string) {
    if (username === 'admin') {
      toast('无法删除系统管理员账号 Cannot delete admin', 'err');
      return;
    }
    if (!window.confirm(
      `确定要永久删除用户 "${username}" 吗？此操作无法撤销！\nAre you sure you want to permanently delete "${username}"?`
    )) return;
    setBusy(b => ({ ...b, [uid]: true }));
    try {
      await deleteUser(username);
      toast('用户已成功删除 User deleted');
      load();
    } catch {
      toast('删除失败 Delete failed', 'err');
    } finally {
      setBusy(b => ({ ...b, [uid]: false }));
    }
  }

  const isActive = (u: User) => u.active !== false;

  return (
    <div>
      <h1 style={{ font: '600 22px var(--v6-font-sans)', color: 'var(--v6-fg)', marginBottom: 4 }}>
        用户管理 Users
      </h1>
      <div style={{ color: 'var(--v6-fg-muted)', fontSize: 13, marginBottom: 24 }}>
        对系统的注册用户进行生命周期和状态的调度管理 · Manage registered users and account status
      </div>

      <div className="v6-card">
        {/* Search bar */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input
            placeholder="搜索用户… Search user…"
            className="v6-input-global"
            style={{ flex: 1 }}
            value={q}
            onChange={e => setQ(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && load()}
          />
          <button className="v6-btn v6-btn--primary" onClick={load}>查询 Search</button>
        </div>

        {/* Table */}
        <table className="v6-table">
          <thead>
            <tr>
              <th>用户名 Username</th>
              <th>租户 Tenant</th>
              <th>记忆数 Memories</th>
              <th>Token 用量</th>
              <th>状态 Status</th>
              <th>操作 Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--v6-fg-muted)' }}>
                  暂无数据 · No data yet
                </td>
              </tr>
            ) : (
              users.map((u) => {
                const active = isActive(u);
                const isBusy = !!busy[u.user_id];
                return (
                  <tr key={u.user_id}>
                    {/* Username + avatar */}
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                          width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                          background: active ? 'rgba(45,191,168,0.12)' : 'rgba(255,77,109,0.1)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 12, fontWeight: 700,
                          color: active ? '#2DBFA8' : 'var(--v6-danger)',
                        }}>
                          {(u.username?.[0] ?? '?').toUpperCase()}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--v6-fg)' }}>{u.username}</div>
                          {u.api_key_prefix && (
                            <div style={{ fontSize: 10, fontFamily: 'var(--v6-font-mono)', color: 'var(--v6-fg-faint)' }}>
                              {u.api_key_prefix}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>

                    <td className="v6-font-mono" style={{ fontSize: 12 }}>{u.team_id}</td>
                    <td className="v6-font-mono" style={{ fontSize: 12 }}>{u.memory_count?.toLocaleString() ?? 0}</td>
                    <td className="v6-font-mono" style={{ fontSize: 12 }}>{u.token_usage?.toLocaleString() ?? 0}</td>

                    {/* Status — breathing dot */}
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                        <div className={`v6-health-item__dot ${active ? 'v6-health-item__dot--ok' : 'v6-health-item__dot--err'}`} />
                        <span style={{
                          fontSize: 11, fontFamily: 'var(--v6-font-mono)', letterSpacing: '0.05em',
                          color: active ? '#2DBFA8' : 'var(--v6-danger)',
                        }}>
                          {active ? '活跃 Active' : '已暂停 Paused'}
                        </span>
                      </div>
                    </td>

                    {/* Actions */}
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button
                          className={`v6-btn v6-btn--xs ${active ? 'v6-btn--danger' : 'v6-btn--primary'}`}
                          disabled={isBusy || u.username === 'admin'}
                          onClick={() => toggle(u.user_id, active)}
                        >
                          {isBusy ? '…' : active ? '暂停 Suspend' : '激活 Activate'}
                        </button>
                        {u.username !== 'admin' && (
                          <button
                            className="v6-btn v6-btn--ghost v6-btn--xs"
                            style={{ color: 'var(--v6-danger)', borderColor: 'rgba(255,77,109,0.4)' }}
                            disabled={isBusy}
                            onClick={() => remove(u.user_id, u.username)}
                          >
                            {isBusy ? '…' : '删除 Delete'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Footer summary */}
        {users.length > 0 && (
          <div style={{ marginTop: 12, fontSize: 11, fontFamily: 'var(--v6-font-mono)', color: 'var(--v6-fg-faint)', textAlign: 'right' }}>
            共 {users.length} 位用户 · {users.filter(isActive).length} 活跃
          </div>
        )}
      </div>
    </div>
  );
}
