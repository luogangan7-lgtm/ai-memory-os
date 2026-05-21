export class MemoryOSClient {
  constructor({ token, server }) {
    this.token  = token;
    this.server = server.replace(/\/$/, '');
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'User-Agent': 'ai-memory-os-mcp/1.0',
    };
  }
  async request(method, path, body = null) {
    const url = `${this.server}${path}`;
    const opts = { method, headers: this.headers, signal: AbortSignal.timeout(15000) };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    if (!res.ok) { const err = await res.text().catch(() => res.statusText); throw new Error(`Memory OS API Error ${res.status}: ${err}`); }
    return res.json();
  }
  search({ query, limit = 5, filter_type = 'all' }) { return this.request('POST', '/memory/search', { query, limit, source_type: filter_type === 'all' ? undefined : filter_type }); }
  store({ content, title, tags = [], importance = 'normal' }) { 
    const imp = { 'low': 0.25, 'normal': 0.5, 'high': 0.85, 'critical': 1.0 }[importance] ?? importance;
    return this.request('POST', '/memory/store', { content, title, tags, importance: imp, source_type: 'agent' }); 
  }
  list({ limit = 10, offset = 0 }) { return this.request('GET', `/memory/recent?limit=${limit}&offset=${offset}`); }
  delete({ memory_id }) { return this.request('DELETE', `/memory/${memory_id}`); }
  status() { return this.request('GET', '/stats'); }
  getPersona() { return this.request('GET', '/persona/default'); }
  reflect() { return this.request('POST', '/memory/reflect'); }
  getCanvas({ task_id = 'main', agent_id = 'default' }) { 
    return this.request('GET', `/canvas/${task_id}`).then(arr => {
      if (!Array.isArray(arr)) return arr;
      return arr.find(x => x.agent_id === agent_id) || null;
    }); 
  }
  updateCanvas({ task_id = 'main', agent_id = 'default', mermaid, title = '', completed = [], next = [] }) { 
    return this.request('POST', `/canvas/${task_id}`, { agent_id, mermaid, title, completed, next }); 
  }
}
