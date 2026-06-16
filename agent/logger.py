"""
Description: Structured run logger for scripts and workflows.
             Used as a context manager — records start time, end time, duration,
             status, and any extra fields. Writes a JSONL entry to logs/ inside
             the project on exit and streams messages to the console via Python logging.
Source Data: N/A — utility module.
Outputs: fantasy-baseball-agent/logs/{script_name}.jsonl
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).parents[1]


def _log_path() -> Path:
    p = _PROJECT_ROOT / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_console_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                                               datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


class RunLogger:
    """
    Context manager that logs the start and end of a script or workflow run.

    Usage:
        with RunLogger("fetch_rosters_espn_season", year=2026) as log:
            rows = fetch_rosters()
            log.set(rows_fetched=len(rows))

    On exit writes one JSONL line to:
        logs/{name}.jsonl  (inside the project root)

    Fields always present in the log entry:
        script, ts_start, ts_end, duration_s, status, error
    Plus any fields added via log.set().
    """

    def __init__(self, name: str, **init_fields: Any) -> None:
        self.name = name
        self._extra: dict[str, Any] = dict(init_fields)
        self._ts_start: datetime | None = None
        self._logger = get_console_logger(name)

    def set(self, **fields: Any) -> None:
        """Add or update fields that will appear in the log entry."""
        self._extra.update(fields)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)

    def __enter__(self) -> "RunLogger":
        self._ts_start = datetime.now()
        self._logger.info(f"START {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        ts_end = datetime.now()
        duration = round((ts_end - self._ts_start).total_seconds(), 2)
        status = "error" if exc_type else "ok"
        error_msg = str(exc_val) if exc_val else None

        entry = {
            "script":     self.name,
            "ts_start":   self._ts_start.isoformat(timespec="seconds"),
            "ts_end":     ts_end.isoformat(timespec="seconds"),
            "duration_s": duration,
            "status":     status,
            "error":      error_msg,
            **self._extra,
        }

        log_file = _log_path() / f"{self.name}.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            self._logger.warning(f"Failed to write log entry: {e}")

        if exc_type:
            self._logger.error(f"FAILED {self.name} after {duration}s — {error_msg}")
        else:
            summary = "  ".join(f"{k}={v}" for k, v in self._extra.items())
            self._logger.info(f"DONE {self.name} in {duration}s  {summary}")

        return False  # never suppress exceptions
