"""Memory OS Agent SDK — Client for AI agents."""
import os, httpx
from typing import Optional
from .types import Memory, SearchResult, GraphResult

class MemoryOSClient:
    """Client for the Memory OS API. Designed for AI agents to use."""
    def __init__(self, base_url: str = None, api_key: str = None, team_id: str = "default"):
        self.base_url = (base_url or os.environ.get("MEMORY_OS_URL", "http://localhost:8000")).rstrip("/")
        self.api_key = api_key or os.environ.get("MEMORY_OS_KEY", "")
        self.team_id = team_id
        self._client = httpx.Client(timeout=30)

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key: h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def store(self, title: str, content: str, category: str = "general", **kw) -> Memory:
        r = self._client.post(f"{self.base_url}/memory/store", json={"title":title,"content":content,"category":category,**kw}, headers=self._headers())
        r.raise_for_status()
        return Memory(**r.json())

    def search(self, query: str, top_k: int = 10, use_rerank: bool = True, **kw) -> list[SearchResult]:
        r = self._client.post(f"{self.base_url}/memory/search", json={"query":query,"top_k":top_k,"use_rerank":use_rerank,**kw}, headers=self._headers())
        r.raise_for_status()
        return [SearchResult(memory=Memory(**sr["memory"]), score=sr["score"], chunk_text=sr.get("chunk_text")) for sr in r.json()]

    def upload(self, file_path: str, category: str = "general") -> dict:
        with open(file_path, "rb") as f:
            r = self._client.post(f"{self.base_url}/memory/upload", files={"file": f}, data={"category":category}, headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})
        r.raise_for_status()
        return r.json()

    def graph(self, memory_id: str = "", max_depth: int = 2, top_k: int = 20) -> GraphResult:
        r = self._client.post(f"{self.base_url}/memory/graph", json={"memory_id":memory_id,"max_depth":max_depth,"top_k":top_k}, headers=self._headers())
        r.raise_for_status()
        return GraphResult(**r.json())

    def longterm(self, top_k: int = 10, min_importance: float = 0.6) -> list[SearchResult]:
        r = self._client.post(f"{self.base_url}/memory/longterm", json={"top_k":top_k,"min_importance":min_importance}, headers=self._headers())
        r.raise_for_status()
        return [SearchResult(memory=Memory(**sr["memory"]), score=sr["score"]) for sr in r.json()]

    def lifecycle(self, memory_id: str, target_stage: str) -> dict:
        r = self._client.post(f"{self.base_url}/memory/lifecycle", json={"memory_id":memory_id,"target_stage":target_stage}, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def reflect(self) -> dict:
        r = self._client.post(f"{self.base_url}/memory/reflect", headers=self._headers())
        r.raise_for_status()
        return r.json()
