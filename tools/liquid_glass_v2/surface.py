from __future__ import annotations

import numpy as np


def smoothstep(a: float, b: float, x):
    t = np.clip((x - a) / max(b - a, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def superellipse_surface(size: int, exponent: float = 4.6):
    """Independent v2 convex lens field. No legacy Clear material code is used."""
    yy, xx = np.indices((size, size), dtype=np.float32)
    c = (size - 1) * 0.5
    xn = (xx - c) / max(c, 1.0)
    yn = (yy - c) / max(c, 1.0)
    q = (np.abs(xn) ** exponent + np.abs(yn) ** exponent) ** (1.0 / exponent)
    inside = (q <= 1.0).astype(np.float32)

    # A flatter core and a deliberately broad, steep shoulder. The old renderer
    # behaved like a plate with a rim; v2 reserves a large fraction of the icon
    # for curved optical volume.
    core = np.clip(1.0 - q, 0.0, 1.0)
    shoulder = smoothstep(0.48, 0.96, q) * inside
    lip = smoothstep(0.82, 1.0, q) * inside
    very_lip = smoothstep(0.935, 1.0, q) * inside
    height = (0.10 + 0.90 * (core ** 0.46)) * inside

    spacing = 2.0 / max(size - 1, 1)
    gy, gx = np.gradient(height, spacing, spacing)
    slope = 0.82
    nx = -gx * slope
    ny = -gy * slope
    nz = np.ones_like(nx)
    mag = np.maximum(np.sqrt(nx * nx + ny * ny + nz * nz), 1e-6)
    nx, ny, nz = nx / mag, ny / mag, nz / mag

    # Apparent path length intentionally rises in the shoulder/lip. This is a
    # perceptual thickness map, not opacity.
    thickness = (0.10 + 0.16 * smoothstep(0.18, 0.62, q) + 0.55 * shoulder + 0.82 * lip + 0.40 * very_lip) * inside

    # Schlick-like view response, then widened perceptually so the edge is a
    # region rather than a one-pixel border.
    f0 = 0.035
    fresnel = (f0 + (1.0 - f0) * (1.0 - np.clip(nz, 0.0, 1.0)) ** 5) * inside
    broad_fresnel = np.clip(fresnel * 0.55 + shoulder * 0.18, 0.0, 1.0)
    tight_fresnel = np.clip(fresnel * 1.15 + lip * 0.36 + very_lip * 0.22, 0.0, 1.0)

    return {
        'q': q, 'inside': inside, 'height': height,
        'nx': nx, 'ny': ny, 'nz': nz,
        'shoulder': shoulder, 'lip': lip, 'very_lip': very_lip,
        'thickness': thickness,
        'fresnel': fresnel,
        'broad_fresnel': broad_fresnel,
        'tight_fresnel': tight_fresnel,
    }
