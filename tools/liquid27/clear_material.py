from __future__ import annotations

import hashlib

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


def _top_weight(power: float = 1.0) -> Image.Image:
    g = ImageOps.invert(Image.linear_gradient('L').resize((WORK, WORK)))
    if power != 1.0:
        g = g.point(lambda v: int(((v / 255.0) ** power) * 255))
    return g


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


def _crescent(key: str, salt: int = 0, *, strength: int = 255) -> Image.Image:
    """Broad curved reflection, deliberately different per icon but deterministic."""
    s = _seed(key, salt)
    side = -1 if (s & 1) else 1
    cx = WORK * (0.72 if side > 0 else 0.28)
    cy = WORK * (0.22 + ((s >> 8) & 31) / 31.0 * 0.14)
    rx = WORK * (0.46 + ((s >> 13) & 15) / 15.0 * 0.07)
    ry = WORK * (0.24 + ((s >> 17) & 15) / 15.0 * 0.06)
    angle = side * (18 + ((s >> 21) & 15))

    outer = _soft_ellipse(cx, cy, rx, ry, angle=angle, blur=11, strength=strength)
    inner = _soft_ellipse(cx - side * WORK * .055, cy + WORK * .038,
                          rx * .79, ry * .64, angle=angle, blur=16, strength=strength)
    cres = ImageChops.subtract(outer, inner)
    return _clip(cres)


def _streak(key: str, salt: int = 0, *, strength: int = 255) -> Image.Image:
    """Narrow soft reflected light streak crossing only part of the surface."""
    s = _seed(key, 100 + salt)
    y = WORK * (0.18 + ((s >> 5) & 63) / 63.0 * .34)
    x = WORK * (0.42 + ((s >> 12) & 31) / 31.0 * .20)
    m = _soft_ellipse(x, y, WORK * .58, WORK * .045,
                      angle=(-18 if s & 1 else 18), blur=18, strength=strength)
    return _clip(m)


def _variable_surface_field(key: str, salt: int = 0) -> Image.Image:
    """Per-pixel material density: clear center, denser edges and reflection zones."""
    # A low base density keeps the wallpaper visible.
    field = Image.new('L', (WORK, WORK), 112)

    # The top is slightly milkier, but nowhere near a uniform frost overlay.
    top = _top_weight(1.7).point(lambda v: int(v * .21))
    field = ImageChops.add(field, top, scale=1.0, offset=0)

    # Curved and streak reflections locally increase apparent material density.
    cres = _crescent(key, salt, strength=170).point(lambda v: int(v * .55))
    streak = _streak(key, salt, strength=150).point(lambda v: int(v * .38))
    field = ImageChops.add(field, cres, scale=1.0, offset=0)
    field = ImageChops.add(field, streak, scale=1.0, offset=0)

    # Edge density makes the lens readable while leaving the central plane clearer.
    edge = inner_edge(ENCL, 18).filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * .22))
    field = ImageChops.add(field, edge, scale=1.0, offset=0)
    return _clip(field)


def clearify_layers(layers, key: str):
    """Turn shared glyph geometry into variable-density clear glass.

    Geometry is unchanged. Only the per-pixel material mask and optical treatment differ.
    """
    result = []
    for index, src in enumerate(layers):
        item = dict(src)
        source_mask = item['mask']
        source_luma = luminance(item.get('fill', '#ffffff'))
        field = _variable_surface_field(key, index + 17)
        material_mask = inter(source_mask, field)

        item['mask'] = material_mask
        item['material'] = 'glass'
        item['fill'] = '#d3dbe6' if source_luma < 145 else '#eef3f8'
        item['opacity'] = .36 if source_luma < 145 else .41
        item['refraction'] = max(.125, min(.175, float(item.get('refraction', .06)) * 1.70))
        item['specular'] = 'outside'
        item['shadow'] = .002
        item['blend'] = 'normal'
        item['blur'] = min(.55, float(item.get('blur', 0)))
        item['shadow_offset'] = .8
        item['shadow_blur'] = 2.5
        result.append(item)

        # Broad local reflection across only part of each foreground layer.
        reflection = inter(source_mask, _crescent(key, index + 61, strength=195))
        reflection = reflection.point(lambda v: int(v * .72))
        if reflection.getbbox():
            result.append(layer(
                reflection, '#ffffff', .28, 0, 'off', 0,
                'ink', 'screen', (0, 0), 0, 0, 0,
            ))

        # A very thin top-facing glint gives the crisp glass edge without a full outline.
        glint = inter(top_facing_edge(source_mask, 2.4), _top_weight(.8)).point(lambda v: int(v * .58))
        if glint.getbbox():
            result.append(layer(
                glint, '#ffffff', .44, 0, 'off', 0,
                'ink', 'screen', (0, 0), 0, 0, 0,
            ))

    return result


def clear_background(key: str) -> Image.Image:
    """A much clearer enclosure with non-uniform transparency and reflections."""
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))

    # 6–17% neutral body rather than the old uniform ~20% gray plate.
    density = Image.new('L', (WORK, WORK), 16)
    top = _top_weight(1.9).point(lambda v: int(v * .055))
    density = ImageChops.add(density, top, scale=1.0, offset=0)

    # Slightly denser glass near the enclosure edge.
    edge = inner_edge(ENCL, 28).filter(ImageFilter.GaussianBlur(11)).point(lambda v: int(v * .12))
    density = ImageChops.add(density, edge, scale=1.0, offset=0)
    density = _clip(density)

    neutral = Image.new('RGBA', (WORK, WORK), (225, 232, 241, 0))
    neutral.putalpha(density)
    canvas.alpha_composite(neutral)

    # Large environmental reflection. This is intentionally local, not a full-surface haze.
    cres = _crescent(key, 1, strength=220).point(lambda v: int(v * .34))
    white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    white.putalpha(cres)
    canvas.alpha_composite(white)

    # Narrow secondary reflection/caustic.
    streak = _streak(key, 3, strength=200).point(lambda v: int(v * .26))
    cold = Image.new('RGBA', (WORK, WORK), (241, 248, 255, 0))
    cold.putalpha(streak)
    canvas.alpha_composite(cold)

    # Directional edge response, stronger at the top and only subtly dark at the bottom.
    top_edge = inter(top_facing_edge(ENCL, 4.2), _top_weight(.72)).point(lambda v: int(v * .78))
    hi = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    hi.putalpha(top_edge)
    canvas.alpha_composite(hi)

    low_edge = inter(bottom_facing_edge(ENCL, 2.0), _bottom_weight(1.15)).point(lambda v: int(v * .07))
    shade = Image.new('RGBA', (WORK, WORK), (55, 63, 76, 0))
    shade.putalpha(low_edge)
    canvas.alpha_composite(shade)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    """Final surface reflections while retaining the already-variable alpha channel."""
    # Secondary broad lobe at a different phase. It should read as a reflection, not frost.
    lobe = _crescent(key, 9, strength=170).point(lambda v: int(v * .18))
    white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    white.putalpha(lobe)
    canvas.alpha_composite(white)

    # Hairline exterior highlight only where the top-facing edge catches light.
    hair = inter(outer_edge(ENCL, 1.35), _top_weight(.7)).point(lambda v: int(v * .30))
    rim = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    rim.putalpha(hair)
    canvas.alpha_composite(rim)

    # Do NOT replace alpha with ENCL. Preserve real local transparency.
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))
