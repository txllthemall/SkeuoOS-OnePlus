from __future__ import annotations

"""Coherent Clear/Liquid Glass material model.

Preview optics use the real wallpaper. Static Android assets remain strictly
neutral and encode only alpha/thickness/specular cues.
"""

import hashlib
from functools import lru_cache

import numpy as np
from PIL import Image, ImageChops, ImageFilter

from .material import (
    WORK, ENCL, inter, inner_edge, outer_edge, top_facing_edge,
    bottom_facing_edge, layer, luminance,
)
from .clear_material import _bilinear_warp


def _seed(key: str, salt: int = 0) -> int:
    return int.from_bytes(hashlib.sha256(f'{key}:{salt}'.encode()).digest()[:4], 'big')


def _smoothstep(a, b, x):
    t = np.clip((x - a) / max(b - a, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


@lru_cache(maxsize=8)
def _surface_np(size: int):
    yy, xx = np.indices((size, size), dtype=np.float32)
    c = (size - 1) * .5
    xn = (xx - c) / max(c, 1.0)
    yn = (yy - c) / max(c, 1.0)
    n = 4.0
    q = (np.abs(xn) ** n + np.abs(yn) ** n) ** (1.0 / n)
    inside = (q <= 1.0).astype(np.float32)
    center = np.clip(1.0 - q, 0.0, 1.0)
    edge = _smoothstep(.48, 1.0, q) * inside
    shell = _smoothstep(.70, 1.0, q) * inside
    tight = _smoothstep(.88, 1.0, q) * inside
    fresnel_soft = edge ** 1.8
    fresnel_mid = shell ** 2.5
    fresnel_tight = tight ** 4.0

    gx = np.sign(xn) * np.abs(xn) ** (n - 1)
    gy = np.sign(yn) * np.abs(yn) ** (n - 1)
    gm = np.maximum(np.sqrt(gx * gx + gy * gy), 1e-6)
    nx, ny = gx / gm, gy / gm

    lx, ly = -.62, -.78
    ndotl = np.clip(-(nx * lx + ny * ly), 0.0, 1.0)
    spec = (ndotl ** 10.0) * (fresnel_mid * .58 + fresnel_tight * 1.10)
    opposite = (np.clip(nx * lx + ny * ly, 0.0, 1.0) ** 2.4) * fresnel_mid

    return {
        'q': q, 'inside': inside, 'center': center, 'edge': edge,
        'shell': shell, 'tight': tight, 'fsoft': fresnel_soft,
        'fmid': fresnel_mid, 'ftight': fresnel_tight,
        'nx': nx, 'ny': ny, 'spec': spec, 'opposite': opposite,
    }


def _mask_from(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(np.round(arr * 255.0), 0, 255).astype(np.uint8), 'L')


@lru_cache(maxsize=1)
def _static_fields():
    s = _surface_np(WORK)
    density = (0.018 + .055 * s['fsoft'] + .12 * s['fmid'] + .24 * s['ftight']) * s['inside']
    spec = np.clip(.10 * s['fsoft'] + .34 * s['spec'], 0.0, .36)
    dark = np.clip(.055 * s['opposite'] + .030 * s['ftight'], 0.0, .10)
    return _mask_from(density), _mask_from(spec), _mask_from(dark)


def reflection_style(key: str) -> int:
    return 2 if (_seed(key, 401) % 5) == 0 else 1


@lru_cache(maxsize=256)
def clear_reflection_mask(key: str) -> Image.Image:
    s = _surface_np(WORK)
    flip = -1.0 if (_seed(key, 409) & 1) else 1.0
    lx, ly = -.62 * flip, -.78
    ndotl = np.clip(-(s['nx'] * lx + s['ny'] * ly), 0.0, 1.0)
    energy = (ndotl ** (8.0 if reflection_style(key) == 1 else 6.5))
    energy *= (.16 * s['fsoft'] + .62 * s['fmid'] + .90 * s['ftight'])
    return _mask_from(np.clip(energy * (.44 if reflection_style(key) == 1 else .58), 0, .42))


def clear_reflection_coverage_pct(key: str) -> float:
    a = np.asarray(clear_reflection_mask(key), dtype=np.float32) / 255.0
    return float(a.mean() * 100.0)


def _glyph_density(mask: Image.Image) -> Image.Image:
    body = Image.new('L', (WORK, WORK), 102)
    mid = inner_edge(mask, 10).filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * .22))
    tight = inner_edge(mask, 3).filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: int(v * .34))
    return inter(ImageChops.add(ImageChops.add(body, mid), tight), mask)


def clearify_layers(layers, key: str):
    result = []
    for src in layers:
        item = dict(src)
        mask = item['mask']
        src_luma = luminance(item.get('fill', '#fff'))
        item['mask'] = _glyph_density(mask)
        item['material'] = 'glass'
        item['fill'] = '#c2c2c2' if src_luma < 145 else '#dddddd'
        item['opacity'] = .105 if src_luma < 145 else .125
        item['refraction'] = max(.20, min(.28, float(item.get('refraction', .07)) * 2.4))
        item['specular'] = 'off'
        item['shadow'] = .0001
        item['blur'] = 0
        item['blend'] = 'normal'
        result.append(item)

        top = top_facing_edge(mask, 2.6).filter(ImageFilter.GaussianBlur(.55)).point(lambda v: int(v * .62))
        if top.getbbox():
            result.append(layer(top, '#ffffff', .28, 0, 'off', 0, 'ink', 'screen', (0,0), 0,0,0))
        inner = inner_edge(mask, 2.2).filter(ImageFilter.GaussianBlur(.7)).point(lambda v: int(v * .22))
        if inner.getbbox():
            result.append(layer(inner, '#ffffff', .12, 0, 'off', 0, 'ink', 'screen', (0,0), 0,0,0))
        low = bottom_facing_edge(mask, 1.8).point(lambda v: int(v * .38))
        if low.getbbox():
            result.append(layer(low, '#202020', .16, 0, 'off', 0, 'ink', 'multiply', (0,0), 0,0,0))
    return result


def clear_background(key: str) -> Image.Image:
    canvas = Image.new('RGBA', (WORK, WORK), (0,0,0,0))
    density, spec_base, dark_base = _static_fields()
    neutral = Image.new('RGBA', (WORK, WORK), (226,226,226,0)); neutral.putalpha(density); canvas.alpha_composite(neutral)
    white = Image.new('RGBA', (WORK, WORK), (255,255,255,0)); white.putalpha(ImageChops.lighter(spec_base, clear_reflection_mask(key))); canvas.alpha_composite(white)
    dark = Image.new('RGBA', (WORK, WORK), (30,30,30,0)); dark.putalpha(dark_base); canvas.alpha_composite(dark)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    hair = outer_edge(ENCL, .82).point(lambda v: int(v * .17))
    h = Image.new('RGBA', (WORK, WORK), (248,248,248,0)); h.putalpha(hair); canvas.alpha_composite(h)
    dark = outer_edge(ENCL, .62).point(lambda v: int(v * .042))
    d = Image.new('RGBA', (WORK, WORK), (26,26,26,0)); d.putalpha(dark); canvas.alpha_composite(d)
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))


def _local_luma_and_contrast(base: Image.Image):
    gray = base.convert('L')
    radius = max(1.2, base.size[0] * .045)
    mean = np.asarray(gray.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0
    raw = np.asarray(gray, dtype=np.float32) / 255.0
    contrast = np.clip(np.abs(raw - mean) * 2.4, 0.0, 1.0)
    return mean, contrast


def _refract_container(arr: np.ndarray, size: int):
    s = _surface_np(size)
    centre = -0.7 * (s['center'] ** 2.8)
    mid = 2.3 * np.exp(-((s['q'] - .58) / .20) ** 2) * s['inside']
    edge = 9.0 * s['fmid']
    rim = 8.5 * s['ftight']
    strength = centre + mid + edge + rim
    dx = s['nx'] * strength - s['nx'] * 2.2 * s['ftight']
    dy = s['ny'] * strength * .91 - s['ny'] * 1.8 * s['ftight']
    return _bilinear_warp(arr, dx, dy), dx, dy, s


def _mask_gradient_displacement(mask: Image.Image, size: int, strength: float = 8.6):
    m = mask.resize((size,size), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(max(.65, size*.0055)))
    a = np.asarray(m, dtype=np.float32) / 255.0
    gy, gx = np.gradient(a)
    mag = np.sqrt(gx*gx + gy*gy)
    nx = gx / np.maximum(mag, 1e-4); ny = gy / np.maximum(mag, 1e-4)
    edge = np.clip(mag * size * .52, 0.0, 1.0)
    return nx * edge * strength, ny * edge * strength, a


def preview_refract_patch(under: Image.Image, foreground_mask: Image.Image | None = None) -> Image.Image:
    base = under.convert('RGB')
    if base.size[0] != base.size[1]:
        raise ValueError('preview refraction expects a square wallpaper patch')
    size = base.size[0]
    arr = np.asarray(base, dtype=np.float32)
    warped, dx, dy, s = _refract_container(arr, size)
    sharp = Image.fromarray(warped, 'RGB')
    soft = sharp.filter(ImageFilter.GaussianBlur(max(.35, size*.0032)))
    blur_mask = _mask_from(np.clip(.10*s['fsoft'] + .34*s['fmid'] + .44*s['ftight'],0,.42))
    refracted = Image.composite(soft, sharp, blur_mask)
    encl = ENCL.resize((size,size), Image.Resampling.LANCZOS)
    result = Image.composite(refracted, base, encl)

    local_luma, local_contrast = _local_luma_and_contrast(result)
    r = np.asarray(result, dtype=np.float32) / 255.0
    brighten = (1.0-local_luma) * (.045*s['fsoft'] + .16*s['spec'])
    darken = local_luma * (.035*s['fmid'] + .075*s['opposite'])
    contrast_gain = 1.0 + (.05 + .10*(1.0-local_contrast)) * s['fmid']
    mean3 = local_luma[...,None]
    r = (r-mean3)*contrast_gain[...,None] + mean3
    r = np.clip(r + brighten[...,None] - darken[...,None], 0, 1)
    result = Image.fromarray(np.round(r*255).astype(np.uint8),'RGB')

    if foreground_mask is not None and foreground_mask.getbbox():
        dx2, dy2, alpha = _mask_gradient_displacement(foreground_mask, size)
        arr2 = np.asarray(result, dtype=np.float32)
        warped2 = _bilinear_warp(arr2, dx2, dy2).astype(np.float32)
        mix = np.clip(arr2*.08 + warped2*.92, 0, 255).astype(np.uint8)
        gm = Image.fromarray(np.clip(alpha*230,0,255).astype(np.uint8),'L')
        result = Image.composite(Image.fromarray(mix,'RGB'), result, gm)
        lm, _ = _local_luma_and_contrast(result)
        rr = np.asarray(result,dtype=np.float32)/255.0
        a = np.asarray(gm,dtype=np.float32)/255.0
        lift = (1.0-lm) * .050 * a; suppress = lm * .035 * a
        rr = np.clip(rr + lift[...,None] - suppress[...,None],0,1)
        result = Image.fromarray(np.round(rr*255).astype(np.uint8),'RGB')
        top = top_facing_edge(foreground_mask,2.3).resize((size,size),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(.45)).point(lambda v:int(v*.24))
        result = Image.composite(Image.new('RGB',(size,size),(255,255,255)),result,top)
        low = bottom_facing_edge(foreground_mask,1.7).resize((size,size),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(.35)).point(lambda v:int(v*.13))
        result = Image.composite(Image.new('RGB',(size,size),(34,34,34)),result,low)
    return result


@lru_cache(maxsize=1)
def _metric_base():
    s = _surface_np(128)
    dummy = np.zeros((128,128,3),dtype=np.float32)
    _, dx, dy, _ = _refract_container(dummy,128)
    disp = np.sqrt(dx*dx+dy*dy)
    center = s['q'] < .35; mid = (s['q'] >= .45) & (s['q'] < .72); edge = (s['q'] >= .82) & (s['q'] <= 1.0)
    density128 = np.asarray(_static_fields()[0].resize((128,128),Image.Resampling.LANCZOS),dtype=np.float32)
    return {
        'enclosure_center_density': float(density128[center].mean()),
        'enclosure_edge_density': float(density128[edge].mean()),
        'specular_coverage_pct': float((s['spec']>.08).mean()*100),
        'refraction_displacement_mean': float(disp[s['inside']>0].mean()),
        'refraction_displacement_median': float(np.median(disp[s['inside']>0])),
        'refraction_displacement_max': float(disp.max()),
        'refraction_center_mean': float(disp[center].mean()),
        'refraction_mid_mean': float(disp[mid].mean()),
        'refraction_edge_mean': float(disp[edge].mean()),
    }


def material_metrics(key: str) -> dict:
    out = dict(_metric_base())
    out['reflection_coverage_pct'] = clear_reflection_coverage_pct(key)
    out['edge_center_density_ratio'] = out['enclosure_edge_density'] / max(out['enclosure_center_density'],1e-6)
    return out
