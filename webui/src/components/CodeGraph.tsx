import { useState, useEffect } from 'react';

export function CodeGraph({ token }: { token: string }) {
  const [entities, setEntities] = useState<any[]>([]);
  const [files, setFiles] = useState<any[]>([]);
  const [langs, setLangs] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'entities'|'files'|'langs'>('files');
  const [typeFilter, setTypeFilter] = useState('all');

  const load = () => {
    let url = '/api/code-entities?limit=200';
    if (typeFilter !== 'all') url += '&entity_type=' + encodeURIComponent(typeFilter);
    fetch(url, { headers: { Authorization: 'Bearer ' + token } })
      .then(r => r.json()).then(d => {
        setEntities(d.entities || []);
        setFiles(d.files || []);
        setLangs(d.languages || []);
        setProjects(d.projects || []);
        setLoading(false);
      }).catch(() => setLoading(false));
  };
  useEffect(load, [token, typeFilter]);

  const types = ['all', ...new Set(entities.map((e:any) => e.entity_type))];

  if (loading) return (
    <div className="v6-card"><div className="v6-card__head"><div className="v6-card__title">CodeGraph</div></div>
      <div className="v6-empty" style={{padding:40}}>Loading...</div></div>
  );

  return (
    <div className="v6-card">
      <div className="v6-card__head">
        <div className="v6-card__title">CodeGraph
          <span className="v6-card__title-hint" style={{marginLeft:8}}>
            {entities.length} entities / {files.length} files / {langs.length} langs
          </span>
        </div>
      </div>
      <div className="v6-chips" style={{marginBottom:12}}>
        <button className="v6-chip" aria-current={view==='files'?"page":undefined} onClick={()=>setView('files')}>Files ({files.length})</button>
        <button className="v6-chip" aria-current={view==='entities'?"page":undefined} onClick={()=>setView('entities')}>Entities ({entities.length})</button>
        <button className="v6-chip" aria-current={view==='langs'?"page":undefined} onClick={()=>setView('langs')}>Languages ({langs.length})</button>
      </div>
      {entities.length === 0 ? (
        <div className="v6-empty" style={{padding:30}}>
          <div style={{fontSize:14,fontWeight:600,marginBottom:8}}>No code entities indexed</div>
          <div style={{fontSize:12,color:"var(--v6-fg-muted)",lineHeight:1.6}}>
            Agent use code_index to index your project
          </div>
        </div>
      ) : view === 'files' ? (
        <div style={{maxHeight:480,overflow:"auto"}}>
          {files.map((f:any,i:number)=>(
            <div key={i} className="v6-usage-row">
              <div><span className="v6-tag" style={{marginRight:8}}>{f.language}</span>
                <span style={{fontWeight:500,fontFamily:"var(--v6-font-mono)",fontSize:12}}>{f.file_path}</span></div>
              <span style={{fontSize:11,color:"var(--v6-fg-muted)"}}>{f.ecnt} entities ({f.types})</span>
            </div>
          ))}
        </div>
      ) : view === 'entities'
 ? (
        <>
          <div className="v6-chips" style={{marginBottom:12}}>
            {types.map((t:string)=>(<button key={t} className="v6-chip" aria-current={typeFilter===t?"page":undefined} onClick={()=>setTypeFilter(t)}>{t==="all"?"All":t}</button>))}
          </div>
          <div style={{maxHeight:480,overflow:"auto"}}>
            {entities.slice(0,50).map((e:any,i:number)=>(
              <div key={i} className="v6-usage-row">
                <div><span className="v6-tag" style={{marginRight:8}}>{e.entity_type}</span>
                  <span style={{fontWeight:500,fontFamily:"var(--v6-font-mono)",fontSize:12}}>{e.name}</span></div>
                <span style={{fontSize:11,color:"var(--v6-fg-muted)",fontFamily:"var(--v6-font-mono)"}}>{e.file_path?.split("/").pop()}</span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div style={{maxHeight:480,overflow:"auto"}}>
          {langs.map((l:any,i:number)=>(
            <div key={i} className="v6-usage-row">
              <div><span className="v6-tag" style={{marginRight:8}}>{l.language}</span>
                <span style={{fontWeight:500}}>{l.cnt} entities</span></div>
              <span style={{fontSize:11,color:"var(--v6-fg-muted)"}}>Types: {l.types}</span>
            </div>
          ))}
        </div>
      )}
      {projects.length > 0 && (
        <div className="v6-byok" style={{marginTop:16,fontSize:12}}>
          Projects indexed: {projects.map((p:any)=>(p.project_path||'unknown')).join(', ')}
        </div>
      )}
    </div>
  );
}
