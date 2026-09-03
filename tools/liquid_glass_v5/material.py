from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from liquid_glass_v4.surface import SurfaceMaps, smootherstep


@dataclass(frozen=True)
class TransportParams:
    ior: float = 1.50

    # V5.1 treats the medium as a mostly clear dielectric. Extinction is now
    # energy-conserving: absorption + scattering both reduce transmission, and
    # scattering returns neutral radiance instead of silently turning glass gray.
    container_absorption: float = 0.006
    container_scattering: float = 0.030
    glyph_absorption_add: float = 0.025
    glyph_scattering_add: float = 0.340

    path_base: float = 0.40
    path_gain: float = 0.75
    glyph_path_gain: float = 0.55

    scatter_luma_container: float = 0.72
    scatter_luma_glyph: float = 0.99
    scatter_energy: float = 0.95

    front_reflection_gain: float = 1.10
    back_reflection_gain: float = 0.80
    edge_reflection_boost: float = 0.165
    edge_back_boost: float = 0.105

    interface_bright_gain: float = 0.100
    interface_dark_gain: float = 0.080

    sharp_specular_gain: float = 0.18
    glyph_specular_gain: float = 0.27
    rim_energy: float = 0.012


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
    env = 0.055 + 0.76 * k + 0.18 * f + 0.13 * horizon - 0.16 * floor
    return np.clip(env, 0.025, 1.0).astype(np.float32)


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
    """Derive a straight-alpha RGBA asset from a neutral transport operator.

    The target static operator is C_out = T*C_bg + R. Android's normal alpha
    blend implements the same form when alpha=1-T and source_rgb=R/alpha.
    V5.1 makes the medium energy-conserving and moves the perceptual glass cue
    toward broad front/back interfaces rather than uniform absorption.
    """
    cm = np.clip(maps.container_mask, 0.0, 1.0)
    gm = np.clip(maps.glyph_mask, 0.0, 1.0)

    tvals = maps.thickness[cm > 0.5]
    tmax = max(float(np.percentile(tvals, 99.0)) if tvals.size else 1.0, 1e-6)
    tn = np.clip(maps.thickness / tmax, 0.0, 1.0)
    radius = np.clip(maps.local_radius / 28.0, 0.0, 1.0)
    glyph_mass = gm * np.clip(0.36 + 0.64 * radius, 0.0, 1.0)

    path = params.path_base + params.path_gain * np.sqrt(tn) + params.glyph_path_gain * glyph_mass
    sigma_a = params.container_absorption + params.glyph_absorption_add * glyph_mass
    sigma_s = params.container_scattering + params.glyph_scattering_add * glyph_mass
    sigma_t = np.maximum(sigma_a + sigma_s, 1e-6)

    medium_T = np.exp(-sigma_t * path).astype(np.float32)
    single_scatter = (sigma_s / sigma_t) * (1.0 - medium_T)

    nf = maps.front_normals
    nb = maps.back_normals
    ff = _fresnel(nf[..., 2], params.ior)
    fb = _fresnel(nb[..., 2], params.ior)

    # Physical F0 remains low in the clear crown. The broad curved shoulder gets
    # an art-directed grazing boost so the material survives 64–96 px without
    # becoming an opaque card.
    slope = _norm01(maps.front_slope)
    back_slope = _norm01(maps.back_slope)
    ff_eff = np.clip(
        ff * params.front_reflection_gain + params.edge_reflection_boost * np.power(slope, 0.62),
        0.0,
        0.66,
    )
    fb_eff = np.clip(
        fb * params.back_reflection_gain + params.edge_back_boost * np.power(back_slope, 0.66),
        0.0,
        0.50,
    )

    env_f = _studio_env(nf)
    env_b = _studio_env(nb)

    # Two-interface transmittance through a genuinely low-extinction core.
    T = (1.0 - ff_eff) * medium_T * (1.0 - fb_eff)

    # Front reflection, rear interface reflection after a partial internal path,
    # and energy-conserving single-scatter return.
    R_front = ff_eff * env_f
    internal_to_back = (1.0 - ff_eff) * np.sqrt(medium_T)
    R_back = internal_to_back * fb_eff * env_b

    scatter_luma = (
        params.scatter_luma_container * (1.0 - gm)
        + (0.22 * params.scatter_luma_container + 0.78 * params.scatter_luma_glyph) * gm
    )
    R_scatter = (1.0 - ff_eff) * params.scatter_energy * single_scatter * scatter_luma

    R = R_front + R_back + R_scatter

    # Signed front/back disagreement acts as a static approximation of the
    # luminance redistribution normally produced by lensing. It is evaluated on
    # the entire curved shoulder, not drawn as two hand-authored outlines.
    signed_interface = (env_f - env_b) * np.sqrt(np.clip(slope * back_slope, 0.0, 1.0)) * cm
    pos = np.clip(signed_interface, 0.0, 1.0)
    neg = np.clip(-signed_interface, 0.0, 1.0)
    R += params.interface_bright_gain * pos
    T *= (1.0 - params.interface_dark_gain * neg)

    if flags.explicit_rim:
        # Subpixel silhouette stabilizer only. No material gate may depend on it.
        rim = smootherstep(np.clip((maps.q - 0.968) / 0.032, 0.0, 1.0)) * cm
        R += params.rim_energy * rim
        T *= (1.0 - 0.008 * rim)

    if flags.specular:
        csp = _sharp_spec(maps.container_front_normals, 50.0) * np.sqrt(_norm01(maps.container_front_slope)) * cm
        gsp = _sharp_spec(nf, 36.0) * np.sqrt(np.clip(_norm01(maps.glyph_slope), 0.0, 1.0)) * gm
        R += params.sharp_specular_gain * csp + params.glyph_specular_gain * gsp

    # No external shadow. The object must remain dimensional in no-shadow mode.
    T = np.where(cm > 1e-4, np.clip(T, 0.12, 0.998), 1.0)
    R = np.where(cm > 1e-4, np.clip(R, 0.0, 1.0), 0.0)

    alpha = np.clip(1.0 - T, 0.0, 0.88)
    src = np.divide(
        R,
        np.maximum(alpha, 1e-6),
        out=np.full_like(alpha, 0.5),
        where=alpha > 1e-6,
    )
    src = np.clip(src, 0.0, 1.0)

    # Intrinsic hue is exactly neutral. Wallpaper colour only arrives through T.
    rgb = np.round(src * 255.0).astype(np.uint8)
    a = np.round(alpha * 255.0).astype(np.uint8)
    return np.stack((rgb, rgb, rgb, a), axis=-1)
