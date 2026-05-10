# AI Memory OS - Structured Logging (Section 35)
from __future__ import annotations
import logging, json, sys, time, os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }, default=str)

def setup_logging(level: str = "INFO", log_file: str = None):
    if log_file is None:
        log_dir = Path(os.environ.get("MEMORY_OS_LOG_DIR", str(Path.home() / ".codex" / "memory-os" / "logs")))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(log_dir / "app.log")
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(JSONFormatter())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.addHandler(file_handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").addHandler(handler)
