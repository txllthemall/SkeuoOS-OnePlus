from __future__ import annotations

"""High-polish Clear material layer.

This module deliberately separates wallpaper-aware preview optics from the
wallpaper-agnostic static Android asset. Geometry remains owned by geometry.py.
"""

import hashlib
from functools import lru_cache

import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

from .material import (
    WORK,
    ENCL,
    blank_mask,
    inter,
    inner_edge,
    outer_edge,
    top_facing_edge,
    bottom_facing_edge,
    layer,
    luminance,
)
from .clear_material import _bilinear_warp


def _seed(key: str, salt: int = 0) -> int:
    raw = hashlib.sha256(f'{key}:{salt}'.encode('utf-8')).digest()
    return int.from_bytes(raw[:4], 'big')


@lru_cache(maxsize=16)
def _top_weight(power: float = 1.0) -> Image.Image:
    g = ImageOps.invert(Image.linear_gradient('L').resize((WORK, WORK)))
    if power != 1.0:
        g = g.point(lambda v: int(((v / 255.0) ** power) * 255))
    return g


@lru_cache(maxsize=16)
def _bottom_weight(power: float = 1.0) -> Image.Image:
    g = Image.linear_gradient('L').resize((WORK, WORK))
    if power != 1.0:
        g = g.point(lambda v: int(((v / 255.0) ** power) * 255))
    return g


@lru_cache(maxsize=4)
def _horizontal_weight(left: bool) -> Image.Image:
    g = Image.linear_gradient('L').resize((WORK, WORK)).rotate(90, expand=False)
    return ImageOps.invert(g) if left else g


@lru_cache(maxsize=4)
def _environment_field(left: bool) -> Image.Image:
    """Directional environment field used by rims/reflections, never a fake blob."""
    v = np.asarray(_top_weight(.62), dtype=np.float32) / 255.0
    h = np.asarray(_horizontal_weight(left), dtype=np.float32) / 255.0
    diagonal = np.clip(v * .72 + h * .28, 0.0, 1.0)
    diagonal = np.power(diagonal, 1.22)
    return Image.fromarray(np.round(diagonal * 255).astype(np.uint8), 'L')


@lru_cache(maxsize=1)
def _edge_fresnel() -> Image.Image:
    """Fresnel-like energy rising toward the rounded-square boundary."""
    wide = inner_edge(ENCL, 72).filter(ImageFilter.GaussianBlur(28))
    mid = inner_edge(ENCL, 24).filter(ImageFilter.GaussianBlur(11))
    tight = inner_edge(ENCL, 6).filter(ImageFilter.GaussianBlur(2.4))
    field = ImageChops.add(wide.point(lambda v: int(v * .12)), mid.point(lambda v: int(v * .18)))
    field = ImageChops.add(field, tight.point(lambda v: int(v * .30)))
    return inter(field, ENCL)


@lru_cache(maxsize=1)
def _enclosure_density() -> Image.Image:
    """Clear centre plus enough neutral body to read as one continuous glass sheet."""
    base = Image.new('L', (WORK, WORK), 7)
    fresnel = _edge_fresnel().point(lambda v: int(v * .50))
    top = inter(ENCL, _top_weight(2.3)).point(lambda v: int(v * .012))
    return inter(ImageChops.add(ImageChops.add(base, fresnel), top), ENCL)


def reflection_style(key: str) -> int:
    return 2 if (_seed(key, 401) % 5) == 0 else 1


@lru_cache(maxsize=256)
def clear_reflection_mask(key: str) -> Image.Image:
    style = reflection_style(key)
    left = bool(_seed(key, 409) & 1)
    env = _environment_field(left)
    fresnel = _edge_fresnel()

    edge = inter(inner_edge(ENCL, 4.0 if style == 1 else 5.2), env)
    edge = edge.filter(ImageFilter.GaussianBlur(1.8 if style == 1 else 2.4))
    edge = edge.point(lambda v: int(v * (.28 if style == 1 else .38)))

    # Broader low-energy reflection reads as a curved surface instead of four
    # bright corner handles.
    broad = inter(fresnel, env).filter(ImageFilter.GaussianBlur(10))
    broad = broad.point(lambda v: int(v * (.095 if style == 1 else .125)))
    return ImageChops.lighter(edge, broad)


def clear_reflection_coverage_pct(key: str) -> float:
    m = clear_reflection_mask(key)
    return 100.0 * sum(m.getdata()) / (255.0 * WORK * WORK)


def _glyph_density(source_mask: Image.Image) -> Image.Image:
    base = Image.new('L', (WORK, WORK), 132)
    edge = inner_edge(source_mask, 8).filter(ImageFilter.GaussianBlur(5)).point(lambda v: int(v * .24))
    top = inter(source_mask, _top_weight(1.7)).point(lambda v: int(v * .030))
    return inter(ImageChops.add(ImageChops.add(base, edge), top), source_mask)


def clearify_layers(layers, key: str):
    """Turn existing glyph geometry into transparent neutral glass, not white ink."""
    result = []
    top = _top_weight(.58)
    bottom = _bottom_weight(.78)
    side = _horizontal_weight(bool(_seed(key, 503) & 1))

    for src in layers:
        item = dict(src)
        mask = item['mask']
        source_luma = luminance(item.get('fill', '#ffffff'))
        item['mask'] = _glyph_density(mask)
        item['material'] = 'glass'
        item['fill'] = '#c8c8c8' if source_luma < 145 else '#e0e0e0'
        item['opacity'] = .150 if source_luma < 145 else .180
        item['refraction'] = max(.175, min(.235, float(item.get('refraction', .06)) * 2.05))
        item['specular'] = 'off'
        item['shadow'] = .0002
        item['blend'] = 'normal'
        item['blur'] = min(.08, float(item.get('blur', 0)))
        item['shadow_offset'] = .15
        item['shadow_blur'] = .8
        result.append(item)

        bright = inter(inter(top_facing_edge(mask, 2.3), top), side)
        bright = bright.point(lambda v: int(v * .52))
        if bright.getbbox():
            result.append(layer(bright, '#ffffff', .27, 0, 'off', 0, 'ink', 'screen', (0, 0), 0, 0, 0))

        inner = inter(inner_edge(mask, 3.2), top).filter(ImageFilter.GaussianBlur(.65))
        inner = inner.point(lambda v: int(v * .26))
        if inner.getbbox():
            result.append(layer(inner, '#ffffff', .14, 0, 'off', 0, 'ink', 'screen', (0, 0), 0, 0, 0))

        lower = inter(bottom_facing_edge(mask, 1.8), bottom).point(lambda v: int(v * .34))
        if lower.getbbox():
            result.append(layer(lower, '#242424', .14, 0, 'off', 0, 'ink', 'multiply', (0, 0), 0, 0, 0))

    return result


def clear_background(key: str) -> Image.Image:
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))

    neutral = Image.new('RGBA', (WORK, WORK), (226, 226, 226, 0))
    neutral.putalpha(_enclosure_density())
    canvas.alpha_composite(neutral)

    reflection = clear_reflection_mask(key)
    white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    white.putalpha(reflection)
    canvas.alpha_composite(white)

    left = bool(_seed(key, 613) & 1)
    env = _environment_field(left)

    # Extremely low-energy surface sheen bridges the centre and bevel. It is
    # directional and geometry-clipped, not a decorative highlight blob.
    surface = inter(ENCL, env).filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * .022))
    sheen = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    sheen.putalpha(surface)
    canvas.alpha_composite(sheen)

    high = inter(inter(inner_edge(ENCL, 3.0), env), _top_weight(.50))
    high = high.point(lambda v: int(v * .44))
    hi = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    hi.putalpha(high)
    canvas.alpha_composite(hi)

    opposite = inter(inner_edge(ENCL, 2.1), ImageOps.invert(env))
    opposite = inter(opposite, _bottom_weight(.78)).point(lambda v: int(v * .12))
    dk = Image.new('RGBA', (WORK, WORK), (30, 30, 30, 0))
    dk.putalpha(opposite)
    canvas.alpha_composite(dk)

    boundary = inner_edge(ENCL, 1.05).point(lambda v: int(v * .040))
    bd = Image.new('RGBA', (WORK, WORK), (40, 40, 40, 0))
    bd.putalpha(boundary)
    canvas.alpha_composite(bd)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    left = bool(_seed(key, 719) & 1)
    env = _environment_field(left)

    outer = inter(outer_edge(ENCL, .85), env).point(lambda v: int(v * .19))
    rim = Image.new('RGBA', (WORK, WORK), (248, 248, 248, 0))
    rim.putalpha(outer)
    canvas.alpha_composite(rim)

    dark = inter(outer_edge(ENCL, .72), ImageOps.invert(env)).point(lambda v: int(v * .065))
    d = Image.new('RGBA', (WORK, WORK), (26, 26, 26, 0))
    d.putalpha(dark)
    canvas.alpha_composite(d)
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))


def _superellipse_lens(size: int):
    """Rounded-square surface normals + smoothly varying Apple-like lensing."""
    yy, xx = np.indices((size, size), dtype=np.float32)
    c = (size - 1) / 2.0
    xn = (xx - c) / max(c, 1.0)
    yn = (yy - c) / max(c, 1.0)

    q = np.clip((np.abs(xn) ** 4 + np.abs(yn) ** 4) ** .25, 0.0, 1.5)
    inside = np.clip(1.0 - q, 0.0, 1.0)
    mid = np.exp(-((q - .64) / .22) ** 2)
    edge = np.clip((q - .58) / .42, 0.0, 1.0) ** 1.55

    gx = np.sign(xn) * np.abs(xn) ** 3
    gy = np.sign(yn) * np.abs(yn) ** 3
    mag = np.maximum(np.sqrt(gx * gx + gy * gy), 1e-5)
    nx = gx / mag
    ny = gy / mag

    # Pass 1 over-broke thin rails. This retains obvious edge lensing while
    # keeping line continuity closer to polished system glass.
    strength = -1.45 * inside ** 2.4 + 2.15 * mid + 11.2 * edge
    dx = nx * strength + xn * (.65 * mid)
    dy = ny * strength * .90 + yn * (.50 * mid)
    return dx, dy, q


def _mask_gradient_displacement(mask: Image.Image, size: int, strength: float = 6.4):
    m = mask.resize((size, size), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(max(.8, size * .007)))
    a = np.asarray(m, dtype=np.float32) / 255.0
    gy, gx = np.gradient(a)
    mag = np.sqrt(gx * gx + gy * gy)
    denom = np.maximum(mag, 1e-4)
    edge = np.clip(mag * size * .41, 0.0, 1.0)
    return (gx / denom) * edge * strength, (gy / denom) * edge * strength, a


def _resized(mask: Image.Image, size: int, blur: float = 0.0) -> Image.Image:
    out = mask.resize((size, size), Image.Resampling.LANCZOS)
    if blur:
        out = out.filter(ImageFilter.GaussianBlur(blur))
    return out


def _adaptive_surface(base: Image.Image) -> Image.Image:
    """Smooth local contrast adaptation without changing material hue."""
    size = base.size[0]
    original = base.convert('RGB')
    arr_l = np.asarray(original.convert('L'), dtype=np.float32) / 255.0
    luma = float(arr_l.mean())
    contrast = float(arr_l.std())
    encl = _resized(ENCL, size)

    # Bright wallpaper receives substantially more neutral attenuation so white
    # glyph facets stay legible; dark wallpaper receives a small transmission lift.
    brightness = 1.0 + np.clip(.48 - luma, -.40, .40) * .235
    contrast_gain = 1.018 + np.clip(.16 - contrast, -.12, .16) * .18
    body = ImageEnhance.Brightness(original).enhance(float(brightness))
    body = ImageEnhance.Contrast(body).enhance(float(contrast_gain))
    result = Image.composite(body, original, encl)

    top_gain = .15 + (1.0 - luma) * .23
    top = _resized(inter(inner_edge(ENCL, 7), _environment_field(True)), size, .85)
    top = top.point(lambda v: int(v * top_gain))
    result = Image.composite(Image.new('RGB', result.size, (255, 255, 255)), result, top)

    low_gain = .050 + luma * .145
    low = _resized(inter(inner_edge(ENCL, 5), _bottom_weight(.82)), size, .8)
    low = low.point(lambda v: int(v * low_gain))
    result = Image.composite(Image.new('RGB', result.size, (24, 24, 24)), result, low)
    return result


def preview_refract_patch(under: Image.Image, foreground_mask: Image.Image | None = None) -> Image.Image:
    base = under.convert('RGB')
    if base.size[0] != base.size[1]:
        raise ValueError('preview refraction expects a square wallpaper patch')

    arr = np.asarray(base, dtype=np.float32)
    size = base.size[0]
    dx, dy, q = _superellipse_lens(size)
    warped = _bilinear_warp(arr, dx, dy)

    sharp = Image.fromarray(warped, 'RGB')
    soft = sharp.filter(ImageFilter.GaussianBlur(max(.55, size * .0055)))
    shell = np.clip((q - .46) / .54, 0.0, 1.0)
    shell_mask = Image.fromarray(np.round(shell * 255 * .46).astype(np.uint8), 'L')
    warped_img = Image.composite(soft, sharp, shell_mask)

    encl = ENCL.resize(base.size, Image.Resampling.LANCZOS)
    result = Image.composite(warped_img, base, encl)
    result = _adaptive_surface(result)

    if foreground_mask is not None and foreground_mask.getbbox():
        dx2, dy2, alpha = _mask_gradient_displacement(foreground_mask, size)
        arr2 = np.asarray(result, dtype=np.float32)
        warped2 = _bilinear_warp(arr2, dx2, dy2)
        mixed = (arr2 * .16 + warped2.astype(np.float32) * .84).astype(np.uint8)
        fm = Image.fromarray(np.clip(alpha * 240, 0, 255).astype(np.uint8), 'L')
        result = Image.composite(Image.fromarray(mixed, 'RGB'), result, fm)

        gm = foreground_mask.resize((size, size), Image.Resampling.LANCZOS)
        patch_luma = float(np.asarray(base.convert('L'), dtype=np.float32).mean()) / 255.0

        if patch_luma > .55:
            amount = min(.105, (patch_luma - .55) * .20 + .030)
            support = gm.filter(ImageFilter.GaussianBlur(max(.35, size * .002))).point(lambda v: int(v * amount))
            result = Image.composite(Image.new('RGB', result.size, (62, 62, 62)), result, support)
        else:
            amount = min(.08, (.55 - patch_luma) * .13 + .020)
            support = gm.filter(ImageFilter.GaussianBlur(max(.35, size * .002))).point(lambda v: int(v * amount))
            result = Image.composite(Image.new('RGB', result.size, (242, 242, 242)), result, support)

        gtop = _resized(inter(top_facing_edge(foreground_mask, 2.4), _top_weight(.56)), size, .50)
        gtop = gtop.point(lambda v: int(v * (.29 if patch_luma < .45 else .21)))
        result = Image.composite(Image.new('RGB', result.size, (255, 255, 255)), result, gtop)

        glow = gm.filter(ImageFilter.GaussianBlur(max(.5, size * .0025))).point(lambda v: int(v * .009))
        result = Image.composite(Image.new('RGB', result.size, (238, 238, 238)), result, glow)

    return result


@lru_cache(maxsize=1)
def _metric_base():
    density = np.asarray(_enclosure_density(), dtype=np.float32)
    yy, xx = np.indices(density.shape)
    centre = (np.abs(xx - WORK / 2) < WORK * .20) & (np.abs(yy - WORK / 2) < WORK * .20)
    edge_mask = np.asarray(inner_edge(ENCL, 10), dtype=np.uint8) > 0
    dx, dy, _ = _superellipse_lens(128)
    disp = np.sqrt(dx * dx + dy * dy)
    spec = np.asarray(inter(inner_edge(ENCL, 3), _environment_field(True)), dtype=np.uint8)
    return {
        'enclosure_center_density': float(density[centre].mean()),
        'enclosure_edge_density': float(density[edge_mask].mean()) if edge_mask.any() else 0.0,
        'specular_coverage_pct': float((spec > 12).mean() * 100.0),
        'refraction_displacement_mean': float(disp.mean()),
        'refraction_displacement_max': float(disp.max()),
    }


def material_metrics(key: str) -> dict:
    result = dict(_metric_base())
    result['reflection_coverage_pct'] = clear_reflection_coverage_pct(key)
    return result
