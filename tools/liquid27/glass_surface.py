from __future__ import annotations

from functools import lru_cache
import numpy as np
from PIL import Image, ImageFilter


def smoothstep(a: float, b: float, x):
    t = np.clip((x - a) / max(b - a, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _normalize3(nx, ny, nz):
    m = np.maximum(np.sqrt(nx * nx + ny * ny + nz * nz), 1e-6)
    return nx / m, ny / m, nz / m


@lru_cache(maxsize=16)
def enclosure_surface(size: int, exponent: float = 4.0):
    """Scale-invariant convex superellipse optical surface."""
    yy, xx = np.indices((size, size), dtype=np.float32)
    c = (size - 1) * .5
    xn = (xx - c) / max(c, 1.0)
    yn = (yy - c) / max(c, 1.0)
    q = (np.abs(xn) ** exponent + np.abs(yn) ** exponent) ** (1.0 / exponent)
    inside = (q <= 1.0).astype(np.float32)
    signed_distance = (1.0 - q) * inside

    # A broad dome with a steep rolloff in the final edge zone. Derivatives are
    # taken in normalized surface coordinates, so normals are stable from 48 px
    # launcher icons through 768 px debug renders.
    core = np.clip(1.0 - q ** 2.45, 0.0, 1.0)
    height = (core ** .70) * inside
    spacing = 2.0 / max(size - 1, 1)
    gy, gx = np.gradient(height, spacing, spacing)
    slope_scale = .58
    nx, ny, nz = _normalize3(-gx * slope_scale, -gy * slope_scale, np.ones_like(gx))

    gradmag = np.sqrt(gx * gx + gy * gy)
    curvature = np.clip(gradmag * .52, 0.0, 1.0) * inside
    center = smoothstep(.72, .20, q) * inside
    mid = np.exp(-((q - .60) / .22) ** 2) * inside
    edge = smoothstep(.54, .91, q) * inside
    rim = smoothstep(.80, 1.00, q) * inside
    very_rim = smoothstep(.925, 1.00, q) * inside

    thickness = (.15 + .18 * mid + .58 * edge + .95 * very_rim) * inside

    view_cos = np.clip(nz, 0.0, 1.0)
    f0 = 0.035
    fresnel = (f0 + (1.0 - f0) * (1.0 - view_cos) ** 5) * inside
    fsoft = np.clip(fresnel * .60 + edge * .085, 0.0, 1.0)
    fmid = np.clip(fresnel * .90 + rim * .18, 0.0, 1.0)
    ftight = np.clip(fresnel * 1.10 + very_rim * .34, 0.0, 1.0)

    return {
        'q': q, 'inside': inside, 'signed_distance': signed_distance,
        'height': height, 'gx': gx, 'gy': gy,
        'nx': nx, 'ny': ny, 'nz': nz, 'curvature': curvature,
        'center': center, 'mid': mid, 'edge': edge, 'rim': rim,
        'very_rim': very_rim, 'thickness': thickness,
        'fresnel': fresnel, 'fsoft': fsoft, 'fmid': fmid, 'ftight': ftight,
    }


def glyph_surface(mask: Image.Image, size: int):
    """Secondary dielectric surface derived from arbitrary glyph geometry."""
    m = mask.resize((size, size), Image.Resampling.LANCZOS)
    a = np.asarray(m, dtype=np.float32) / 255.0
    broad = np.asarray(m.filter(ImageFilter.GaussianBlur(max(.8, size * .012))), dtype=np.float32) / 255.0
    inner = np.clip(broad ** .72, 0.0, 1.0) * (a > .02)
    spacing = 2.0 / max(size - 1, 1)
    gy, gx = np.gradient(inner, spacing, spacing)
    nx, ny, nz = _normalize3(-gx * .34, -gy * .34, np.ones_like(gx))
    gradmag = np.sqrt(gx * gx + gy * gy)
    curvature = np.clip(gradmag * .34, 0.0, 1.0)
    edge = np.clip(curvature * 1.20, 0.0, 1.0) * a
    thickness = np.clip(.12 * a + .60 * broad + .78 * edge, 0.0, 1.35)
    view_cos = np.clip(nz, 0.0, 1.0)
    f0 = .038
    fresnel = (f0 + (1.0 - f0) * (1.0 - view_cos) ** 5) * a
    return {
        'alpha': a, 'height': inner, 'gx': gx, 'gy': gy,
        'nx': nx, 'ny': ny, 'nz': nz, 'curvature': curvature,
        'edge': edge, 'thickness': thickness, 'fresnel': fresnel,
    }
