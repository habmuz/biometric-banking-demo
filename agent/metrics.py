"""
Prometheus metrics registry for the biometric agent.
All metric objects are defined here to prevent double-registration
when modules are reloaded. Import from here, never redefine elsewhere.

NOTE: For multi-worker uvicorn deployments, enable prometheus multiprocess mode:
  PROMETHEUS_MULTIPROC_DIR=/tmp/prom_multiproc
  and use MultiProcessCollector. Single-worker (current) has no issue.
"""
from prometheus_client import Counter, Histogram

auth_requests_total = Counter(
    "auth_requests_total",
    "Total biometric auth requests by outcome",
    ["outcome"],  # success | face_invalid | liveness_failed | token_failed | agent_error
)

auth_duration_seconds = Histogram(
    "auth_duration_seconds",
    "End-to-end auth latency (API receipt → response)",
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0, 15.0, 30.0, 60.0],
)

liveness_score_histogram = Histogram(
    "liveness_score",
    "Distribution of liveness scores from MiniFASNet (higher = more real)",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.85, 0.9, 0.95, 1.0],
)

deepfake_score_histogram = Histogram(
    "deepfake_score",
    "Distribution of deepfake scores from DCT analysis (lower = more real)",
    buckets=[0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 1.0],
)

claude_input_tokens_total = Counter(
    "claude_input_tokens_total",
    "Cumulative input tokens sent to Claude across all auth requests",
)

claude_output_tokens_total = Counter(
    "claude_output_tokens_total",
    "Cumulative output tokens received from Claude",
)

tool_call_duration_seconds = Histogram(
    "tool_call_duration_seconds",
    "Tool execution latency by tool name",
    ["tool_name"],  # validate_face_capture | detect_liveness | issue_keycloak_token
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0],
)
