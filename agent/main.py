"""
Biometric Agent API Server
Mobile app POSTs a face image here → agent runs → JWT returned.
"""
import time
import uuid
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

import audit
import face_db
from agent import run_auth
from registration_agent import run_registration
from config import get_settings
from metrics import auth_duration_seconds, auth_requests_total
from observability import get_tracer

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("biometric_agent_starting", model=get_settings().claude_model)
    try:
        from tools.liveness import _get_model
        _get_model()
        log.info("insightface_model_loaded", model=get_settings().insightface_model)
    except Exception as e:
        log.warning("insightface_warmup_failed", error=str(e))
    yield
    get_tracer().flush()
    log.info("biometric_agent_stopped")


app = FastAPI(
    title="Biometric Authentication Agent",
    description="Claude-powered biometric auth agent for Al Habibi Bank.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.mount("/metrics", make_asgi_app())


# ── Request / Response models ───────────────────────────────────────────────

class BiometricRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    image_b64: str = Field(..., min_length=100, description="Base64-encoded face image.")


class AuthSuccess(BaseModel):
    status: str
    access_token: str
    token_type: str
    expires_in: int
    acr: str
    message: str


class AuthFailure(BaseModel):
    status: str
    reason: str
    retry_allowed: bool


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "biometric-agent"}


@app.get("/users/{username}/registered")
async def user_registered(username: str):
    """Check whether a user has a stored face template (i.e. has completed registration)."""
    return {"registered": face_db.is_registered(username)}


@app.post("/auth/biometric", response_model=AuthSuccess | AuthFailure)
async def biometric_auth(body: BiometricRequest, request: Request):
    """Login flow — verifies identity against stored face template."""
    request_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"

    log.info("auth_request_received", username=body.username, request_id=request_id)
    audit.log_auth_attempt(username=body.username, request_id=request_id, source_ip=client_ip)

    start = time.perf_counter()
    try:
        result = run_auth(image_b64=body.image_b64, username=body.username, request_id=request_id)
    except Exception as e:
        elapsed = time.perf_counter() - start
        auth_duration_seconds.observe(elapsed)
        auth_requests_total.labels(outcome="agent_error").inc()
        log.error("agent_error", error=str(e), request_id=request_id)
        audit.log_auth_failure(body.username, request_id, reason=f"Agent error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication service error.")

    elapsed = time.perf_counter() - start
    auth_duration_seconds.observe(elapsed)

    if result.get("status") == "authentication_success":
        auth_requests_total.labels(outcome="success").inc()
    else:
        reason = result.get("reason", "").lower()
        if "face" in reason or "capture" in reason or "image" in reason:
            outcome = "face_invalid"
        elif "liveness" in reason or "deepfake" in reason or "spoof" in reason:
            outcome = "liveness_failed"
        elif "identity" in reason or "similarity" in reason or "template" in reason:
            outcome = "identity_mismatch"
        elif "token" in reason or "keycloak" in reason or "jwt" in reason:
            outcome = "token_failed"
        else:
            outcome = "agent_error"
        auth_requests_total.labels(outcome=outcome).inc()

    log.info("auth_result", username=body.username, status=result.get("status"),
             request_id=request_id, duration_s=round(elapsed, 2))

    return JSONResponse(content=result, status_code=200 if result.get("status") == "authentication_success" else 401)


@app.post("/register/biometric", response_model=AuthSuccess | AuthFailure)
async def biometric_register(body: BiometricRequest, request: Request):
    """Registration flow — enrolls face template and issues first-login token."""
    request_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"

    log.info("registration_request_received", username=body.username, request_id=request_id)
    audit.log_auth_attempt(username=body.username, request_id=request_id, source_ip=client_ip)

    start = time.perf_counter()
    try:
        result = run_registration(image_b64=body.image_b64, username=body.username, request_id=request_id)
    except Exception as e:
        elapsed = time.perf_counter() - start
        auth_duration_seconds.observe(elapsed)
        auth_requests_total.labels(outcome="agent_error").inc()
        log.error("registration_agent_error", error=str(e), request_id=request_id)
        audit.log_auth_failure(body.username, request_id, reason=f"Registration agent error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration service error.")

    elapsed = time.perf_counter() - start
    auth_duration_seconds.observe(elapsed)

    if result.get("status") == "registration_success":
        auth_requests_total.labels(outcome="success").inc()
    else:
        auth_requests_total.labels(outcome="agent_error").inc()

    log.info("registration_result", username=body.username, status=result.get("status"),
             request_id=request_id, duration_s=round(elapsed, 2))

    # Normalise registration_success → authentication_success shape for mobile compatibility
    if result.get("status") == "registration_success":
        result["status"] = "authentication_success"
        return JSONResponse(content=result, status_code=200)
    return JSONResponse(content=result, status_code=401)


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
