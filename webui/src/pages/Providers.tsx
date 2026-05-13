import { useState } from "react";
import { saveEmbedConfig, saveRerankConfig, detectLocalModels } from "../api/endpoints";
import { useToast } from "../contexts/ToastContext";
export function ProvidersPage(){
const{toast}=useToast();
const[ep,setEp]=useState("alibaba");
const[ek,setEk]=useState("");
const[em,setEm]=useState("text-embedding-v3");
const[eb,setEb]=useState("");
const[rp,setRp]=useState("alibaba");
const[rk,setRk]=useState("");
const[rm,setRm]=useState("gte-rerank");
const[rt,setRt]=useState(0.3);
const[lr,setLr]=useState("");
async function se(){try{await saveEmbedConfig({provider:ep,api_key:ek,model:em,base_url:eb});toast("saved")}catch{toast("err","err")}}
async function sr(){try{await saveRerankConfig({provider:rp,api_key:rk,model:rm,threshold:rt});toast("saved")}catch{toast("err","err")}}
async function dl(){setLr("scanning");try{const r=await detectLocalModels();setLr(r.detected?.length?r.detected.map(m=>m.name).join(", "):"none")}catch{setLr("failed")}}
return(<div><div className="page-title">SYSTEM COMPUTE</div><div className="page-sub">Embedding + Rerank</div>
<div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:18}}>
<div className="card"><div className="card-head"><div className="card-title">Embedding</div></div>
<select value={ep} onChange={e=>setEp(e.target.value)}><option>alibaba</option><option>openai</option></select>
<input type="password" value={ek} onChange={e=>setEk(e.target.value)} placeholder="API Key"/>
<input value={em} onChange={e=>setEm(e.target.value)} placeholder="Model"/>
<input value={eb} onChange={e=>setEb(e.target.value)} placeholder="Base URL"/>
<button className="btn btn-cyan" onClick={se}>Save</button></div>
<div className="card"><div className="card-head"><div className="card-title">Rerank</div></div>
<select value={rp} onChange={e=>setRp(e.target.value)}><option>alibaba</option><option>cohere</option></select>
<input type="password" value={rk} onChange={e=>setRk(e.target.value)} placeholder="API Key"/>
<input value={rm} onChange={e=>setRm(e.target.value)} placeholder="Model"/>
<label>Threshold: {rt}</label>
<input type="range" min={0} max={1} step={0.05} value={rt} onChange={e=>setRt(+e.target.value)}/>
<button className="btn btn-cyan" onClick={sr}>Save</button></div></div>
<div className="card"><div className="card-head"><div className="card-title">Local Models</div><button className="btn btn-ghost" onClick={dl}>Scan</button></div><p>{lr}</p></div></div>)}
