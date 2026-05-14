import { useEffect, useState, useCallback } from 'react';
import { getUsers, toggleUserStatus } from '../api/endpoints';
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
    catch { toast('加载失败', 'err'); }
  }

  return (
    <div>
      <div className='page-title'>用户管理</div>
      <div className='page-sub'>用户管理</div>
      <div className='card'>
        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input placeholder='搜索用户' style={{flex:1,background:'rgba(4,8,16,.85)',border:'1px solid var(--border)',borderRadius:10,padding:'10px 14px',color:'var(--text)',fontSize:12,outline:'none'}} value={q} onChange={e => setQ(e.target.value)} />
          <button className='btn btn-teal' onClick={load}>search</button>
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
                <td><button className={`btn ${u.active !== false ? 'btn-danger' : 'btn-ghost'}`} onClick={() => toggle(u.user_id, u.active !== false)}>{u.active !== false ? '暂停' : '激活'}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
