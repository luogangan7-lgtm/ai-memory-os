# AI Memory OS — Memory Lifecycle Engine
# Blueprint Section 12: Recent → Working → Long-term → Core

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional


class LifecycleStage(StrEnum):
    RECENT = "recent"
    WORKING = "working"
    LONGTERM = "longterm"
    CORE = "core"


# Stage transition rules
TRANSITION_RULES = {
    LifecycleStage.RECENT: {
        LifecycleStage.WORKING: lambda m: (
            m.get("access_count", 0) >= 3
            or m.get("importance", 0) >= 0.6
        ),
    },
    LifecycleStage.WORKING: {
        LifecycleStage.LONGTERM: lambda m: (
            m.get("access_count", 0) >= 10
            or m.get("importance", 0) >= 0.8
        ),
        LifecycleStage.RECENT: lambda m: (
            m.get("freshness", 1.0) < 0.2
            and m.get("importance", 0) < 0.5
        ),
    },
    LifecycleStage.LONGTERM: {
        LifecycleStage.CORE: lambda m: (
            m.get("confidence", 0) >= 0.9
            and m.get("importance", 0) >= 0.9
        ),
        LifecycleStage.WORKING: lambda m: (
            m.get("freshness", 1.0) < 0.1
            and m.get("access_count", 0) < 5
        ),
    },
}


def compute_freshness(memory: dict[str, Any]) -> float:
    """Decay freshness based on age. Halves every 7 days."""
    created = memory.get("created_at")
    if created is None:
        return 1.0
    if isinstance(created, str):
        created = datetime.fromisoformat(created.replace("Z", "+00:00"))
    age_days = (datetime.now(timezone.utc) - created).total_seconds() / 86400.0
    return max(0.0, 1.0 * (0.5 ** (age_days / 7.0)))


def compute_next_stage(memory: dict[str, Any], current: str) -> LifecycleStage:
    """Determine the next lifecycle stage based on metrics."""
    try:
        stage = LifecycleStage(current)
    except ValueError:
        stage = LifecycleStage.RECENT

    # Always re-evaluate from RECENT upward
    m = dict(memory)
    m["freshness"] = compute_freshness(memory)

    # Check promotions first
    for target in (LifecycleStage.CORE, LifecycleStage.LONGTERM, LifecycleStage.WORKING):
        if target.value > stage.value:
            for src, rules in TRANSITION_RULES.items():
                if target in rules and rules[target](m):
                    return target

    # Check demotions
    for target in (LifecycleStage.RECENT, LifecycleStage.WORKING):
        if target.value < stage.value:
            if stage in TRANSITION_RULES and target in TRANSITION_RULES[stage]:
                if TRANSITION_RULES[stage][target](m):
                    return target

    return stage
