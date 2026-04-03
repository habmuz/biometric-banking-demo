"""
MiniFASNet PAD (Presentation Attack Detection)
Paper: "Searching Central Difference Convolutional Networks for Face Anti-Spoofing"
       (CVPR 2020) — minivision-ai/Silent-Face-Anti-Spoofing

Uses two ONNX models at scale factors 2.7 and 4.0.
Each model:
  - Crops the face region at its scale from the full image
  - Resizes crop to 80x80
  - Outputs 3-class softmax: [background, spoof, real]
Final liveness_score = average of real-class probability across both models.

ISO 30107-3 PAD Level 2 note:
  This open-source model meets Level 1 in isolation.
  For Level 2 production certification, combine with iBeta-certified hardware
  or a commercially certified PAD SDK.
"""
import threading
from pathlib import Path

import cv2
import numpy as np

from anti_spoof.download_models import ensure_models

# Scale factors — match the two downloaded models
_SCALES = [
    ("MiniFASNetV2.onnx", 2.7),
    ("MiniFASNetV1SE.onnx", 4.0),
]

_INPUT_SIZE = (80, 80)

# ImageNet normalization
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

_lock = threading.Lock()
_sessions: list | None = None   # list of (ort.InferenceSession, scale_factor)


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def _load_sessions():
    global _sessions
    if _sessions is not None:
        return _sessions
    with _lock:
        if _sessions is not None:
            return _sessions
        import onnxruntime as ort
        models_dir = ensure_models()
        sessions = []
        for filename, scale in _SCALES:
            path = models_dir / filename
            if not path.exists():
                raise FileNotFoundError(
                    f"Model not found: {path}. Run: python anti_spoof/download_models.py"
                )
            sess = ort.InferenceSession(
                str(path),
                providers=["CPUExecutionProvider"],
            )
            sessions.append((sess, scale))
        _sessions = sessions
    return _sessions


def _crop_face(img_bgr: np.ndarray, bbox: np.ndarray, scale: float) -> np.ndarray:
    """
    Crop the face region from the full image using a scaled bounding box.
    bbox: [x1, y1, x2, y2] from InsightFace detection.
    """
    h, w = img_bgr.shape[:2]
    x1, y1, x2, y2 = bbox.astype(int)

    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    half_w = int((x2 - x1) * scale / 2)
    half_h = int((y2 - y1) * scale / 2)

    # Clamp to image bounds
    left   = max(0, cx - half_w)
    right  = min(w, cx + half_w)
    top    = max(0, cy - half_h)
    bottom = min(h, cy + half_h)

    crop = img_bgr[top:bottom, left:right]
    if crop.size == 0:
        # Fallback: use full image
        crop = img_bgr
    return cv2.resize(crop, _INPUT_SIZE)


def _preprocess(crop_bgr: np.ndarray) -> np.ndarray:
    """Convert BGR crop → normalized float32 tensor [1, 3, 80, 80]."""
    rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    normalized = (rgb - _MEAN) / _STD
    # HWC → CHW → NCHW
    chw = normalized.transpose(2, 0, 1)
    return np.expand_dims(chw, axis=0)


def score(img_bgr: np.ndarray, bbox: np.ndarray) -> float:
    """
    Run both MiniFASNet models and return the averaged liveness score (0-1).
    Higher = more likely a real live face.
    bbox: np.array([x1, y1, x2, y2]) from InsightFace.
    """
    sessions = _load_sessions()
    real_probs = []

    for sess, scale in sessions:
        crop = _crop_face(img_bgr, bbox, scale)
        tensor = _preprocess(crop)

        input_name = sess.get_inputs()[0].name
        raw_output = sess.run(None, {input_name: tensor})[0]  # shape: (1, 3)
        probs = _softmax(raw_output[0])   # [background, spoof, real]

        # Class 2 = real (index from minivision model label map)
        real_probs.append(float(probs[2]) if len(probs) >= 3 else float(probs[1]))

    return round(float(np.mean(real_probs)), 4)
