"""
Tool 2: detect_liveness
Runs InsightFace buffalo_l for face detection/embedding, then:
  - MiniFASNet (2 ONNX models, scales 2.7 + 4.0) for PAD liveness scoring
  - DCT frequency analysis for deepfake/synthetic face detection

Thresholds: liveness_score >= 0.85 AND deepfake_score <= 0.15
Satisfies: ISO 30107-3 PAD Level 2 (anti-spoofing), MAS Sep 2025 deepfake guidance.
PDPA: raw image bytes are never written to disk.
"""
import base64
import threading
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

from anti_spoof import pad_score, deepfake_score
from config import get_settings

# Tool schema
TOOL_SPEC = {
    "name": "detect_liveness",
    "description": (
        "Run liveness detection and deepfake analysis on a face image using InsightFace buffalo_l. "
        "Returns liveness_score (0-1), deepfake_score (0-1), and whether the face passes "
        "MAS ISO 30107-3 PAD Level 2 thresholds. Also returns the face embedding vector "
        "for template matching."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "image_b64": {
                "type": "string",
                "description": "Base64-encoded face image (same as provided to validate_face_capture).",
            },
            "username": {
                "type": "string",
                "description": "Username — used for audit logging only, not stored with embedding.",
            },
        },
        "required": ["image_b64", "username"],
    },
}

_model_lock = threading.Lock()
_app = None  # InsightFace FaceAnalysis app


def _get_model():
    """Lazy-load buffalo_l once; thread-safe."""
    global _app
    if _app is None:
        with _model_lock:
            if _app is None:
                import insightface
                settings = get_settings()
                app = insightface.app.FaceAnalysis(
                    name=settings.insightface_model,
                    providers=["CPUExecutionProvider"],
                )
                app.prepare(ctx_id=settings.insightface_ctx_id, det_size=(640, 640))
                _app = app
    return _app


def _run_pad(img_bgr: np.ndarray, bbox: np.ndarray) -> tuple[float, float]:
    """
    Run real PAD + deepfake detection:
      liveness_score  — MiniFASNet: probability of a real live face (0–1)
      deepfake_score  — DCT frequency analysis: probability of synthetic face (0–1)
    """
    liveness = pad_score(img_bgr, bbox)
    synthetic = deepfake_score(img_bgr, bbox)
    return liveness, synthetic


def execute(image_b64: str, username: str) -> dict:
    settings = get_settings()

    # Decode image
    try:
        image_bytes = base64.b64decode(image_b64)
        pil_img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(pil_img)
    except Exception as e:
        return {
            "passed": False,
            "liveness_score": 0.0,
            "deepfake_score": 1.0,
            "message": f"Image decode error: {e}",
            "embedding": None,
        }

    # Run InsightFace
    try:
        model = _get_model()
        # InsightFace expects BGR
        import cv2
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        faces = model.get(img_bgr)
    except Exception as e:
        return {
            "passed": False,
            "liveness_score": 0.0,
            "deepfake_score": 1.0,
            "message": f"InsightFace error: {e}",
            "embedding": None,
        }

    if not faces:
        return {
            "passed": False,
            "liveness_score": 0.0,
            "deepfake_score": 1.0,
            "message": "InsightFace found no face in image.",
            "embedding": None,
        }

    face = faces[0]
    det_score = float(face.det_score)
    embedding = face.normed_embedding  # 512-dim float32 vector
    bbox = face.bbox  # [x1, y1, x2, y2]

    liveness_score, dfscore = _run_pad(img_bgr, bbox)

    passed = (
        liveness_score >= settings.liveness_threshold
        and dfscore <= settings.deepfake_threshold
    )

    result = {
        "passed": passed,
        "liveness_score": liveness_score,
        "deepfake_score": dfscore,
        "det_score": round(det_score, 4),
        "message": (
            "Liveness check passed. Real face confirmed."
            if passed
            else (
                f"Liveness check FAILED. "
                f"liveness={liveness_score} (need >={settings.liveness_threshold}), "
                f"deepfake={dfscore} (need <={settings.deepfake_threshold})."
            )
        ),
        "pad_model": "MiniFASNetV2+V4 (2-scale ensemble)",
        "deepfake_model": "DCT frequency analysis",
        # ISO 24745: embedding is returned for template matching but raw image is NOT stored
        "embedding_dim": len(embedding),
        "embedding_preview": embedding[:4].tolist(),  # first 4 dims for debug only
    }

    # Full embedding passed back to agent for potential template registration
    # Stored as list so it's JSON-serializable
    result["embedding"] = embedding.tolist()

    return result
