# AI Memory OS — Neo4j Graph Client
# Blueprint Section 28 - Neo4j / Section 16 - Knowledge Graph

from __future__ import annotations

from typing import Any, Optional

from neo4j import AsyncGraphDatabase


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
