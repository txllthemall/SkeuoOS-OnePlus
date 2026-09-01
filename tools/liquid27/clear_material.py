from __future__ import annotations

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


@lru_cache(maxsize=4)
def _diagonal_light(left: bool = True) -> Image.Image:
    """Broad directional environment response, clipped later by actual glass geometry."""
    v = np.asarray(_top_weight(.72), dtype=np.float32) / 255.0
    h = np.asarray(_horizontal_weight(left), dtype=np.float32) / 255.0
    field = np.clip((v * .70 + h * .30) ** 1.35, 0.0, 1.0)
    return Image.fromarray(np.round(field * 255).astype(np.uint8), 'L')


def reflection_style(key: str) -> int:
    """Every icon reflects; style only changes direction/intensity, never material presence."""
    return 2 if (_seed(key, 401) % 10) >= 7 else 1


@lru_cache(maxsize=256)
def clear_reflection_mask(key: str) -> Image.Image:
    """Directional reflection built from the real curved enclosure, never a decorative blob."""
    style = reflection_style(key)
    left = bool(_seed(key, 409) & 1)
    field = _diagonal_light(left)

    edge = inner_edge(ENCL, 3.0 if style == 1 else 4.2)
    edge = edge.filter(ImageFilter.GaussianBlur(1.5 if style == 1 else 2.1))
    edge = inter(edge, field).point(lambda v: int(v * (.24 if style == 1 else .33)))

    # A broad, extremely faint surface catch is what makes the tile read as a
    # continuous curved sheet instead of only a stroked rounded rectangle.
    broad = inner_edge(ENCL, 42).filter(ImageFilter.GaussianBlur(28))
    broad = inter(broad, field).point(lambda v: int(v * (.030 if style == 1 else .045)))
    return ImageChops.lighter(edge, broad)


def clear_reflection_coverage_pct(key: str) -> float:
    m = clear_reflection_mask(key)
    return 100.0 * sum(m.getdata()) / (255.0 * WORK * WORK)


def _soft_inner_band(mask: Image.Image, edge_px: int, blur_px: int) -> Image.Image:
    return inner_edge(mask, edge_px).filter(ImageFilter.GaussianBlur(blur_px))


@lru_cache(maxsize=1)
def _enclosure_density() -> Image.Image:
    """Optical density rises toward the curved boundary; the centre stays almost clear."""
    density = Image.new('L', (WORK, WORK), 4)
    wide = _soft_inner_band(ENCL, 15, 34).point(lambda v: int(v * .11))
    mid = _soft_inner_band(ENCL, 6, 14).point(lambda v: int(v * .15))
    tight = _soft_inner_band(ENCL, 2, 4).point(lambda v: int(v * .22))
    top = inter(ENCL, _diagonal_light(True)).point(lambda v: int(v * .010))
    density = ImageChops.add(density, wide, scale=1.0, offset=0)
    density = ImageChops.add(density, mid, scale=1.0, offset=0)
    density = ImageChops.add(density, tight, scale=1.0, offset=0)
    density = ImageChops.add(density, top, scale=1.0, offset=0)
    return _clip(density)


def _glyph_density(source_mask: Image.Image) -> Image.Image:
    """Glyph body is denser than the enclosure but still transparent glass, not white ink."""
    base = Image.new('L', (WORK, WORK), 166)
    top = _top_weight(1.8).point(lambda v: int(v * .034))
    edge = _soft_inner_band(source_mask, 6, 10).point(lambda v: int(v * .20))
    field = ImageChops.add(base, top, scale=1.0, offset=0)
    field = ImageChops.add(field, edge, scale=1.0, offset=0)
    return inter(source_mask, field)


def clearify_layers(layers, key: str):
    """Convert shared glyph geometry into a neutral translucent optical material."""
    result = []
    top_weight = _top_weight(.66)
    bottom_weight = _bottom_weight(.82)
    side_weight = _horizontal_weight(bool(_seed(key, 503) & 1))

    for src in layers:
        item = dict(src)
        source_mask = item['mask']
        source_luma = luminance(item.get('fill', '#ffffff'))
        item['mask'] = _glyph_density(source_mask)
        item['material'] = 'glass'
        item['fill'] = '#dedede' if source_luma < 145 else '#f2f2f2'
        item['opacity'] = .18 if source_luma < 145 else .22
        item['refraction'] = max(.145, min(.195, float(item.get('refraction', .06)) * 1.82))
        item['specular'] = 'off'
        item['shadow'] = .0003
        item['blend'] = 'normal'
        item['blur'] = min(.12, float(item.get('blur', 0)))
        item['shadow_offset'] = .2
        item['shadow_blur'] = 1.0
        result.append(item)

        # Directional micro-facets following the real glyph silhouette.
        catch = inter(inter(top_facing_edge(source_mask, 1.8), top_weight), side_weight)
        catch = catch.point(lambda v: int(v * .42))
        if catch.getbbox():
            result.append(layer(catch, '#ffffff', .23, 0, 'off', 0, 'ink', 'screen', (0, 0), 0, 0, 0))

        inner = inner_edge(source_mask, 2.4).filter(ImageFilter.GaussianBlur(.8))
        inner = inter(inner, top_weight).point(lambda v: int(v * .20))
        if inner.getbbox():
            result.append(layer(inner, '#ffffff', .11, 0, 'off', 0, 'ink', 'screen', (0, 0), 0, 0, 0))

        lower = inter(bottom_facing_edge(source_mask, 1.5), bottom_weight).point(lambda v: int(v * .26))
        if lower.getbbox():
            result.append(layer(lower, '#303030', .10, 0, 'off', 0, 'ink', 'multiply', (0, 0), 0, 0, 0))

    return result


def clear_background(key: str) -> Image.Image:
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))

    # Intrinsic material is strictly neutral. Environmental hue comes only from
    # the wallpaper in preview/runtime composition, never from these RGB values.
    neutral = Image.new('RGBA', (WORK, WORK), (230, 230, 230, 0))
    neutral.putalpha(_enclosure_density())
    canvas.alpha_composite(neutral)

    reflection = clear_reflection_mask(key)
    white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    white.putalpha(reflection)
    canvas.alpha_composite(white)

    # Multi-component boundary: bright top/side, faint neutral outer hairline,
    # and weak opposite edge. None is a full white outline.
    light_side = _horizontal_weight(bool(_seed(key, 613) & 1))
    top_edge = inter(inter(top_facing_edge(ENCL, 3.0), _top_weight(.52)), light_side)
    top_edge = top_edge.point(lambda v: int(v * .52))
    hi = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    hi.putalpha(top_edge)
    canvas.alpha_composite(hi)

    inner_rim = inter(inner_edge(ENCL, 1.7), _diagonal_light(bool(_seed(key, 617) & 1)))
    inner_rim = inner_rim.point(lambda v: int(v * .18))
    ir = Image.new('RGBA', (WORK, WORK), (250, 250, 250, 0))
    ir.putalpha(inner_rim)
    canvas.alpha_composite(ir)

    low_edge = inter(bottom_facing_edge(ENCL, 2.0), _bottom_weight(1.25)).point(lambda v: int(v * .075))
    shade = Image.new('RGBA', (WORK, WORK), (38, 38, 38, 0))
    shade.putalpha(low_edge)
    canvas.alpha_composite(shade)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    left = bool(_seed(key, 719) & 1)
    hair = inter(outer_edge(ENCL, .85), _diagonal_light(left)).point(lambda v: int(v * .22))
    rim = Image.new('RGBA', (WORK, WORK), (248, 248, 248, 0))
    rim.putalpha(hair)
    canvas.alpha_composite(rim)

    opposite = inter(outer_edge(ENCL, .70), ImageOps.invert(_diagonal_light(left))).point(lambda v: int(v * .035))
    dark = Image.new('RGBA', (WORK, WORK), (32, 32, 32, 0))
    dark.putalpha(opposite)
    canvas.alpha_composite(dark)
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))


# Preview-only live-background optics. Static Android PNG assets cannot sample
# the launcher's wallpaper at runtime; the production asset therefore keeps only
# the neutral alpha/edge structure authored above.
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


def _lens_displacement(size: int):
    """Continuous rounded-square lens: mild centre magnification plus strong curved-edge refraction."""
    yy, xx = np.indices((size, size), dtype=np.float32)
    c = (size - 1) / 2.0
    xn = (xx - c) / max(c, 1.0)
    yn = (yy - c) / max(c, 1.0)
    q = np.clip((np.abs(xn) ** 4 + np.abs(yn) ** 4) ** .25, 0.0, 1.4)

    # Sample slightly toward the centre through most of the lens (magnification),
    # then bend strongly outward in the curved shell near the boundary.
    centre = np.clip(1.0 - q, 0.0, 1.0) ** 2.2
    shell = np.clip((q - .58) / .42, 0.0, 1.0) ** 1.75
    centre_pull = -2.2 * centre
    shell_push = 8.6 * shell
    strength = centre_pull + shell_push
    return xn * strength, yn * strength * .90


def _enclosure_displacement(size: int, strength: float = 1.0):
    dx, dy = _lens_displacement(size)
    return dx * strength, dy * strength


def _mask_gradient_displacement(mask: Image.Image, size: int, strength: float = 4.8):
    m = mask.resize((size, size), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(max(1.0, size * .009)))
    a = np.asarray(m, dtype=np.float32) / 255.0
    gy, gx = np.gradient(a)
    mag = np.sqrt(gx * gx + gy * gy)
    denom = np.maximum(mag, 1e-4)
    edge = np.clip(mag * size * .34, 0.0, 1.0)
    return (gx / denom) * edge * strength, (gy / denom) * edge * strength, a


def _resized_mask(mask: Image.Image, size: int, blur: float = 0.0) -> Image.Image:
    out = mask.resize((size, size), Image.Resampling.LANCZOS)
    if blur > 0:
        out = out.filter(ImageFilter.GaussianBlur(blur))
    return out


def _apply_preview_surface_response(base: Image.Image) -> Image.Image:
    """Environment-adaptive surface response: brighter on dark backgrounds, darker edge on bright ones."""
    size = base.size[0]
    result = base.convert('RGB')
    luma = float(np.asarray(result.convert('L'), dtype=np.float32).mean()) / 255.0

    top = _resized_mask(inter(inner_edge(ENCL, 5.0), _diagonal_light(True)), size, .8)
    top_gain = .15 + (1.0 - luma) * .13
    top = top.point(lambda v: int(v * top_gain))
    hi = Image.new('RGB', result.size, (255, 255, 255))
    result = Image.composite(hi, result, top)

    low = _resized_mask(inter(inner_edge(ENCL, 4.0), _bottom_weight(.82)), size, .8)
    low_gain = .040 + luma * .065
    low = low.point(lambda v: int(v * low_gain))
    dk = Image.new('RGB', result.size, (28, 28, 28))
    result = Image.composite(dk, result, low)

    # Subtle contrast compression inside the lens feels optical rather than frosted.
    contrast = .985 if luma > .66 else 1.015 if luma < .28 else 1.0
    return ImageEnhance.Contrast(result).enhance(contrast)


def preview_refract_patch(under: Image.Image, foreground_mask: Image.Image | None = None) -> Image.Image:
    base = under.convert('RGB')
    if base.size[0] != base.size[1]:
        raise ValueError('preview refraction expects a square wallpaper patch')

    arr = np.asarray(base, dtype=np.float32)
    size = base.size[0]
    dx, dy = _enclosure_displacement(size)
    warped = _bilinear_warp(arr, dx, dy)
    warped_img = Image.fromarray(warped, 'RGB').filter(ImageFilter.GaussianBlur(max(.45, size * .0042)))

    encl = ENCL.resize(base.size, Image.Resampling.LANCZOS)
    result = Image.composite(warped_img, base, encl)
    result = _apply_preview_surface_response(result)

    if foreground_mask is not None and foreground_mask.getbbox():
        dx2, dy2, alpha = _mask_gradient_displacement(foreground_mask, size)
        arr2 = np.asarray(result, dtype=np.float32)
        warped2 = _bilinear_warp(arr2, dx2, dy2)
        mixed = (arr2 * .24 + warped2.astype(np.float32) * .76).astype(np.uint8)
        fm = Image.fromarray(np.clip(alpha * 242, 0, 255).astype(np.uint8), 'L')
        result = Image.composite(Image.fromarray(mixed, 'RGB'), result, fm)

        # The glyph catches the environment on its upper-facing edge, but keeps
        # the wallpaper visible through its body.
        gm = foreground_mask.resize((size, size), Image.Resampling.LANCZOS)
        gtop = _resized_mask(inter(top_facing_edge(foreground_mask, 2.0), _top_weight(.65)), size, .6)
        gtop = gtop.point(lambda v: int(v * .18))
        result = Image.composite(Image.new('RGB', result.size, (255, 255, 255)), result, gtop)
        glow = gm.filter(ImageFilter.GaussianBlur(max(.6, size * .003))).point(lambda v: int(v * .018))
        result = Image.composite(Image.new('RGB', result.size, (245, 245, 245)), result, glow)

    return result


@lru_cache(maxsize=1)
def _metric_base():
    """Expensive morphology is shared by every icon, never recomputed per row."""
    density = np.asarray(_enclosure_density(), dtype=np.float32)
    yy, xx = np.indices(density.shape)
    centre = (np.abs(xx - WORK / 2) < WORK * .20) & (np.abs(yy - WORK / 2) < WORK * .20)
    edge_mask = np.asarray(inner_edge(ENCL, 8), dtype=np.uint8) > 0
    top_spec = np.asarray(inter(top_facing_edge(ENCL, 3.0), _top_weight(.52)), dtype=np.uint8)
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
