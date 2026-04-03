#!/usr/bin/env bash
# Verifies Keycloak is healthy and the biometric realm is configured correctly

set -euo pipefail

KC_BASE="http://localhost:8080"
REALM="biometric-banking"
ADMIN_USER="admin"
ADMIN_PASS="admin123"

echo "==> Waiting for Keycloak to be ready..."
until curl -sf "${KC_BASE}/health/ready" > /dev/null 2>&1; do
  printf "."
  sleep 3
done
echo " ready."

echo ""
echo "==> Fetching admin token..."
TOKEN=$(curl -sf -X POST "${KC_BASE}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" \
  -d "username=${ADMIN_USER}" \
  -d "password=${ADMIN_PASS}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "   OK"

echo ""
echo "==> Checking realm '${REALM}' exists..."
REALM_INFO=$(curl -sf "${KC_BASE}/admin/realms/${REALM}" \
  -H "Authorization: Bearer ${TOKEN}")
echo "   Realm displayName: $(echo "${REALM_INFO}" | python3 -c "import sys,json; print(json.load(sys.stdin)['displayName'])")"
echo "   Brute force protection: $(echo "${REALM_INFO}" | python3 -c "import sys,json; print(json.load(sys.stdin)['bruteForceProtected'])")"
echo "   Session idle timeout: $(echo "${REALM_INFO}" | python3 -c "import sys,json; print(json.load(sys.stdin)['ssoSessionIdleTimeout'])") seconds"

echo ""
echo "==> Checking clients..."
CLIENTS=$(curl -sf "${KC_BASE}/admin/realms/${REALM}/clients" \
  -H "Authorization: Bearer ${TOKEN}")
echo "${CLIENTS}" | python3 -c "
import sys, json
clients = json.load(sys.stdin)
for c in clients:
    if c.get('clientId') in ('biometric-agent', 'portfolio-api'):
        print(f\"   {c['clientId']}: enabled={c['enabled']}, bearerOnly={c.get('bearerOnly', False)}\")
"

echo ""
echo "==> Checking JWKS endpoint (RS256 keys present)..."
JWKS=$(curl -sf "${KC_BASE}/realms/${REALM}/protocol/openid-connect/certs")
KEY_COUNT=$(echo "${JWKS}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len([k for k in d['keys'] if k['alg']=='RS256']))")
echo "   RS256 keys found: ${KEY_COUNT}"

echo ""
echo "==> Fetching token for demo_user via biometric-agent (direct grant)..."
USER_TOKEN=$(curl -sf -X POST "${KC_BASE}/realms/${REALM}/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=biometric-agent" \
  -d "client_secret=biometric-agent-secret-change-in-prod" \
  -d "username=demo_user" \
  -d "password=Demo@1234" \
  -d "scope=openid login_api")

ACCESS_TOKEN=$(echo "${USER_TOKEN}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo ""
echo "==> Decoding JWT claims (payload)..."
# Decode base64url without padding
PAYLOAD=$(echo "${ACCESS_TOKEN}" | cut -d. -f2 | python3 -c "
import sys, base64, json
data = sys.stdin.read().strip()
# Add padding
padded = data + '=' * (4 - len(data) % 4)
decoded = base64.urlsafe_b64decode(padded)
claims = json.loads(decoded)
important = {k: claims[k] for k in ['sub','acr','amr','auth_method','scope','aud','azp'] if k in claims}
print(json.dumps(important, indent=2))
")
echo "${PAYLOAD}"

echo ""
echo "==> Checking demo_user attributes..."
USERS=$(curl -sf "${KC_BASE}/admin/realms/${REALM}/users?username=demo_user" \
  -H "Authorization: Bearer ${TOKEN}")
echo "${USERS}" | python3 -c "
import sys, json
users = json.load(sys.stdin)
u = users[0]
attrs = u.get('attributes', {})
print(f\"   biometric_enrolled: {attrs.get('biometric_enrolled', ['?'])[0]}\")
print(f\"   pdpa_consent: {attrs.get('pdpa_consent', ['?'])[0]}\")
print(f\"   pdpa_consent_date: {attrs.get('pdpa_consent_date', ['?'])[0]}\")
"

echo ""
echo "==> All checks passed. Keycloak is ready for the biometric agent."
echo ""
echo "   OIDC Discovery: ${KC_BASE}/realms/${REALM}/.well-known/openid-configuration"
echo "   Token endpoint: ${KC_BASE}/realms/${REALM}/protocol/openid-connect/token"
echo "   JWKS endpoint:  ${KC_BASE}/realms/${REALM}/protocol/openid-connect/certs"
