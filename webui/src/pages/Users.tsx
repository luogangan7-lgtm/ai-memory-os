import { useEffect, useState, useCallback } from 'react';
import { getUsers, toggleUserStatus, deleteUser } from '../api/endpoints';
import { useToast } from '../contexts/ToastContext';

export function UsersPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<{user_id:string;username:string;team_id:string;memory_count:number;token_usage:number;active:boolean}[]>([]);
  const [q, setQ] = useState('');

  const load = useCallback(async () => {
    try { const r = await getUsers(q); setUsers(r.users); }
    catch { toast('加载失败', 'err'); }
  }, [q, toast]);
  useEffect(() => { load(); }, [load]);

  async function toggle(uid: string, active: boolean) {
    try { await toggleUserStatus(uid, active); toast(active ? '已暂停' : '已激活'); load(); }
    catch { toast('操作失败', 'err'); }
  }

  async function remove(username: string) {
    if (username === 'admin') {
      toast('无法删除系统管理员账号', 'err');
      return;
    }
    if (!window.confirm(`确定要永久删除用户 "${username}" 吗？此操作无法撤销！`)) {
      return;
    }
    try {
      await deleteUser(username);
      toast('用户已成功删除');
      load();
    } catch {
      toast('删除失败', 'err');
    }
  }

  return (
    <div>
      <div className='page-title'>用户管理</div>
      <div className='page-sub'>对系统的注册用户进行生命周期和暂停状态的调度管理</div>
      <div className='card'>
        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input placeholder='搜索用户' style={{flex:1,background:'rgba(4,8,16,.85)',border:'1px solid var(--border)',borderRadius:10,padding:'10px 14px',color:'var(--text)',fontSize:12,outline:'none'}} value={q} onChange={e => setQ(e.target.value)} />
          <button className='btn btn-teal' onClick={load}>搜索</button>
        </div>
        <table className='table'>
          <thead><tr><th>用户名</th><th>租户</th><th>记忆数</th><th>Token</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            {users.map((u, i) => (
              <tr key={i}>
                <td>{u.username}</td>
                <td>{u.team_id}</td>
                <td>{u.memory_count?.toLocaleString()}</td>
                <td>{u.token_usage?.toLocaleString()}</td>
                <td><span className={`badge ${u.active !== false ? 'badge-emerald' : 'badge-red'}`}>{u.active !== false ? '活跃' : '已暂停'}</span></td>
                <td>
                  <button className={`btn ${u.active !== false ? 'btn-danger' : 'btn-ghost'}`} onClick={() => toggle(u.user_id, u.active !== false)}>{u.active !== false ? '暂停' : '激活'}</button>
                  {u.username !== 'admin' && (
                    <button className='btn btn-danger' style={{ marginLeft: 8 }} onClick={() => remove(u.username)}>删除</button>
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
