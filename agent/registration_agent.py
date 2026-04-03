"""
Biometric Registration Agent (sign-up flow)
Uses the Claude SDK agentic loop to orchestrate 4 tools in strict sequence:
  1. validate_face_capture  — image quality + single face check
  2. detect_liveness        — InsightFace buffalo_l PAD Level 2
  3. register_face          — stores face template + registers user in token-server
  4. issue_keycloak_token   — RS256 JWT acr=3 scope=login_api

image_b64 and face embedding are NEVER sent to Claude — injected at tool-dispatch time.
"""
import json
import time
import uuid
from typing import Any

import numpy as np
import anthropic
import structlog

import audit
from json_extract import extract_json
from config import get_settings
from metrics import (
    claude_input_tokens_total,
    claude_output_tokens_total,
    deepfake_score_histogram,
    liveness_score_histogram,
    tool_call_duration_seconds,
)
from observability import get_tracer
from tools import TOOL_HANDLERS
from tools.face_capture import TOOL_SPEC as FACE_SPEC
from tools.keycloak_auth import TOOL_SPEC as TOKEN_SPEC
from tools.liveness import TOOL_SPEC as LIVENESS_SPEC
from tools.register_face import TOOL_SPEC as REGISTER_FACE_SPEC

log = structlog.get_logger()

_SYSTEM_PROMPT = """You are a biometric registration agent for a regulated Singapore banking application.

Your job is to register a NEW user by enrolling their face biometric, calling four tools IN STRICT ORDER:

STEP 1 — Call validate_face_capture(username)
  - If valid=false: respond with registration_failed and reason. STOP.
  - If valid=true: proceed to step 2.

STEP 2 — Call detect_liveness(username)
  - If passed=false: respond with registration_failed and reason. STOP.
  - If passed=true: proceed to step 3.

STEP 3 — Call register_face(username)
  - If registered=false: respond with registration_failed and reason. STOP.
  - If registered=true: proceed to step 4.

STEP 4 — Call issue_keycloak_token(username, liveness_score, deepfake_score)
  - If success=false: respond with registration_failed and reason.
  - If success=true: respond with registration_success and the access_token.

RULES:
- Never skip a step. Never call step 4 before steps 2 and 3 both pass.
- Never fabricate scores or tokens.
- If any tool returns an error, treat it as registration_failed.
- Your final JSON response must have exactly one of these structures:

  Registration success:
  {
    "status": "registration_success",
    "access_token": "<jwt>",
    "token_type": "Bearer",
    "expires_in": <int>,
    "acr": "3",
    "message": "Biometric registration successful. You can now log in with your face."
  }

  Registration failure:
  {
    "status": "registration_failed",
    "reason": "<human-readable reason>",
    "retry_allowed": <true|false>
  }

Always respond with valid JSON only. No prose outside the JSON object.
"""

_FACE_SPEC_SLIM = {
    "name": "validate_face_capture",
    "description": FACE_SPEC["description"],
    "input_schema": {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "Username being registered."},
        },
        "required": ["username"],
    },
}

_LIVENESS_SPEC_SLIM = {
    "name": "detect_liveness",
    "description": LIVENESS_SPEC["description"],
    "input_schema": {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "Username — for audit logging only."},
        },
        "required": ["username"],
    },
}

_REGISTER_FACE_SPEC_SLIM = {
    "name": "register_face",
    "description": REGISTER_FACE_SPEC["description"],
    "input_schema": {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "Username to register the face template for."},
        },
        "required": ["username"],
    },
}

_ALL_TOOLS = [_FACE_SPEC_SLIM, _LIVENESS_SPEC_SLIM, _REGISTER_FACE_SPEC_SLIM, TOKEN_SPEC]


def run_registration(image_b64: str, username: str, request_id: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    request_id = request_id or str(uuid.uuid4())
    tracer = get_tracer()

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    lf_trace = tracer.trace(
        id=request_id,
        name="biometric_registration",
        user_id=username,
        metadata={"model": settings.claude_model, "request_id": request_id},
    )

    messages = [
        {
            "role": "user",
            "content": f"Register new user '{username}'. Request ID: {request_id}",
        }
    ]

    turn_index = 0
    total_input_tokens = 0
    total_output_tokens = 0
    _embedding_ctx: dict[str, Any] = {}

    while True:
        turn_index += 1

        lf_gen = lf_trace.generation(
            name=f"claude_turn_{turn_index}",
            model=settings.claude_model,
            input=messages,
        )

        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            tools=_ALL_TOOLS,
            messages=messages,
        )

        in_tok = response.usage.input_tokens
        out_tok = response.usage.output_tokens
        total_input_tokens += in_tok
        total_output_tokens += out_tok
        claude_input_tokens_total.inc(in_tok)
        claude_output_tokens_total.inc(out_tok)

        lf_gen.end(
            output={"stop_reason": response.stop_reason, "content_blocks": len(response.content)},
            usage={"input": in_tok, "output": out_tok},
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            result = None
            for block in response.content:
                if block.type == "text":
                    result = extract_json(block.text)
                    if result is not None:
                        break
                    log.warning("registration_agent_non_json", text=block.text[:300])

            if result is None:
                result = {
                    "status": "registration_failed",
                    "reason": "Agent returned non-JSON response.",
                    "retry_allowed": False,
                }

            _finalize(lf_trace, tracer, result, total_input_tokens, total_output_tokens)
            _handle_audit(result, username, request_id)
            return result

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name  = block.name
                tool_input = block.input
                handler    = TOOL_HANDLERS.get(tool_name)

                lf_span = lf_gen.span(name=tool_name, input=tool_input)

                if handler is None:
                    tool_output = {"error": f"Unknown tool: {tool_name}"}
                else:
                    t0 = time.perf_counter()
                    try:
                        if tool_name in ("validate_face_capture", "detect_liveness"):
                            tool_output = handler(image_b64=image_b64, **tool_input)
                            if tool_name == "detect_liveness" and isinstance(tool_output, dict):
                                emb = tool_output.get("embedding")
                                if emb:
                                    _embedding_ctx["embedding"] = np.array(emb, dtype=np.float32)
                        elif tool_name == "register_face":
                            tool_output = handler(embedding=_embedding_ctx.get("embedding"), **tool_input)
                        else:
                            tool_output = handler(**tool_input)
                    except Exception as e:
                        tool_output = {"error": str(e)}
                    elapsed = time.perf_counter() - t0

                    tool_call_duration_seconds.labels(tool_name=tool_name).observe(elapsed)

                    if tool_name == "detect_liveness" and isinstance(tool_output, dict):
                        if "liveness_score" in tool_output:
                            liveness_score_histogram.observe(tool_output["liveness_score"])
                        if "deepfake_score" in tool_output:
                            deepfake_score_histogram.observe(tool_output["deepfake_score"])

                is_error = "error" in tool_output if isinstance(tool_output, dict) else False
                lf_span.end(output=tool_output, level="ERROR" if is_error else "DEFAULT")

                # Strip raw embedding from tool result sent to Claude
                if isinstance(tool_output, dict) and "embedding" in tool_output:
                    tool_output = {k: v for k, v in tool_output.items() if k != "embedding"}

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(tool_output),
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        result = {
            "status": "registration_failed",
            "reason": f"Unexpected agent stop reason: {response.stop_reason}",
            "retry_allowed": False,
        }
        _finalize(lf_trace, tracer, result, total_input_tokens, total_output_tokens)
        _handle_audit(result, username, request_id)
        return result


def _finalize(lf_trace, tracer, result: dict, total_in: int, total_out: int) -> None:
    lf_trace.update(
        output={"status": result.get("status"), "reason": result.get("reason")},
        metadata={"total_input_tokens": total_in, "total_output_tokens": total_out},
        level="DEFAULT" if result.get("status") == "registration_success" else "WARNING",
    )
    tracer.flush()


def _handle_audit(result: dict, username: str, request_id: str) -> None:
    if result.get("status") == "registration_success":
        audit.log_token_issued(
            username=username,
            request_id=request_id,
            jti=result.get("jti", "unknown"),
            acr=result.get("acr", "3"),
        )
    else:
        audit.log_auth_failure(
            username=username,
            request_id=request_id,
            reason=result.get("reason", "unknown"),
        )
