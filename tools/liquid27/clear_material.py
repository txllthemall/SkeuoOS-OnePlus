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


def _soft_ellipse(cx: float, cy: float, rx: float, ry: float, *, angle: float = 0,
                  blur: float = 26, strength: int = 255) -> Image.Image:
    m = blank_mask()
    d = ImageDraw.Draw(m)
    d.ellipse((int(cx-rx), int(cy-ry), int(cx+rx), int(cy+ry)), fill=max(0, min(255, strength)))
    if angle:
        m = m.rotate(angle, center=(WORK // 2, WORK // 2), resample=Image.Resampling.BICUBIC)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    return m


@lru_cache(maxsize=512)
def _crescent(key: str, salt: int = 0, strength: int = 255) -> Image.Image:
    """Broad curved reflection, deterministic per icon."""
    s = _seed(key, salt)
    side = -1 if (s & 1) else 1
    cx = WORK * (0.72 if side > 0 else 0.28)
    cy = WORK * (0.22 + ((s >> 8) & 31) / 31.0 * 0.14)
    rx = WORK * (0.46 + ((s >> 13) & 15) / 15.0 * 0.07)
    ry = WORK * (0.24 + ((s >> 17) & 15) / 15.0 * 0.06)
    angle = side * (18 + ((s >> 21) & 15))

    outer = _soft_ellipse(cx, cy, rx, ry, angle=angle, blur=10, strength=strength)
    inner = _soft_ellipse(cx - side * WORK * .055, cy + WORK * .038,
                          rx * .79, ry * .64, angle=angle, blur=14, strength=strength)
    return _clip(ImageChops.subtract(outer, inner))


@lru_cache(maxsize=512)
def _streak(key: str, salt: int = 0, strength: int = 255) -> Image.Image:
    """Narrow reflected-light streak crossing only part of the surface."""
    s = _seed(key, 100 + salt)
    y = WORK * (0.18 + ((s >> 5) & 63) / 63.0 * .34)
    x = WORK * (0.42 + ((s >> 12) & 31) / 31.0 * .20)
    return _clip(_soft_ellipse(
        x, y, WORK * .58, WORK * .045,
        angle=(-18 if s & 1 else 18), blur=15, strength=strength,
    ))


@lru_cache(maxsize=256)
def _variable_surface_field(key: str) -> Image.Image:
    """Shared optical field for an icon: clear plane + denser reflection zones."""
    field = Image.new('L', (WORK, WORK), 108)

    top = _top_weight(1.7).point(lambda v: int(v * .18))
    field = ImageChops.add(field, top, scale=1.0, offset=0)

    cres = _crescent(key, 17, 175).point(lambda v: int(v * .58))
    streak = _streak(key, 17, 155).point(lambda v: int(v * .41))
    field = ImageChops.add(field, cres, scale=1.0, offset=0)
    field = ImageChops.add(field, streak, scale=1.0, offset=0)

    # One cached edge field rather than recomputing it for every glyph layer.
    edge = inner_edge(ENCL, 18).filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * .20))
    field = ImageChops.add(field, edge, scale=1.0, offset=0)
    return _clip(field)


def clearify_layers(layers, key: str):
    """Turn shared glyph geometry into coherent variable-density clear glass."""
    result = []
    field = _variable_surface_field(key)
    reflection_field = _crescent(key, 61, 205).point(lambda v: int(v * .76))
    glint_weight = _top_weight(.8)

    for src in layers:
        item = dict(src)
        source_mask = item['mask']
        source_luma = luminance(item.get('fill', '#ffffff'))
        material_mask = inter(source_mask, field)

        item['mask'] = material_mask
        item['material'] = 'glass'
        item['fill'] = '#cbd5e2' if source_luma < 145 else '#eef4fa'
        item['opacity'] = .34 if source_luma < 145 else .39
        item['refraction'] = max(.130, min(.180, float(item.get('refraction', .06)) * 1.78))
        item['specular'] = 'outside'
        item['shadow'] = .0015
        item['blend'] = 'normal'
        item['blur'] = min(.45, float(item.get('blur', 0)))
        item['shadow_offset'] = .7
        item['shadow_blur'] = 2.2
        result.append(item)

        # All layers of one icon share the same environmental reflection direction.
        reflection = inter(source_mask, reflection_field)
        if reflection.getbbox():
            result.append(layer(
                reflection, '#ffffff', .34, 0, 'off', 0,
                'ink', 'screen', (0, 0), 0, 0, 0,
            ))

        # Crisp top-facing glint, intentionally incomplete rather than an outline.
        glint = inter(top_facing_edge(source_mask, 2.35), glint_weight).point(lambda v: int(v * .64))
        if glint.getbbox():
            result.append(layer(
                glint, '#ffffff', .48, 0, 'off', 0,
                'ink', 'screen', (0, 0), 0, 0, 0,
            ))

    return result


def clear_background(key: str) -> Image.Image:
    """Very clear enclosure with locally varying reflection and density."""
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))

    # Roughly 5–14% neutral base: the wallpaper should dominate most of the plane.
    density = Image.new('L', (WORK, WORK), 13)
    top = _top_weight(1.9).point(lambda v: int(v * .045))
    density = ImageChops.add(density, top, scale=1.0, offset=0)

    edge = inner_edge(ENCL, 28).filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * .10))
    density = ImageChops.add(density, edge, scale=1.0, offset=0)
    density = _clip(density)

    neutral = Image.new('RGBA', (WORK, WORK), (222, 230, 240, 0))
    neutral.putalpha(density)
    canvas.alpha_composite(neutral)

    # Strong local reflections create the glass reading; the rest remains clear.
    cres = _crescent(key, 1, 225).point(lambda v: int(v * .43))
    white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    white.putalpha(cres)
    canvas.alpha_composite(white)

    streak = _streak(key, 3, 210).point(lambda v: int(v * .32))
    cold = Image.new('RGBA', (WORK, WORK), (240, 248, 255, 0))
    cold.putalpha(streak)
    canvas.alpha_composite(cold)

    top_edge = inter(top_facing_edge(ENCL, 4.1), _top_weight(.72)).point(lambda v: int(v * .88))
    hi = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    hi.putalpha(top_edge)
    canvas.alpha_composite(hi)

    low_edge = inter(bottom_facing_edge(ENCL, 2.0), _bottom_weight(1.15)).point(lambda v: int(v * .055))
    shade = Image.new('RGBA', (WORK, WORK), (55, 63, 76, 0))
    shade.putalpha(low_edge)
    canvas.alpha_composite(shade)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    """Final reflection pass while preserving the locally varying alpha channel."""
    lobe = _crescent(key, 9, 185).point(lambda v: int(v * .24))
    white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    white.putalpha(lobe)
    canvas.alpha_composite(white)

    hair = inter(outer_edge(ENCL, 1.35), _top_weight(.7)).point(lambda v: int(v * .36))
    rim = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    rim.putalpha(hair)
    canvas.alpha_composite(rim)

    # Never replace the alpha with an opaque rounded-square mask.
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))
