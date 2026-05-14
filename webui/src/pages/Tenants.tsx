import { useEffect, useState } from "react";
import { getTenants } from "../api/endpoints";
import { useToast } from "../contexts/ToastContext";
export function TenantsPage(){const{toast}=useToast();const[tenants,setTenants]=useState<{team_id:string;name:string;user_count:number;memory_count:number;active:boolean}[]>([]);useEffect(()=>{getTenants().then(r=>setTenants(r.tenants)).catch(()=>toast("err","err"))},[toast]);return(<div><div className="page-title">租户管理</div><table className="table"><thead><tr><th>ID</th><th>名称</th><th>用户数</th><th>记忆数</th><th>状态</th></tr></thead><tbody>{tenants.map((t,i)=><tr key={i}><td>{t.team_id}</td><td>{t.name}</td><td>{t.user_count}</td><td>{t.memory_count?.toLocaleString()}</td><td>{t.active?"ACTIVE":"PAUSED"}</td></tr>)}</tbody></table></div>)}
