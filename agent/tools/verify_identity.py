"""
Tool: verify_identity
Compares the captured face embedding against the stored biometric template.
Called only during login flow, after detect_liveness passes.
"""
import numpy as np

import face_db
from config import get_settings

TOOL_SPEC = {
    "name": "verify_identity",
    "description": (
        "Compare the captured face embedding against the stored template for this username. "
        "Returns matched=true if cosine similarity meets the MAS-required threshold. "
        "Only call this during login after detect_liveness returns passed=true."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "Username to verify identity for.",
            },
        },
        "required": ["username"],
    },
}


def execute(username: str, embedding: np.ndarray | None = None) -> dict:
    settings = get_settings()
    threshold = settings.face_similarity_threshold

    if embedding is None:
        return {
            "matched": False,
            "similarity": 0.0,
            "message": "No face embedding available. Run detect_liveness first.",
        }

    stored = face_db.load_template(username)
    if stored is None:
        return {
            "matched": False,
            "similarity": 0.0,
            "message": (
                f"No face template found for '{username}'. "
                "User must complete biometric registration before logging in."
            ),
        }

    similarity = face_db.cosine_similarity(stored, embedding)
    matched = similarity >= threshold

    return {
        "matched": matched,
        "similarity": round(float(similarity), 4),
        "threshold": threshold,
        "message": (
            f"Identity verified. Similarity {similarity:.4f} >= threshold {threshold}."
            if matched
            else (
                f"Identity verification FAILED. "
                f"Similarity {similarity:.4f} < threshold {threshold}. "
                "Face does not match registered template."
            )
        ),
    }
