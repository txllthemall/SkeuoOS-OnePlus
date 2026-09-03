from __future__ import annotations

import numpy as np
from PIL import Image

from .material import MaterialParams
from .surface import SurfaceMaps


def _normalize(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-8)


def _refract(i: np.ndarray, n: np.ndarray, eta: float) -> np.ndarray:
    dotni = np.sum(n * i, axis=-1, keepdims=True)
    k = 1.0 - eta * eta * (1.0 - dotni * dotni)
    root = np.sqrt(np.maximum(k, 0.0))
    t = eta * i - (eta * dotni + root) * n
    bad = k[..., 0] < 0.0
    if np.any(bad):
        t[bad] = i[bad]
    return _normalize(t).astype(np.float32)


def _sample(arr: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
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
    return (
        arr[y0, x0] * (1 - wx) * (1 - wy)
        + arr[y0, x1] * wx * (1 - wy)
        + arr[y1, x0] * (1 - wx) * wy
        + arr[y1, x1] * wx * wy
    )


def _blur_field(a: np.ndarray, passes: int = 2) -> np.ndarray:
    out = a.astype(np.float32)
    k = np.asarray([1, 4, 6, 4, 1], dtype=np.float32) / 16.0
    for _ in range(max(0, int(passes))):
        p = np.pad(out, ((0, 0), (2, 2)), mode="edge")
        out = sum(k[j] * p[:, j : j + out.shape[1]] for j in range(5))
        p = np.pad(out, ((2, 2), (0, 0)), mode="edge")
        out = sum(k[j] * p[j : j + out.shape[0], :] for j in range(5))
    return out.astype(np.float32)


def _flow(maps: SurfaceMaps, ior: float, gain: float) -> tuple[np.ndarray, np.ndarray]:
    h, w = maps.thickness.shape
    incident = np.zeros((h, w, 3), dtype=np.float32)
    incident[..., 2] = -1.0

    inside = _refract(incident, maps.front_normals, 1.0 / max(float(ior), 1.0001))
    iz = np.maximum(-inside[..., 2], 0.30)
    travel = np.clip(maps.thickness, 0.0, None) / iz

    scale = float(min(h, w)) / 640.0
    path_gain = 19.0 * scale * float(gain)
    dx = inside[..., 0] * travel * path_gain
    dy = inside[..., 1] * travel * path_gain

    # Independent exit interface. The short external propagation produces local
    # scale compression near the shoulder without the run-10 tearing.
    outside = _refract(inside, -maps.back_normals, max(float(ior), 1.0001))
    oz = np.maximum(-outside[..., 2], 0.35)
    gap = np.clip(maps.thickness, 0.0, None) * (3.2 * scale * float(gain))
    dx += outside[..., 0] / oz * gap
    dy += outside[..., 1] / oz * gap

    # Secondary dielectric glyph: use the difference between full and container
    # normals rather than a raw mask warp.
    dnx = maps.front_normals[..., 0] - maps.container_front_normals[..., 0]
    dny = maps.front_normals[..., 1] - maps.container_front_normals[..., 1]
    dx += dnx * maps.glyph_mask * (5.5 * scale)
    dy += dny * maps.glyph_mask * (5.5 * scale)

    dx = _blur_field(dx, 2)
    dy = _blur_field(dy, 2)
    cap = 10.5 * scale * max(float(gain), 0.5)
    dx = cap * np.tanh(dx / max(cap, 1e-5))
    dy = cap * np.tanh(dy / max(cap, 1e-5))
    dx *= maps.container_mask
    dy *= maps.container_mask
    return dx.astype(np.float32), dy.astype(np.float32)


def render_optical_preview(
    maps: SurfaceMaps,
    wallpaper: Image.Image,
    *,
    params: MaterialParams = MaterialParams(),
    gain: float = 1.0,
    specular: bool = True,
) -> Image.Image:
    size = maps.container_mask.shape[0]
    arr = np.asarray(wallpaper.convert("RGB").resize((size, size), Image.Resampling.LANCZOS), dtype=np.float32)
    dx, dy = _flow(maps, params.ior, gain)
    glass = _sample(arr, dx, dy)

    # Finite footprint only on curved zones; the clear crown remains sharp.
    slope = maps.front_slope + 0.55 * maps.back_slope
    active = maps.container_mask > 0.1
    hi = max(float(np.percentile(slope[active], 99.0)) if np.any(active) else 1.0, 1e-6)
    edge = np.clip(slope / hi, 0.0, 1.0)[..., None]
    secondary = _sample(arr, 0.94 * dx - 0.025 * dy, 0.94 * dy + 0.025 * dx)
    glass = glass * (1.0 - 0.055 * edge) + secondary * (0.055 * edge)

    # Wallpaper-derived reflection from the actual surface orientation.
    nf = maps.front_normals
    rx = 2.0 * nf[..., 2] * nf[..., 0]
    ry = 2.0 * nf[..., 2] * nf[..., 1]
    env = _sample(arr, 3.2 * rx - 0.10 * dx, 3.2 * ry - 0.10 * dy)
    fres = np.power(1.0 - np.clip(nf[..., 2], 0.0, 1.0), 5.0)
    ew = np.clip((0.020 + 0.14 * fres) * maps.container_mask, 0.0, 0.13)[..., None]
    glass = glass * (1.0 - ew) + env * ew

    if specular:
        light = np.array([-0.46, -0.72, 0.518], dtype=np.float32)
        light /= max(float(np.linalg.norm(light)), 1e-8)
        halfv = light + np.array([0.0, 0.0, 1.0], dtype=np.float32)
        halfv /= max(float(np.linalg.norm(halfv)), 1e-8)
        ndh = np.clip(nf[..., 0] * halfv[0] + nf[..., 1] * halfv[1] + nf[..., 2] * halfv[2], 0.0, 1.0)
        sp = np.power(ndh, 52.0) * np.clip(edge[..., 0] + 0.25 * maps.glyph_mask, 0.0, 1.0)
        glass = glass * (1.0 - 0.075 * sp[..., None]) + 255.0 * (0.075 * sp[..., None])

    mask = maps.container_mask[..., None]
    out = arr * (1.0 - mask) + glass * mask
    return Image.fromarray(np.clip(out, 0.0, 255.0).astype(np.uint8), "RGB")
