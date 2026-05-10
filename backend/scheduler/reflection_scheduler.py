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
        while True:
            await asyncio.sleep(self.interval * 60)
            try:
                import logging
                log = logging.getLogger(__name__)
                log.info("Scheduled reflection starting...")
                report = await self.engine.reflect_all()
                self.last_run = datetime.now(timezone.utc).isoformat()
                log.info(f"Reflection done: {report}")
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Reflection error: {e}")
