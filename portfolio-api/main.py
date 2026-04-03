"""
Portfolio API — Resource Server
Validates the Keycloak RS256 JWT (acr=3, scope=login_api) and returns mock portfolio data.
Mobile app calls this directly after receiving the token from the biometric agent.
"""
import os
from datetime import datetime, timezone
from functools import lru_cache

import httpx
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

# ── Config ──────────────────────────────────────────────────────────────────

KEYCLOAK_BASE = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "biometric-banking")
REQUIRED_SCOPE = "login_api"
REQUIRED_AUDIENCE = "portfolio-api"
MIN_ACR = "3"

# ── JWKS fetching (cached) ───────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    jwks_uri = f"{KEYCLOAK_BASE}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    resp = httpx.get(jwks_uri, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _refresh_jwks() -> dict:
    _get_jwks.cache_clear()
    return _get_jwks()

# ── JWT validation ───────────────────────────────────────────────────────────

bearer_scheme = HTTPBearer()


def validate_token(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)) -> dict:
    token = credentials.credentials
    jwks = _get_jwks()

    try:
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=REQUIRED_AUDIENCE,
            options={"verify_exp": True},
        )
    except JWTError:
        # Try with refreshed JWKS once (key rotation)
        try:
            jwks = _refresh_jwks()
            claims = jwt.decode(
                token, jwks,
                algorithms=["RS256"],
                audience=REQUIRED_AUDIENCE,
                options={"verify_exp": True},
            )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {e}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Enforce scope
    token_scopes = claims.get("scope", "").split()
    if REQUIRED_SCOPE not in token_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Token missing required scope: {REQUIRED_SCOPE}",
        )

    # Enforce ACR (biometric auth level)
    if claims.get("acr") != MIN_ACR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient authentication level. Required acr={MIN_ACR}.",
        )

    return claims

# ── Models ───────────────────────────────────────────────────────────────────

class Account(BaseModel):
    id: str
    name: str
    type: str
    currency: str
    balance: float
    accountNumber: str


class Portfolio(BaseModel):
    totalValue: float
    currency: str
    accounts: list[Account]
    lastUpdated: str

# ── Mock data (per user) ─────────────────────────────────────────────────────

_MOCK_PORTFOLIOS: dict[str, Portfolio] = {
    "demo_user": Portfolio(
        totalValue=284_750.00,
        currency="SGD",
        lastUpdated=datetime.now(timezone.utc).isoformat(),
        accounts=[
            Account(
                id="acc-001",
                name="Primary Current",
                type="current",
                currency="SGD",
                balance=12_480.35,
                accountNumber="••••  4821",
            ),
            Account(
                id="acc-002",
                name="Bonus Saver",
                type="savings",
                currency="SGD",
                balance=68_920.10,
                accountNumber="••••  3307",
            ),
            Account(
                id="acc-003",
                name="12M Fixed Deposit",
                type="fixed_deposit",
                currency="SGD",
                balance=100_000.00,
                accountNumber="••••  9914",
            ),
            Account(
                id="acc-004",
                name="AHB Invest Portfolio",
                type="investment",
                currency="SGD",
                balance=103_349.55,
                accountNumber="••••  7763",
            ),
        ],
    )
}

_DEFAULT_PORTFOLIO = Portfolio(
    totalValue=0.0,
    currency="SGD",
    lastUpdated=datetime.now(timezone.utc).isoformat(),
    accounts=[],
)

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Portfolio API",
    description="Banking portfolio resource server — requires biometric JWT (acr=3, scope=login_api).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["Authorization"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "portfolio-api"}


@app.get("/portfolio", response_model=Portfolio)
def get_portfolio(claims: dict = Depends(validate_token)):
    """
    Returns the authenticated user's portfolio.
    Requires: valid RS256 JWT with acr=3 and scope=login_api issued by Keycloak.
    """
    # preferred_username is set by Keycloak from the user's username
    username = claims.get("preferred_username") or claims.get("sub", "")
    portfolio = _MOCK_PORTFOLIOS.get(username, _DEFAULT_PORTFOLIO)
    # Refresh lastUpdated on each call
    return portfolio.model_copy(update={"lastUpdated": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)
