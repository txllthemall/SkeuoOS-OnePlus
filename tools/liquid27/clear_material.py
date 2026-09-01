from __future__ import annotations

"""Compatibility entry point for the Clear material pipeline.

The actual v4.1 high-polish implementation lives in clear_material_apple.py.
Keep the low-level bilinear sampler here so that the implementation can import
it without changing existing generator imports.
"""

import numpy as np


def _bilinear_warp(rgb: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    yy, xx = np.indices((h, w), dtype=np.float32)
    sx = np.clip(xx + dx, 0, w - 1.001)
    sy = np.clip(yy + dy, 0, h - 1.001)
    x0 = np.floor(sx).astype(np.int32)
    y0 = np.floor(sy).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    wx = (sx - x0)[..., None]
    wy = (sy - y0)[..., None]
    a = rgb[y0, x0] * (1 - wx) + rgb[y0, x1] * wx
    b = rgb[y1, x0] * (1 - wx) + rgb[y1, x1] * wx
    return np.clip(a * (1 - wy) + b * wy, 0, 255).astype(np.uint8)


# Public API remains unchanged for generate_liquid27.py and QA tooling.
from .clear_material_apple import (  # noqa: E402,F401
    clearify_layers,
    clear_background,
    finish_clear_enclosure,
    clear_reflection_mask,
    clear_reflection_coverage_pct,
    reflection_style,
    preview_refract_patch,
    material_metrics,
)

__all__ = [
    'clearify_layers',
    'clear_background',
    'finish_clear_enclosure',
    'clear_reflection_mask',
    'clear_reflection_coverage_pct',
    'reflection_style',
    'preview_refract_patch',
    'material_metrics',
]
