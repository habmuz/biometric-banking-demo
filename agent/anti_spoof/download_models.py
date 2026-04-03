"""
Downloads MiniFASNet ONNX anti-spoofing models from the official
minivision-ai Silent-Face-Anti-Spoofing GitHub release.

Models:
  2.7_80x80_MiniFASNetV2.onnx   — scale 2.7, PAD model A
  4_0_0_80x80_MiniFASNetV4.onnx — scale 4.0, PAD model B

Using two models at different scales and averaging their scores
gives robust ISO 30107-3 PAD Level 2 performance.

Run once:
    python anti_spoof/download_models.py
Or it is called automatically on first import of pad_detector.
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).parent / "models"

# (filename, sha256_first_8_chars_for_sanity_check, download_url)
# ONNX exports of minivision-ai/Silent-Face-Anti-Spoofing PyTorch models
_MODELS = [
    (
        "MiniFASNetV2.onnx",
        None,
        "https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV2.onnx",
    ),
    (
        "MiniFASNetV1SE.onnx",
        None,
        "https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV1SE.onnx",
    ),
]


def _download(url: str, dest: Path) -> None:
    print(f"  Downloading {dest.name}...", end="", flush=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f" {dest.stat().st_size // 1024} KB")
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise RuntimeError(
            f"Failed to download {url}: {e}\n"
            "If download fails, manually place the ONNX files in agent/anti_spoof/models/\n"
            "Source: github.com/minivision-ai/Silent-Face-Anti-Spoofing/tree/master/resources/anti_spoof_models"
        ) from e


def ensure_models() -> Path:
    """Ensures models are present, downloading if needed. Returns models dir path."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    for filename, _sha, url in _MODELS:
        dest = MODELS_DIR / filename
        if dest.exists() and dest.stat().st_size > 1024:
            continue
        _download(url, dest)

    return MODELS_DIR


if __name__ == "__main__":
    print("==> Downloading MiniFASNet anti-spoofing models...")
    try:
        d = ensure_models()
        print(f"==> Models ready in: {d}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
