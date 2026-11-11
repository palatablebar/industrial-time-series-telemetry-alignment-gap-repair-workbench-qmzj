"""Structured single-line logs so `docker compose logs` stays greppable."""
import json
import logging
import sys

_logger = logging.getLogger("tsalign")
if not _logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


def log_event(event: str, **fields) -> None:
    payload = {"event": event, **fields}
    _logger.info(json.dumps(payload, ensure_ascii=False, default=str))
