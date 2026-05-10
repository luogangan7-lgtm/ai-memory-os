# AI Memory OS — Neo4j Graph Client
# Blueprint Section 28 - Neo4j / Section 16 - Knowledge Graph

from __future__ import annotations

from typing import Any, Optional

from neo4j import GraphDatabase


class GraphStore:
    """Knowledge graph wrapper for memory relations."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def create_memory_node(
        self, memory_id: str, title: str, category: str, memory_type: str
    ) -> None:
        query = """
        MERGE (m:Memory {id: $id})
        SET m.title = $title, m.category = $category, m.memory_type = $memory_type
        """
        with self.driver.session() as session:
            session.run(
                query,
                id=memory_id, title=title,
                category=category, memory_type=memory_type,
            )

    def create_relation(
        self, source_id: str, target_id: str,
        relation_type: str, weight: float = 1.0,
    ) -> None:
        query = """
        MATCH (a:Memory {id: $source_id})
        MATCH (b:Memory {id: $target_id})
        MERGE (a)-[r:RELATES {type: $relation_type}]->(b)
        SET r.weight = $weight
        """
        with self.driver.session() as session:
            session.run(
                query,
                source_id=source_id, target_id=target_id,
                relation_type=relation_type, weight=weight,
            )

    def get_relations(
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

        with self.driver.session() as session:
            result = session.run(query, **params)
            for record in result:
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

    def find_related(
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
        with self.driver.session() as session:
            result = session.run(query, ids=memory_ids, top_k=top_k)
            return [
                {
                    "source": record["source"],
                    "target": record["target"],
                    "relation_type": record["relation_type"],
                    "weight": record["weight"],
                }
                for record in result
            ]

    def delete_memory_node(self, memory_id: str) -> None:
        with self.driver.session() as session:
            session.run(
                "MATCH (m:Memory {id: $id}) DETACH DELETE m",
                id=memory_id,
            )
