import { useEffect, useState } from "react";
import { getMonitoring } from "../api/endpoints";
import { useToast } from "../contexts/ToastContext";
export function MonitoringPage(){
const{toast}=useToast();
const[d,_setD]=useState<{token_values?:number[]}|null>(null);
useEffect(()=>{getMonitoring().then(_setD).catch(()=>toast("err","err"))},[toast]);
const vals:number[]=d?.token_values||[];
return(<div><div className="page-title">遥测监控</div><div className="page-sub">Token usage and latency</div>
<div className="stats-grid"><div className="stat-card amber"><div className="stat-label">总 Token 用量</div><div className="stat-value">{vals.reduce((a:number,b:number)=>a+b,0).toLocaleString()}</div></div></div></div>)}
