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
    """Vectorized GLSL-style refract(I, N, eta), used for front entry only."""
    dotni = np.sum(n * i, axis=-1, keepdims=True)
    k = 1.0 - eta * eta * (1.0 - dotni * dotni)
    root = np.sqrt(np.maximum(k, 0.0))
    t = eta * i - (eta * dotni + root) * n
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
    """Stable paired-interface optical flow for the preview renderer.

    We use Snell refraction for AIR->GLASS entry, then use the difference
    between front/back interface orientation as a bounded exit correction.
    This keeps the physically meaningful cause/effect (normals + thickness)
    while avoiding near-grazing singularities that produced noisy TIR-like
    speckle in the first paired-interface experiment.
    """
    h, w = thickness.shape
    incident = np.zeros((h, w, 3), dtype=np.float32)
    incident[..., 2] = -1.0

    inside = _refract(incident, front_normals, 1.0 / max(ior, 1.0001))
    travel = thickness / np.maximum(-inside[..., 2], 0.34)
    dx_inside = inside[..., 0] * travel
    dy_inside = inside[..., 1] * travel

    # Back interface contributes a bounded differential-lens term. This is
    # spatially distinct from the front surface because its height field is
    # generated from the variable-thickness back profile.
    dnx = front_normals[..., 0] - back_normals[..., 0]
    dny = front_normals[..., 1] - back_normals[..., 1]
    exit_gain = 0.62 * thickness
    dx_exit = dnx * exit_gain
    dy_exit = dny * exit_gain

    dx = (dx_inside + dx_exit) * scale
    dy = (dy_inside + dy_exit) * scale

    # Hard visual-safety clamp. This is not an artistic rim; it merely prevents
    # pathological UV jumps when a sampled silhouette contains a near-vertical
    # one-pixel slope after rasterization.
    limit = max(10.0, 0.055 * float(min(h, w)))
    mag = np.sqrt(dx * dx + dy * dy)
    gain = np.minimum(1.0, limit / np.maximum(mag, 1e-6))
    return (dx * gain).astype(np.float32), (dy * gain).astype(np.float32)


def render_optical_preview(
    maps: SurfaceMaps,
    wallpaper: Image.Image,
    *,
    params: MaterialParams = MaterialParams(),
    displacement_scale: float = 30.0,
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

    front_s = maps.front_slope
    back_s = maps.back_slope
    fs = front_s / max(float(np.percentile(front_s, 99.5)), 1e-6)
    bs = back_s / max(float(np.percentile(back_s, 99.5)), 1e-6)
    edge = np.clip(0.62 * fs + 0.38 * bs, 0.0, 1.0)[..., None]

    # Small optical integration near curved zones. The center remains a single
    # crisp sample; only high-slope areas blend secondary rays.
    secondary = _bilinear_sample(arr, dx * 0.90 - dy * 0.045, dy * 0.90 + dx * 0.045)
    glass = primary * (1.0 - 0.14 * edge) + secondary * (0.14 * edge)

    # Weak caustic-like luminance redistribution from flow divergence.
    ddx_dx = np.gradient(dx, axis=1)
    ddy_dy = np.gradient(dy, axis=0)
    compression = np.clip(-(ddx_dx + ddy_dy) * 0.030, -0.045, 0.060)
    glass *= 1.0 + compression[..., None]

    nf = maps.front_normals
    nb = maps.back_normals
    ndotv = np.clip(nf[..., 2], 0.0, 1.0)
    fresnel = schlick_fresnel(ndotv, params.ior)

    env_front = _bilinear_sample(arr, -dx * 0.18 + 4.0 * nf[..., 0], -dy * 0.18 + 4.0 * nf[..., 1])
    env_back = _bilinear_sample(arr, dx * 0.08 - 2.5 * nb[..., 0], dy * 0.08 - 2.5 * nb[..., 1])
    env = 0.72 * env_front + 0.28 * env_back
    env_w = np.clip((0.045 + 0.24 * fresnel) * maps.container_mask, 0.0, 0.19)[..., None]
    glass = glass * (1.0 - env_w) + env * env_w

    if specular:
        light = np.array([-0.42, -0.74, 0.52], dtype=np.float32)
        light /= max(float(np.linalg.norm(light)), 1e-6)
        view = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        halfv = light + view
        halfv /= max(float(np.linalg.norm(halfv)), 1e-6)
        ndoth = np.clip(nf[..., 0] * halfv[0] + nf[..., 1] * halfv[1] + nf[..., 2] * halfv[2], 0.0, 1.0)
        sp = np.power(ndoth, 40.0) * (0.16 + 0.84 * fresnel)
        sp *= np.clip(maps.container_mask + 0.56 * maps.glyph_mask, 0.0, 1.0)
        glass = glass * (1.0 - 0.11 * sp[..., None]) + 255.0 * (0.11 * sp[..., None])

    core = np.clip(maps.container_profile * maps.container_mask, 0.0, 1.0)[..., None]
    glyph_volume = np.clip(0.45 * maps.glyph_profile + 0.55 * maps.glyph_back_profile, 0.0, 1.0)[..., None]
    effect = np.clip(
        (1.0 - 0.74 * core) * maps.container_mask[..., None]
        + 0.30 * glyph_volume,
        0.0,
        1.0,
    )
    out = arr * (1.0 - effect) + glass * effect
    return Image.fromarray(np.clip(out, 0.0, 255.0).astype(np.uint8), "RGB")
