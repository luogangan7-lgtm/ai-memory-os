# AI Memory OS — Neo4j Graph Client
# Blueprint Section 28 - Neo4j / Section 16 - Knowledge Graph

from __future__ import annotations

from typing import Any, Optional

from neo4j import AsyncGraphDatabase



SEMANTIC_RELATIONS = {
    "CAUSED_BY", "CONTRADICTS", "SUPPORTS", "PRECEDES",
    "GENERALIZES", "SPECIALIZES", "DERIVED_FROM", "REQUIRES",
    "SUPERSEDES", "HAS_SKILL"
}

class GraphStore:
    """Knowledge graph wrapper for memory relations."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
    ):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self) -> None:
        await self.driver.close()

    async def setup_indexes(self) -> None:
        """Create critical unique constraints/indexes to prevent full node scans."""
        query = "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE"
        async with self.driver.session() as session:
            try:
                await session.run(query)
                import logging
                logging.getLogger("graph_store").info("Neo4j unique constraint on Memory(id) verified.")
            except Exception as e:
                import logging
                logging.getLogger("graph_store").warning(f"Could not setup Neo4j constraint: {e}")

    async def create_memory_node(
        self, memory_id: str, title: str, category: str, memory_type: str
    ) -> None:
        query = """
        MERGE (m:Memory {id: $id})
        SET m.title = $title, m.category = $category, m.memory_type = $memory_type
        """
        async with self.driver.session() as session:
            await session.run(
                query,
                id=memory_id, title=title,
                category=category, memory_type=memory_type,
            )


    async def create_semantic_relation(self, source_id: str, target_id: str, relation_type: str, team_id: str = "default", confidence: float = 1.0):
        """Create a typed semantic relation (CAUSED_BY, SUPPORTS, etc). Falls back to RELATES if unknown type."""
        if relation_type not in SEMANTIC_RELATIONS:
            relation_type = "RELATES"
        async with self.driver.session() as session:
            await session.run(f"""
                MATCH (a:Memory {{id: $source_id}})
                MATCH (b:Memory {{id: $target_id}})
                MERGE (a)-[r:{relation_type}]->(b)
                SET r.confidence = $confidence, r.created_at = datetime()
            """, source_id=source_id, target_id=target_id, confidence=confidence)

    async def create_relation(
        self, source_id: str, target_id: str,
        relation_type: str, weight: float = 1.0,
    ) -> None:
        query = """
        MATCH (a:Memory {id: $source_id})
        MATCH (b:Memory {id: $target_id})
        MERGE (a)-[r:RELATES {type: $relation_type}]->(b)
        SET r.weight = $weight
        """
        async with self.driver.session() as session:
            await session.run(
                query,
                source_id=source_id, target_id=target_id,
                relation_type=relation_type, weight=weight,
            )


    async def get_stats(self) -> dict[str, int]:
        """Return total count of nodes and relationships in Neo4j."""
        async with self.driver.session() as session:
            nodes_result = await session.run("MATCH (n) RETURN count(n) AS cnt")
            nodes_rec = await nodes_result.single()
            nodes = nodes_rec["cnt"] if nodes_rec else 0
            edges_result = await session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
            edges_rec = await edges_result.single()
            edges = edges_rec["cnt"] if edges_rec else 0
            return {"nodes": nodes, "edges": edges}


    async def get_full_graph(self, limit: int = 200) -> dict[str, list]:
        """Return all nodes and edges for knowledge graph visualization."""
        async with self.driver.session() as session:
            nodes_result = await session.run(
                "MATCH (n) RETURN n LIMIT $limit", limit=limit)
            nodes = []
            node_ids = set()
            async for record in nodes_result:
                n = record["n"]
                node_data = dict(n.items())
                node_data["id"] = n.element_id
                nodes.append(node_data)
                node_ids.add(n.element_id)
            
            edges_result = await session.run(
                "MATCH (a)-[r]->(b) WHERE elementId(a) IN $ids AND elementId(b) IN $ids RETURN elementId(a) AS source, elementId(b) AS target, type(r) AS rel_type LIMIT 500",
                ids=list(node_ids))
            edges = []
            async for record in edges_result:
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "label": record["rel_type"]
                })
            return {"nodes": nodes, "edges": edges}

    async def get_relations(
        self, memory_id: str,
        relation_types: Optional[list[str]] = None,
        max_depth: int = 2, top_k: int = 20,
    ) -> dict[str, Any]:
        nodes_set: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []

        params: dict[str, Any] = {
            "id": memory_id, "max_depth": max_depth, "top_k": top_k
        }
        rel_filter = ""
        if relation_types:
            rel_filter = "WHERE type(r) IN $relation_types"
            params["relation_types"] = relation_types

        depth = params.pop("max_depth")
        top = params.pop("top_k")
        query = f"""
        MATCH (m:Memory {{id: $id}})-[r*1..{depth}]-(related:Memory)
        {rel_filter}
        RETURN m, r, related
        LIMIT {top}
        """

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            async for record in result:
                for n in (record["m"], record["related"]):
                    if n["id"] not in nodes_set:
                        nodes_set[n["id"]] = {
                            "id": n["id"],
                            "title": n.get("title", ""),
                            "category": n.get("category", ""),
                            "memory_type": n.get("memory_type", ""),
                        }
                for rel in record["r"]:
                    edges.append({
                        "source": rel.start_node["id"],
                        "target": rel.end_node["id"],
                        "relation_type": rel.get("type", "RELATES"),
                        "weight": rel.get("weight", 1.0),
                    })

        return {"nodes": list(nodes_set.values()), "edges": edges}

    async def find_related(
        self, memory_ids: list[str], top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Find relations between a set of memory IDs."""
        if not memory_ids:
            return []
        query = """
        MATCH (a:Memory)-[r:RELATES]-(b:Memory)
        WHERE a.id IN $ids AND b.id IN $ids AND a.id < b.id
        RETURN a.id AS source, b.id AS target,
               r.type AS relation_type, r.weight AS weight
        LIMIT $top_k
        """
        async with self.driver.session() as session:
            result = await session.run(query, ids=memory_ids, top_k=top_k)
            return [
                {
                    "source": record["source"],
                    "target": record["target"],
                    "relation_type": record["relation_type"],
                    "weight": record["weight"],
                }
                async for record in result
            ]

    async def delete_memory_node(self, memory_id: str) -> None:
        async with self.driver.session() as session:
            await session.run(
                "MATCH (m:Memory {id: $id}) DETACH DELETE m",
                id=memory_id,
            )

    async def ingest_code_entity(self, entity_id: str, name: str, entity_type: str, file_path: str, team_id: str = "default", qualified_name: str = "") -> None:
        query = """
        MERGE (c:Code {id: $id})
        SET c.name = $name, c.entity_type = $entity_type, c.file_path = $file_path, c.team_id = $team_id, c.qualified_name = $qualified_name, c.indexed_at = datetime()
        """
        async with self.driver.session() as session:
            await session.run(
                query,
                id=entity_id, name=name,
                entity_type=entity_type, file_path=file_path, team_id=team_id,
                qualified_name=qualified_name
            )

    async def create_code_relation(self, source_id: str, target_id: str, relation_type: str) -> None:
        import re
        rel_type = relation_type.upper()
        if not re.match(r"^[A-Z0-9_]+$", rel_type):
            rel_type = "DEPENDS_ON"
        async with self.driver.session() as session:
            await session.run(f"""
                MATCH (a {{id: $source_id}})
                MATCH (b {{id: $target_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r.created_at = datetime()
            """, source_id=source_id, target_id=target_id)

    async def find_contradictions(self, team_id: str = "default") -> list[dict[str, Any]]:
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (a:Memory)-[r:CONTRADICTS]-(b:Memory)
                WHERE a.id < b.id
                RETURN a.id AS source, b.id AS target, a.title AS source_title, b.title AS target_title
            """)
            return [
                {
                    "source": record["source"],
                    "target": record["target"],
                    "source_title": record["source_title"],
                    "target_title": record["target_title"]
                }
                async for record in result
            ]

