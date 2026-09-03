from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

FloatMap = np.ndarray


@dataclass(frozen=True)
class SurfaceParams:
    # Analytic continuous-corner shell. Unlike V3, the container is not built
    # from a raster rounded-rectangle EDT; the superellipse itself defines the
    # surface and therefore the normals all the way through the corners.
    margin: float = 0.105
    superellipse_n: float = 5.2
    edge_fraction: float = 0.245
    boundary_fraction: float = 0.024
    front_height: float = 0.86
    edge_height: float = 0.010

    core_thickness: float = 0.265
    lip_thickness_gain: float = 0.345
    lip_center_q: float = 0.79
    lip_width_q: float = 0.115

    glyph_relief: float = 0.245
    glyph_mass_gain: float = 0.365
    glyph_bevel_px: float = 23.0
    glyph_back_bevel_px: float = 34.0
    normal_scale: float = 2.45


@dataclass
class SurfaceMaps:
    container_mask: FloatMap
    glyph_mask: FloatMap
    container_sdf: FloatMap
    glyph_sdf: FloatMap
    q: FloatMap

    container_front: FloatMap
    container_back: FloatMap
    glyph_relief: FloatMap
    glyph_mass: FloatMap
    front_height: FloatMap
    back_height: FloatMap
    thickness: FloatMap

    container_front_normals: FloatMap
    container_back_normals: FloatMap
    front_normals: FloatMap
    back_normals: FloatMap

    container_front_slope: FloatMap
    container_back_slope: FloatMap
    glyph_slope: FloatMap
    glyph_back_slope: FloatMap
    front_slope: FloatMap
    back_slope: FloatMap
    curvature: FloatMap
    local_radius: FloatMap


def smootherstep(x: FloatMap) -> FloatMap:
    x = np.clip(x, 0.0, 1.0).astype(np.float32)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def _edt_1d(f: np.ndarray) -> np.ndarray:
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
    d_in = _distance_to_true(~inside)
    d_out = _distance_to_true(inside)
    return np.where(inside, d_in, -d_out).astype(np.float32)


def _gradient(a: FloatMap) -> tuple[FloatMap, FloatMap]:
    gy, gx = np.gradient(a.astype(np.float32))
    return gx.astype(np.float32), gy.astype(np.float32)


def _normals(h: FloatMap, z_scale: float) -> FloatMap:
    gx, gy = _gradient(h)
    n = np.stack((-z_scale * gx, -z_scale * gy, np.ones_like(h)), axis=-1)
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-8)
    return n.astype(np.float32)


def _slope(h: FloatMap) -> FloatMap:
    gx, gy = _gradient(h)
    return np.sqrt(gx * gx + gy * gy).astype(np.float32)


def _curvature(h: FloatMap) -> FloatMap:
    gx, gy = _gradient(h)
    gxx, _ = _gradient(gx)
    _, gyy = _gradient(gy)
    return (gxx + gyy).astype(np.float32)


def _glyph_mask_array(glyph_mask: Image.Image, size: int) -> FloatMap:
    return np.asarray(glyph_mask.convert("L").resize((size, size), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0


def build_surface_maps(glyph_mask: Image.Image, params: SurfaceParams = SurfaceParams(), *, size: int = 640) -> SurfaceMaps:
    yy, xx = np.indices((size, size), dtype=np.float32)
    c = (size - 1.0) * 0.5
    half = size * (0.5 - params.margin)
    nx = np.abs((xx - c) / max(half, 1e-6))
    ny = np.abs((yy - c) / max(half, 1e-6))
    p = max(float(params.superellipse_n), 2.1)
    q = np.power(np.power(nx, p) + np.power(ny, p), 1.0 / p).astype(np.float32)
    cm = (q <= 1.0).astype(np.float32)

    # Approximate signed distance in pixels from the analytic superellipse.
    csdf = ((1.0 - q) * half).astype(np.float32)

    inward = np.clip((1.0 - q) / max(params.edge_fraction, 1e-4), 0.0, 1.0)
    crown = smootherstep(inward)
    boundary = smootherstep(np.clip((1.0 - q) / max(params.boundary_fraction, 1e-4), 0.0, 1.0))

    # Broad optically curved shoulder with a clean, almost planar crown.
    shaped = np.power(crown, 0.72).astype(np.float32)
    container_front = boundary * (params.edge_height + (params.front_height - params.edge_height) * shaped) * cm

    lip = np.exp(-0.5 * np.square((q - params.lip_center_q) / max(params.lip_width_q, 1e-4))).astype(np.float32)
    container_thickness = boundary * (params.core_thickness + params.lip_thickness_gain * lip) * cm
    container_back = (container_front - container_thickness) * cm

    gm = _glyph_mask_array(glyph_mask, size)
    gsdf = signed_distance(gm)
    gd = np.maximum(gsdf - 0.65, 0.0)
    gu = np.clip(gd / max(params.glyph_bevel_px, 1e-4), 0.0, 1.0)
    gbu = np.clip(gd / max(params.glyph_back_bevel_px, 1e-4), 0.0, 1.0)
    gfront_profile = smootherstep(gu) * gm
    gback_profile = smootherstep(gbu) * gm

    glyph_relief = params.glyph_relief * np.power(gfront_profile, 0.82)
    glyph_mass = params.glyph_mass_gain * np.power(gback_profile, 0.74)

    front = (container_front + glyph_relief).astype(np.float32)
    thickness = (container_thickness + glyph_mass).astype(np.float32)
    back = ((front - thickness) * cm).astype(np.float32)

    cfn = _normals(container_front, params.normal_scale)
    cbn = _normals(container_back, params.normal_scale)
    fn = _normals(front, params.normal_scale)
    bn = _normals(back, params.normal_scale)

    cfs = _slope(container_front)
    cbs = _slope(container_back)
    gs = _slope(glyph_relief)
    gbs = _slope(glyph_mass)
    fs = _slope(front)
    bs = _slope(back)
    curv = _curvature(front)
    local_radius = np.where(gm > 0.5, np.maximum(gsdf, 0.0), 0.0).astype(np.float32)

    return SurfaceMaps(
        container_mask=cm,
        glyph_mask=gm,
        container_sdf=csdf,
        glyph_sdf=gsdf,
        q=q,
        container_front=container_front.astype(np.float32),
        container_back=container_back.astype(np.float32),
        glyph_relief=glyph_relief.astype(np.float32),
        glyph_mass=glyph_mass.astype(np.float32),
        front_height=front,
        back_height=back,
        thickness=thickness,
        container_front_normals=cfn,
        container_back_normals=cbn,
        front_normals=fn,
        back_normals=bn,
        container_front_slope=cfs,
        container_back_slope=cbs,
        glyph_slope=gs,
        glyph_back_slope=gbs,
        front_slope=fs,
        back_slope=bs,
        curvature=curv,
        local_radius=local_radius,
    )
