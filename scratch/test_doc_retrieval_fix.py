#!/usr/bin/env python3
"""
本地单元测试：验证 4 个 Fix 的逻辑正确性
无需数据库连接，纯 mock 测试
"""
import sys
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, call

sys.path.insert(0, "/Volumes/data/ai-memory-os")


# ──────────────────────────────────────────────
# Test 1: ingestion.py — Qdrant payload 包含 source_type / layer
# ──────────────────────────────────────────────
class TestIngestionPayload(unittest.IsolatedAsyncioTestCase):
    async def test_qdrant_payload_has_source_type_and_layer(self):
        """Fix 1: ingest() 的 Qdrant payload 必须包含 source_type 和 layer"""
        from backend.memory.ingestion import IngestionPipeline, SemanticChunker

        qdrant_mock = MagicMock()
        qdrant_mock.upsert = MagicMock()

        pipeline = IngestionPipeline(qdrant_store=qdrant_mock)

        async def fake_embed(text):
            return [0.1] * 1024

        await pipeline.ingest(
            content="Stagehand 是一个多厂商模型适配框架。它支持 OpenAI、Anthropic 等多个 LLM 提供商。",
            memory_id="test-memory-id-001",
            team_id="luolimoa",
            workspace_id="default",
            embedding_fn=fake_embed,
            title="Stagehand架构方案.md",
            source_type="document",
            layer="DOC",
        )

        assert qdrant_mock.upsert.called, "qdrant.upsert 应该被调用"
        call_kwargs = qdrant_mock.upsert.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")

        assert payload is not None, "payload 不能为 None"
        assert payload.get("source_type") == "document", \
            f"payload.source_type 应为 'document'，实际为 {payload.get('source_type')}"
        assert payload.get("layer") == "DOC", \
            f"payload.layer 应为 'DOC'，实际为 {payload.get('layer')}"
        assert payload.get("workspace_id") == "default", \
            f"payload.workspace_id 应为 'default'，实际为 {payload.get('workspace_id')}"

        print("✅ Test 1 PASSED: Qdrant payload 正确包含 source_type 和 layer")


# ──────────────────────────────────────────────
# Test 2: qdrant_store.py — workspace_id="default" 不加过滤
# ──────────────────────────────────────────────
class TestQdrantWorkspaceFilter(unittest.TestCase):
    def test_default_workspace_skips_filter(self):
        """Fix 3: workspace_id='default' 时 must 列表里不应有 workspace_id 过滤条件"""
        from backend.memory.qdrant_store import QdrantStore
        from qdrant_client import models

        # Mock client 避免真实连接
        with patch("backend.memory.qdrant_store.QdrantClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            # Mock get_collection 避免创建 collection
            mock_client.get_collection = MagicMock(return_value=True)
            mock_client.query_points = MagicMock(return_value=MagicMock(points=[]))

            with patch("backend.memory.qdrant_store.get_bm25", return_value=None):
                store = QdrantStore.__new__(QdrantStore)
                store.client = mock_client
                store._bm25 = None

                # 调用 hybrid_search，workspace_id="default"
                store.hybrid_search(
                    query_vector=[0.1] * 1024,
                    query_text="Stagehand 多厂商适配",
                    team_id="luolimoa",
                    workspace_id="default",
                    top_k=5,
                )

                assert mock_client.query_points.called
                call_args = mock_client.query_points.call_args
                query_filter = call_args.kwargs.get("query_filter")

                # workspace_id="default" 时 filter 应为 None（无任何过滤条件）
                assert query_filter is None, \
                    f"workspace_id='default' 时 query_filter 应为 None，实际为 {query_filter}"

        print("✅ Test 2 PASSED: workspace_id='default' 时不添加 Qdrant 过滤条件")

    def test_custom_workspace_adds_filter(self):
        """workspace_id 非 default 时应正常过滤"""
        from backend.memory.qdrant_store import QdrantStore

        with patch("backend.memory.qdrant_store.QdrantClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_client.get_collection = MagicMock(return_value=True)
            mock_client.query_points = MagicMock(return_value=MagicMock(points=[]))

            with patch("backend.memory.qdrant_store.get_bm25", return_value=None):
                store = QdrantStore.__new__(QdrantStore)
                store.client = mock_client
                store._bm25 = None

                store.hybrid_search(
                    query_vector=[0.1] * 1024,
                    query_text="test",
                    team_id="luolimoa",
                    workspace_id="project-alpha",
                    top_k=5,
                )

                call_args = mock_client.query_points.call_args
                query_filter = call_args.kwargs.get("query_filter")

                # 非 default workspace 时应有 filter
                assert query_filter is not None, \
                    "workspace_id='project-alpha' 时 query_filter 不应为 None"

        print("✅ Test 3 PASSED: 非 default workspace_id 时正常添加过滤条件")


# ──────────────────────────────────────────────
# Test 3: pg_repo.insert() fields 包含 layer
# ──────────────────────────────────────────────
class TestPgRepoInsertFields(unittest.TestCase):
    def test_insert_fields_contains_layer(self):
        """Fix: pg_repo.insert() 的 fields 列表必须包含 'layer'"""
        import inspect
        from backend.memory import pg_repo as pg_module
        source = inspect.getsource(pg_module.MemoryRepo.insert)
        assert '"layer"' in source or "'layer'" in source, \
            "pg_repo.MemoryRepo.insert() 的 fields 列表必须包含 'layer'"
        print("✅ Test 4 PASSED: pg_repo.insert() fields 包含 layer")


# ──────────────────────────────────────────────
# Test 4: routes.py upload_file 传 layer='DOC' 到 ingestion
# ──────────────────────────────────────────────
class TestUploadRoutePassesLayer(unittest.TestCase):
    def _get_upload_function_source(self):
        """从文件中提取 upload_file 函数源码（避免 fastapi import 依赖）"""
        with open("/Volumes/data/ai-memory-os/backend/api/routes.py", "r") as f:
            content = f.read()
        # 提取 upload_file 到 insert_document 之间的代码段
        start = content.find("async def upload_file(")
        end = content.find("\n@router", start + 1)
        return content[start:end] if start != -1 else content

    def test_upload_route_has_layer_doc(self):
        """Fix 2: routes.py 的 upload_file 必须给 ingestion.ingest 传 layer='DOC'"""
        source = self._get_upload_function_source()
        assert 'layer="DOC"' in source or "layer='DOC'" in source, \
            "upload_file() 必须传 layer='DOC' 给 ingestion.ingest()"
        print("✅ Test 5 PASSED: upload_file() 传递 layer='DOC'")

    def test_upload_route_pg_insert_has_layer_doc(self):
        """Fix 2: routes.py 的 pg_repo.insert() 和 ingestion.ingest() 均包含 layer='DOC'"""
        source = self._get_upload_function_source()
        count = source.count('layer="DOC"') + source.count("layer='DOC'")
        assert count >= 2, \
            f"upload_file() 的 pg_repo.insert 和 ingestion.ingest 调用都必须包含 layer='DOC'，实际出现 {count} 次"
        print("✅ Test 6 PASSED: pg_repo.insert() 和 ingestion.ingest() 均传递 layer='DOC'")


if __name__ == "__main__":
    print("=" * 60)
    print("文档检索修复验证测试")
    print("=" * 60)
    unittest.main(verbosity=2)
