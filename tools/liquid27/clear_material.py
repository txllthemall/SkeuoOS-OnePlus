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
    """Edge-attached environmental catch-light, not a floating white pill."""
    s = _seed(key, salt)
    side = -1 if s & 1 else 1
    cx = WORK * (0.73 if side > 0 else 0.27)
    # Put most of the lobe above the visible enclosure; clipping leaves an
    # irregular reflection entering from the illuminated top edge.
    cy = WORK * (0.070 + ((s >> 7) & 31) / 31.0 * .045)
    rx = WORK * (0.135 + ((s >> 13) & 15) / 15.0 * .050)
    ry = WORK * (0.030 + ((s >> 18) & 7) / 7.0 * .014)
    angle = side * (7 + ((s >> 22) & 15) / 15.0 * 12)
    m = blank_mask()
    ImageDraw.Draw(m).ellipse((int(cx-rx), int(cy-ry), int(cx+rx), int(cy+ry)), fill=strength)
    m = m.rotate(angle, center=(WORK // 2, WORK // 2), resample=Image.Resampling.BICUBIC)
    m = m.filter(ImageFilter.GaussianBlur(10))
    return _clip(m)


def _edge_gate(key: str, salt: int = 0) -> Image.Image:
    """Select one top/side section of a rim so no complete white outline appears."""
    s = _seed(key, salt)
    side = -1 if s & 1 else 1
    m = blank_mask()
    d = ImageDraw.Draw(m)
    if side < 0:
        d.polygon([(0, 0), (int(WORK*.68), 0), (int(WORK*.46), int(WORK*.48)), (0, int(WORK*.66))], fill=255)
    else:
        d.polygon([(int(WORK*.32), 0), (WORK, 0), (WORK, int(WORK*.66)), (int(WORK*.54), int(WORK*.48))], fill=255)
    return _clip(m.filter(ImageFilter.GaussianBlur(18)))


@lru_cache(maxsize=256)
def _density_field(key: str) -> Image.Image:
    field = Image.new('L', (WORK, WORK), 184)
    top = _top_weight(1.9).point(lambda v: int(v * .050))
    field = ImageChops.add(field, top, scale=1.0, offset=0)
    patch = _soft_patch(key, 17, strength=120).point(lambda v: int(v * .080))
    field = ImageChops.add(field, patch, scale=1.0, offset=0)
    return _clip(field)


def clearify_layers(layers, key: str):
    result = []
    field = _density_field(key)
    reflection_field = _soft_patch(key, 61, strength=190)
    top_weight = _top_weight(.68)
    gate = _edge_gate(key, 91)

    for src in layers:
        item = dict(src)
        source_mask = item['mask']
        source_luma = luminance(item.get('fill', '#ffffff'))

        item['mask'] = inter(source_mask, field)
        item['material'] = 'glass'
        item['fill'] = '#cbd4df' if source_luma < 145 else '#f3f6fa'
        item['opacity'] = .27 if source_luma < 145 else .32
        item['refraction'] = max(.110, min(.150, float(item.get('refraction', .06)) * 1.48))
        item['specular'] = 'inside'
        item['shadow'] = .001
        item['blend'] = 'normal'
        item['blur'] = min(.26, float(item.get('blur', 0)))
        item['shadow_offset'] = .4
        item['shadow_blur'] = 1.5
        result.append(item)

        # If a glyph reaches the illuminated region it catches a small highlight;
        # low glyphs get none, avoiding the same artificial mark on every icon.
        reflection = inter(source_mask, reflection_field).point(lambda v: int(v * .32))
        if reflection.getbbox():
            result.append(layer(
                reflection, '#ffffff', .13, 0, 'off', 0,
                'ink', 'screen', (0, 0), 0, 0, 0,
            ))

        glint = inter(inter(top_facing_edge(source_mask, 2.0), top_weight), gate).point(lambda v: int(v * .54))
        if glint.getbbox():
            result.append(layer(
                glint, '#ffffff', .25, 0, 'off', 0,
                'ink', 'screen', (0, 0), 0, 0, 0,
            ))

    return result


def clear_background(key: str) -> Image.Image:
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))

    density = Image.new('L', (WORK, WORK), 16)
    density = ImageChops.add(density, _top_weight(2.1).point(lambda v: int(v * .024)))
    edge = inner_edge(ENCL, 24).filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * .045))
    density = _clip(ImageChops.add(density, edge, scale=1.0, offset=0))

    neutral = Image.new('RGBA', (WORK, WORK), (228, 233, 240, 0))
    neutral.putalpha(density)
    canvas.alpha_composite(neutral)

    # Broad, partially clipped edge reflection. At launcher scale this reads as
    # a change in glass density rather than a painted white object.
    patch = _soft_patch(key, 1, strength=205).point(lambda v: int(v * .25))
    white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    white.putalpha(patch)
    canvas.alpha_composite(white)

    gate = _edge_gate(key, 7)
    top_edge = inter(inter(top_facing_edge(ENCL, 3.0), _top_weight(.66)), gate).point(lambda v: int(v * .58))
    hi = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    hi.putalpha(top_edge)
    canvas.alpha_composite(hi)

    side_edge = inter(inner_edge(ENCL, 2.0), gate).point(lambda v: int(v * .19))
    side = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    side.putalpha(side_edge)
    canvas.alpha_composite(side)

    low_edge = inter(bottom_facing_edge(ENCL, 1.5), _bottom_weight(1.25)).point(lambda v: int(v * .030))
    shade = Image.new('RGBA', (WORK, WORK), (54, 61, 74, 0))
    shade.putalpha(low_edge)
    canvas.alpha_composite(shade)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    gate = _edge_gate(key, 23)
    hair = inter(inter(outer_edge(ENCL, 1.05), _top_weight(.68)), gate).point(lambda v: int(v * .30))
    rim = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    rim.putalpha(hair)
    canvas.alpha_composite(rim)
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))
