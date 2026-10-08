"""Logging in one shape across the service: a timestamp, a level, a component and key=value fields."""

from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s.%(msecs)03d %(levelname)-5s %(name)-8s %(message)s"
_DATE = "%H:%M:%S"
_configured = False


class _ComponentFormatter(logging.Formatter):
    """Print the component, not the dotted logger name, so a line reads `worker  job start ...`."""

    def format(self, record: logging.LogRecord) -> str:
        record.name = record.name.rsplit(".", 1)[-1]
        return super().format(record)


def get_logger(component: str) -> logging.Logger:
    """Get the logger for one component: worker, github, packer, provider, ledger, cache."""
    global _configured
    if not _configured:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_ComponentFormatter(_FORMAT, datefmt=_DATE))
        root = logging.getLogger("review_assistant")
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        root.propagate = False
        _configured = True
    return logging.getLogger(f"review_assistant.{component}")


def fields(**values: object) -> str:
    """Render key=value pairs the way the log lines in the course show them."""
    return " ".join(f"{key}={value}" for key, value in values.items())
