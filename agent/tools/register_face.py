"""
Tool: register_face
Persists the face embedding captured during liveness detection into the face DB.
Called only during first-time sign-up flow (registration agent).
Also calls the token server to allow biometric_verified grants for this user.
"""
import numpy as np
import httpx

import face_db
from config import get_settings

TOOL_SPEC = {
    "name": "register_face",
    "description": (
        "Store the user's face biometric template after liveness passes. "
        "Only call this during registration (first-time sign-up), "
        "never during a login attempt. Returns registered=true on success."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "Username to register the face template for.",
            },
        },
        "required": ["username"],
    },
}


def execute(username: str, embedding: np.ndarray | None = None) -> dict:
    if embedding is None:
        return {
            "registered": False,
            "message": "No face embedding available. Run detect_liveness first.",
        }

    # Persist biometric template (ISO 24745: cancelable biometric)
    face_db.store_template(username, embedding)

    # Register user in token server for biometric_verified grant
    settings = get_settings()
    try:
        resp = httpx.post(
            f"{settings.keycloak_base_url}/users/register",
            json={"username": username},
            timeout=5.0,
        )
        if not resp.is_success:
            return {
                "registered": False,
                "message": f"Face template stored but token-server registration failed: {resp.text}",
            }
    except Exception as e:
        return {
            "registered": False,
            "message": f"Face template stored but token-server unreachable: {e}",
        }

    return {
        "registered": True,
        "message": (
            f"Face template registered for '{username}'. "
            "User may now authenticate with face biometrics."
        ),
    }
