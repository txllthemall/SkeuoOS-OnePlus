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
    bad = k[..., 0] < 0.0
    if np.any(bad):
        t[bad] = i[bad]
    return _normalize(t).astype(np.float32)


def _blur5(a: np.ndarray, passes: int = 1) -> np.ndarray:
    """Low-pass an optical FLOW field, never the wallpaper itself.

    Height-field derivatives can contain one-pixel spikes at rasterized edges.
    Integrating the vector field over a small pixel footprint removes those
    spikes without creating a fake frosted-glass blur.
    """
    out = a.astype(np.float32)
    weights = np.asarray([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float32) / 16.0
    for _ in range(max(int(passes), 0)):
        p = np.pad(out, ((0, 0), (2, 2)), mode="edge")
        out = sum(weights[j] * p[:, j : j + out.shape[1]] for j in range(5))
        p = np.pad(out, ((2, 2), (0, 0)), mode="edge")
        out = sum(weights[j] * p[j : j + out.shape[0], :] for j in range(5))
    return out.astype(np.float32)


def _soft_cap(v: np.ndarray, limit: float) -> np.ndarray:
    limit = max(float(limit), 1e-5)
    return (limit * np.tanh(v / limit)).astype(np.float32)


def _two_interface_flow(
    maps: SurfaceMaps,
    ior: float,
    *,
    displacement_scale: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Paired front/back-interface optical flow.

    Run #10 still tore checker lines because the back surface was treated as a
    large differential correction after a single entry refraction. Here the
    ray actually enters through the FRONT interface, traverses measured glass
    thickness, and is evaluated against the BACK interface before the final UV
    sample. The resulting field is footprint-filtered and softly saturated.
    """
    h, w = maps.thickness.shape
    incident = np.zeros((h, w, 3), dtype=np.float32)
    incident[..., 2] = -1.0

    nf = maps.front_normals.astype(np.float32)
    nb_out = -maps.back_normals.astype(np.float32)

    inside = _refract(incident, nf, 1.0 / max(float(ior), 1.0001))
    inside_z = np.maximum(-inside[..., 2], 0.22)
    travel = np.clip(maps.thickness, 0.0, None) / inside_z

    size_gain = float(min(h, w)) / 640.0
    internal_gain = 23.0 * size_gain * float(displacement_scale)
    dx = inside[..., 0] * travel * internal_gain
    dy = inside[..., 1] * travel * internal_gain

    # Refract out through the independently shaped rear interface. Because the
    # backdrop in this preview is conceptually close to the glass, the exit ray
    # contributes only a short extra path instead of a second huge warp.
    outgoing = _refract(inside, nb_out, max(float(ior), 1.0001))
    out_z = np.maximum(-outgoing[..., 2], 0.28)
    exit_gap = np.clip(maps.thickness, 0.0, None) * 4.0 * size_gain * float(displacement_scale)
    dx += outgoing[..., 0] / out_z * exit_gap
    dy += outgoing[..., 1] / out_z * exit_gap

    # Secondary glass glyph: add its own smooth relief-gradient lens instead of
    # multiplying the entire container displacement inside the glyph.
    gy, gx = np.gradient(maps.glyph_relief_map.astype(np.float32))
    glyph_volume = np.clip(maps.glyph_mask * (0.32 + 0.68 * maps.glyph_profile), 0.0, 1.0)
    dx += -gx * glyph_volume * (19.0 * size_gain)
    dy += -gy * glyph_volume * (19.0 * size_gain)

    # Integrate the vector field over a small footprint before sampling.
    dx = _blur5(dx, passes=2)
    dy = _blur5(dy, passes=2)

    # Soft saturation preserves direction/order and prevents the run-#10
    # fun-house-mirror spikes without introducing a hard clipped contour.
    max_disp = 13.5 * size_gain * max(float(displacement_scale), 0.45)
    dx = _soft_cap(dx, max_disp)
    dy = _soft_cap(dy, max_disp)

    gate = np.clip(maps.container_mask, 0.0, 1.0)
    dx *= gate
    dy *= gate
    return dx.astype(np.float32), dy.astype(np.float32)


def render_optical_preview(
    maps: SurfaceMaps,
    wallpaper: Image.Image,
    *,
    params: MaterialParams = MaterialParams(),
    displacement_scale: float = 1.0,
    specular: bool = True,
) -> Image.Image:
    """Wallpaper-aware V3 optical preview. Never used for production PNG."""
    size = maps.container_mask.shape[0]
    bg = wallpaper.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    arr = np.asarray(bg, dtype=np.float32)

    dx, dy = _two_interface_flow(maps, params.ior, displacement_scale=displacement_scale)
    primary = _bilinear_sample(arr, dx, dy)

    # Tiny finite-footprint integration only where the actual front/back
    # surfaces are steep. The clear center stays a single crisp sample.
    surface = maps.front_slope + 0.60 * maps.back_slope
    active = maps.container_mask > 0.2
    s_hi = max(float(np.percentile(surface[active], 99.0)) if np.any(active) else 1.0, 1e-6)
    edge = np.clip(surface / s_hi, 0.0, 1.0)[..., None]
    secondary = _bilinear_sample(arr, dx * 0.95 - dy * 0.030, dy * 0.95 + dx * 0.030)
    glass = primary * (1.0 - 0.075 * edge) + secondary * (0.075 * edge)

    nf = maps.front_normals
    nb = maps.back_normals
    ff = schlick_fresnel(np.clip(nf[..., 2], 0.0, 1.0), params.ior)
    fb = schlick_fresnel(np.clip(nb[..., 2], 0.0, 1.0), params.ior)
    fresnel = np.clip(0.72 * ff + 0.28 * fb, 0.0, 1.0)

    # Environment colour comes only from nearby wallpaper samples.
    env_front = _bilinear_sample(arr, -0.16 * dx + 3.0 * nf[..., 0], -0.16 * dy + 3.0 * nf[..., 1])
    env_back = _bilinear_sample(arr, 0.06 * dx - 1.8 * nb[..., 0], 0.06 * dy - 1.8 * nb[..., 1])
    env = 0.78 * env_front + 0.22 * env_back
    env_w = np.clip((0.020 + 0.15 * fresnel) * maps.container_mask, 0.0, 0.14)[..., None]
    glass = glass * (1.0 - env_w) + env * env_w

    # Very small caustic-like energy redistribution from the FILTERED flow.
    # This is intentionally two orders gentler than the first V3 experiment.
    sdx = _blur5(dx, 1)
    sdy = _blur5(dy, 1)
    divergence = np.gradient(sdx, axis=1) + np.gradient(sdy, axis=0)
    compression = _blur5(-divergence, 1)
    compression = np.clip(compression * 0.012, -0.018, 0.024)
    glass *= 1.0 + compression[..., None]

    if specular:
        light = np.array([-0.42, -0.74, 0.52], dtype=np.float32)
        light /= max(float(np.linalg.norm(light)), 1e-6)
        view = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        halfv = light + view
        halfv /= max(float(np.linalg.norm(halfv)), 1e-6)
        ndoth = np.clip(nf[..., 0] * halfv[0] + nf[..., 1] * halfv[1] + nf[..., 2] * halfv[2], 0.0, 1.0)
        slope = maps.front_slope + 0.45 * maps.glyph_slope
        slope_hi = max(float(np.percentile(slope[active], 99.0)) if np.any(active) else 1.0, 1e-6)
        slope = np.clip(slope / slope_hi, 0.0, 1.0)
        sp = np.power(ndoth, 44.0) * (0.09 + 0.91 * fresnel) * slope
        sp *= np.clip(maps.container_mask + 0.30 * maps.glyph_mask, 0.0, 1.0)
        glass = glass * (1.0 - 0.085 * sp[..., None]) + 255.0 * (0.085 * sp[..., None])

    # Inside the object the refracted sample is authoritative. In the flat core
    # the computed flow approaches zero, so wallpaper detail remains intact.
    effect = np.clip(maps.container_mask[..., None], 0.0, 1.0)
    out = arr * (1.0 - effect) + glass * effect
    return Image.fromarray(np.clip(out, 0.0, 255.0).astype(np.uint8), "RGB")
