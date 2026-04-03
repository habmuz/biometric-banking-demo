"""
Lightweight OAuth2/OIDC Token Server — drop-in Keycloak replacement.
Exposes the same URL paths Keycloak uses so agent + portfolio-api need zero changes.

Starts in ~1 second. Generates a fresh RSA-2048 keypair on boot.
Issues RS256 JWTs with acr=3, amr=["face"], scope=login_api.

Endpoints (Keycloak-compatible paths):
  POST /realms/{realm}/protocol/openid-connect/token
  GET  /realms/{realm}/protocol/openid-connect/certs      (JWKS)
  GET  /health/ready
  GET  /realms/{realm}/.well-known/openid-configuration

Biometric registration endpoints:
  POST /users/register                    (register user for biometric_verified grant)
  GET  /users/{username}/registered       (check if user is biometrically registered)
"""
import json
import os
import time
import uuid
from base64 import urlsafe_b64encode
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import jwt
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────
REALM           = "biometric-banking"
CLIENT_ID       = "biometric-agent"
CLIENT_SECRET   = os.environ["TOKEN_SERVER_CLIENT_SECRET"]
TOKEN_TTL       = int(os.getenv("TOKEN_TTL", "300"))
BASE_URL        = "http://localhost:8080"

# Pre-seeded demo users (password grant)
USERS = {
    "demo_user": os.environ["DEMO_USER_PASSWORD"],
}

# Biometrically registered users (biometric_verified grant — no password)
_BIOMETRIC_USERS_FILE = Path("data/biometric_users.json")
_biometric_users: set[str] = set()


def _load_biometric_users() -> None:
    _BIOMETRIC_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _BIOMETRIC_USERS_FILE.exists():
        try:
            data = json.loads(_BIOMETRIC_USERS_FILE.read_text())
            _biometric_users.update(data)
        except Exception:
            pass


def _save_biometric_users() -> None:
    _BIOMETRIC_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _BIOMETRIC_USERS_FILE.write_text(json.dumps(list(_biometric_users)))


_load_biometric_users()

# ── RSA key generation (once on startup) ─────────────────────────────────
print("Generating RSA-2048 keypair…")
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key  = _private_key.public_key()
_kid         = str(uuid.uuid4())[:8]

_private_pem = _private_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,
    serialization.NoEncryption(),
).decode()

_pub_numbers = _public_key.public_key().public_numbers() if hasattr(_public_key, "public_key") else _public_key.public_numbers()


def _b64url_uint(n: int) -> str:
    length = (n.bit_length() + 7) // 8
    return urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()


_JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": _kid,
            "n":   _b64url_uint(_pub_numbers.n),
            "e":   _b64url_uint(_pub_numbers.e),
        }
    ]
}
print(f"RSA keypair ready — kid={_kid}")

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title="Biometric Token Server", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_realm_prefix = f"/realms/{REALM}/protocol/openid-connect"


# ── Health ─────────────────────────────────────────────────────────────────
@app.get("/health/ready")
@app.get("/health/live")
def health():
    return {"status": "UP"}


# ── JWKS ───────────────────────────────────────────────────────────────────
@app.get(_realm_prefix + "/certs")
def jwks():
    return _JWKS


# ── OIDC Discovery ─────────────────────────────────────────────────────────
@app.get(f"/realms/{REALM}/.well-known/openid-configuration")
def discovery():
    base = f"{BASE_URL}/realms/{REALM}"
    return {
        "issuer":                                base,
        "token_endpoint":                        f"{base}/protocol/openid-connect/token",
        "jwks_uri":                              f"{base}/protocol/openid-connect/certs",
        "id_token_signing_alg_values_supported": ["RS256"],
        "grant_types_supported":                 ["password", "client_credentials", "biometric_verified"],
    }


# ── Biometric user registration ────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str


@app.post("/users/register")
def register_user(body: RegisterRequest):
    _biometric_users.add(body.username)
    _save_biometric_users()
    return {"registered": True, "username": body.username}


@app.get("/users/{username}/registered")
def check_registered(username: str):
    return {"registered": username in _biometric_users}


# ── Token endpoint ─────────────────────────────────────────────────────────
@app.post(_realm_prefix + "/token")
async def token(
    request: Request,
    grant_type:    str = Form(...),
    client_id:     str = Form(...),
    client_secret: str = Form(...),
    username:      str = Form(None),
    password:      str = Form(None),
    scope:         str = Form("openid"),
):
    # Validate client
    if client_id != CLIENT_ID or client_secret != CLIENT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    if grant_type == "password":
        if not username or not password:
            raise HTTPException(status_code=400, detail="username and password required")
        expected_pw = USERS.get(username)
        if expected_pw is None:
            raise HTTPException(status_code=401, detail=f"User '{username}' not found")
        if password != expected_pw:
            raise HTTPException(status_code=401, detail="Invalid password")
        sub = f"user-{username}"

    elif grant_type == "biometric_verified":
        # Biometric agent has already verified face + liveness + identity
        if not username:
            raise HTTPException(status_code=400, detail="username required")
        if username not in _biometric_users:
            raise HTTPException(
                status_code=401,
                detail=f"User '{username}' not enrolled for biometric authentication.",
            )
        sub = f"user-{username}"

    elif grant_type == "client_credentials":
        sub = f"service-{client_id}"
        username = client_id

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")

    now = int(time.time())
    scopes = scope.split() if scope else []
    audience = ["portfolio-api", client_id] if "login_api" in scopes else [client_id]

    claims = {
        "iss":                f"{BASE_URL}/realms/{REALM}",
        "sub":                sub,
        "aud":                audience,
        "iat":                now,
        "exp":                now + TOKEN_TTL,
        "jti":                str(uuid.uuid4()),
        "preferred_username": username,
        "azp":                client_id,
        "scope":              scope,
        "acr":                "3",
        "amr":                ["face"],
        "auth_method":        "biometric_face_liveness",
    }

    access_token = jwt.encode(
        claims,
        _private_pem,
        algorithm="RS256",
        headers={"kid": _kid},
    )

    return {
        "access_token": access_token,
        "token_type":   "Bearer",
        "expires_in":   TOKEN_TTL,
        "scope":        scope,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
