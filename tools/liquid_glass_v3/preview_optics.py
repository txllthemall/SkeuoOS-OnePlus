from __future__ import annotations

import numpy as np
from PIL import Image

from .material import MaterialParams, schlick_fresnel
from .surface import SurfaceMaps


def _bilinear_sample(arr: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    yy, xx = np.indices((h, w), dtype=np.float32)
    sx = np.clip(xx + dx, 0.0, w - 1.001)
    sy = np.clip(yy + dy, 0.0, h - 1.001)
    x0 = np.floor(sx).astype(np.int32)
    y0 = np.floor(sy).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    wx = (sx - x0)[..., None]
    wy = (sy - y0)[..., None]
    a = arr[y0, x0]
    b = arr[y0, x1]
    c = arr[y1, x0]
    d = arr[y1, x1]
    return a * (1 - wx) * (1 - wy) + b * wx * (1 - wy) + c * (1 - wx) * wy + d * wx * wy


def _normalize(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-8)


def _refract(i: np.ndarray, n: np.ndarray, eta: float) -> np.ndarray:
    """Vectorized GLSL-style refract(I, N, eta)."""
    dotni = np.sum(n * i, axis=-1, keepdims=True)
    k = 1.0 - eta * eta * (1.0 - dotni * dotni)
    root = np.sqrt(np.maximum(k, 0.0))
    t = eta * i - (eta * dotni + root) * n
    # Total internal reflection is not expected at our art-directed slopes, but
    # keep a stable fallback rather than emitting NaNs.
    bad = k[..., 0] < 0.0
    if np.any(bad):
        t[bad] = i[bad]
    return _normalize(t).astype(np.float32)


def _two_interface_flow(
    front_normals: np.ndarray,
    back_normals: np.ndarray,
    thickness: np.ndarray,
    ior: float,
    scale: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Trace a view ray through the front and back height-field interfaces.

    The wallpaper is treated as a shallow virtual plane behind the glass. The
    first term is lateral travel inside the material, while the second is the
    exit-ray travel over a small backdrop gap. This creates scale/compression
    changes that a one-interface radial warp cannot reproduce.
    """
    h, w = thickness.shape
    incident = np.zeros((h, w, 3), dtype=np.float32)
    incident[..., 2] = -1.0

    # Air -> glass.
    inside = _refract(incident, front_normals, 1.0 / max(ior, 1.0001))

    # Lateral travel inside the actual V3 thickness field.
    travel_inside = thickness / np.maximum(-inside[..., 2], 1e-4)
    dx_inside = inside[..., 0] * travel_inside
    dy_inside = inside[..., 1] * travel_inside

    # Glass -> air. Surface normals returned by the height field point upward;
    # the outward normal of the lower interface points downward.
    back_outward = -back_normals
    exited = _refract(inside, back_outward, max(ior, 1.0001))

    # Virtual backdrop gap is deliberately shallow. It makes the second
    # interface visible without turning the icon into an exaggerated lens demo.
    gap = 0.18 + 0.22 * np.clip(thickness, 0.0, 1.0)
    travel_air = gap / np.maximum(-exited[..., 2], 1e-4)
    dx_air = exited[..., 0] * travel_air
    dy_air = exited[..., 1] * travel_air

    return (dx_inside + dx_air) * scale, (dy_inside + dy_air) * scale


def render_optical_preview(
    maps: SurfaceMaps,
    wallpaper: Image.Image,
    *,
    params: MaterialParams = MaterialParams(),
    displacement_scale: float = 34.0,
    specular: bool = True,
) -> Image.Image:
    """Wallpaper-aware V3 optical preview. Never used for production PNG."""
    size = maps.container_mask.shape[0]
    bg = wallpaper.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    arr = np.asarray(bg, dtype=np.float32)

    dx, dy = _two_interface_flow(
        maps.front_normals,
        maps.back_normals,
        maps.thickness,
        params.ior,
        displacement_scale,
    )

    primary = _bilinear_sample(arr, dx, dy)

    # Multi-sample only in high-curvature regions. This is optical integration
    # at the shell, not a global Gaussian blur.
    front_s = maps.front_slope
    back_s = maps.back_slope
    fs = front_s / max(float(np.percentile(front_s, 99.5)), 1e-6)
    bs = back_s / max(float(np.percentile(back_s, 99.5)), 1e-6)
    edge = np.clip(0.62 * fs + 0.38 * bs, 0.0, 1.0)[..., None]

    secondary = _bilinear_sample(arr, dx * 0.90 - dy * 0.055, dy * 0.90 + dx * 0.055)
    tertiary = _bilinear_sample(arr, dx * 1.04 + dy * 0.030, dy * 1.04 - dx * 0.030)
    glass = primary * (1.0 - 0.20 * edge) + secondary * (0.13 * edge) + tertiary * (0.07 * edge)

    # Compression/expansion cue from the optical-flow Jacobian.
    ddx_dx = np.gradient(dx, axis=1)
    ddy_dy = np.gradient(dy, axis=0)
    compression = np.clip(-(ddx_dx + ddy_dy) * 0.042, -0.07, 0.09)
    glass *= 1.0 + compression[..., None]

    nf = maps.front_normals
    nb = maps.back_normals
    ndotv = np.clip(nf[..., 2], 0.0, 1.0)
    fresnel = schlick_fresnel(ndotv, params.ior)

    # Environmental response samples around BOTH interfaces. Hue comes only
    # from the wallpaper; the renderer adds no intrinsic cyan/blue tint.
    env_front = _bilinear_sample(arr, -dx * 0.20 + 5.0 * nf[..., 0], -dy * 0.20 + 5.0 * nf[..., 1])
    env_back = _bilinear_sample(arr, dx * 0.10 - 3.0 * nb[..., 0], dy * 0.10 - 3.0 * nb[..., 1])
    env = 0.68 * env_front + 0.32 * env_back
    env_w = np.clip((0.055 + 0.30 * fresnel) * maps.container_mask, 0.0, 0.25)[..., None]
    glass = glass * (1.0 - env_w) + env * env_w

    if specular:
        light = np.array([-0.42, -0.74, 0.52], dtype=np.float32)
        light /= max(float(np.linalg.norm(light)), 1e-6)
        view = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        halfv = light + view
        halfv /= max(float(np.linalg.norm(halfv)), 1e-6)
        ndoth = np.clip(nf[..., 0] * halfv[0] + nf[..., 1] * halfv[1] + nf[..., 2] * halfv[2], 0.0, 1.0)
        sp = np.power(ndoth, 38.0) * (0.18 + 0.82 * fresnel)
        surface = np.clip(maps.container_mask + 0.58 * maps.glyph_mask, 0.0, 1.0)
        sp *= surface
        glass = glass * (1.0 - 0.14 * sp[..., None]) + 255.0 * (0.14 * sp[..., None])

    # Clear center, stronger shell, and a second optical pass through the glyph
    # because the glyph already changes both front and back surfaces.
    core = np.clip(maps.container_profile * maps.container_mask, 0.0, 1.0)[..., None]
    glyph_volume = np.clip(0.45 * maps.glyph_profile + 0.55 * maps.glyph_back_profile, 0.0, 1.0)[..., None]
    effect = np.clip(
        (1.0 - 0.70 * core) * maps.container_mask[..., None]
        + 0.34 * glyph_volume,
        0.0,
        1.0,
    )
    out = arr * (1.0 - effect) + glass * effect
    return Image.fromarray(np.clip(out, 0.0, 255.0).astype(np.uint8), "RGB")
