"""
Tool 3: issue_keycloak_token
After biometric validation passes, calls Keycloak direct grant
to issue a signed RS256 JWT with acr=3 and scope=login_api.
The agent service account authenticates to Keycloak; the resulting
token is scoped to the end user.
"""
import time

import httpx
from jose import jwt as jose_jwt

from config import get_settings

_KEYCLOAK_RETRY_SECS = 10
_KEYCLOAK_POLL_INTERVAL = 1.0

TOOL_SPEC = {
    "name": "issue_keycloak_token",
    "description": (
        "Issue a Keycloak JWT for the authenticated user after biometric liveness has passed. "
        "Returns a signed RS256 access token with acr=3 and scope=login_api. "
        "Only call this tool AFTER detect_liveness has returned passed=true."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "Username of the authenticated user.",
            },
            "liveness_score": {
                "type": "number",
                "description": "Liveness score from detect_liveness (must be >= 0.85).",
            },
            "deepfake_score": {
                "type": "number",
                "description": "Deepfake score from detect_liveness (must be <= 0.15).",
            },
        },
        "required": ["username", "liveness_score", "deepfake_score"],
    },
}

_JWKS_CACHE: dict | None = None


def _token_endpoint(settings) -> str:
    return (
        f"{settings.keycloak_base_url}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/token"
    )


def _jwks_uri(settings) -> str:
    return (
        f"{settings.keycloak_base_url}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/certs"
    )


def execute(username: str, liveness_score: float, deepfake_score: float) -> dict:
    settings = get_settings()

    # Safety guard — agent should enforce this, but double-check
    if liveness_score < settings.liveness_threshold or deepfake_score > settings.deepfake_threshold:
        return {
            "success": False,
            "message": (
                f"Biometric thresholds not met. Cannot issue token. "
                f"liveness={liveness_score}, deepfake={deepfake_score}"
            ),
            "access_token": None,
        }

    # Call Keycloak token endpoint, retrying for up to 10 seconds if Keycloak
    # is still starting up (connection refused / 503).
    deadline = time.monotonic() + _KEYCLOAK_RETRY_SECS
    last_error = "Keycloak did not respond within 10 seconds."
    resp = None

    while time.monotonic() < deadline:
        try:
            resp = httpx.post(
                _token_endpoint(settings),
                data={
                    "grant_type": "biometric_verified",
                    "client_id": settings.keycloak_client_id,
                    "client_secret": settings.keycloak_client_secret,
                    "username": username,
                    "scope": "openid login_api",
                },
                timeout=5.0,
            )
            # 4xx means Keycloak is up but rejected the request — don't retry
            if resp.status_code < 500:
                break
            last_error = f"Keycloak returned {resp.status_code} — retrying…"
        except (httpx.ConnectError, httpx.TimeoutException):
            last_error = "Keycloak not reachable — retrying…"

        time.sleep(_KEYCLOAK_POLL_INTERVAL)

    if resp is None:
        return {"success": False, "message": last_error, "access_token": None}

    if not resp.is_success:
        return {
            "success": False,
            "message": f"Keycloak token request failed: {resp.status_code} {resp.text}",
            "access_token": None,
        }

    token_data = resp.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return {
            "success": False,
            "message": "Keycloak returned no access_token.",
            "access_token": None,
        }

    # Decode (unverified) to extract claims for audit log
    try:
        unverified = jose_jwt.get_unverified_claims(access_token)
        jti = unverified.get("jti", "unknown")
        acr = unverified.get("acr", "unknown")
        exp = unverified.get("exp", 0)
        sub = unverified.get("sub", "unknown")
    except Exception:
        jti, acr, exp, sub = "unknown", "unknown", 0, "unknown"

    return {
        "success": True,
        "message": "JWT issued successfully with acr=3 and scope=login_api.",
        "access_token": access_token,
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": token_data.get("expires_in", 300),
        "jti": jti,
        "acr": acr,
        "sub": sub,
    }
