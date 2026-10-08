"""Small append-only JSON audit log for non-sensitive agent activity."""

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict
import json


AUDIT_PATH = Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"
_AUDIT_LOCK = Lock()


def _argument_summary(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Describe argument shape without copying customer text or secrets."""
    summary: Dict[str, Any] = {}
    for key, value in arguments.items():
        if isinstance(value, str):
            summary[key] = {"type": "string", "length": len(value)}
        elif isinstance(value, (int, float, bool)) or value is None:
            summary[key] = {"type": type(value).__name__ if value is not None else "null"}
        else:
            summary[key] = {"type": type(value).__name__}
    return summary


def _result_summary(result: Any) -> Dict[str, Any]:
    """Keep useful outcome metadata while excluding full product/customer content."""
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    if isinstance(result, dict):
        summary: Dict[str, Any] = {"fields": sorted(str(key) for key in result.keys())}
        for key in ("found", "count", "available", "size_listed"):
            if key in result and isinstance(result[key], (bool, int)):
                summary[key] = result[key]
        if isinstance(result.get("products"), list):
            summary["product_count"] = len(result["products"])
        return summary
    return {"type": type(result).__name__}


def record_activity(action: str, arguments: Dict[str, Any], result: Any, reason: str) -> None:
    """Append one JSON object to the persistent JSON-array audit trail."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "arguments": _argument_summary(arguments),
        "result": _result_summary(result),
        "reason": reason,
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_LOCK:
        if AUDIT_PATH.exists():
            raw = AUDIT_PATH.read_text(encoding="utf-8").strip()
            entries = json.loads(raw) if raw else []
            if not isinstance(entries, list):
                raise ValueError("Audit trail must contain a JSON array")
        else:
            entries = []
        entries.append(entry)
        AUDIT_PATH.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def audit_tool(function):
    """Wrap a synchronous PydanticAI tool while preserving its signature metadata."""
    from functools import wraps

    @wraps(function)
    def wrapped(*args, **kwargs):
        arguments = {"positional_count": len(args), **{key: value for key, value in kwargs.items()}}
        try:
            result = function(*args, **kwargs)
        except Exception as error:
            record_activity(function.__name__, arguments, {"error_type": type(error).__name__}, "tool failed with an exception")
            raise
        record_activity(function.__name__, arguments, result, "tool completed")
        return result

    return wrapped
