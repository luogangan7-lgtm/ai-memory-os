import { useEffect, useState, useCallback } from 'react';
import { getUsers, toggleUserStatus } from '../api/endpoints';
import { useToast } from '../contexts/ToastContext';

export function UsersPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<{user_id:string;username:string;team_id:string;memory_count:number;token_usage:number;active:boolean}[]>([]);
  const [q, setQ] = useState('');

  const load = useCallback(async () => {
    try { const r = await getUsers(q); setUsers(r.users); }
    catch { toast('err', 'err'); }
  }, [q, toast]);
  useEffect(() => { load(); }, [load]);

  async function toggle(uid: string, active: boolean) {
    try { await toggleUserStatus(uid, active); toast(active ? 'paused' : 'activated'); load(); }
    catch { toast('err', 'err'); }
  }

  return (
    <div>
      <div className='page-title'>USER REGISTRY</div>
      <div className='page-sub'>User management</div>
      <div className='card'>
        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input placeholder='search' value={q} onChange={e => setQ(e.target.value)} />
          <button className='btn btn-cyan' onClick={load}>search</button>
        </div>
        <table className='table'>
          <thead><tr><th>User</th><th>Team</th><th>Memories</th><th>Tokens</th><th>Status</th><th>Action</th></tr></thead>
          <tbody>
            {users.map((u, i) => (
              <tr key={i}>
                <td>{u.username}</td>
                <td>{u.team_id}</td>
                <td>{u.memory_count?.toLocaleString()}</td>
                <td>{u.token_usage?.toLocaleString()}</td>
                <td><span className={`badge ${u.active !== false ? 'badge-emerald' : 'badge-red'}`}>{u.active !== false ? 'ACTIVE' : 'SUSPENDED'}</span></td>
                <td><button className={`btn ${u.active !== false ? 'btn-danger' : 'btn-ghost'}`} onClick={() => toggle(u.user_id, u.active !== false)}>{u.active !== false ? 'Pause' : 'Activate'}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
