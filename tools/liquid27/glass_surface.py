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
    """Convex superellipse glass surface used by every preview optical effect."""
    yy, xx = np.indices((size, size), dtype=np.float32)
    c = (size - 1) * .5
    xn = (xx - c) / max(c, 1.0)
    yn = (yy - c) / max(c, 1.0)
    q = (np.abs(xn) ** exponent + np.abs(yn) ** exponent) ** (1.0 / exponent)
    inside = (q <= 1.0).astype(np.float32)
    signed_distance = (1.0 - q) * inside

    # Broad convex body with a deliberately steep final rolloff. This produces
    # a real normal field instead of a decorative edge mask.
    core = np.clip(1.0 - q ** 2.35, 0.0, 1.0)
    height = (core ** .72) * inside
    gy, gx = np.gradient(height)
    slope_scale = 5.2
    nx, ny, nz = _normalize3(-gx * slope_scale, -gy * slope_scale, np.ones_like(gx))

    gradmag = np.sqrt(gx * gx + gy * gy)
    curvature = np.clip(gradmag * size * 1.55, 0.0, 1.0) * inside
    center = smoothstep(.72, .20, q) * inside
    mid = np.exp(-((q - .60) / .22) ** 2) * inside
    edge = smoothstep(.55, .92, q) * inside
    rim = smoothstep(.82, 1.00, q) * inside
    very_rim = smoothstep(.925, 1.00, q) * inside

    # Apparent optical path, not opacity. Kept small in the centre and rises
    # strongly as the surface turns toward grazing incidence.
    thickness = (.18 + .22 * mid + .62 * edge + .92 * very_rim) * inside

    view_cos = np.clip(nz, 0.0, 1.0)
    f0 = 0.035
    fresnel = (f0 + (1.0 - f0) * (1.0 - view_cos) ** 5) * inside
    fsoft = np.clip(fresnel * .55 + edge * .10, 0.0, 1.0)
    fmid = np.clip(fresnel * .80 + rim * .22, 0.0, 1.0)
    ftight = np.clip(fresnel + very_rim * .48, 0.0, 1.0)

    return {
        'q': q, 'inside': inside, 'signed_distance': signed_distance,
        'height': height, 'gx': gx, 'gy': gy,
        'nx': nx, 'ny': ny, 'nz': nz, 'curvature': curvature,
        'center': center, 'mid': mid, 'edge': edge, 'rim': rim,
        'very_rim': very_rim, 'thickness': thickness,
        'fresnel': fresnel, 'fsoft': fsoft, 'fmid': fmid, 'ftight': ftight,
    }


def glyph_surface(mask: Image.Image, size: int):
    """Build a secondary dielectric surface directly from arbitrary glyph geometry."""
    m = mask.resize((size, size), Image.Resampling.LANCZOS)
    # Two scales make broad glyph masses transparent lenses while retaining
    # strong curvature on thin strokes.
    a = np.asarray(m, dtype=np.float32) / 255.0
    broad = np.asarray(m.filter(ImageFilter.GaussianBlur(max(.8, size * .012))), dtype=np.float32) / 255.0
    inner = np.clip(broad ** .72, 0.0, 1.0) * (a > .02)
    gy, gx = np.gradient(inner)
    nx, ny, nz = _normalize3(-gx * 7.4, -gy * 7.4, np.ones_like(gx))
    gradmag = np.sqrt(gx * gx + gy * gy)
    curvature = np.clip(gradmag * size * 2.1, 0.0, 1.0)
    edge = np.clip(curvature * 1.15, 0.0, 1.0) * a
    thickness = np.clip(.18 * a + .76 * broad + .70 * edge, 0.0, 1.45)
    view_cos = np.clip(nz, 0.0, 1.0)
    f0 = .038
    fresnel = (f0 + (1.0 - f0) * (1.0 - view_cos) ** 5) * a
    return {
        'alpha': a, 'height': inner, 'gx': gx, 'gy': gy,
        'nx': nx, 'ny': ny, 'nz': nz, 'curvature': curvature,
        'edge': edge, 'thickness': thickness, 'fresnel': fresnel,
    }
