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
return(<div><div className="page-title">AUDIT TRAIL</div><div className="page-sub">audit logs</div><div className="card">
<div style={{display:"flex",gap:10,marginBottom:16}}>
<select value={action} onChange={e=>setAction(e.target.value)}><option value="">all</option><option value="store">store</option><option value="delete">delete</option><option value="login">login</option></select>
<input placeholder="user" value={user} onChange={e=>setUser(e.target.value)}/>
<button className="btn btn-cyan" onClick={load}>search</button></div>
<table className="table"><thead><tr><th>time</th><th>user</th><th>team</th><th>action</th><th>target</th><th>ip</th><th>result</th></tr></thead>
<tbody>{(logs||[]).map((l,i)=>(<tr key={i}><td>{l.created_at||"-"}</td><td>{l.username||"-"}</td><td>{(l.team_id||"").substring(0,12)}</td><td><span className={"badge "+(l.action==="delete"?"badge-red":"badge-emerald")}>{l.action}</span></td><td>{(l.target_id||"").substring(0,12)}</td><td>{l.ip_address||"-"}</td><td><span className={"badge "+(l.success?"badge-emerald":"badge-red")}>{l.success?"OK":"FAIL"}</span></td></tr>))}</tbody></table></div></div>)}
