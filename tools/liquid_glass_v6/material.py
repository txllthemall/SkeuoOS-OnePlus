from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from liquid_glass_v4.surface import SurfaceMaps, smootherstep


@dataclass(frozen=True)
class MaterialParams:
    # V6 abandons the pale V5 transport look. A static Android RGBA cannot
    # reproduce live refraction, so we encode the portable perceptual cues of a
    # dielectric object directly from geometry: clear core, broad curved optical
    # shoulder, signed dual-polarity interfaces, and a denser secondary glyph.
    container_core_alpha: float = 0.010
    container_edge_alpha: float = 0.125
    container_lip_alpha: float = 0.040

    glyph_core_alpha: float = 0.255
    glyph_mass_alpha: float = 0.095
    glyph_interface_alpha: float = 0.105
    glyph_thin_alpha: float = 0.055

    container_env_gain: float = 0.285
    container_back_gain: float = 0.110
    glyph_env_gain: float = 0.245
    glyph_back_gain: float = 0.105

    glyph_base_luma: float = 0.445
    rim_alpha: float = 0.012
    specular_alpha: float = 0.045
    glyph_specular_alpha: float = 0.060


@dataclass(frozen=True)
class BakeFlags:
    specular: bool = True
    shadow: bool = False
    explicit_rim: bool = True


def _norm01(a: np.ndarray, p: float = 99.4) -> np.ndarray:
    vals = np.abs(a)
    nz = vals[vals > 1e-8]
    hi = float(np.percentile(nz, p)) if nz.size else 1.0
    return np.clip(vals / max(hi, 1e-8), 0.0, 1.0).astype(np.float32)


def _reflection_signed(normal: np.ndarray) -> np.ndarray:
    """Signed neutral studio response in [-1, 1].

    It is deliberately bipolar. On a static PNG the same asset must carry a
    bright cue for dark wallpaper and a dark cue for bright wallpaper, while
    midtones need spatial variation rather than a flat gray/white fill.
    """
    nx, ny, nz = normal[..., 0], normal[..., 1], normal[..., 2]
    rx = 2.0 * nz * nx
    ry = 2.0 * nz * ny
    rz = 2.0 * nz * nz - 1.0

    key = -0.61 * rx - 0.73 * ry + 0.31 * rz
    fill = 0.42 * rx - 0.20 * ry + 0.10 * rz
    room = 0.70 * key + 0.30 * fill
    return np.tanh(1.55 * room).astype(np.float32)


def _specular(normal: np.ndarray, exponent: float) -> np.ndarray:
    light = np.array([-0.43, -0.72, 0.54], dtype=np.float32)
    light /= max(float(np.linalg.norm(light)), 1e-8)
    halfv = light + np.array([0.0, 0.0, 1.0], dtype=np.float32)
    halfv /= max(float(np.linalg.norm(halfv)), 1e-8)
    ndh = np.clip(
        normal[..., 0] * halfv[0] + normal[..., 1] * halfv[1] + normal[..., 2] * halfv[2],
        0.0,
        1.0,
    )
    return np.power(ndh, exponent).astype(np.float32)


def bake_static_rgba(
    maps: SurfaceMaps,
    params: MaterialParams = MaterialParams(),
    flags: BakeFlags = BakeFlags(),
) -> np.ndarray:
    cm = np.clip(maps.container_mask, 0.0, 1.0)
    gm = np.clip(maps.glyph_mask, 0.0, 1.0)

    # ------------------------------ container: clear crown + broad optical edge
    # q is the analytic superellipse radius. The shoulder occupies a large area;
    # it is not a perimeter stroke.
    edge = smootherstep(np.clip((maps.q - 0.60) / 0.40, 0.0, 1.0)) * cm
    edge2 = smootherstep(np.clip((maps.q - 0.74) / 0.25, 0.0, 1.0)) * cm

    tvals = maps.thickness[cm > 0.5]
    tmax = max(float(np.percentile(tvals, 99.0)) if tvals.size else 1.0, 1e-6)
    tn = np.clip(maps.thickness / tmax, 0.0, 1.0)

    cfront = _reflection_signed(maps.container_front_normals)
    cback = _reflection_signed(maps.container_back_normals)
    # A front/back disagreement is a depth cue: opposite interfaces do not
    # respond identically when the surface turns through the thick shoulder.
    cdepth = np.clip(cfront - cback, -1.0, 1.0)

    calpha = (
        params.container_core_alpha * cm
        + params.container_edge_alpha * np.power(edge, 0.72)
        + params.container_lip_alpha * np.sqrt(tn) * edge2
    )
    calpha = np.clip(calpha, 0.0, 0.24)

    cluma = (
        0.50
        + params.container_env_gain * cfront * edge
        + params.container_back_gain * cdepth * edge2
        + 0.035 * (tn - 0.50) * edge
    )
    cluma = np.clip(cluma, 0.10, 0.90)

    # ------------------------------ glyph: second, denser dielectric volume
    radius = np.clip(maps.local_radius / 30.0, 0.0, 1.0)
    gcore = gm * (0.64 + 0.24 * smootherstep(radius))
    gedge = gm * (1.0 - smootherstep(np.clip(maps.local_radius / 18.0, 0.0, 1.0)))
    thin = gm * (1.0 - smootherstep(np.clip((maps.local_radius - 2.0) / 9.0, 0.0, 1.0)))

    # Glyph thickness relative to container thickness. This keeps a real body in
    # solid logos instead of degenerating into an outline.
    base_t = np.maximum(maps.thickness - maps.glyph_mass, 1e-6)
    gmass = np.clip(maps.glyph_mass / np.maximum(base_t + maps.glyph_mass, 1e-6), 0.0, 1.0) * gm

    gfront = _reflection_signed(maps.front_normals)
    gback = _reflection_signed(maps.back_normals)
    gdepth = np.clip(gfront - gback, -1.0, 1.0)

    galpha = (
        params.glyph_core_alpha * gcore
        + params.glyph_mass_alpha * gmass
        + params.glyph_interface_alpha * gedge
        + params.glyph_thin_alpha * thin
    )
    galpha = np.clip(galpha, 0.0, 0.56)

    # Base luma below 0.5 is intentional. A neutral translucent object at ~0.44
    # remains visible on near-black, near-white and the muted mauve hard gate.
    # Geometry-derived bipolar response stops it reading as a flat gray SVG.
    gluma = (
        params.glyph_base_luma
        + params.glyph_env_gain * gfront
        + params.glyph_back_gain * gdepth
        - 0.055 * smootherstep(radius)
        + 0.035 * gedge
    )
    gluma = np.clip(gluma, 0.08, 0.94)

    # Combine container and glyph as two transmissive volumes in one final
    # straight-alpha pixel. This is a single material solution, not a pile of
    # pre-rendered rim/fill layers.
    alpha = 1.0 - (1.0 - calpha) * (1.0 - galpha)
    premul = calpha * cluma + (1.0 - calpha) * galpha * gluma

    if flags.explicit_rim:
        # Only a tiny analytic silhouette stabilizer. V6 must survive without it.
        rim = smootherstep(np.clip((maps.q - 0.975) / 0.025, 0.0, 1.0)) * cm
        ra = params.rim_alpha * rim
        premul = premul * (1.0 - ra) + ra * 0.72
        alpha = alpha + ra * (1.0 - alpha)

    if flags.specular:
        csp = _specular(maps.container_front_normals, 56.0) * np.sqrt(_norm01(maps.container_front_slope)) * edge
        gsp = _specular(maps.front_normals, 42.0) * np.sqrt(_norm01(maps.glyph_slope)) * gm
        sa = params.specular_alpha * csp + params.glyph_specular_alpha * gsp
        sa = np.clip(sa, 0.0, 0.12)
        premul = premul * (1.0 - sa) + sa
        alpha = alpha + sa * (1.0 - alpha)

    # No external shadow; the flag exists for the hard gate only.
    alpha = np.where(cm > 1e-5, np.clip(alpha, 0.0, 0.78), 0.0)
    src = np.divide(
        premul,
        np.maximum(alpha, 1e-6),
        out=np.full_like(alpha, 0.5),
        where=alpha > 1e-6,
    )
    src = np.where(cm > 1e-5, np.clip(src, 0.0, 1.0), 0.5)

    rgb = np.round(src * 255.0).astype(np.uint8)
    a = np.round(alpha * 255.0).astype(np.uint8)
    return np.stack((rgb, rgb, rgb, a), axis=-1)
