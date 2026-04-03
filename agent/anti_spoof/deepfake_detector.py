"""
Deepfake / Synthetic Face Detector — Frequency Domain Analysis

GAN-generated and diffusion-model faces leave characteristic artifacts
in the frequency domain that differ from real camera-captured photos:

  1. GAN fingerprints: regular spectral peaks from upsampling grids
  2. Blending artifacts: abrupt frequency transitions at face boundaries
  3. Texture unnaturalness: abnormal high-frequency energy distribution

Method:
  - Apply 2D DCT to luminance channel of the face crop
  - Compute log power spectrum
  - Measure spectral irregularity (variance in radial bins)
  - Check for periodic grid artifacts via autocorrelation
  - Normalize to [0, 1] deepfake_score (higher = more likely synthetic)

MAS Sep 2025 deepfake paper requirement:
  This covers GAN/diffusion synthetic faces (injection attacks).
  For adversarial deepfake video injection, combine with a
  certified video deepfake detector in the capture pipeline.

Note: This is a signal-level heuristic suitable for demo/dev.
For production: use a trained deepfake classifier (e.g. EfficientNet
fine-tuned on FaceForensics++) — requires significant training data.
"""
import cv2
import numpy as np
from scipy.fft import dctn

_CROP_SIZE = (128, 128)


def _face_crop(img_bgr: np.ndarray, bbox: np.ndarray) -> np.ndarray:
    """Crop face region (1.3x scale) and resize to standard size."""
    h, w = img_bgr.shape[:2]
    x1, y1, x2, y2 = bbox.astype(int)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    half = int(max(x2 - x1, y2 - y1) * 0.65)

    left   = max(0, cx - half)
    right  = min(w, cx + half)
    top    = max(0, cy - half)
    bottom = min(h, cy + half)

    crop = img_bgr[top:bottom, left:right]
    if crop.size == 0:
        crop = img_bgr
    return cv2.resize(crop, _CROP_SIZE)


def _radial_spectrum(dct_log: np.ndarray, num_bins: int = 16) -> np.ndarray:
    """Bin DCT coefficients into radial frequency rings and return mean per bin."""
    h, w = dct_log.shape
    cx, cy = h // 2, w // 2
    y_idx, x_idx = np.mgrid[0:h, 0:w]
    radius = np.sqrt((y_idx - cx) ** 2 + (x_idx - cy) ** 2)
    max_r = radius.max()

    bins = np.zeros(num_bins)
    for i in range(num_bins):
        r_lo = max_r * i / num_bins
        r_hi = max_r * (i + 1) / num_bins
        mask = (radius >= r_lo) & (radius < r_hi)
        if mask.any():
            bins[i] = dct_log[mask].mean()
    return bins


def _grid_artifact_score(dct_log: np.ndarray) -> float:
    """
    Detect GAN upsampling grid artifacts.
    GANs with stride-2 upsampling leave periodic peaks every N pixels.
    Measure via autocorrelation of the DCT spectrum.
    Returns 0 (clean) to 1 (strong grid artifact).
    """
    # Autocorrelation of the spectrum
    spectrum = np.exp(dct_log)  # undo log
    ac = np.abs(np.fft.fft2(spectrum))
    ac_norm = ac / (ac.max() + 1e-8)

    # Mask DC component (always highest)
    h, w = ac_norm.shape
    ac_norm[0, 0] = 0

    # Score: how much energy is in off-DC peaks relative to total
    threshold = 0.3
    peak_energy = (ac_norm > threshold).sum() / ac_norm.size
    return float(np.clip(peak_energy * 20, 0, 1))  # scale to [0,1]


def _high_freq_energy_ratio(dct_log: np.ndarray) -> float:
    """
    Real camera images have natural 1/f spectrum (high-freq energy decreases smoothly).
    Synthetic images often show unnatural high-freq energy from texture generation.
    Returns ratio of high-freq to low-freq energy (higher = more synthetic-looking).
    """
    h, w = dct_log.shape
    mid_h, mid_w = h // 2, w // 2
    low_freq  = np.exp(dct_log[:mid_h, :mid_w]).sum()
    high_freq = np.exp(dct_log[mid_h:, mid_w:]).sum()
    total = low_freq + high_freq + 1e-8
    return float(high_freq / total)


def score(img_bgr: np.ndarray, bbox: np.ndarray) -> float:
    """
    Compute deepfake_score for a face image.
    Returns 0.0 (certainly real) to 1.0 (certainly synthetic).

    img_bgr: full image in BGR format (from OpenCV).
    bbox: np.array([x1, y1, x2, y2]) from InsightFace.
    """
    crop = _face_crop(img_bgr, bbox)

    # Work in luminance (Y channel of YCrCb)
    ycrcb = cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb)
    luma = ycrcb[:, :, 0].astype(np.float32)

    # 2D DCT of luminance
    dct_coeffs = dctn(luma, norm="ortho")
    dct_log = np.log(np.abs(dct_coeffs) + 1e-8)

    # Feature 1: radial spectral flatness (real faces have 1/f rolloff)
    bins = _radial_spectrum(dct_log)
    # Fit expected 1/f decay and measure deviation
    expected = np.linspace(bins[0], bins[-1], len(bins))
    spectral_deviation = float(np.std(bins - expected) / (np.abs(bins).mean() + 1e-8))
    spectral_deviation = np.clip(spectral_deviation, 0, 1)

    # Feature 2: GAN grid artifacts
    grid_score = _grid_artifact_score(dct_log)

    # Feature 3: high-frequency energy ratio
    hf_ratio = _high_freq_energy_ratio(dct_log)
    # Real camera images: hf_ratio typically 0.05–0.20
    # GAN/diffusion: often > 0.25 due to texture over-sharpening
    hf_score = float(np.clip((hf_ratio - 0.10) / 0.25, 0, 1))

    # Weighted combination
    deepfake_score = 0.4 * spectral_deviation + 0.4 * grid_score + 0.2 * hf_score

    return round(float(np.clip(deepfake_score, 0.0, 1.0)), 4)
