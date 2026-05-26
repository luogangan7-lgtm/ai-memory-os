# AI Memory OS — Token Cost Tracking
# Records actual token usage across all cloud providers and models.

from __future__ import annotations
import json, time
from pathlib import Path
from typing import Any

COST_FILE = Path.home() / ".codex" / "memory-os" / "costs.json"

# Pricing per 1M tokens (USD for OpenAI, CNY for Alibaba/Zhipu)
# Source: official pricing pages (May 2025)
PRICING = {
    # Alibaba DashScope (CNY ¥/1M tokens)
    "text-embedding-v3":     {"input": 0.70,  "output": 0,    "currency": "CNY"},
    "qwen3-rerank":          {"input": 0.50,  "output": 0,    "currency": "CNY"},
    "qwen-turbo":            {"input": 0.30,  "output": 1.20, "currency": "CNY"},
    "qwen-plus":             {"input": 0.80,  "output": 2.00, "currency": "CNY"},
    "qwen3.6-plus":          {"input": 0.80,  "output": 0.80, "currency": "CNY"},
    "qwen3.6-flash":         {"input": 0.20,  "output": 0.20, "currency": "CNY"},
    "qwen3.6-max-preview":   {"input": 2.50,  "output": 2.50, "currency": "CNY"},
    "qwen3.5-omni-plus":     {"input": 0.50,  "output": 0.50, "currency": "CNY"},
    "qwen-flash":            {"input": 0.00,  "output": 0.00, "currency": "CNY"},
    
    # Zhipu AI (CNY ¥/1M tokens)
    "embedding-3":           {"input": 0.10,  "output": 0,    "currency": "CNY"},
    "glm-4-flash":           {"input": 0.00,  "output": 0.00, "currency": "CNY"},
    "glm-4-flash-250414":    {"input": 0.00,  "output": 0.00, "currency": "CNY"},
    "glm-4.7-flash":         {"input": 0.00,  "output": 0.00, "currency": "CNY"},
    "glm-4.7":               {"input": 0.00,  "output": 0.00, "currency": "CNY"},
    "glm-5":                 {"input": 2.00,  "output": 2.00, "currency": "CNY"},
    "glm-5.1":               {"input": 1.00,  "output": 1.00, "currency": "CNY"},
    "glm-4-plus":            {"input": 2.00,  "output": 2.00, "currency": "CNY"},
    "glm-4-air":             {"input": 1.00,  "output": 1.00, "currency": "CNY"},
    "glm-4-long":            {"input": 1.00,  "output": 1.00, "currency": "CNY"},
    "glm-5v-turbo":          {"input": 1.00,  "output": 1.00, "currency": "CNY"},
    "glm-5-turbo":           {"input": 0.50,  "output": 0.50, "currency": "CNY"},
    "glm-4-rerank":          {"input": 0.50,  "output": 0,    "currency": "CNY"},
    
    # OpenAI (USD $/1M tokens)
    "text-embedding-3-small":{"input": 0.02,  "output": 0,    "currency": "USD"},
    "text-embedding-3-large":{"input": 0.13,  "output": 0,    "currency": "USD"},
    "gpt-4o-mini":           {"input": 0.15,  "output": 0.60, "currency": "USD"},
    "gpt-4o":                {"input": 2.50,  "output": 10.0, "currency": "USD"},
    "gpt-5.5":               {"input": 5.00,  "output": 15.0, "currency": "USD"},
    "gpt-5.5-pro":           {"input": 10.0,  "output": 30.0, "currency": "USD"},
    "gpt-5.4":               {"input": 2.00,  "output": 6.00, "currency": "USD"},
    "gpt-5.4-mini":          {"input": 0.10,  "output": 0.40, "currency": "USD"},
    "o1":                    {"input": 15.0,  "output": 15.0, "currency": "USD"},
    "o3-mini":               {"input": 1.10,  "output": 1.10, "currency": "USD"},

    # DeepSeek (CNY ¥/1M tokens)
    "deepseek-v4-flash":     {"input": 1.00,  "output": 1.00, "currency": "CNY"},
    "deepseek-v4-pro":       {"input": 4.00,  "output": 4.00, "currency": "CNY"},
    "deepseek-chat":         {"input": 1.99,  "output": 1.99, "currency": "CNY"},
    "deepseek-reasoner":     {"input": 4.00,  "output": 4.00, "currency": "CNY"},

    # Moonshot (CNY ¥/1M tokens)
    "kimi-latest":           {"input": 1.20,  "output": 1.20, "currency": "CNY"},
    "kimi-k2.5":             {"input": 2.40,  "output": 2.40, "currency": "CNY"},
    "moonshot-v1-8k":        {"input": 1.20,  "output": 1.20, "currency": "CNY"},
    "moonshot-v1-32k":       {"input": 2.40,  "output": 2.40, "currency": "CNY"},
    "moonshot-v1-128k":      {"input": 8.00,  "output": 8.00, "currency": "CNY"},

    # MiniMax (CNY ¥/1M tokens)
    "MiniMax-M2.7":          {"input": 1.00,  "output": 1.00, "currency": "CNY"},
    "MiniMax-M2.5":          {"input": 0.50,  "output": 0.50, "currency": "CNY"},
    "MiniMax-M2.7-highspeed":{"input": 0.10,  "output": 0.10, "currency": "CNY"},
    "MiniMax-M2":            {"input": 0.80,  "output": 0.80, "currency": "CNY"},

    # Doubao (CNY ¥/1M tokens)
    "doubao-seed-2-0-pro-260215": {"input": 0.80, "output": 0.80, "currency": "CNY"},
    "doubao-seed-2-0-lite-260215": {"input": 0.30, "output": 0.30, "currency": "CNY"},
    "doubao-1-5-pro-32k":    {"input": 0.80,  "output": 0.80, "currency": "CNY"},
    "doubao-1-5-lite-32k":   {"input": 0.30,  "output": 0.30, "currency": "CNY"},
    "doubao-embedding":      {"input": 0.10,  "output": 0,    "currency": "CNY"},

    # Baidu Ernie (CNY ¥/1M tokens)
    "ernie-4.5-8k":          {"input": 1.60,  "output": 1.60, "currency": "CNY"},
    "ernie-4.5-turbo-8k":    {"input": 0.80,  "output": 0.80, "currency": "CNY"},
    "ernie-lite-8k":         {"input": 0.00,  "output": 0.00, "currency": "CNY"},
    "bce-embedding-v1":      {"input": 0.50,  "output": 0,    "currency": "CNY"},
    "bce-reranker-base_v1":  {"input": 0.50,  "output": 0,    "currency": "CNY"},

    # Tencent Hunyuan (CNY ¥/1M tokens)
    "hunyuan-2.0-thinking":  {"input": 1.00,  "output": 1.00, "currency": "CNY"},
    "hunyuan-2.0-instruct":  {"input": 1.00,  "output": 1.00, "currency": "CNY"},
    "hunyuan-turbos-latest": {"input": 0.80,  "output": 0.80, "currency": "CNY"},
    "hunyuan-turbos":        {"input": 0.80,  "output": 0.80, "currency": "CNY"},
    "hunyuan-lite":          {"input": 0.00,  "output": 0.00, "currency": "CNY"},
    "hunyuan-embedding":     {"input": 0.70,  "output": 0,    "currency": "CNY"},

    # SiliconFlow (CNY ¥/1M tokens)
    "BAAI/bge-m3":           {"input": 0.10,  "output": 0,    "currency": "CNY"},
    "BAAI/bge-large-zh-v1.5":{"input": 0.10,  "output": 0,    "currency": "CNY"},
    "BAAI/bge-reranker-v2-m3":{"input": 0.20, "output": 0,    "currency": "CNY"},
    "deepseek-ai/DeepSeek-V3":{"input": 1.00,  "output": 1.00, "currency": "CNY"},
    "Qwen/Qwen2.5-7B-Instruct":{"input": 0.00, "output": 0.00, "currency": "CNY"},
    "THUDM/glm-4-9b-chat":   {"input": 0.00,  "output": 0.00, "currency": "CNY"},
    "internlm/internlm2_5-7b-chat":{"input": 0.00, "output": 0.00, "currency": "CNY"},
    "meta-llama/Meta-Llama-3.1-8B-Instruct":{"input": 0.00, "output": 0.00, "currency": "CNY"},

    # Jina AI (USD $/1M tokens)
    "jina-embeddings-v3":    {"input": 0.02,  "output": 0,    "currency": "USD"},
    "jina-reranker-v2-base-multilingual": {"input": 0.02, "output": 0, "currency": "USD"},
}


class CostTracker:
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for a string (handles CJK characters)."""
        cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        return int(cjk / 1.5 + (len(text) - cjk) / 4.0)

    @staticmethod
    def record(model: str, input_tokens: int, output_tokens: int = 0, provider: str = "") -> None:
        """Record token usage and compute cost for a model call."""
        COST_FILE.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = json.loads(COST_FILE.read_text()) if COST_FILE.exists() else {
            "total_cost_cny": 0.0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "by_model": {},
            "history": []
        }

        p: dict[str, Any] = PRICING.get(model, {"input": 0.0, "output": 0.0, "currency": "USD"})
        cost = (input_tokens * float(p["input"]) + output_tokens * float(p.get("output", 0.0))) / 1_000_000
        currency = p.get("currency", "USD")

        # Update totals
        if currency == "CNY":
            data["total_cost_cny"] = round(data.get("total_cost_cny", 0) + cost, 6)
        else:
            data["total_cost_usd"] = round(data.get("total_cost_usd", 0) + cost, 6)
        data["total_tokens"] = data.get("total_tokens", 0) + input_tokens + output_tokens

        # Update per-model breakdown
        m: dict[str, Any] = data["by_model"].setdefault(model, {
            "input_tokens": 0, "output_tokens": 0,
            "total_cost": 0.0, "calls": 0, "currency": currency
        })
        m["input_tokens"] += input_tokens
        m["output_tokens"] += output_tokens
        m["total_cost"] = round(m["total_cost"] + cost, 6)
        m["calls"] += 1

        # Keep last 1000 history entries to ensure charts have data even for busy days
        data.setdefault("history", []).append({
            "ts": int(time.time()),
            "model": model,
            "provider": provider or model.split("-")[0],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": round(cost, 8),
            "currency": currency
        })
        data["history"] = data["history"][-1000:]

        COST_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @staticmethod
    def summary() -> dict:
        base: dict[str, Any] = {
            "total_cost_cny": 0.0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "by_model": {},
            "history": [],
            "daily_trends": {}
        }
        if COST_FILE.exists():
            data_loaded: dict[str, Any] = json.loads(COST_FILE.read_text())
            base.update(data_loaded)
        
        # Compute daily trends from history (last 14 days)
        trends = {}
        now = int(time.time())
        # init last 14 days
        for i in range(14):
            d = time.strftime("%Y-%m-%d", time.localtime(now - (13-i)*86400))
            trends[d] = 0
            
        for h in base.get("history", []):
            d = time.strftime("%Y-%m-%d", time.localtime(h["ts"]))
            if d in trends:
                trends[d] += (h.get("input_tokens", 0) + h.get("output_tokens", 0))
        
        base["daily_trends"] = trends
        return base

    # Legacy compat
    @staticmethod
    def estimate(text: str) -> int:
        return CostTracker.estimate_tokens(text)
