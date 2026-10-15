import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """No raw request, query, IP, payload or exception traceback in foundation logs."""

    def format(self, record: logging.LogRecord) -> str:
        result = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", "application_log"),
        }
        for key in ("request_id", "status", "duration_ms", "route"):
            if hasattr(record, key):
                result[key] = getattr(record, key)
        if record.exc_info and record.exc_info[0]:
            result["exception_type"] = record.exc_info[0].__name__
        return json.dumps(result)
