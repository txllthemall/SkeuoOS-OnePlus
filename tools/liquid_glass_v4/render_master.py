from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from generate_liquid27 import render
from liquid27.catalog import ICON_SPECS
from liquid_glass_v3.diagnostics import (
    composite_center,
    difference_heatmap,
    map_to_gray,
    normal_map_image,
    wallpaper,
)
from liquid_glass_v3.sources import github_octocat_mask
from liquid_glass_v3.static_android import launcher_scale_suite
from liquid_glass_v4.material import BakeFlags, MaterialParams, bake_static_rgba
from liquid_glass_v4.preview_optics import render_optical_preview
from liquid_glass_v4.surface import SurfaceParams, build_surface_maps

OUT = Path(__file__).resolve().parents[2] / "build" / "liquid-glass-v4"
SIZE = 640


def old_github() -> Image.Image:
    bg, kind, _ = ICON_SPECS["skeuo_github"]
    return render("skeuo_github", bg, kind, "clear").convert("RGBA")


def build_variant(*, specular: bool = True, shadow: bool = False, rim: bool = True):
    glyph = github_octocat_mask(SIZE)
    maps = build_surface_maps(glyph, SurfaceParams(), size=SIZE)
    rgba = bake_static_rgba(maps, MaterialParams(), BakeFlags(specular=specular, shadow=shadow, explicit_rim=rim))
    return Image.fromarray(rgba, "RGBA"), maps


def material_lab(icon: Image.Image) -> Image.Image:
    kinds = ["warm", "midtone", "blue", "dark", "bright", "highcontrast"]
    cell = 360
    board = Image.new("RGB", (cell * 3, cell * 2), (0, 0, 0))
    for i, kind in enumerate(kinds):
        bg = wallpaper(kind, (cell, cell))
        board.paste(composite_center(bg, icon, 215), ((i % 3) * cell, (i // 3) * cell))
    return board


def ab_board(old: Image.Image, new: Image.Image) -> Image.Image:
    cell = 650
    bg1 = wallpaper("midtone", (cell, cell))
    bg2 = wallpaper("midtone", (cell, cell))
    board = Image.new("RGB", (cell * 2, cell), (0, 0, 0))
    board.paste(composite_center(bg1, old, 300), (0, 0))
    board.paste(composite_center(bg2, new, 300), (cell, 0))
    return board


def container_only(maps) -> Image.Image:
    # Rebuild with an empty glyph using the exact same V4 material path.
    empty = Image.new("L", (SIZE, SIZE), 0)
    mm = build_surface_maps(empty, SurfaceParams(), size=SIZE)
    rgba = bake_static_rgba(mm, MaterialParams(), BakeFlags())
    return Image.fromarray(rgba, "RGBA")


def glyph_only(full: Image.Image, maps) -> Image.Image:
    arr = np.asarray(full.convert("RGBA"), dtype=np.uint8).copy()
    gate = np.clip(maps.glyph_mask, 0.0, 1.0)
    arr[..., 3] = np.round(arr[..., 3].astype(np.float32) * gate).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    old = old_github()
    new, maps = build_variant()
    nospec, _ = build_variant(specular=False)
    noshadow, _ = build_variant(shadow=False)
    norim, _ = build_variant(rim=False)
    cont = container_only(maps)
    gly = glyph_only(new, maps)

    new.save(OUT / "github_v4_rgba.png")
    material_lab(new).save(OUT / "preview_v4_master.png")
    for kind in ("midtone", "dark", "bright", "warm", "blue"):
        composite_center(wallpaper(kind, (900, 900)), new, 390).save(OUT / f"preview_v4_master_{kind}.png")

    launcher_scale_suite(new).save(OUT / "preview_v4_launcher_scale.png")
    composite_center(wallpaper("midtone", (900, 900)), nospec, 390).save(OUT / "preview_v4_no_specular.png")
    composite_center(wallpaper("midtone", (900, 900)), noshadow, 390).save(OUT / "preview_v4_no_shadow.png")
    composite_center(wallpaper("midtone", (900, 900)), norim, 390).save(OUT / "preview_v4_no_rim.png")
    composite_center(wallpaper("midtone", (900, 900)), cont, 390).save(OUT / "preview_v4_container_only.png")
    composite_center(wallpaper("midtone", (900, 900)), gly, 390).save(OUT / "preview_v4_glyph_only.png")

    ab_board(old, new).save(OUT / "preview_ANDROID_BRUTAL_AB.png")
    difference_heatmap(old, new, wallpaper("midtone", (900, 900))).save(OUT / "preview_v4_difference_heatmap.png")

    map_to_gray(maps.front_height).save(OUT / "preview_v4_height.png")
    map_to_gray(maps.back_height).save(OUT / "preview_v4_back_height.png")
    map_to_gray(maps.thickness).save(OUT / "preview_v4_thickness.png")
    normal_map_image(maps.front_normals).save(OUT / "preview_v4_normals.png")
    normal_map_image(maps.back_normals).save(OUT / "preview_v4_back_normals.png")
    map_to_gray(maps.glyph_relief).save(OUT / "preview_v4_glyph_relief.png")

    render_optical_preview(maps, wallpaper("highcontrast", (SIZE, SIZE)), gain=1.0).save(OUT / "preview_v4_refraction_stress.png")
    render_optical_preview(maps, wallpaper("midtone", (SIZE, SIZE)), gain=0.95).save(OUT / "preview_v4_optical_midtone.png")

    # Diagnostic JSON intentionally records the architectural break from V3.
    a = np.asarray(new.convert("RGBA"), dtype=np.float32)
    gm = maps.glyph_mask > 0.5
    cm = maps.container_mask > 0.5
    data = {
        "renderer": "liquid_glass_v4_analytic_volume_studio_bake",
        "size": SIZE,
        "static_background_sampling": False,
        "container_alpha_mean": float(a[..., 3][cm].mean() / 255.0),
        "glyph_alpha_mean": float(a[..., 3][gm].mean() / 255.0) if np.any(gm) else 0.0,
        "max_alpha": float(a[..., 3].max() / 255.0),
        "analytic_superellipse_surface": True,
        "independent_front_back_surfaces": True,
        "neutral_studio_reflection_bake": True,
        "external_shadow": False,
        "legacy_material_used": False,
    }
    (OUT / "v4_diagnostics.json").write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
