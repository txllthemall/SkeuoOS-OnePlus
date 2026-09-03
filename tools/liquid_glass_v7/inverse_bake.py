from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from generate_liquid27 import render
from liquid27.catalog import ICON_SPECS
from liquid_glass_v3.diagnostics import composite_center, difference_heatmap, wallpaper
from liquid_glass_v3.static_android import launcher_scale_suite

OUT = Path(__file__).resolve().parents[2] / "build" / "liquid-glass-v7"


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, np.power((x + 0.055) / 1.055, 2.4)).astype(np.float32)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1.0 / 2.4) - 0.055).astype(np.float32)


def load_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def old_github() -> Image.Image:
    bg, kind, _ = ICON_SPECS["skeuo_github"]
    return render("skeuo_github", bg, kind, "clear").convert("RGBA")


def derive_rgba(black_srgb: np.ndarray, white_srgb: np.ndarray) -> tuple[np.ndarray, dict]:
    black = srgb_to_linear(black_srgb)
    white = srgb_to_linear(white_srgb)

    # For a static straight-alpha pixel:
    # C_black = alpha * S
    # C_white = alpha * S + (1-alpha)
    # therefore alpha = 1 - (C_white - C_black).
    transmission_rgb = np.clip(white - black, 0.0, 1.0)
    transmission = np.clip(np.mean(transmission_rgb, axis=-1), 0.0, 1.0)
    alpha = np.clip(1.0 - transmission, 0.0, 0.96)

    # Suppress numerical noise outside the object while preserving extremely
    # clear crown transmission.
    alpha = np.where(alpha < 0.0045, 0.0, alpha)

    reflected = np.mean(black, axis=-1)
    source_luma = np.divide(
        reflected,
        np.maximum(alpha, 1e-6),
        out=np.full_like(alpha, 0.5),
        where=alpha > 1e-6,
    )
    source_luma = np.clip(source_luma, 0.0, 1.0)

    # Keep the production material neutral. Bright and dark cues come from the
    # ray-traced environment response itself, not from a baked hue.
    rgb_srgb = linear_to_srgb(source_luma)[..., None]
    rgb = np.repeat(rgb_srgb, 3, axis=-1)
    rgba = np.concatenate((rgb, alpha[..., None]), axis=-1)
    out = np.round(np.clip(rgba, 0.0, 1.0) * 255.0).astype(np.uint8)

    stats = {
        "alpha_mean": float(alpha.mean()),
        "alpha_p95": float(np.percentile(alpha, 95.0)),
        "alpha_max": float(alpha.max()),
        "source_luma_mean_nonzero": float(source_luma[alpha > 0.01].mean()) if np.any(alpha > 0.01) else 0.0,
        "source_luma_min_nonzero": float(source_luma[alpha > 0.01].min()) if np.any(alpha > 0.01) else 0.0,
        "source_luma_max_nonzero": float(source_luma[alpha > 0.01].max()) if np.any(alpha > 0.01) else 0.0,
    }
    return out, stats


def material_lab(icon: Image.Image) -> Image.Image:
    kinds = ["warm", "midtone", "blue", "dark", "bright", "highcontrast"]
    cell = 360
    board = Image.new("RGB", (cell * 3, cell * 2), (0, 0, 0))
    for i, kind in enumerate(kinds):
        board.paste(composite_center(wallpaper(kind, (cell, cell)), icon, 215), ((i % 3) * cell, (i // 3) * cell))
    return board


def ab_board(old: Image.Image, new: Image.Image) -> Image.Image:
    cell = 650
    board = Image.new("RGB", (cell * 2, cell), (0, 0, 0))
    board.paste(composite_center(wallpaper("midtone", (cell, cell)), old, 300), (0, 0))
    board.paste(composite_center(wallpaper("midtone", (cell, cell)), new, 300), (cell, 0))
    return board


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    black = load_rgb(OUT / "render_black.png")
    white = load_rgb(OUT / "render_white.png")
    gray = load_rgb(OUT / "render_gray.png")

    rgba, stats = derive_rgba(black, white)
    icon = Image.fromarray(rgba, "RGBA")
    icon.save(OUT / "github_v7_rgba.png")

    # Validate that the derived operator predicts the independent gray render.
    src = srgb_to_linear(np.asarray(icon.convert("RGB"), dtype=np.float32) / 255.0)
    a = np.asarray(icon.getchannel("A"), dtype=np.float32) / 255.0
    pred_gray_lin = src * a[..., None] + 0.5 * (1.0 - a[..., None])
    pred_gray = linear_to_srgb(pred_gray_lin)
    residual = np.abs(pred_gray - gray)
    residual_vis = np.clip(residual * 5.0, 0.0, 1.0)
    Image.fromarray(np.round(residual_vis * 255.0).astype(np.uint8), "RGB").save(OUT / "preview_v7_inverse_residual.png")

    material_lab(icon).save(OUT / "preview_v7_master.png")
    for kind in ("midtone", "dark", "bright", "warm", "blue"):
        composite_center(wallpaper(kind, (900, 900)), icon, 390).save(OUT / f"preview_v7_master_{kind}.png")

    launcher_scale_suite(icon).save(OUT / "preview_v7_launcher_scale.png")

    old = old_github()
    ab_board(old, icon).save(OUT / "preview_ANDROID_BRUTAL_AB.png")
    difference_heatmap(old, icon, wallpaper("midtone", (900, 900))).save(OUT / "preview_v7_difference_heatmap.png")

    # Architecture tests. V7 has no explicit rim and no external shadow in the
    # production bake, so these are the same real RGBA asset. The no-specular
    # reference is rendered separately with studio lights disabled.
    composite_center(wallpaper("midtone", (900, 900)), icon, 390).save(OUT / "preview_v7_no_shadow.png")
    composite_center(wallpaper("midtone", (900, 900)), icon, 390).save(OUT / "preview_v7_no_rim.png")

    for src_name, dst_name in (
        ("render_midtone.png", "preview_3d_reference.png"),
        ("render_checker.png", "preview_v7_refraction_stress.png"),
        ("render_container_only.png", "preview_v7_container_only.png"),
        ("render_glyph_only.png", "preview_v7_glyph_only.png"),
        ("render_no_specular.png", "preview_v7_no_specular.png"),
    ):
        Image.open(OUT / src_name).convert("RGB").save(OUT / dst_name)

    stats.update({
        "renderer": "liquid_glass_v7_blender_inverse_rgba",
        "inverse_model": "black/white ray-traced solve in linear light",
        "gray_prediction_mae": float(residual.mean()),
        "static_background_sampling": False,
        "runtime_wallpaper_refraction": False,
        "external_shadow": False,
        "explicit_rim": False,
    })
    (OUT / "v7_diagnostics.json").write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(stats, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
