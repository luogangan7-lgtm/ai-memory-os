import { useState } from 'react';

export function CodeGraph({ token }: { token: string }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const r = await fetch('/mcp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ method: 'tools/call', params: { name: 'code_search', arguments: { query, limit: 10 } } })
      });
      const d = await r.json();
      const text = d?.result?.content?.[0]?.text || 'No results';
      setResults(text.split('\n').filter(Boolean));
    } catch { setResults([]); }
    setLoading(false);
  };

  return (
    <div className="v6-card" style={{ padding: 20 }}>
      <div className="v6-card__title">Code Graph</div>
      <div style={{ display: 'flex', gap: 8, marginTop: 12, marginBottom: 16 }}>
        <input className="v6-input" style={{ flex: 1 }} value={query} onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()} placeholder="Search functions, classes..." />
        <button className="v6-btn" onClick={search} disabled={loading}>{loading ? '...' : 'Search'}</button>
      </div>
      {results.length > 0 && (
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          {results.map((r, i) => <div key={i} className="v6-list__item" style={{ fontFamily: 'monospace', fontSize: 12, padding: '8px 12px' }}>{r}</div>)}
        </div>
      )}
    </div>
  );
}
