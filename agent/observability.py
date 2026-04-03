"""
Langfuse LLM observability — optional, zero-cost when disabled.

If LANGFUSE_PUBLIC_KEY is not set, all calls resolve to no-ops.
No try/except guards needed at call sites — the noop objects absorb everything.

Trace structure per auth request:
  Trace: biometric_auth  (id = request_id for correlation with audit log)
    ├── Generation: claude_turn_1  (tokens, model, full message input/output)
    │     └── Span: validate_face_capture  (tool input/output)
    ├── Generation: claude_turn_2
    │     └── Span: detect_liveness
    └── Generation: claude_turn_3
          └── Span: issue_keycloak_token
"""
import os
import structlog

log = structlog.get_logger()


# ── Noop sentinels ────────────────────────────────────────────────────────────

class _NoopObj:
    """Absorbs any attribute access and any call, returns itself."""
    id = None

    def __getattr__(self, _):
        return self

    def __call__(self, *args, **kwargs):
        return self


_NOOP = _NoopObj()


class _NoopLangfuse:
    def trace(self, **kwargs):       return _NOOP
    def generation(self, **kwargs):  return _NOOP
    def span(self, **kwargs):        return _NOOP
    def flush(self):                 pass


# ── Real Langfuse client (lazy init) ─────────────────────────────────────────

_client = None


def _init_client():
    global _client
    if _client is not None:
        return _client

    pub  = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sec  = os.getenv("LANGFUSE_SECRET_KEY", "")
    # Accept both LANGFUSE_HOST and LANGFUSE_BASE_URL (latter used by some SDK versions)
    host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    if not pub or not sec:
        log.info("langfuse_disabled", reason="LANGFUSE keys not set — tracing disabled")
        _client = _NoopLangfuse()
        return _client

    try:
        from langfuse import Langfuse
        _client = Langfuse(public_key=pub, secret_key=sec, host=host)
        log.info("langfuse_enabled", host=host)
    except Exception as e:
        log.warning("langfuse_init_failed", error=str(e))
        _client = _NoopLangfuse()

    return _client


def get_tracer():
    return _init_client()
