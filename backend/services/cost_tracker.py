# AI Memory OS — Token Cost Tracking
# Records actual token usage across all cloud providers and models.

from __future__ import annotations
import json, time
from pathlib import Path

COST_FILE = Path.home() / ".codex" / "memory-os" / "costs.json"

# Pricing per 1M tokens (USD for OpenAI, CNY for Alibaba/Zhipu)
# Source: official pricing pages (May 2025)
PRICING = {
    # Alibaba DashScope (CNY ¥/1M tokens)
    "text-embedding-v3":     {"input": 0.70,  "output": 0,    "currency": "CNY"},
    "gte-rerank":            {"input": 0.50,  "output": 0,    "currency": "CNY"},
    "qwen-turbo":            {"input": 0.30,  "output": 1.20, "currency": "CNY"},
    "qwen-plus":             {"input": 0.80,  "output": 2.00, "currency": "CNY"},
    # Zhipu AI (CNY ¥/1M tokens)
    "embedding-3":           {"input": 0.50,  "output": 0,    "currency": "CNY"},
    "glm-4-flash":           {"input": 0.10,  "output": 0.10, "currency": "CNY"},
    "glm-4":                 {"input": 100.0, "output": 100.0,"currency": "CNY"},
    # OpenAI (USD $/1M tokens)
    "text-embedding-3-small":{"input": 0.02,  "output": 0,    "currency": "USD"},
    "text-embedding-3-large":{"input": 0.13,  "output": 0,    "currency": "USD"},
    "gpt-4o-mini":           {"input": 0.15,  "output": 0.60, "currency": "USD"},
    "gpt-4o":                {"input": 2.50,  "output": 10.0, "currency": "USD"},
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
        data = json.loads(COST_FILE.read_text()) if COST_FILE.exists() else {
            "total_cost_cny": 0.0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "by_model": {},
            "history": []
        }

        p = PRICING.get(model, {"input": 0, "output": 0, "currency": "USD"})
        cost = (input_tokens * p["input"] + output_tokens * p.get("output", 0)) / 1_000_000
        currency = p.get("currency", "USD")

        # Update totals
        if currency == "CNY":
            data["total_cost_cny"] = round(data.get("total_cost_cny", 0) + cost, 6)
        else:
            data["total_cost_usd"] = round(data.get("total_cost_usd", 0) + cost, 6)
        data["total_tokens"] = data.get("total_tokens", 0) + input_tokens + output_tokens

        # Update per-model breakdown
        m = data["by_model"].setdefault(model, {
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
        base = {
            "total_cost_cny": 0.0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "by_model": {},
            "history": [],
            "daily_trends": {}
        }
        if COST_FILE.exists():
            data = json.loads(COST_FILE.read_text())
            base.update(data)
        
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
