from __future__ import annotations

import hashlib
from functools import lru_cache

import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageOps

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


def _seed(key: str, salt: int = 0) -> int:
    raw = hashlib.sha256(f'{key}:{salt}'.encode('utf-8')).digest()
    return int.from_bytes(raw[:4], 'big')


def _clip(mask: Image.Image) -> Image.Image:
    return inter(mask, ENCL)


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


def reflection_style(key: str) -> int:
    """0 none (~25%), 1 subtle edge catch (~50%), 2 stronger catch (~25%)."""
    v = _seed(key, 401) % 20
    if v < 5:
        return 0
    if v < 15:
        return 1
    return 2


@lru_cache(maxsize=256)
def clear_reflection_mask(key: str) -> Image.Image:
    """Environmental response derived only from the real enclosure edge."""
    style = reflection_style(key)
    if style == 0:
        return blank_mask()
    left = bool(_seed(key, 409) & 1)
    edge = inner_edge(ENCL, 2.2 if style == 1 else 3.0)
    edge = edge.filter(ImageFilter.GaussianBlur(1.2 if style == 1 else 1.8))
    mask = inter(inter(edge, _top_weight(.52)), _horizontal_weight(left))
    strength = .18 if style == 1 else .26
    return mask.point(lambda v: int(v * strength))


def clear_reflection_coverage_pct(key: str) -> float:
    m = clear_reflection_mask(key)
    return 100.0 * sum(m.getdata()) / (255.0 * WORK * WORK)


def _soft_inner_band(mask: Image.Image, edge_px: int, blur_px: int) -> Image.Image:
    return inner_edge(mask, edge_px).filter(ImageFilter.GaussianBlur(blur_px))


@lru_cache(maxsize=1)
def _enclosure_density() -> Image.Image:
    # Keep the centre extremely clear and concentrate optical density near the
    # curved boundary. The tile should read as a lens, never a translucent plate.
    density = Image.new('L', (WORK, WORK), 3)
    wide = _soft_inner_band(ENCL, 8, 22).point(lambda v: int(v * .13))
    tight = _soft_inner_band(ENCL, 2, 4).point(lambda v: int(v * .18))
    top = _top_weight(2.7).point(lambda v: int(v * .014))
    density = ImageChops.add(density, wide, scale=1.0, offset=0)
    density = ImageChops.add(density, tight, scale=1.0, offset=0)
    density = ImageChops.add(density, top, scale=1.0, offset=0)
    return _clip(density)


def _glyph_density(source_mask: Image.Image) -> Image.Image:
    base = Image.new('L', (WORK, WORK), 190)
    top = _top_weight(2.0).point(lambda v: int(v * .030))
    edge = _soft_inner_band(source_mask, 5, 9).point(lambda v: int(v * .16))
    field = ImageChops.add(base, top, scale=1.0, offset=0)
    field = ImageChops.add(field, edge, scale=1.0, offset=0)
    return inter(source_mask, field)


def clearify_layers(layers, key: str):
    """Convert shared geometry into colorless Clear material without decorative blobs."""
    result = []
    top_weight = _top_weight(.72)
    for src in layers:
        item = dict(src)
        source_mask = item['mask']
        source_luma = luminance(item.get('fill', '#ffffff'))
        item['mask'] = _glyph_density(source_mask)
        item['material'] = 'glass'
        # Equal-channel fills keep intrinsic material neutral; wallpaper is the
        # only allowed source of hue in the clear treatment.
        item['fill'] = '#e2e2e2' if source_luma < 145 else '#f4f4f4'
        item['opacity'] = .30 if source_luma < 145 else .34
        item['refraction'] = max(.12, min(.17, float(item.get('refraction', .06)) * 1.55))
        item['specular'] = 'off'
        item['shadow'] = .0004
        item['blend'] = 'normal'
        item['blur'] = min(.10, float(item.get('blur', 0)))
        item['shadow_offset'] = .2
        item['shadow_blur'] = 1.0
        result.append(item)

        # Shape-following catch only. No fake oval/ribbon highlight textures.
        catch = inter(top_facing_edge(source_mask, 1.5), top_weight).point(lambda v: int(v * .28))
        if catch.getbbox():
            result.append(layer(catch, '#ffffff', .14, 0, 'off', 0, 'ink', 'screen', (0, 0), 0, 0, 0))
    return result


def clear_background(key: str) -> Image.Image:
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))
    neutral = Image.new('RGBA', (WORK, WORK), (232, 232, 232, 0))
    neutral.putalpha(_enclosure_density())
    canvas.alpha_composite(neutral)

    reflection = clear_reflection_mask(key)
    if reflection.getbbox():
        white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
        white.putalpha(reflection)
        canvas.alpha_composite(white)

    top_edge = inter(top_facing_edge(ENCL, 2.0), _top_weight(.55)).point(lambda v: int(v * .38))
    hi = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    hi.putalpha(top_edge)
    canvas.alpha_composite(hi)

    low_edge = inter(bottom_facing_edge(ENCL, 1.1), _bottom_weight(1.5)).point(lambda v: int(v * .032))
    shade = Image.new('RGBA', (WORK, WORK), (48, 48, 48, 0))
    shade.putalpha(low_edge)
    canvas.alpha_composite(shade)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    hair = inter(outer_edge(ENCL, .75), _top_weight(.60)).point(lambda v: int(v * .16))
    rim = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    rim.putalpha(hair)
    canvas.alpha_composite(rim)
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))


# Preview-only real background displacement. Static Android PNG assets cannot
# access the launcher's wallpaper at runtime; DESIGN_NOTES documents this limit.
def _bilinear_warp(rgb: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    yy, xx = np.indices((h, w), dtype=np.float32)
    sx = np.clip(xx + dx, 0, w - 1.001)
    sy = np.clip(yy + dy, 0, h - 1.001)
    x0 = np.floor(sx).astype(np.int32)
    y0 = np.floor(sy).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    wx = (sx - x0)[..., None]
    wy = (sy - y0)[..., None]
    a = rgb[y0, x0] * (1 - wx) + rgb[y0, x1] * wx
    b = rgb[y1, x0] * (1 - wx) + rgb[y1, x1] * wx
    return np.clip(a * (1 - wy) + b * wy, 0, 255).astype(np.uint8)


def _enclosure_displacement(size: int, strength: float = 6.8):
    yy, xx = np.indices((size, size), dtype=np.float32)
    c = (size - 1) / 2.0
    xn = (xx - c) / max(c, 1.0)
    yn = (yy - c) / max(c, 1.0)
    q = (np.abs(xn) ** 4 + np.abs(yn) ** 4) ** .25
    edge = np.clip((q - .46) / .54, 0.0, 1.0) ** 2.15
    return xn * edge * strength, yn * edge * strength * .88


def _mask_gradient_displacement(mask: Image.Image, size: int, strength: float = 3.4):
    m = mask.resize((size, size), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(max(1.0, size * .010)))
    a = np.asarray(m, dtype=np.float32) / 255.0
    gy, gx = np.gradient(a)
    mag = np.sqrt(gx * gx + gy * gy)
    denom = np.maximum(mag, 1e-4)
    edge = np.clip(mag * size * .30, 0.0, 1.0)
    return (gx / denom) * edge * strength, (gy / denom) * edge * strength, a


def preview_refract_patch(under: Image.Image, foreground_mask: Image.Image | None = None) -> Image.Image:
    base = under.convert('RGB')
    if base.size[0] != base.size[1]:
        raise ValueError('preview refraction expects a square wallpaper patch')
    arr = np.asarray(base, dtype=np.float32)
    size = base.size[0]
    dx, dy = _enclosure_displacement(size)
    warped = _bilinear_warp(arr, dx, dy)
    warped_img = Image.fromarray(warped, 'RGB').filter(ImageFilter.GaussianBlur(max(.40, size * .0035)))
    encl = ENCL.resize(base.size, Image.Resampling.LANCZOS)
    result = Image.composite(warped_img, base, encl)

    if foreground_mask is not None and foreground_mask.getbbox():
        dx2, dy2, alpha = _mask_gradient_displacement(foreground_mask, size)
        arr2 = np.asarray(result, dtype=np.float32)
        warped2 = _bilinear_warp(arr2, dx2, dy2)
        mixed = (arr2 * .42 + warped2.astype(np.float32) * .58).astype(np.uint8)
        fm = Image.fromarray(np.clip(alpha * 255, 0, 255).astype(np.uint8), 'L')
        result = Image.composite(Image.fromarray(mixed, 'RGB'), result, fm)
    return result


@lru_cache(maxsize=1)
def _metric_base():
    """Expensive morphology is shared by every icon, never recomputed per row."""
    density = np.asarray(_enclosure_density(), dtype=np.float32)
    yy, xx = np.indices(density.shape)
    centre = (np.abs(xx - WORK / 2) < WORK * .20) & (np.abs(yy - WORK / 2) < WORK * .20)
    edge_mask = np.asarray(inner_edge(ENCL, 6), dtype=np.uint8) > 0
    top_spec = np.asarray(inter(top_facing_edge(ENCL, 2.0), _top_weight(.55)), dtype=np.uint8)
    dx, dy = _enclosure_displacement(128)
    disp = np.sqrt(dx * dx + dy * dy)
    return {
        'enclosure_center_density': float(density[centre].mean()),
        'enclosure_edge_density': float(density[edge_mask].mean()) if edge_mask.any() else 0.0,
        'specular_coverage_pct': float((top_spec > 12).mean() * 100.0),
        'refraction_displacement_mean': float(disp.mean()),
        'refraction_displacement_max': float(disp.max()),
    }


def material_metrics(key: str) -> dict:
    result = dict(_metric_base())
    result['reflection_coverage_pct'] = clear_reflection_coverage_pct(key)
    return result
