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
    return (a * (1 - wx) * (1 - wy) + b * wx * (1 - wy) + c * (1 - wx) * wy + d * wx * wy)


def _refract_displacement(normals: np.ndarray, thickness: np.ndarray, ior: float, scale: float) -> tuple[np.ndarray, np.ndarray]:
    nx, ny, nz = normals[..., 0], normals[..., 1], normals[..., 2]
    eta = 1.0 / max(ior, 1.0001)
    cosi = np.clip(nz, 0.0, 1.0)
    k = np.maximum(1.0 - eta * eta * (1.0 - cosi * cosi), 1e-8)
    f = eta * cosi - np.sqrt(k)
    tx = f * nx
    ty = f * ny
    tz = -eta + f * nz
    travel = thickness / np.maximum(-tz, 1e-4)
    return tx * travel * scale, ty * travel * scale


def render_optical_preview(
    maps: SurfaceMaps,
    wallpaper: Image.Image,
    *,
    params: MaterialParams = MaterialParams(),
    displacement_scale: float = 52.0,
    specular: bool = True,
) -> Image.Image:
    """Wallpaper-aware V3 optical preview. Never used for production PNG."""
    size = maps.container_mask.shape[0]
    bg = wallpaper.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    arr = np.asarray(bg, dtype=np.float32)

    dx, dy = _refract_displacement(maps.normals, maps.thickness, params.ior, displacement_scale)

    # Secondary glyph lens: same geometric surface, with extra optical path in
    # the raised glyph volume. This is preview-only and intentionally explicit.
    glyph_gain = 1.0 + 0.55 * maps.glyph_profile
    dx *= glyph_gain
    dy *= glyph_gain

    primary = _bilinear_sample(arr, dx, dy)
    # Small multi-sample integration near high-slope areas: optical integration,
    # not a global blur.
    slope = maps.slope
    smax = max(float(np.percentile(slope, 99.5)), 1e-6)
    edge = np.clip(slope / smax, 0.0, 1.0)[..., None]
    secondary = _bilinear_sample(arr, dx * 0.88 - dy * 0.07, dy * 0.88 + dx * 0.07)
    glass = primary * (1.0 - 0.18 * edge) + secondary * (0.18 * edge)

    # Mild compression-caustic cue from flow divergence.
    ddx_dx = np.gradient(dx, axis=1)
    ddy_dy = np.gradient(dy, axis=0)
    compression = np.clip(-(ddx_dx + ddy_dy) * 0.055, -0.08, 0.10)
    glass *= (1.0 + compression[..., None])

    n = maps.normals
    ndotv = np.clip(n[..., 2], 0.0, 1.0)
    fresnel = schlick_fresnel(ndotv, params.ior)

    # Broad environment response from nearby wallpaper, not hardcoded hue.
    env = _bilinear_sample(arr, -dx * 0.24 + 5.0 * n[..., 0], -dy * 0.24 + 5.0 * n[..., 1])
    env_w = np.clip((0.08 + 0.34 * fresnel) * maps.container_mask, 0.0, 0.30)[..., None]
    glass = glass * (1.0 - env_w) + env * env_w

    # Restrained directional specular.
    if specular:
        light = np.array([-0.42, -0.74, 0.52], dtype=np.float32)
        light /= max(float(np.linalg.norm(light)), 1e-6)
        view = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        halfv = light + view
        halfv /= max(float(np.linalg.norm(halfv)), 1e-6)
        ndoth = np.clip(n[..., 0] * halfv[0] + n[..., 1] * halfv[1] + n[..., 2] * halfv[2], 0.0, 1.0)
        sp = np.power(ndoth, 34.0) * (0.20 + 0.80 * fresnel)
        sp *= np.clip(maps.container_mask + 0.55 * maps.glyph_mask, 0.0, 1.0)
        glass = glass * (1.0 - 0.18 * sp[..., None]) + 255.0 * (0.18 * sp[..., None])

    # Keep center clean: outside mask and very flat core are mostly untouched.
    core = np.clip(maps.container_profile * maps.container_mask, 0.0, 1.0)[..., None]
    effect = np.clip((1.0 - 0.64 * core) * maps.container_mask[..., None] + 0.28 * maps.glyph_mask[..., None], 0.0, 1.0)
    out = arr * (1.0 - effect) + glass * effect
    return Image.fromarray(np.clip(out, 0.0, 255.0).astype(np.uint8), "RGB")
