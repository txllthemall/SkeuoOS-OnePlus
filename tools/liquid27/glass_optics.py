from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .clear_material import _bilinear_warp
from .glass_surface import enclosure_surface, glyph_surface


def _mask(arr):
    return Image.fromarray(np.clip(np.round(arr * 255.0), 0, 255).astype(np.uint8), 'L')


def _local_stats(img: Image.Image):
    gray = img.convert('L')
    size = img.size[0]
    low = np.asarray(gray.filter(ImageFilter.GaussianBlur(max(1.0, size * .055))), dtype=np.float32) / 255.0
    med = np.asarray(gray.filter(ImageFilter.GaussianBlur(max(.7, size * .020))), dtype=np.float32) / 255.0
    raw = np.asarray(gray, dtype=np.float32) / 255.0
    high = raw - med
    contrast = np.clip(np.abs(high) * 3.0 + np.abs(med - low) * 1.5, 0.0, 1.0)
    return low, med, contrast


def _snell_flow(surface: dict, size: int, ior: float = 1.48):
    """Cheap normal-derived Snell approximation for a front-facing camera."""
    nx, ny, nz = surface['nx'], surface['ny'], surface['nz']
    eta = 1.0 / ior
    # Incident direction (0,0,-1), with normals facing camera. For the xy part
    # of the transmitted ray the scalar below is sufficient and stable.
    cosi = np.clip(nz, 0.0, 1.0)
    k = np.clip(1.0 - eta * eta * (1.0 - cosi * cosi), 0.0, 1.0)
    transmitted_xy = eta + (eta * cosi - np.sqrt(k))
    tx = nx * transmitted_xy
    ty = ny * transmitted_xy
    thickness = surface['thickness']
    curvature = surface['curvature']
    scale = size * .120
    dx = tx * thickness * scale
    dy = ty * thickness * scale

    # Local magnification/compression: a coherent extra term from the surface
    # slope rather than a separate radial warp.
    dx += surface['gx'] * size * (.55 + curvature * 1.25)
    dy += surface['gy'] * size * (.55 + curvature * 1.25)
    return dx.astype(np.float32), dy.astype(np.float32)


def _multisample(arr: np.ndarray, dx: np.ndarray, dy: np.ndarray, weight: np.ndarray):
    primary = _bilinear_warp(arr, dx, dy).astype(np.float32)
    # Small integration along and across the transmitted direction. The blend is
    # only active on highly curved zones; the centre stays crisp.
    a = _bilinear_warp(arr, dx * .82 - dy * .045, dy * .82 + dx * .045).astype(np.float32)
    b = _bilinear_warp(arr, dx * 1.10 + dy * .030, dy * 1.10 - dx * .030).astype(np.float32)
    integrated = primary * .64 + a * .20 + b * .16
    w = np.clip(weight, 0.0, .72)[..., None]
    return np.clip(primary * (1.0 - w) + integrated * w, 0, 255)


def _environment_reflection(arr: np.ndarray, surface: dict, dx, dy):
    # Reflection is derived from nearby scene samples, not white paint.
    env = _bilinear_warp(arr, -dx * .34, -dy * .34).astype(np.float32)
    env = np.asarray(Image.fromarray(env.astype(np.uint8), 'RGB').filter(ImageFilter.GaussianBlur(2.2)), dtype=np.float32)
    f = np.clip(surface['fsoft'] * .12 + surface['fmid'] * .24, 0.0, .28)[..., None]
    return env, f


def _specular(surface: dict, light=(-.54, -.68, .50)):
    lx, ly, lz = light
    lm = max((lx*lx + ly*ly + lz*lz) ** .5, 1e-6)
    lx, ly, lz = lx/lm, ly/lm, lz/lm
    # Half-vector between camera and virtual light.
    hx, hy, hz = lx, ly, lz + 1.0
    hm = max((hx*hx + hy*hy + hz*hz) ** .5, 1e-6)
    hx, hy, hz = hx/hm, hy/hm, hz/hm
    ndoth = np.clip(surface['nx']*hx + surface['ny']*hy + surface['nz']*hz, 0.0, 1.0)
    spec = (ndoth ** 30.0) * np.clip(surface['fmid'] * 1.8 + surface['ftight'] * 1.9, 0.0, 1.0)
    return np.clip(spec, 0.0, .72)


def _caustic(dx, dy, inside):
    ddy, ddx = np.gradient(dx)
    edy, edx = np.gradient(dy)
    div = ddx + edy
    compression = np.clip(-div * .055, -.035, .055) * inside
    return compression


def composite_container(base: Image.Image):
    if base.size[0] != base.size[1]:
        raise ValueError('Liquid Glass preview expects a square patch')
    size = base.size[0]
    surface = enclosure_surface(size)
    arr = np.asarray(base.convert('RGB'), dtype=np.float32)
    dx, dy = _snell_flow(surface, size)
    refracted = _multisample(arr, dx, dy, surface['curvature'] * surface['edge'])

    env, env_w = _environment_reflection(arr, surface, dx, dy)
    out = refracted * (1.0 - env_w) + env * env_w

    spec = _specular(surface)[..., None]
    out = out * (1.0 - spec * .34) + 255.0 * spec * .34

    # Opposite interface follows surface orientation and Fresnel, not distance alone.
    lx, ly = -.54, -.68
    opposite = np.clip(surface['nx']*(-lx) + surface['ny']*(-ly), 0.0, 1.0)
    opposite = opposite ** 3.0 * surface['fmid']
    out *= (1.0 - opposite[..., None] * .10)

    # Secondary internal interface: a soft, inward-biased Fresnel layer.
    secondary = np.clip(surface['fsoft'] * surface['edge'] * .10 + surface['fmid'] * .055, 0.0, .11)
    out = out * (1.0 - secondary[..., None]) + 232.0 * secondary[..., None]

    caustic = _caustic(dx, dy, surface['inside'])
    out = out * (1.0 + caustic[..., None])

    tmp = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')
    low, _, local_contrast = _local_stats(tmp)
    rr = np.asarray(tmp, dtype=np.float32) / 255.0
    bright_support = np.clip((low - .70) / .25, 0.0, 1.0) * surface['edge'] * .055
    dark_support = np.clip((.34 - low) / .34, 0.0, 1.0) * surface['fmid'] * .065
    contrast_gain = 1.0 + (1.0 - local_contrast) * surface['edge'] * .07
    rr = (rr - low[...,None]) * contrast_gain[...,None] + low[...,None]
    rr = np.clip(rr - bright_support[...,None] + dark_support[...,None], 0.0, 1.0)
    processed = np.round(rr * 255.0).astype(np.uint8)

    inside = surface['inside'][..., None]
    final = arr * (1.0 - inside) + processed * inside
    return Image.fromarray(np.clip(final, 0, 255).astype(np.uint8), 'RGB'), dx, dy, surface


def composite_glyph(base: Image.Image, glyph_mask: Image.Image):
    size = base.size[0]
    surf = glyph_surface(glyph_mask, size)
    arr = np.asarray(base.convert('RGB'), dtype=np.float32)

    # Re-use Snell form with glyph-specific normals/thickness.
    eta = 1.0 / 1.50
    cosi = np.clip(surf['nz'], 0.0, 1.0)
    k = np.clip(1.0 - eta*eta*(1.0-cosi*cosi), 0.0, 1.0)
    scalar = eta + (eta*cosi - np.sqrt(k))
    dx = surf['nx'] * scalar * surf['thickness'] * size * .155 + surf['gx'] * size * 1.55
    dy = surf['ny'] * scalar * surf['thickness'] * size * .155 + surf['gy'] * size * 1.55
    warped = _multisample(arr, dx, dy, surf['curvature'] * .58)

    alpha = np.clip(surf['alpha'], 0.0, 1.0)
    edge = np.clip(surf['edge'], 0.0, 1.0)
    fresnel = np.clip(surf['fresnel'] + edge * .18, 0.0, .72)
    env = _bilinear_warp(arr, -dx*.25, -dy*.25).astype(np.float32)
    env_w = (fresnel * .16)[...,None]
    glass = warped*(1.0-env_w) + env*env_w

    # Directional glyph specular from its own normals.
    lx, ly, lz = -.50, -.72, .48
    lm = (lx*lx+ly*ly+lz*lz) ** .5
    lx,ly,lz=lx/lm,ly/lm,lz/lm
    ndotl = np.clip(surf['nx']*lx + surf['ny']*ly + surf['nz']*lz, 0.0, 1.0)
    spec = (ndotl ** 24.0) * np.clip(fresnel*1.6 + edge*.20, 0.0, .65)
    glass = glass*(1.0-spec[...,None]*.32) + 255.0*spec[...,None]*.32

    opposite = np.clip(-(surf['nx']*lx + surf['ny']*ly), 0.0, 1.0) ** 2.5 * edge
    glass *= (1.0 - opposite[...,None]*.10)

    # Keep large glyph interiors genuinely transmissive. Most identity comes
    # from secondary refraction and edge physics, not a white body.
    body_mix = np.clip(alpha * (.70 + .16*edge), 0.0, .88)[...,None]
    out = arr*(1.0-body_mix) + glass*body_mix
    return Image.fromarray(np.clip(out,0,255).astype(np.uint8),'RGB'), dx, dy, surf
