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


def _soft_patch(key: str, salt: int = 0, *, strength=255) -> Image.Image:
    """Small environmental reflection, never a ribbon across the whole icon."""
    s = _seed(key, salt)
    side = -1 if s & 1 else 1
    cx = WORK * (0.70 if side > 0 else 0.30)
    cy = WORK * (0.20 + ((s >> 7) & 31) / 31.0 * .10)
    rx = WORK * (0.19 + ((s >> 13) & 15) / 15.0 * .035)
    ry = WORK * (0.040 + ((s >> 18) & 7) / 7.0 * .018)
    angle = side * (12 + ((s >> 22) & 7))
    m = blank_mask()
    ImageDraw.Draw(m).ellipse((int(cx-rx), int(cy-ry), int(cx+rx), int(cy+ry)), fill=strength)
    m = m.rotate(angle, center=(WORK // 2, WORK // 2), resample=Image.Resampling.BICUBIC)
    m = m.filter(ImageFilter.GaussianBlur(14))
    return _clip(m)


@lru_cache(maxsize=256)
def _density_field(key: str) -> Image.Image:
    """Subtle optical-density variation. No high-contrast painted reflections."""
    field = Image.new('L', (WORK, WORK), 172)
    top = _top_weight(1.8).point(lambda v: int(v * .055))
    field = ImageChops.add(field, top, scale=1.0, offset=0)
    patch = _soft_patch(key, 17, strength=120).point(lambda v: int(v * .16))
    field = ImageChops.add(field, patch, scale=1.0, offset=0)
    return _clip(field)


def clearify_layers(layers, key: str):
    """Clear variant: clean glyph geometry, low tint, sparse edge/specular response."""
    result = []
    field = _density_field(key)
    reflection_field = _soft_patch(key, 61, strength=150)
    top_weight = _top_weight(.72)

    for src in layers:
        item = dict(src)
        source_mask = item['mask']
        source_luma = luminance(item.get('fill', '#ffffff'))

        # Keep the complete silhouette readable. Density variation is mild and
        # must never chew holes into brand geometry.
        item['mask'] = inter(source_mask, field)
        item['material'] = 'glass'
        item['fill'] = '#cbd4df' if source_luma < 145 else '#f1f5f9'
        item['opacity'] = .25 if source_luma < 145 else .30
        item['refraction'] = max(.105, min(.145, float(item.get('refraction', .06)) * 1.42))
        item['specular'] = 'inside'
        item['shadow'] = .001
        item['blend'] = 'normal'
        item['blur'] = min(.30, float(item.get('blur', 0)))
        item['shadow_offset'] = .5
        item['shadow_blur'] = 1.8
        result.append(item)

        # Tiny local reflection only. Previous v4.1 used giant white crescents
        # that read as shrink-wrap/cellophane and obscured the glyph.
        reflection = inter(source_mask, reflection_field).point(lambda v: int(v * .24))
        if reflection.getbbox():
            result.append(layer(
                reflection, '#ffffff', .10, 0, 'off', 0,
                'ink', 'screen', (0, 0), 0, 0, 0,
            ))

        # Incomplete top-facing edge highlight. No full white outline.
        glint = inter(top_facing_edge(source_mask, 1.8), top_weight).point(lambda v: int(v * .34))
        if glint.getbbox():
            result.append(layer(
                glint, '#ffffff', .18, 0, 'off', 0,
                'ink', 'screen', (0, 0), 0, 0, 0,
            ))

    return result


def clear_background(key: str) -> Image.Image:
    """Transparent enclosure whose wallpaper remains visually dominant."""
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))

    # Around 8-13% neutral body with a little more density at the upper edge.
    density = Image.new('L', (WORK, WORK), 20)
    density = ImageChops.add(density, _top_weight(2.0).point(lambda v: int(v * .030)))
    edge = inner_edge(ENCL, 24).filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * .065))
    density = _clip(ImageChops.add(density, edge, scale=1.0, offset=0))

    neutral = Image.new('RGBA', (WORK, WORK), (228, 233, 240, 0))
    neutral.putalpha(density)
    canvas.alpha_composite(neutral)

    # One weak environmental reflection near the top/side. Most of the surface
    # intentionally contains no reflection at all.
    patch = _soft_patch(key, 1, strength=145).point(lambda v: int(v * .22))
    white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    white.putalpha(patch)
    canvas.alpha_composite(white)

    top_edge = inter(top_facing_edge(ENCL, 3.2), _top_weight(.70)).point(lambda v: int(v * .36))
    hi = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    hi.putalpha(top_edge)
    canvas.alpha_composite(hi)

    low_edge = inter(bottom_facing_edge(ENCL, 1.6), _bottom_weight(1.2)).point(lambda v: int(v * .035))
    shade = Image.new('RGBA', (WORK, WORK), (64, 70, 82, 0))
    shade.putalpha(low_edge)
    canvas.alpha_composite(shade)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    # Only a hairline catch-light remains at the enclosure boundary. There is no
    # second broad lobe, so the icon no longer looks wrapped in wet plastic.
    hair = inter(outer_edge(ENCL, 1.05), _top_weight(.72)).point(lambda v: int(v * .18))
    rim = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    rim.putalpha(hair)
    canvas.alpha_composite(rim)
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))
