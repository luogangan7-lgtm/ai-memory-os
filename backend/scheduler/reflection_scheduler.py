# AI Memory OS — Scheduler (built-in asyncio, no external deps)
# Blueprint Section 32

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional


class ReflectionScheduler:
    """Runs reflection periodically in the background."""

    def __init__(self, engine, interval_minutes: int = 60):
        self.engine = engine
        self.interval = interval_minutes
        self._task: Optional[asyncio.Task] = None
        self.last_run: Optional[str] = None

    async def start(self):
        """Start the background reflection loop."""
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self):
        import time
        last_executed = time.time()
        while True:
            await asyncio.sleep(60)
            try:
                from backend.services.config import load_system_config
                sys_config = load_system_config()
                interval_hours = sys_config.get("reflection", {}).get("interval_hours", 24)
            except Exception:
                interval_hours = 24

            if interval_hours <= 0:
                continue

            now = time.time()
            if now - last_executed >= interval_hours * 3600:
                try:
                    import logging
                    log = logging.getLogger(__name__)
                    log.info("Scheduled reflection starting...")
                    from backend.api.db_helper import get_db_conn
                    conn = await get_db_conn()
                    try:
                        rows = await conn.fetch("SELECT DISTINCT team_id FROM memories")
                        teams = [r["team_id"] for r in rows]
                        if "default" not in teams:
                            teams.append("default")
                    finally:
                        await conn.close()

                    for team_id in teams:
                        try:
                            log.info(f"Scheduled reflection running for team: {team_id}")
                            report = await self.engine.reflect_all(team_id)
                            log.info(f"Reflection for team {team_id} done: {report}")
                        except Exception as te:
                            log.error(f"Reflection failed for team {team_id}: {te}")

                    self.last_run = datetime.now(timezone.utc).isoformat()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Scheduled reflection general error: {e}")
                finally:
                    last_executed = time.time()
