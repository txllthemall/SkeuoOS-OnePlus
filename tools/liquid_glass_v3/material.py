from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50
    # Static PNG has no live backdrop. Keep the core genuinely clear, but give
    # the curved body enough neutral optical mass to survive launcher scale.
    container_core_alpha: float = 0.020
    container_edge_alpha: float = 0.082
    container_interface_alpha: float = 0.024
    glyph_core_alpha: float = 0.315
    glyph_edge_alpha: float = 0.115
    glyph_thin_boost: float = 0.070
    bright_interface_gain: float = 0.19
    dark_interface_gain: float = 0.28
    internal_interface_gain: float = 0.045
    specular_gain: float = 0.095
    curvature_gain: float = 0.040


@dataclass(frozen=True)
class BakeFlags:
    specular: bool = True
    shadow: bool = True
    explicit_rim: bool = True


def _smoothstep(a: float, b: float, x: np.ndarray) -> np.ndarray:
    if abs(b - a) < 1e-8:
        return (x >= b).astype(np.float32)
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _norm01(a: np.ndarray, p: float = 99.5) -> np.ndarray:
    hi = float(np.percentile(np.abs(a), p)) if a.size else 1.0
    if hi <= 1e-8:
        return np.zeros_like(a, dtype=np.float32)
    return np.clip(np.abs(a) / hi, 0.0, 1.0).astype(np.float32)


def schlick_fresnel(ndotv: np.ndarray, ior: float) -> np.ndarray:
    f0 = ((ior - 1.0) / (ior + 1.0)) ** 2
    return (f0 + (1.0 - f0) * np.power(1.0 - np.clip(ndotv, 0.0, 1.0), 5.0)).astype(np.float32)


def bake_static_rgba(
    maps: SurfaceMaps,
    params: MaterialParams = MaterialParams(),
    flags: BakeFlags = BakeFlags(),
) -> np.ndarray:
    """Bake wallpaper-independent straight-alpha RGBA from V3 geometry.

    The static surrogate is intentionally NOT an outline stack. The broad
    curved height-field controls body density and directional light/dark
    transmission; narrow interfaces are subordinate. Specular is a final small
    term and can be disabled without destroying the volume.
    """
    cm = np.clip(maps.container_mask, 0.0, 1.0)
    gm = np.clip(maps.glyph_mask, 0.0, 1.0)
    cprof = np.clip(maps.container_profile, 0.0, 1.0)
    gprof = np.clip(maps.glyph_profile, 0.0, 1.0)
    n = maps.normals

    container_slope = _norm01(maps.container_slope)
    glyph_slope = _norm01(maps.glyph_slope)
    curv = _norm01(maps.curvature)

    # Broad physical curvature zones. These occupy area; they are not borders.
    edge_zone = np.clip((1.0 - cprof) * cm, 0.0, 1.0)
    glyph_edge_zone = np.clip((1.0 - gprof) * gm, 0.0, 1.0)
    curved_body = np.power(edge_zone, 0.72).astype(np.float32)
    glyph_curved_body = np.power(glyph_edge_zone, 0.72).astype(np.float32)

    thin = 1.0 - _smoothstep(3.0, 14.0, maps.local_radius)
    thin *= gm

    # Virtual environment direction. The same surface normal drives broad body
    # response, interfaces and specular so the material remains coherent.
    lx, ly = -0.58, -0.82
    lnorm = max((lx * lx + ly * ly) ** 0.5, 1e-6)
    lx, ly = lx / lnorm, ly / lnorm
    q = np.clip(n[..., 0] * lx + n[..., 1] * ly, -1.0, 1.0)
    facing_light = 0.5 + 0.5 * q
    facing_dark = 1.0 - facing_light
    bright_dir = _smoothstep(0.03, 0.34, q)
    dark_dir = _smoothstep(0.03, 0.34, -q)

    # Slope-derived transition lobes. Edge-zone contribution is intentionally
    # low so this does not become a uniform concentric rim.
    broad_interface = np.clip(0.84 * container_slope + 0.16 * edge_zone, 0.0, 1.0)
    glyph_interface = np.clip(0.80 * glyph_slope + 0.20 * glyph_edge_zone, 0.0, 1.0)

    # Very weak back/internal interface, used as a thickness cue rather than a
    # second drawn outline.
    inner_band = np.clip(
        _smoothstep(0.26, 0.58, 1.0 - cprof)
        - _smoothstep(0.62, 0.84, 1.0 - cprof),
        0.0,
        1.0,
    ) * cm
    glyph_inner = np.clip(
        _smoothstep(0.24, 0.60, 1.0 - gprof)
        - _smoothstep(0.66, 0.88, 1.0 - gprof),
        0.0,
        1.0,
    ) * gm

    # Alpha topology: clear plateau + broad curved volume. A static PNG cannot
    # displace unknown wallpaper, so alpha is the transferable transmission
    # channel. Most optical mass lives across the slope zone, not on a rim.
    alpha = params.container_core_alpha * cm
    alpha += 0.040 * curved_body
    alpha += params.container_edge_alpha * broad_interface
    alpha += params.container_interface_alpha * inner_band

    # Glyph is a second, denser glass body. Thick regions retain a translucent
    # core; thin strokes automatically receive more interface support.
    glyph_body = gm * (0.70 + 0.30 * gprof)
    alpha += params.glyph_core_alpha * glyph_body
    alpha += 0.040 * glyph_curved_body
    alpha += params.glyph_edge_alpha * glyph_interface
    alpha += params.glyph_thin_boost * thin

    if flags.explicit_rim:
        # Hairline only. It is not allowed to carry the material identity.
        tight_rim = _smoothstep(0.93, 0.996, edge_zone) * cm
        glyph_tight = _smoothstep(0.91, 0.996, glyph_edge_zone) * gm
        alpha += 0.012 * tight_rim + 0.016 * glyph_tight

    alpha = np.clip(alpha, 0.0, 0.70)

    tnorm = np.clip(
        maps.thickness / max(float(np.max(maps.thickness)), 1e-6),
        0.0,
        1.0,
    )

    # Neutral broad surface illumination. This is the static counterpart of an
    # environment reflection: its shape comes from geometry, while hue stays
    # neutral so wallpaper colour remains responsible for perceived colour.
    broad_light = curved_body * facing_light
    broad_dark = curved_body * facing_dark
    container_luma = 154.0 + 13.0 * tnorm
    container_luma += 24.0 * broad_light - 28.0 * broad_dark
    container_luma += params.curvature_gain * 255.0 * curv

    c_bright = params.bright_interface_gain * broad_interface * bright_dir
    c_dark = params.dark_interface_gain * broad_interface * dark_dir
    c_internal = params.internal_interface_gain * inner_band * (0.55 + 0.45 * np.abs(q))
    luma = container_luma + 120.0 * c_bright + 42.0 * c_internal - 116.0 * c_dark

    # Secondary volumetric glyph: readable because its optical mass differs
    # from the shell, not because a flat white SVG was painted on top.
    radius_mass = np.clip(maps.local_radius / 22.0, 0.0, 1.0)
    glyph_luma = 203.0 + 20.0 * gprof + 18.0 * radius_mass
    glyph_luma += 30.0 * facing_light - 42.0 * facing_dark
    glyph_luma += 12.0 * glyph_inner
    glyph_mix = np.clip(gm * (0.80 + 0.14 * gprof), 0.0, 0.94)
    luma = luma * (1.0 - glyph_mix) + glyph_luma * glyph_mix

    # Dual polarity only along the real glyph surface transition. This keeps
    # silhouette recognition on both near-white and near-black backgrounds.
    luma += 78.0 * glyph_interface * bright_dir
    luma -= 92.0 * glyph_interface * dark_dir

    if flags.specular:
        l3 = np.array([-0.45, -0.72, 0.53], dtype=np.float32)
        l3 /= max(float(np.linalg.norm(l3)), 1e-6)
        h = l3 + np.array([0.0, 0.0, 1.0], dtype=np.float32)
        h /= max(float(np.linalg.norm(h)), 1e-6)
        ndoth = np.clip(
            n[..., 0] * h[0] + n[..., 1] * h[1] + n[..., 2] * h[2],
            0.0,
            1.0,
        )
        ndotv = np.clip(n[..., 2], 0.0, 1.0)
        fresnel = schlick_fresnel(ndotv, params.ior)
        surface_weight = np.clip(0.62 * container_slope + 0.92 * glyph_slope, 0.0, 1.0)
        spec = np.power(ndoth, 42.0) * (0.18 + 0.82 * fresnel) * surface_weight
        luma += 255.0 * params.specular_gain * spec
        alpha += 0.016 * spec

    # No baked external drop shadow. Depth must survive this path unchanged.
    if flags.shadow:
        pass

    luma = np.clip(luma, 48.0, 244.0)
    rgb = np.repeat(luma[..., None], 3, axis=2)
    rgb = np.where(cm[..., None] > 1e-4, rgb, 128.0)
    rgba = np.concatenate((rgb, (np.clip(alpha, 0.0, 1.0) * 255.0)[..., None]), axis=2)
    return np.clip(rgba, 0.0, 255.0).astype(np.uint8)
