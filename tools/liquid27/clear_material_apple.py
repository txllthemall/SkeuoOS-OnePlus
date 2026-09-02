from __future__ import annotations

"""Clear material with separate optical preview and static Android products.

Static Android cannot sample wallpaper. Its glass therefore relies on a clean
shell plus a denser glyph built from broad neutral light/dark body lobes and
multi-scale interfaces. The glyph must remain recognizable without labels at
launcher scale while still transmitting the wallpaper through its RGBA alpha.
"""

import hashlib
from functools import lru_cache
import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageOps

from .material import WORK, ENCL, inter, inner_edge, outer_edge, top_facing_edge, bottom_facing_edge, layer
from .glass_surface import enclosure_surface
from .glass_optics import composite_container, composite_glyph


def _seed(key: str, salt: int = 0) -> int:
    return int.from_bytes(hashlib.sha256(f'{key}:{salt}'.encode()).digest()[:4], 'big')


def _mask(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(np.round(arr * 255.0), 0, 255).astype(np.uint8), 'L')


def reflection_style(key: str) -> int:
    return 2 if (_seed(key, 401) % 5) == 0 else 1


@lru_cache(maxsize=256)
def clear_reflection_mask(key: str) -> Image.Image:
    s = enclosure_surface(WORK)
    flip = -1.0 if (_seed(key, 409) & 1) else 1.0
    lx, ly, lz = -.50 * flip, -.72, .48
    lm = (lx*lx + ly*ly + lz*lz) ** .5
    lx, ly, lz = lx/lm, ly/lm, lz/lm
    hx, hy, hz = lx, ly, lz + 1.0
    hm = (hx*hx + hy*hy + hz*hz) ** .5
    hx, hy, hz = hx/hm, hy/hm, hz/hm
    ndoth = np.clip(s['nx']*hx + s['ny']*hy + s['nz']*hz, 0, 1)
    spec = (ndoth ** 34.0) * np.clip(s['fmid']*1.0 + s['ftight']*1.45, 0, 1)
    return _mask(np.clip(spec * .30, 0, .26))


def clear_reflection_coverage_pct(key: str) -> float:
    return float((np.asarray(clear_reflection_mask(key), dtype=np.float32) / 255.).mean() * 100.)


@lru_cache(maxsize=1)
def _static_enclosure_fields():
    """Low-density shell. Container remains subordinate to the glyph."""
    s = enclosure_surface(WORK)
    body = (.020 + .014*s['mid'] + .022*s['fsoft']) * s['inside']
    curved = (.045*s['edge'] + .095*s['rim'] + .125*s['very_rim']) * s['inside']
    density = np.clip(body + curved, 0, .22)

    lx, ly, lz = -.52, -.70, .49
    lm = (lx*lx + ly*ly + lz*lz) ** .5
    lx, ly, lz = lx/lm, ly/lm, lz/lm
    hx, hy, hz = lx, ly, lz + 1.0
    hm = (hx*hx + hy*hy + hz*hz) ** .5
    hx, hy, hz = hx/hm, hy/hm, hz/hm
    ndoth = np.clip(s['nx']*hx + s['ny']*hy + s['nz']*hz, 0, 1)
    spec = np.clip((ndoth**31.0) * (s['fmid']*.55 + s['ftight']*1.05) * .30, 0, .22)

    opposite = np.clip(-(s['nx']*lx + s['ny']*ly), 0, 1) ** 2.2
    dark = np.clip(opposite * (.050*s['edge'] + .105*s['rim'] + .100*s['very_rim']), 0, .16)

    internal = np.exp(-((s['q']-.76)/.075)**2) * (.034 + .050*np.clip(-s['ny'], 0, 1))
    internal = np.clip(internal, 0, .080) * s['inside']
    return _mask(density), _mask(spec), _mask(dark), _mask(internal)


def _body_lobes(mask: Image.Image):
    """Broad directional body response, not a hairline bevel.

    Light and dark coexist inside the glyph so one static PNG preserves
    recognition on black, white and midtone wallpapers.
    """
    core = inter(mask.filter(ImageFilter.GaussianBlur(3.2)), mask)
    grad = Image.linear_gradient('L').resize((WORK, WORK))
    top_weight = ImageOps.invert(grad).point(lambda v: int(((v/255.0)**1.35)*255))
    low_weight = grad.point(lambda v: int(((v/255.0)**1.55)*255))
    hi = inter(core, top_weight).point(lambda v: int(v * .175))
    lo = inter(core, low_weight).point(lambda v: int(v * .155))
    return hi, lo


def _glyph_static_masks(mask: Image.Image):
    soft = mask.filter(ImageFilter.GaussianBlur(4.0))
    core = inter(soft, mask)
    wide = inner_edge(mask, 14.0).filter(ImageFilter.GaussianBlur(3.8))
    inner = inner_edge(mask, 5.5).filter(ImageFilter.GaussianBlur(1.8))
    tight = inner_edge(mask, 2.1).filter(ImageFilter.GaussianBlur(.60))
    top = top_facing_edge(mask, 2.8).filter(ImageFilter.GaussianBlur(.62))
    low = bottom_facing_edge(mask, 3.0).filter(ImageFilter.GaussianBlur(.68))
    hi_body, low_body = _body_lobes(mask)

    # The base core is intentionally moderate. Recognition comes from the sum of
    # core + broad directional lobes + curved interfaces, not from a flat fill.
    body = core.point(lambda v: int(v * .175))
    curved = wide.point(lambda v: int(v * .255))
    internal = inner.point(lambda v: int(v * .210))
    bright = tight.point(lambda v: int(v * .370))
    spec = top.point(lambda v: int(v * .470))
    dark = low.point(lambda v: int(v * .455))
    return body, hi_body, low_body, curved, internal, bright, spec, dark


def clearify_layers(layers, key: str):
    """Static glyph = readable translucent glass, never a run-60 ghost."""
    result = []
    for src in layers:
        mask = src['mask']
        body, hi_body, low_body, curved, internal, bright, spec, dark = _glyph_static_masks(mask)

        # Neutral mass plus opposite broad body lobes. Wallpaper remains visible
        # because every component is low-alpha, but the silhouette survives.
        result.append(layer(body, '#9e9e9e', 1.0, 0, 'off', 0, 'ink', 'normal', (0,0), 0,0,0))
        result.append(layer(hi_body, '#f1f1f1', 1.0, 0, 'off', 0, 'ink', 'normal', (0,0), 0,0,0))
        result.append(layer(low_body, '#303030', 1.0, 0, 'off', 0, 'ink', 'normal', (0,0), 0,0,0))
        result.append(layer(curved, '#b9b9b9', .94, 0, 'off', 0, 'ink', 'normal', (0,0), 0,0,0))
        result.append(layer(internal, '#727272', .68, 0, 'off', 0, 'ink', 'multiply', (0,0), 0,0,0))

        if bright.getbbox():
            result.append(layer(bright, '#eeeeee', .82, 0, 'off', 0, 'ink', 'screen', (0,0), 0,0,0))
        if spec.getbbox():
            result.append(layer(spec, '#ffffff', .50, 0, 'off', 0, 'ink', 'screen', (0,0), 0,0,0))
        if dark.getbbox():
            result.append(layer(dark, '#0d0d0d', .72, 0, 'off', 0, 'ink', 'multiply', (0,0), 0,0,0))
    return result


def clear_background(key: str) -> Image.Image:
    canvas = Image.new('RGBA', (WORK, WORK), (0,0,0,0))
    density, spec, dark, internal = _static_enclosure_fields()

    neutral = Image.new('RGBA', (WORK,WORK), (150,150,150,0)); neutral.putalpha(density); canvas.alpha_composite(neutral)
    inside = Image.new('RGBA', (WORK,WORK), (202,202,202,0)); inside.putalpha(internal); canvas.alpha_composite(inside)
    white = Image.new('RGBA', (WORK,WORK), (255,255,255,0)); white.putalpha(ImageChops.lighter(spec, clear_reflection_mask(key))); canvas.alpha_composite(white)
    dk = Image.new('RGBA', (WORK,WORK), (18,18,18,0)); dk.putalpha(dark); canvas.alpha_composite(dk)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    hair = outer_edge(ENCL, .65).point(lambda v: int(v * .070))
    h = Image.new('RGBA', (WORK,WORK), (248,248,248,0)); h.putalpha(hair); canvas.alpha_composite(h)
    inner = inner_edge(ENCL, 2.4).filter(ImageFilter.GaussianBlur(.70)).point(lambda v: int(v * .060))
    ii = Image.new('RGBA', (WORK,WORK), (228,228,228,0)); ii.putalpha(inner); canvas.alpha_composite(ii)
    low = bottom_facing_edge(ENCL, 2.2).filter(ImageFilter.GaussianBlur(.50)).point(lambda v: int(v * .205))
    d = Image.new('RGBA', (WORK,WORK), (15,15,15,0)); d.putalpha(low); canvas.alpha_composite(d)
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))


def preview_refract_patch(under: Image.Image, foreground_mask: Image.Image | None = None) -> Image.Image:
    result, _, _, _ = composite_container(under.convert('RGB'))
    if foreground_mask is not None and foreground_mask.getbbox():
        result, _, _, _ = composite_glyph(result, foreground_mask)
    return result


@lru_cache(maxsize=1)
def _metric_base():
    s = enclosure_surface(128)
    dummy = Image.new('RGB', (128,128), (128,128,128))
    _, dx, dy, _ = composite_container(dummy)
    disp = np.sqrt(dx*dx + dy*dy)
    center = s['q'] < .34
    mid = (s['q'] >= .46) & (s['q'] < .72)
    edge = (s['q'] >= .84) & (s['q'] <= 1.0)
    dens = np.asarray(_static_enclosure_fields()[0].resize((128,128), Image.Resampling.LANCZOS), dtype=np.float32)
    return {
        'enclosure_center_density': float(dens[center].mean()),
        'enclosure_edge_density': float(dens[edge].mean()),
        'specular_coverage_pct': float((s['fmid'] > .12).mean() * 100),
        'refraction_displacement_mean': float(disp[s['inside'] > 0].mean()),
        'refraction_displacement_median': float(np.median(disp[s['inside'] > 0])),
        'refraction_displacement_max': float(disp.max()),
        'refraction_center_mean': float(disp[center].mean()),
        'refraction_mid_mean': float(disp[mid].mean()),
        'refraction_edge_mean': float(disp[edge].mean()),
        'fresnel_center_mean': float(s['fresnel'][center].mean()),
        'fresnel_edge_mean': float(s['fresnel'][edge].mean()),
    }


def material_metrics(key: str) -> dict:
    out = dict(_metric_base())
    out['reflection_coverage_pct'] = clear_reflection_coverage_pct(key)
    out['edge_center_density_ratio'] = out['enclosure_edge_density'] / max(out['enclosure_center_density'], 1e-6)
    out['edge_mid_displacement_ratio'] = out['refraction_edge_mean'] / max(out['refraction_mid_mean'], 1e-6)
    return out
