import { useEffect, useState, useCallback } from "react";
import { getAuditLogs } from "../api/endpoints";
import type { AuditLog } from "../api/types";
import { useToast } from "../contexts/ToastContext";
export function AuditLogsPage(){
const{toast}=useToast();
const[logs,setLogs]=useState<AuditLog[]>([]);
const[action,setAction]=useState("");
const[user,setUser]=useState("");
const load=useCallback(async()=>{try{const r=await getAuditLogs(action,user);setLogs(r.logs)}catch{toast("err","err")}},[action,user,toast]);
useEffect(()=>{load()},[load]);
return(<div><div className="page-title">审计日志</div><div className="page-sub">审计日志</div><div className="card">
<div style={{display:"flex",gap:10,marginBottom:16}}>
<select value={action} onChange={e=>setAction(e.target.value)}><option value="">全部操作</option><option value="store">存储记忆</option><option value="delete">删除记忆</option><option value="login">用户登录</option></select>
<input placeholder="搜索用户名..." style={{flex:1,background:"rgba(4,8,16,.85)",border:"1px solid var(--border)",borderRadius:10,padding:"10px 14px",color:"var(--text)",fontSize:12,outline:"none"}} value={user} onChange={e=>setUser(e.target.value)}/>
<button className="btn btn-teal" onClick={load}>search</button></div>
<table className="table"><thead><tr><th>时间</th><th>用户</th><th>租户</th><th>操作</th><th>目标</th><th>IP</th><th>结果</th></tr></thead>
<tbody>{(logs||[]).map((l,i)=>(<tr key={i}><td>{l.created_at||"-"}</td><td>{l.username||"-"}</td><td>{(l.team_id||"").substring(0,12)}</td><td><span className={"badge "+(l.action==="delete"?"badge-red":"badge-emerald")}>{l.action}</span></td><td>{(l.target_id||"").substring(0,12)}</td><td>{l.ip_address||"-"}</td><td><span className={"badge "+(l.success?"badge-emerald":"badge-red")}>{l.success?"OK":"FAIL"}</span></td></tr>))}</tbody></table></div></div>)}
