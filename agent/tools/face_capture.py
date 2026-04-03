"""
Tool 1: validate_face_capture
Validates the base64 face image before passing to liveness detection.
Checks: decodable, single face present, minimum resolution, no truncation.
PDPA: raw bytes are only held in-process, never persisted to disk.
"""
import base64
import json
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

# Tool schema registered with Claude SDK
TOOL_SPEC = {
    "name": "validate_face_capture",
    "description": (
        "Validate a base64-encoded face image before liveness detection. "
        "Checks image integrity, detects exactly one face, and verifies minimum "
        "resolution requirements. Returns validation status and face bounding box."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "image_b64": {
                "type": "string",
                "description": "Base64-encoded JPEG or PNG face image from the mobile camera.",
            },
            "username": {
                "type": "string",
                "description": "Username attempting authentication.",
            },
        },
        "required": ["image_b64", "username"],
    },
}

# Haar cascade for fast face detection at validation stage
_face_cascade = None


def _get_cascade():
    global _face_cascade
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
    return _face_cascade


def execute(image_b64: str, username: str) -> dict:
    """
    Returns dict with keys: valid (bool), message (str), face_bbox (dict|None),
    image_shape (list|None).
    """
    # 1. Decode base64
    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        return {"valid": False, "message": "Image is not valid base64.", "face_bbox": None}

    # 2. Decode image
    try:
        pil_img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(pil_img)
    except Exception:
        return {"valid": False, "message": "Cannot decode image bytes.", "face_bbox": None}

    h, w = img_np.shape[:2]

    # 3. Minimum resolution check (MAS: sufficient biometric quality)
    if h < 224 or w < 224:
        return {
            "valid": False,
            "message": f"Image too small ({w}x{h}). Minimum 224x224 required.",
            "face_bbox": None,
        }

    # 4. Face detection — must have exactly one face
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    faces = _get_cascade().detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))

    if len(faces) == 0:
        return {"valid": False, "message": "No face detected in image.", "face_bbox": None}

    if len(faces) > 1:
        return {
            "valid": False,
            "message": f"Multiple faces detected ({len(faces)}). Only one face allowed.",
            "face_bbox": None,
        }

    x, y, fw, fh = faces[0].tolist()
    face_area_ratio = (fw * fh) / (w * h)

    # Face should occupy reasonable portion of frame
    if face_area_ratio < 0.04:
        return {
            "valid": False,
            "message": "Face too small relative to image. Move closer to camera.",
            "face_bbox": None,
        }

    return {
        "valid": True,
        "message": "Face capture valid. Proceeding to liveness detection.",
        "face_bbox": {"x": x, "y": y, "width": fw, "height": fh},
        "image_shape": [h, w],
        "face_area_ratio": round(face_area_ratio, 3),
    }
