import lancedb
import pandas as pd
import os
from pathlib import Path

class LanceDBStore:
    def __init__(self, uri: str = None):
        if not uri:
            db_dir = Path.home() / ".codex" / "memory-os" / "lancedb"
            db_dir.mkdir(parents=True, exist_ok=True)
            uri = str(db_dir)
        self.db = lancedb.connect(uri)
        self.table_name = "memories"

    async def ingest(self, content, memory_id, team_id, workspace_id, embedding_fn, **kw):
        vector = await embedding_fn(content)
        data = [{
            "vector": vector,
            "id": memory_id,
            "text": content,
            "team_id": team_id,
            "workspace_id": workspace_id,
            "title": kw.get("title", ""),
            "category": kw.get("category", ""),
            "memory_type": kw.get("memory_type", "general"),
            "agent_id": kw.get("agent_id", "default"),
            "importance": float(kw.get("importance", 0.5)),
            "metadata": str(kw.get("metadata", {}))
        }]
        
        if self.table_name in self.db.table_names():
            table = self.db.open_table(self.table_name)
            table.add(data)
        else:
            self.db.create_table(self.table_name, data=data)

    async def search(self, query_vector, team_id, top_k=5, **kw):
        if self.table_name not in self.db.table_names():
            return []
        
        table = self.db.open_table(self.table_name)
        results = table.search(query_vector).where(f"team_id = '{team_id}'").limit(top_k).to_list()
        
        # Format results to match Qdrant output structure
        formatted = []
        for r in results:
            formatted.append({
                "id": r["id"],
                "score": 1.0 - r.get("_distance", 0), # Simple conversion
                "payload": {
                    "text": r["text"],
                    "title": r["title"],
                    "category": r["category"],
                    "memory_id": r["id"],
                    "importance": r["importance"],
                    "tags": []
                }
            })
        return formatted

    async def delete(self, memory_id, team_id):
        if self.table_name not in self.db.table_names():
            return False
        table = self.db.open_table(self.table_name)
        table.delete(f"id = '{memory_id}' AND team_id = '{team_id}'")
        return True
