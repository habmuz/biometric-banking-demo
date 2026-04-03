"""
Immutable append-only audit log.
MAS requirement: all auth events retained for 5 years, write-once.
Each line is a JSON object — never mutated, only appended.
"""
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(
    event_type: str,
    username: str | None,
    outcome: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> str:
    """Append one audit event. Returns the event_id."""
    settings = get_settings()
    event_id = str(uuid.uuid4())

    record = {
        "event_id": event_id,
        "request_id": request_id or str(uuid.uuid4()),
        "timestamp": _now_iso(),
        "epoch_ms": int(time.time() * 1000),
        "event_type": event_type,           # BIOMETRIC_AUTH_ATTEMPT / LIVENESS_CHECK / TOKEN_ISSUED / etc.
        "username": username,
        "outcome": outcome,                  # SUCCESS / FAILURE / ERROR
        "details": details or {},
    }

    path = Path(settings.audit_log_path)
    # Append-only — never truncate or overwrite
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return event_id


# Convenience wrappers
def log_auth_attempt(username: str, request_id: str, source_ip: str) -> str:
    return log_event(
        "BIOMETRIC_AUTH_ATTEMPT", username, "INITIATED",
        {"source_ip": source_ip}, request_id,
    )


def log_liveness_result(
    username: str, request_id: str,
    liveness_score: float, deepfake_score: float, passed: bool,
) -> str:
    return log_event(
        "LIVENESS_CHECK", username,
        "SUCCESS" if passed else "FAILURE",
        {
            "liveness_score": liveness_score,
            "deepfake_score": deepfake_score,
            "threshold_liveness": get_settings().liveness_threshold,
            "threshold_deepfake": get_settings().deepfake_threshold,
        },
        request_id,
    )


def log_token_issued(username: str, request_id: str, jti: str, acr: str) -> str:
    return log_event(
        "TOKEN_ISSUED", username, "SUCCESS",
        {"jti": jti, "acr": acr, "scope": "openid login_api"},
        request_id,
    )


def log_auth_failure(username: str | None, request_id: str, reason: str) -> str:
    return log_event(
        "BIOMETRIC_AUTH_FAILURE", username, "FAILURE",
        {"reason": reason}, request_id,
    )
