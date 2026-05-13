import { useEffect, useState } from "react";
import { getLLMEngineConfig, saveLLMEngineConfig, testLLMEngineConfig } from "../api/endpoints";
import type { LLMEngineResponse } from "../api/types";
import { useToast } from "../contexts/ToastContext";
export function LLMEnginePage(){
const{toast}=useToast();
const[cfg,_setCfg]=useState<LLMEngineResponse | null>(null);
void cfg;
const[cp,setCp]=useState("deepseek");
const[cm,setCm]=useState("deepseek-chat");
const[ck,setCk]=useState("");
const[rp,setRp]=useState("deepseek");
const[rm,setRm]=useState("deepseek-reasoner");
const[rk,setRk]=useState("");
useEffect(()=>{getLLMEngineConfig().then(_setCfg)},[]);
async function sc(){try{await saveLLMEngineConfig({engine:"classifier",provider:cp,model:cm,api_key:ck});toast("saved")}catch{toast("err","err")}}
async function sr(){try{await saveLLMEngineConfig({engine:"reflection",provider:rp,model:rm,api_key:rk});toast("saved")}catch{toast("err","err")}}
async function tc(){try{const r=await testLLMEngineConfig({engine:"classifier",provider:cp,model:cm,api_key:ck});toast(r.success?"ok "+r.latency_ms+"ms":"fail")}catch{toast("err","err")}}
return(<div><div className="page-title">LLM ENGINE</div><div className="page-sub">Classifier + Reflection config</div><div className="card"><div className="card-head"><div className="card-title">Classifier</div></div><select value={cp} onChange={e=>setCp(e.target.value)}><option>deepseek</option><option>openai</option><option>alibaba</option></select><input value={cm} onChange={e=>setCm(e.target.value)} placeholder="Model"/><input type="password" value={ck} onChange={e=>setCk(e.target.value)} placeholder="API Key"/><button className="btn btn-cyan" onClick={sc}>Save Classifier</button><button className="btn btn-ghost" onClick={tc}>Test</button></div><div className="card"><div className="card-head"><div className="card-title">Reflection</div></div><select value={rp} onChange={e=>setRp(e.target.value)}><option>deepseek</option><option>openai</option></select><input value={rm} onChange={e=>setRm(e.target.value)} placeholder="Model"/><input type="password" value={rk} onChange={e=>setRk(e.target.value)} placeholder="API Key"/><button className="btn btn-cyan" onClick={sr}>Save Reflection</button></div></div>)}