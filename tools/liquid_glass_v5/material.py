from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from liquid_glass_v4.surface import SurfaceMaps, smootherstep


@dataclass(frozen=True)
class TransportParams:
    ior: float = 1.50

    # Optical extinction/scattering coefficients are art-directed but applied
    # through Beer-Lambert-style transport instead of layer opacity stacking.
    container_absorption: float = 0.17
    container_scattering: float = 0.055
    glyph_absorption_add: float = 0.82
    glyph_scattering_add: float = 0.78

    path_base: float = 0.72
    path_gain: float = 1.55
    glyph_path_gain: float = 0.72

    scatter_luma_container: float = 0.62
    scatter_luma_glyph: float = 0.91
    scatter_energy: float = 0.62

    front_reflection_gain: float = 1.16
    back_reflection_gain: float = 0.86
    sharp_specular_gain: float = 0.22
    glyph_specular_gain: float = 0.30
    rim_energy: float = 0.020


@dataclass(frozen=True)
class BakeFlags:
    specular: bool = True
    shadow: bool = False
    explicit_rim: bool = True


def _norm01(a: np.ndarray, p: float = 99.5) -> np.ndarray:
    vals = np.abs(a)
    nz = vals[vals > 1e-8]
    hi = float(np.percentile(nz, p)) if nz.size else 1.0
    return np.clip(vals / max(hi, 1e-8), 0.0, 1.0).astype(np.float32)


def _fresnel(nz: np.ndarray, ior: float) -> np.ndarray:
    f0 = ((ior - 1.0) / (ior + 1.0)) ** 2
    c = np.clip(np.abs(nz), 0.0, 1.0)
    return (f0 + (1.0 - f0) * np.power(1.0 - c, 5.0)).astype(np.float32)


def _studio_env(normal: np.ndarray) -> np.ndarray:
    """Neutral HDR-like studio radiance evaluated from reflection direction."""
    nx, ny, nz = normal[..., 0], normal[..., 1], normal[..., 2]
    rx = 2.0 * nz * nx
    ry = 2.0 * nz * ny
    rz = 2.0 * nz * nz - 1.0

    # Large white softbox upper-left, smaller silver fill, dark lower room.
    key_dir = np.array([-0.60, -0.72, 0.35], dtype=np.float32)
    fill_dir = np.array([0.58, -0.18, 0.24], dtype=np.float32)
    k = np.clip(0.5 + 0.5 * (rx * key_dir[0] + ry * key_dir[1] + rz * key_dir[2]), 0.0, 1.0)
    f = np.clip(0.5 + 0.5 * (rx * fill_dir[0] + ry * fill_dir[1] + rz * fill_dir[2]), 0.0, 1.0)
    k = smootherstep(k)
    f = smootherstep(f)
    horizon = np.exp(-np.square((rz + 0.02) / 0.24)).astype(np.float32)
    floor = np.clip(0.5 + 0.5 * (0.18 * rx + 0.70 * ry - 0.22 * rz), 0.0, 1.0)
    env = 0.035 + 0.73 * k + 0.16 * f + 0.12 * horizon - 0.20 * floor
    return np.clip(env, 0.015, 1.0).astype(np.float32)


def _sharp_spec(normal: np.ndarray, exponent: float) -> np.ndarray:
    light = np.array([-0.44, -0.73, 0.52], dtype=np.float32)
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
    params: TransportParams = TransportParams(),
    flags: BakeFlags = BakeFlags(),
) -> np.ndarray:
    """Derive a straight-alpha RGBA asset from background-independent transport.

    We model the desired static operator as C_out = T*C_bg + R, where T is
    transmitted background energy and R is neutral reflected/scattered radiance.
    A normal Android RGBA pixel implements the same operator with
    alpha = 1-T and source_rgb = R/alpha. This makes the static bake a compact
    approximation of a dielectric transport operator rather than a pile of
    decorative opacity layers.
    """
    cm = np.clip(maps.container_mask, 0.0, 1.0)
    gm = np.clip(maps.glyph_mask, 0.0, 1.0)

    tvals = maps.thickness[cm > 0.5]
    tmax = max(float(np.percentile(tvals, 99.0)) if tvals.size else 1.0, 1e-6)
    tn = np.clip(maps.thickness / tmax, 0.0, 1.0)
    radius = np.clip(maps.local_radius / 28.0, 0.0, 1.0)
    glyph_mass = gm * np.clip(0.38 + 0.62 * radius, 0.0, 1.0)

    path = params.path_base + params.path_gain * np.sqrt(tn) + params.glyph_path_gain * glyph_mass
    sigma_a = params.container_absorption + params.glyph_absorption_add * glyph_mass
    sigma_s = params.container_scattering + params.glyph_scattering_add * glyph_mass

    beer_absorb = np.exp(-sigma_a * path).astype(np.float32)
    scatter_fraction = (1.0 - np.exp(-sigma_s * path)).astype(np.float32)

    nf = maps.front_normals
    nb = maps.back_normals
    ff = _fresnel(nf[..., 2], params.ior)
    fb = _fresnel(nb[..., 2], params.ior)

    # Slightly amplify physical Fresnel at launcher scale, but keep center
    # reflection low and let grazing shoulders carry the material identity.
    slope = _norm01(maps.front_slope)
    back_slope = _norm01(maps.back_slope)
    ff_eff = np.clip(ff * params.front_reflection_gain + 0.055 * np.sqrt(slope), 0.0, 0.72)
    fb_eff = np.clip(fb * params.back_reflection_gain + 0.040 * np.sqrt(back_slope), 0.0, 0.58)

    env_f = _studio_env(nf)
    env_b = _studio_env(nb)

    # Transmittance through both interfaces and absorbing medium.
    T = (1.0 - ff_eff) * beer_absorb * (1.0 - fb_eff)

    # Front reflection + attenuated back reflection + volumetric neutral scatter.
    R_front = ff_eff * env_f
    internal_to_back = (1.0 - ff_eff) * np.sqrt(beer_absorb)
    R_back = internal_to_back * fb_eff * env_b

    scatter_luma = (
        params.scatter_luma_container * (1.0 - gm)
        + (params.scatter_luma_container * 0.35 + params.scatter_luma_glyph * 0.65) * gm
    )
    R_scatter = params.scatter_energy * scatter_fraction * scatter_luma

    R = R_front + R_back + R_scatter

    if flags.explicit_rim:
        # Tiny physical silhouette energy only. The volume must survive without it.
        rim = smootherstep(np.clip((maps.q - 0.968) / 0.032, 0.0, 1.0)) * cm
        R += params.rim_energy * rim
        T *= (1.0 - 0.012 * rim)

    if flags.specular:
        csp = _sharp_spec(maps.container_front_normals, 48.0) * np.sqrt(_norm01(maps.container_front_slope)) * cm
        gsp = _sharp_spec(nf, 34.0) * np.sqrt(np.clip(_norm01(maps.glyph_slope), 0.0, 1.0)) * gm
        R += params.sharp_specular_gain * csp + params.glyph_specular_gain * gsp

    # No drop shadow: depth is entirely optical/material.
    T = np.where(cm > 1e-4, np.clip(T, 0.08, 0.995), 1.0)
    R = np.where(cm > 1e-4, np.clip(R, 0.0, 1.0), 0.0)

    alpha = np.clip(1.0 - T, 0.0, 0.92)
    src = np.divide(R, np.maximum(alpha, 1e-6), out=np.full_like(alpha, 0.5), where=alpha > 1e-6)
    src = np.clip(src, 0.0, 1.0)

    # Neutral material: all channels exactly equal. Wallpaper hue comes only
    # from the background transmitted by alpha compositing.
    rgb = np.round(src * 255.0).astype(np.uint8)
    a = np.round(alpha * 255.0).astype(np.uint8)
    return np.stack((rgb, rgb, rgb, a), axis=-1)
