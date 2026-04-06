# Al Habibi Bank — Biometric Authentication Demo

A production-grade biometric authentication system for mobile banking, built with a Claude AI agentic loop, React Native, and a lightweight OAuth2/OIDC token server. Designed to meet **MAS FSM-N05/N06** regulatory standards for Singapore-licensed financial institutions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Mobile App (React Native / Expo)                               │
│  Camera → Consent → Capture → Processing → Dashboard           │
└─────────────────────┬───────────────────────────────────────────┘
                      │ POST /auth/biometric { username, image_b64 }
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Biometric Agent (FastAPI :8000)                                │
│                                                                 │
│  Claude Agentic Loop (claude-opus-4-6):                        │
│  ① validate_face_capture  — image quality, 1 face, centered    │
│  ② detect_liveness        — MiniFASNet PAD + DCT deepfake      │
│  ③ verify_identity        — cosine similarity vs stored template│
│  ④ issue_keycloak_token   — biometric_verified OAuth2 grant    │
└──────┬────────────────────────────────────────────────┬─────────┘
       │                                                │
       ▼                                                ▼
┌──────────────────┐                        ┌──────────────────────┐
│  Token Server    │                        │  SQLite Face DB      │
│  (FastAPI :8080) │                        │  face_templates      │
│  RS256 JWT       │                        │  registered_users    │
│  acr=3, amr=face │                        └──────────────────────┘
└──────────────────┘
       │
       ▼ Bearer JWT (acr=3)
┌──────────────────┐       ┌──────────────────┐  ┌──────────────────┐
│  Portfolio API   │       │  Prometheus       │  │  Grafana         │
│  (FastAPI :9000) │       │  (:9090)          │  │  (:3000)         │
│  /portfolio      │       │  metrics scraper  │  │  dashboard       │
└──────────────────┘       └──────────────────┘  └──────────────────┘
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker Desktop | 24+ | Run all backend services |
| Docker Compose | v2 | Orchestration (`docker compose`) |
| Node.js | 18+ | Mobile app |
| Expo CLI | latest | `npm install -g expo-cli` |
| Git | any | Clone repo |

> **Apple Silicon (M1/M2/M3)**: Works natively. InsightFace runs on CPU (`INSIGHTFACE_CTX_ID=-1`).

---

## Quick Start (Local Testing)

### 1. Clone & Configure

```bash
git clone https://github.com/habmuz/biometric-banking-demo.git
cd biometric-banking-demo
```

Copy environment files and fill in your keys:

```bash
cp agent/.env.example agent/.env
cp token-server/.env.example token-server/.env
```

Edit `agent/.env` — minimum required:

```env
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here   # required
CLAUDE_MODEL=claude-opus-4-6

KEYCLOAK_BASE_URL=http://token-server:8080
KEYCLOAK_REALM=biometric-banking
KEYCLOAK_CLIENT_ID=biometric-agent
KEYCLOAK_CLIENT_SECRET=biometric-agent-secret-change-in-prod

LIVENESS_THRESHOLD=0.50
DEEPFAKE_THRESHOLD=0.60
INSIGHTFACE_MODEL=buffalo_l
INSIGHTFACE_CTX_ID=-1

LANGFUSE_SECRET_KEY=     # optional — leave blank to disable tracing
LANGFUSE_PUBLIC_KEY=
LANGFUSE_BASE_URL=https://cloud.langfuse.com

AUDIT_LOG_PATH=audit.jsonl
PORT=8000
```

Edit `token-server/.env`:

```env
TOKEN_SERVER_CLIENT_SECRET=biometric-agent-secret-change-in-prod
DEMO_USER_PASSWORD=Demo@1234
TOKEN_TTL=300
```

### 2. Start All Backend Services

```bash
docker compose up --build
```

First build downloads ~1.2 GB of ML models (InsightFace buffalo_l + anti-spoof ONNX). Subsequent starts are fast.

Wait for all services to be ready:

```
✓ token-server     http://localhost:8080
✓ biometric-agent  http://localhost:8000
✓ portfolio-api    http://localhost:9000
✓ prometheus       http://localhost:9090
✓ grafana          http://localhost:3000  (admin / admin)
```

### 3. Verify Backend Health

```bash
# Agent health
curl http://localhost:8000/docs

# Token server OIDC discovery
curl http://localhost:8080/realms/biometric-banking/.well-known/openid-configuration

# Portfolio API (unauthenticated — expect 403)
curl http://localhost:9000/portfolio
```

### 4. Run the Mobile App

```bash
cd mobile
npm install       # first time only
npm start         # starts Expo dev server
```

Press **`w`** to open in browser, or scan the QR code with Expo Go on your phone.

> **Agent URL**: The mobile app calls `http://localhost:8000` by default. On a physical device, replace `localhost` with your machine's local IP in `mobile/src/store/authStore.ts` or `CaptureScreen.tsx`.

---

## API Endpoints

### Biometric Agent (`http://localhost:8000`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/biometric` | Authenticate with face image |
| `POST` | `/register/biometric` | Register new face template |
| `GET` | `/users/{username}/registered` | Check enrollment status |
| `GET` | `/metrics/` | Prometheus metrics |
| `GET` | `/docs` | Swagger UI |

**Auth request body:**
```json
{
  "username": "demo_user",
  "image_b64": "<base64-encoded JPEG>"
}
```

**Auth response (success):**
```json
{
  "success": true,
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 300,
  "acr": "3",
  "amr": ["face"]
}
```

### Token Server (`http://localhost:8080`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/realms/biometric-banking/protocol/openid-connect/token` | OAuth2 token endpoint |
| `GET` | `/realms/biometric-banking/protocol/openid-connect/certs` | JWKS (public keys) |
| `GET` | `/realms/biometric-banking/.well-known/openid-configuration` | OIDC discovery |
| `POST` | `/users/register` | Register user (called internally by agent) |

### Portfolio API (`http://localhost:9000`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/portfolio` | Returns mock portfolio (requires Bearer JWT with acr=3) |

---

## Registration Flow

To register a new user before authenticating:

1. Open the mobile app → tap **Sign Up**
2. Enter a username and capture your face
3. The agent stores your face embedding in SQLite
4. You can now authenticate with the same username

Or via API:
```bash
curl -X POST http://localhost:8000/register/biometric \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "image_b64": "<base64-jpeg>"}'
```

---

## Authentication Flow (Detail)

```
Mobile ──► POST /auth/biometric
              │
              ▼ Claude picks up the request
          ┌───────────────────────────────────────────┐
          │  Tool 1: validate_face_capture            │
          │  • Min 256×256 px                         │
          │  • Exactly 1 face detected                │
          │  • Face occupies centre of frame          │
          └───────────────────┬───────────────────────┘
                              │ pass
          ┌───────────────────▼───────────────────────┐
          │  Tool 2: detect_liveness                  │
          │  • MiniFASNet V2 + V1SE (ONNX)            │
          │  • liveness_score >= 0.50                 │
          │  • DCT deepfake_score < 0.60              │
          └───────────────────┬───────────────────────┘
                              │ pass
          ┌───────────────────▼───────────────────────┐
          │  Tool 3: verify_identity                  │
          │  • InsightFace buffalo_l embedding        │
          │  • Cosine similarity >= 0.35              │
          └───────────────────┬───────────────────────┘
                              │ pass
          ┌───────────────────▼───────────────────────┐
          │  Tool 4: issue_keycloak_token             │
          │  • biometric_verified grant               │
          │  • RS256 JWT, acr=3, amr=["face"]         │
          └───────────────────┬───────────────────────┘
                              │
              ◄───── access_token ──────────────────────
```

Every step is logged to `agent/audit.jsonl` (append-only, 5-year retention per MAS).

---

## Monitoring

### Prometheus — `http://localhost:9090`

Key metrics:
- `biometric_auth_requests_total{result="success|failure"}`
- `biometric_auth_duration_seconds`
- `biometric_liveness_score`
- `biometric_deepfake_score`

### Grafana — `http://localhost:3000`

Login: `admin` / `admin`

Pre-provisioned dashboard: **Biometric Auth Overview**
- Auth success/failure rate
- p50/p95/p99 latency
- Liveness score distribution
- Token issue rate

---

## Project Structure

```
biometric-banking-demo/
├── agent/                    # Biometric AI engine (FastAPI + Claude)
│   ├── main.py               # API server
│   ├── agent.py              # Claude auth agentic loop
│   ├── registration_agent.py # Claude registration agentic loop
│   ├── face_db.py            # SQLite face template store
│   ├── audit.py              # MAS-compliant audit logging
│   ├── metrics.py            # Prometheus metrics
│   ├── tools/                # Agent tool implementations
│   │   ├── face_capture.py   # Image validation
│   │   ├── liveness.py       # PAD + deepfake detection
│   │   ├── verify_identity.py # Face matching
│   │   ├── register_face.py  # Enrollment
│   │   └── keycloak_auth.py  # Token issuance
│   ├── anti_spoof/           # Anti-spoofing models (downloaded at build)
│   ├── .env.example          # Config template
│   ├── Dockerfile
│   └── requirements.txt
│
├── token-server/             # Lightweight OAuth2/OIDC issuer
│   ├── main.py               # Keycloak-compatible token server
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
│
├── portfolio-api/            # Protected resource server
│   ├── main.py               # JWT-validated API
│   ├── Dockerfile
│   └── requirements.txt
│
├── mobile/                   # React Native Expo app
│   ├── App.tsx               # Navigation stack
│   ├── src/screens/          # 7 screens (Consent → Dashboard)
│   ├── src/store/            # Zustand auth state
│   └── package.json
│
├── prometheus/               # Metrics config
├── grafana/                  # Dashboard provisioning
├── docker-compose.yml        # All services
└── .gitignore
```

---

## Environment Variables Reference

### `agent/.env`

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | **Required.** Anthropic API key |
| `CLAUDE_MODEL` | `claude-opus-4-6` | Claude model ID |
| `KEYCLOAK_BASE_URL` | `http://token-server:8080` | Token server URL |
| `KEYCLOAK_CLIENT_SECRET` | — | Shared secret between agent and token server |
| `LIVENESS_THRESHOLD` | `0.50` | MiniFASNet liveness score cutoff |
| `DEEPFAKE_THRESHOLD` | `0.60` | DCT deepfake score cutoff |
| `INSIGHTFACE_CTX_ID` | `-1` | `-1` = CPU, `0` = first GPU |
| `LANGFUSE_SECRET_KEY` | blank | Optional — LLM tracing via Langfuse |

### `token-server/.env`

| Variable | Default | Description |
|----------|---------|-------------|
| `TOKEN_SERVER_CLIENT_SECRET` | — | Must match agent's `KEYCLOAK_CLIENT_SECRET` |
| `DEMO_USER_PASSWORD` | — | Password for demo user (password grant) |
| `TOKEN_TTL` | `300` | JWT lifetime in seconds |

---

## MAS Compliance Notes

This demo implements controls relevant to **MAS FSM-N05** (Technology Risk Management) and **FSM-N06** (Internet Banking):

| Control | Implementation |
|---------|---------------|
| ISO 30107-3 PAD Level 2 | MiniFASNet V2 + V1SE dual-model liveness detection |
| ISO 24745 cancelable biometrics | Face embeddings stored in SQLite (production: add per-user randomization salt) |
| PDPA data minimisation | Raw image never stored; only 512-d embedding retained |
| ACR = 3 (AAL2-equivalent) | `acr=3` claim in JWT, `amr=["face"]` |
| Audit log | Append-only JSONL, 5-year retention per MAS Notice 644 |
| Step-up authentication | Agent enforces all 4 tool steps; no step can be skipped |

> **Production gap**: Raw InsightFace embeddings are stored without per-user cancelability salt. Apply ISO 24745 randomization before production deployment.

---

## Troubleshooting

**First build is slow (~10–15 min)**
InsightFace downloads the `buffalo_l` model (~1.2 GB). This is cached in the Docker layer; subsequent builds are fast.

**`biometric-agent` fails to start**
Check that `token-server` is healthy first — the agent depends on it. Wait for `http://localhost:8080/health/ready` to return 200.

**Face not detected**
- Ensure good lighting and a clear frontal view
- Image must be at least 256×256 pixels
- Only one face should be visible in frame

**`verify_identity` always fails**
You must register first. Use the Sign Up flow or `POST /register/biometric`.

**Mobile app can't reach agent on physical device**
Replace `localhost` with your machine's local IP address (e.g. `192.168.1.x`) in the mobile app's API base URL.

**Grafana shows no data**
The agent must have processed at least one auth request for metrics to appear. Try an auth attempt first.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Orchestration | Claude claude-opus-4-6 (Anthropic) |
| Face Recognition | InsightFace buffalo_l (ArcFace) |
| Liveness Detection | MiniFASNet V2 + V1SE (ONNX) |
| Deepfake Detection | DCT frequency analysis |
| Backend | FastAPI (Python 3.11) |
| Auth Protocol | OAuth2 / OIDC (RS256 JWT) |
| Mobile | React Native + Expo 52 |
| State Management | Zustand |
| Metrics | Prometheus + Grafana |
| LLM Tracing | Langfuse (optional) |
| Database | SQLite (face templates) |
| Containerisation | Docker Compose |

---

## License

For demonstration and educational purposes. Not for production use without security review and regulatory compliance validation.
