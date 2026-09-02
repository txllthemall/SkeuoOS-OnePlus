from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .surface import superellipse_surface


def _bilinear(arr: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    yy, xx = np.indices((h, w), dtype=np.float32)
    sx = np.clip(xx + dx, 0, w - 1.001)
    sy = np.clip(yy + dy, 0, h - 1.001)
    x0 = np.floor(sx).astype(np.int32); y0 = np.floor(sy).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1); y1 = np.minimum(y0 + 1, h - 1)
    fx = (sx - x0)[..., None]; fy = (sy - y0)[..., None]
    a = arr[y0, x0] * (1 - fx) + arr[y0, x1] * fx
    b = arr[y1, x0] * (1 - fx) + arr[y1, x1] * fx
    return a * (1 - fy) + b * fy


def render_container_optical(base: Image.Image, *, specular=True, explicit_rim=True):
    size = base.size[0]
    s = superellipse_surface(size)
    arr = np.asarray(base.convert('RGB'), dtype=np.float32)

    # Surface-normal flow with strong shoulder path length. The core remains
    # nearly undisturbed while the shoulder visibly changes scale and direction.
    flow_scale = size * 0.095
    dx = s['nx'] * s['thickness'] * flow_scale
    dy = s['ny'] * s['thickness'] * flow_scale
    # second interface: small reverse component creates thickness rather than a
    # single displaced sheet.
    front = _bilinear(arr, dx, dy)
    back = _bilinear(arr, -dx * 0.28, -dy * 0.28)
    shell_w = np.clip(s['shoulder'] * 0.62 + s['lip'] * 0.32, 0, 0.86)[..., None]
    out = front * (1 - shell_w * 0.18) + back * (shell_w * 0.18)

    # Local compression cue from flow divergence. This redistributes contrast
    # instead of drawing a fake border.
    _, ddx = np.gradient(dx); ddy, _ = np.gradient(dy)
    compression = np.clip(-(ddx + ddy) * 0.075, -0.07, 0.09) * s['inside']
    mean = out.mean(axis=2, keepdims=True)
    out = mean + (out - mean) * (1.0 + compression[..., None] * 1.8)
    out *= (1.0 + compression[..., None] * 0.65)

    # broad environment reflection follows the curved surface and inherits the
    # real wallpaper color instead of being a white overlay.
    env = _bilinear(arr, -dx * 0.55, -dy * 0.55)
    env = np.asarray(Image.fromarray(np.clip(env,0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(1.0,size*0.009))), dtype=np.float32)
    env_w = np.clip(s['broad_fresnel'] * 0.38, 0, 0.25)[..., None]
    out = out * (1 - env_w) + env * env_w

    # asymmetric surface response, not four-side bevel.
    lx, ly, lz = -0.48, -0.70, 0.52
    hm = np.sqrt((lx)**2 + (ly)**2 + (lz+1.0)**2)
    hx, hy, hz = lx/hm, ly/hm, (lz+1.0)/hm
    ndoth = np.clip(s['nx']*hx + s['ny']*hy + s['nz']*hz, 0, 1)
    if specular:
        sp = np.clip((ndoth**24) * (s['broad_fresnel']*0.42 + s['tight_fresnel']*0.90), 0, 0.42)[..., None]
        out = out * (1 - sp*0.42) + 255.0 * sp*0.42
    opposite = np.clip(-(s['nx']*lx + s['ny']*ly), 0, 1)**2.2
    dark = np.clip(opposite * (s['shoulder']*0.12 + s['lip']*0.18), 0, 0.16)[..., None]
    out *= (1 - dark)

    if explicit_rim:
        rim = np.clip((s['lip'] - s['very_lip']*0.25) * np.clip(ndoth*1.35,0,1) * 0.10,0,0.08)[...,None]
        out = out*(1-rim)+255*rim

    inside = s['inside'][..., None]
    final = arr * (1-inside) + np.clip(out,0,255) * inside
    return Image.fromarray(final.astype(np.uint8), 'RGB'), dx, dy, s
