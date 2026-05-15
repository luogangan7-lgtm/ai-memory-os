import { useEffect, useState } from "react";
import { getTenants } from "../api/endpoints";

export function TenantsPage(){
const[tenants,setTenants]=useState<{team_id:string;name:string;user_count:number;memory_count:number;active:boolean}[]>([]);
const [err,setErr] = useState("");
useEffect(()=>{
  getTenants().then(r=>setTenants(r.tenants||[])).catch(()=>setErr("加载失败 — 后端未连接"));
},[]);
return(<div>
  <div className="page-title">租户管理</div>
  {err&&<div style={{color:"var(--crimson)",marginBottom:16,fontSize:13}}>{err}</div>}
  <div className="card">
    <table className="table">
      <thead><tr><th>ID</th><th>名称</th><th>用户数</th><th>记忆数</th><th>状态</th></tr></thead>
      <tbody>
        {tenants.length===0 && !err && <tr><td colSpan={5} style={{textAlign:"center",padding:40,color:"var(--muted)"}}>暂无数据</td></tr>}
        {tenants.map((t,i)=><tr key={i}><td>{t.team_id}</td><td>{t.name}</td><td>{t.user_count}</td><td>{t.memory_count?.toLocaleString()}</td><td><span className={`badge ${t.active?"badge-emerald":"badge-amber"}`}>{t.active?"活跃":"已暂停"}</span></td></tr>)}
      </tbody>
    </table>
  </div>
</div>)}
