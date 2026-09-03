from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw

FloatMap = np.ndarray


@dataclass(frozen=True)
class SurfaceParams:
    edge_width_px: float = 78.0
    center_height: float = 1.00
    edge_height: float = 0.12
    back_depth: float = 0.34
    edge_thickness_gain: float = 0.32
    glyph_relief: float = 0.44
    glyph_mass_gain: float = 0.34
    glyph_bevel_width_px: float = 26.0
    normal_scale: float = 2.8


@dataclass
class SurfaceMaps:
    container_mask: FloatMap
    glyph_mask: FloatMap
    container_sdf: FloatMap
    glyph_sdf: FloatMap
    container_profile: FloatMap
    glyph_profile: FloatMap
    front_height: FloatMap
    back_height: FloatMap
    thickness: FloatMap
    normals: FloatMap
    slope: FloatMap
    curvature: FloatMap
    local_radius: FloatMap


def smootherstep(x: FloatMap) -> FloatMap:
    x = np.clip(x, 0.0, 1.0).astype(np.float32)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def squircle_mask(size: int, margin: float = 0.105, radius: float = 0.235) -> Image.Image:
    """Launcher-like rounded square mask used only as V3 geometry input."""
    px = int(round(size * margin))
    r = int(round(size * radius))
    im = Image.new("L", (size, size), 0)
    ImageDraw.Draw(im).rounded_rectangle((px, px, size - px - 1, size - px - 1), radius=r, fill=255)
    return im


def _edt_1d(f: np.ndarray) -> np.ndarray:
    """Felzenszwalb/Huttenlocher squared Euclidean distance transform, 1D."""
    n = int(f.shape[0])
    v = np.zeros(n, dtype=np.int32)
    z = np.zeros(n + 1, dtype=np.float64)
    d = np.zeros(n, dtype=np.float64)
    k = 0
    v[0] = 0
    z[0] = -np.inf
    z[1] = np.inf
    for q in range(1, n):
        fq = float(f[q])
        while True:
            vk = int(v[k])
            s = ((fq + q * q) - (float(f[vk]) + vk * vk)) / (2.0 * (q - vk))
            if s > z[k]:
                break
            k -= 1
            if k < 0:
                k = 0
                break
        k += 1
        v[k] = q
        z[k] = s
        z[k + 1] = np.inf
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        vk = int(v[k])
        d[q] = (q - vk) * (q - vk) + float(f[vk])
    return d


def _distance_to_true(seed: np.ndarray) -> FloatMap:
    """Exact Euclidean distance in pixels to nearest True seed."""
    inf = 1.0e12
    f = np.where(seed, 0.0, inf).astype(np.float64)
    h, w = f.shape
    g = np.empty_like(f)
    for x in range(w):
        g[:, x] = _edt_1d(f[:, x])
    d2 = np.empty_like(g)
    for y in range(h):
        d2[y, :] = _edt_1d(g[y, :])
    return np.sqrt(np.maximum(d2, 0.0)).astype(np.float32)


def signed_distance(mask: FloatMap) -> FloatMap:
    inside = mask > 0.5
    dist_out = _distance_to_true(~inside)
    dist_in = _distance_to_true(inside)
    return np.where(inside, dist_out, -dist_in).astype(np.float32)


def _central_gradient(a: FloatMap) -> Tuple[FloatMap, FloatMap]:
    gx = np.zeros_like(a, dtype=np.float32)
    gy = np.zeros_like(a, dtype=np.float32)
    gx[:, 1:-1] = 0.5 * (a[:, 2:] - a[:, :-2])
    gx[:, 0] = a[:, 1] - a[:, 0]
    gx[:, -1] = a[:, -1] - a[:, -2]
    gy[1:-1, :] = 0.5 * (a[2:, :] - a[:-2, :])
    gy[0, :] = a[1, :] - a[0, :]
    gy[-1, :] = a[-1, :] - a[-2, :]
    return gx, gy


def height_to_normals(height: FloatMap, z_scale: float) -> FloatMap:
    gx, gy = _central_gradient(height)
    n = np.stack((-z_scale * gx, -z_scale * gy, np.ones_like(height)), axis=-1)
    length = np.linalg.norm(n, axis=-1, keepdims=True)
    return (n / np.maximum(length, 1e-8)).astype(np.float32)


def _curvature(height: FloatMap) -> FloatMap:
    gx, gy = _central_gradient(height)
    gxx, _ = _central_gradient(gx)
    _, gyy = _central_gradient(gy)
    return (gxx + gyy).astype(np.float32)


def _img_to_mask(im: Image.Image, size: int) -> FloatMap:
    return np.asarray(im.convert("L").resize((size, size), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0


def build_surface_maps(
    container_mask: Image.Image,
    glyph_mask: Image.Image,
    params: SurfaceParams = SurfaceParams(),
    *,
    size: int | None = None,
) -> SurfaceMaps:
    if size is None:
        size = container_mask.size[0]

    cm = _img_to_mask(container_mask, size)
    gm = _img_to_mask(glyph_mask, size)

    csdf = signed_distance(cm)
    gsdf = signed_distance(gm)

    # Broad physical edge zone. 1 in flat core, 0 at boundary.
    cu = np.clip(csdf / max(params.edge_width_px, 1e-3), 0.0, 1.0)
    cprof = smootherstep(cu) * (cm > 0.01)

    # Glyph is an actual raised secondary surface, not a composited overlay.
    gu = np.clip(gsdf / max(params.glyph_bevel_width_px, 1e-3), 0.0, 1.0)
    gprof = smootherstep(gu) * (gm > 0.01)

    front = np.where(
        cm > 0.01,
        params.edge_height + (params.center_height - params.edge_height) * cprof,
        0.0,
    ).astype(np.float32)
    front += (params.glyph_relief * gprof).astype(np.float32)

    # Separate thickness field: broad edge thickening + glyph mass.
    base_t = params.back_depth + params.edge_thickness_gain * (1.0 - cprof)
    thickness = np.where(cm > 0.01, base_t, 0.0).astype(np.float32)
    thickness += (params.glyph_mass_gain * gprof).astype(np.float32)
    back = np.where(cm > 0.01, front - thickness, 0.0).astype(np.float32)

    normals = height_to_normals(front, params.normal_scale)
    gx, gy = _central_gradient(front)
    slope = np.sqrt(gx * gx + gy * gy).astype(np.float32)
    curvature = _curvature(front)
    local_radius = np.where(gm > 0.5, np.maximum(gsdf, 0.0), 0.0).astype(np.float32)

    return SurfaceMaps(
        container_mask=cm,
        glyph_mask=gm,
        container_sdf=csdf,
        glyph_sdf=gsdf,
        container_profile=cprof.astype(np.float32),
        glyph_profile=gprof.astype(np.float32),
        front_height=front,
        back_height=back,
        thickness=thickness,
        normals=normals,
        slope=slope,
        curvature=curvature,
        local_radius=local_radius,
    )
