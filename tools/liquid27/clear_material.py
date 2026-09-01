from __future__ import annotations

import hashlib
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

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


def _edge_gate(key: str, salt: int = 0, *, broad=False) -> Image.Image:
    """Select one irregular illuminated corner/edge region."""
    s = _seed(key, salt)
    side = -1 if s & 1 else 1
    reach = .70 if broad else .57
    depth = .52 if broad else .38
    skew = (((s >> 9) & 31) / 31.0 - .5) * .10
    m = blank_mask()
    d = ImageDraw.Draw(m)
    if side < 0:
        d.polygon([
            (0, 0), (int(WORK * reach), 0),
            (int(WORK * (.42 + skew)), int(WORK * depth)),
            (0, int(WORK * (depth + .16))),
        ], fill=255)
    else:
        d.polygon([
            (int(WORK * (1.0 - reach)), 0), (WORK, 0),
            (WORK, int(WORK * (depth + .16))),
            (int(WORK * (.58 + skew)), int(WORK * depth)),
        ], fill=255)
    return _clip(m.filter(ImageFilter.GaussianBlur(14 if broad else 10)))


def reflection_style(key: str) -> int:
    """0 = none, 1/2 = corner catch, 3 = rare broader edge reflection."""
    v = _seed(key, 401) % 20
    if v < 11:
        return 0
    if v < 15:
        return 1
    if v < 19:
        return 2
    return 3


@lru_cache(maxsize=256)
def clear_reflection_mask(key: str) -> Image.Image:
    style = reflection_style(key)
    if style == 0:
        return blank_mask()

    # Use a narrow morphological edge and spread it optically with blur. This is
    # equivalent to a broad soft reflection band visually, but avoids enormous
    # 97–157px MinFilter kernels on every icon.
    edge_px = 8 if style in (1, 2) else 12
    blur_px = 17 if style in (1, 2) else 25
    band = inner_edge(ENCL, edge_px).filter(ImageFilter.GaussianBlur(blur_px))
    gate = _edge_gate(key, 413 + style, broad=(style == 3))
    top = _top_weight(.62 if style == 3 else .74)
    mask = inter(inter(band, gate), top)
    strength = .34 if style in (1, 2) else .43
    return mask.point(lambda v: int(v * strength))


def clear_reflection_coverage_pct(key: str) -> float:
    m = clear_reflection_mask(key)
    return 100.0 * sum(m.getdata()) / (255.0 * WORK * WORK)


def _soft_inner_band(mask: Image.Image, edge_px: int, blur_px: int) -> Image.Image:
    """Fast optical-thickness field from a narrow true edge + soft falloff."""
    return inner_edge(mask, edge_px).filter(ImageFilter.GaussianBlur(blur_px))


def _glyph_density(source_mask: Image.Image) -> Image.Image:
    """Optical density follows thickness: clearer center, denser near edges."""
    base = Image.new('L', (WORK, WORK), 198)
    top = _top_weight(2.1).point(lambda v: int(v * .035))
    edge = _soft_inner_band(source_mask, 6, 11).point(lambda v: int(v * .19))
    field = ImageChops.add(base, top, scale=1.0, offset=0)
    field = ImageChops.add(field, edge, scale=1.0, offset=0)
    return inter(source_mask, field)


def clearify_layers(layers, key: str):
    """Convert shared Color geometry into the Clear optical material.

    No foreground layer receives a mandatory environmental reflection. Glass is
    described by transparency, lower-layer refraction and shape-following edge
    response. This removes both old crescents and repeated top oval/pill marks.
    """
    result = []
    top_weight = _top_weight(.66)
    gate = _edge_gate(key, 91)

    for src in layers:
        item = dict(src)
        source_mask = item['mask']
        source_luma = luminance(item.get('fill', '#ffffff'))

        item['mask'] = _glyph_density(source_mask)
        item['material'] = 'glass'
        item['fill'] = '#cbd4df' if source_luma < 145 else '#f2f5f8'
        item['opacity'] = .29 if source_luma < 145 else .35
        item['refraction'] = max(.118, min(.158, float(item.get('refraction', .06)) * 1.55))
        item['specular'] = 'inside'
        item['shadow'] = .0005
        item['blend'] = 'normal'
        item['blur'] = min(.18, float(item.get('blur', 0)))
        item['shadow_offset'] = .25
        item['shadow_blur'] = 1.2
        result.append(item)

        # Thin directional catch light on the glyph contour itself.
        glint = inter(inter(top_facing_edge(source_mask, 1.8), top_weight), gate)
        glint = glint.point(lambda v: int(v * .46))
        if glint.getbbox():
            result.append(layer(
                glint, '#ffffff', .20, 0, 'off', 0,
                'ink', 'screen', (0, 0), 0, 0, 0,
            ))

    return result


def clear_background(key: str) -> Image.Image:
    """Highly transparent enclosure with edge-dependent optical thickness."""
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))

    # Clear center, denser edge. Narrow true edge bands are blurred outward to
    # produce optical-thickness falloff without huge morphological kernels.
    density = Image.new('L', (WORK, WORK), 11)
    density = ImageChops.add(density, _top_weight(2.25).point(lambda v: int(v * .018)))
    edge_wide = _soft_inner_band(ENCL, 8, 22).point(lambda v: int(v * .15))
    edge_tight = _soft_inner_band(ENCL, 3, 5).point(lambda v: int(v * .11))
    density = _clip(ImageChops.add(density, edge_wide, scale=1.0, offset=0))
    density = _clip(ImageChops.add(density, edge_tight, scale=1.0, offset=0))

    neutral = Image.new('RGBA', (WORK, WORK), (229, 234, 240, 0))
    neutral.putalpha(density)
    canvas.alpha_composite(neutral)

    reflection = clear_reflection_mask(key)
    if reflection.getbbox():
        white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
        white.putalpha(reflection)
        canvas.alpha_composite(white)

    gate = _edge_gate(key, 7)
    top_edge = inter(inter(top_facing_edge(ENCL, 2.7), _top_weight(.62)), gate)
    top_edge = top_edge.point(lambda v: int(v * .52))
    hi = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    hi.putalpha(top_edge)
    canvas.alpha_composite(hi)

    low_edge = inter(bottom_facing_edge(ENCL, 1.35), _bottom_weight(1.3)).point(lambda v: int(v * .024))
    shade = Image.new('RGBA', (WORK, WORK), (48, 55, 68, 0))
    shade.putalpha(low_edge)
    canvas.alpha_composite(shade)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    gate = _edge_gate(key, 23)
    hair = inter(inter(outer_edge(ENCL, .9), _top_weight(.64)), gate).point(lambda v: int(v * .24))
    rim = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    rim.putalpha(hair)
    canvas.alpha_composite(rim)
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))
