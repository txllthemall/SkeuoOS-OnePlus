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
from liquid_glass_v3.diagnostics import (
    composite_center,
    diagnostics_dict,
    difference_heatmap,
    make_material_lab,
    map_to_gray,
    normal_map_image,
    render_map_sheet,
    save_diagnostics_json,
    wallpaper,
)
from liquid_glass_v3.material import BakeFlags, MaterialParams, bake_static_rgba
from liquid_glass_v3.preview_optics import render_optical_preview
from liquid_glass_v3.sources import github_octocat_mask
from liquid_glass_v3.static_android import launcher_scale_suite
from liquid_glass_v3.surface import SurfaceParams, build_surface_maps, squircle_mask

OUT = Path(__file__).resolve().parents[2] / "build" / "liquid-glass-v3"
SIZE = 640


def old_github() -> Image.Image:
    """Legacy render exists only for A/B; it is never material input to V3."""
    bg, kind, _ = ICON_SPECS["skeuo_github"]
    return render("skeuo_github", bg, kind, "clear").convert("RGBA")


def glyph_mask(size: int = SIZE) -> Image.Image:
    # Do NOT use legacy foreground-union semantics here. The legacy GitHub mark
    # is the light field around a negative-space cat, so unioning it makes the
    # ring the glyph. V3 uses the actual Octocat body derived from the official
    # 2026 Primer Octicon geometry.
    return github_octocat_mask(size)


def build_variant(*, specular=True, shadow=True, rim=True):
    g = glyph_mask(SIZE)
    container = squircle_mask(SIZE)
    maps = build_surface_maps(container, g, SurfaceParams(), size=SIZE)
    rgba = bake_static_rgba(
        maps,
        MaterialParams(),
        BakeFlags(specular=specular, shadow=shadow, explicit_rim=rim),
    )
    return Image.fromarray(rgba, "RGBA"), maps


def side_by_side(old: Image.Image, new: Image.Image, kind: str = "midtone") -> Image.Image:
    cell = 720
    bg_l = wallpaper(kind, (cell, cell))
    bg_r = wallpaper(kind, (cell, cell))
    left = composite_center(bg_l, old, 300)
    right = composite_center(bg_r, new, 300)
    board = Image.new("RGB", (cell * 2, cell), (0, 0, 0))
    board.paste(left, (0, 0))
    board.paste(right, (cell, 0))
    return board


def alpha_only(icon: Image.Image) -> Image.Image:
    a = np.asarray(icon.convert("RGBA"), dtype=np.uint8)[..., 3]
    return Image.fromarray(a, "L").convert("RGB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    old = old_github()
    new, maps = build_variant()
    nospec, _ = build_variant(specular=False)
    noshadow, _ = build_variant(shadow=False)
    norim, _ = build_variant(rim=False)

    new.save(OUT / "github_v3_rgba.png")

    make_material_lab(new).save(OUT / "preview_v3_master.png")
    for kind in ("dark", "bright", "midtone", "warm", "blue"):
        composite_center(wallpaper(kind, (900, 900)), new, 390).save(OUT / f"preview_v3_master_{kind}.png")

    launcher_scale_suite(new).save(OUT / "preview_v3_launcher_scale.png")
    make_material_lab(new, cell=300).save(OUT / "preview_v3_no_labels.png")

    composite_center(wallpaper("midtone", (900, 900)), nospec, 390).save(OUT / "preview_v3_no_specular.png")
    composite_center(wallpaper("midtone", (900, 900)), noshadow, 390).save(OUT / "preview_v3_no_shadow.png")
    composite_center(wallpaper("midtone", (900, 900)), norim, 390).save(OUT / "preview_v3_no_rim.png")

    render_map_sheet(maps).save(OUT / "preview_v3_maps.png")
    map_to_gray(maps.front_height).save(OUT / "preview_v3_height.png")
    map_to_gray(maps.back_height).save(OUT / "preview_v3_back_height.png")
    normal_map_image(maps.front_normals).save(OUT / "preview_v3_normals.png")
    normal_map_image(maps.back_normals).save(OUT / "preview_v3_back_normals.png")
    map_to_gray(maps.thickness).save(OUT / "preview_v3_thickness.png")
    map_to_gray(maps.curvature).save(OUT / "preview_v3_curvature.png")
    map_to_gray(maps.back_curvature).save(OUT / "preview_v3_back_curvature.png")
    map_to_gray(maps.local_radius).save(OUT / "preview_v3_local_radius.png")
    map_to_gray(maps.glyph_profile).save(OUT / "preview_v3_glyph_relief.png")
    map_to_gray(maps.glyph_back_relief_map).save(OUT / "preview_v3_glyph_back_relief.png")
    alpha_only(new).save(OUT / "preview_v3_alpha_only.png")

    side_by_side(old, new).save(OUT / "preview_v3_old_vs_new.png")
    difference_heatmap(old, new, wallpaper("midtone", (900, 900))).save(OUT / "preview_v3_difference_heatmap.png")

    checker = wallpaper("highcontrast", (SIZE, SIZE))
    render_optical_preview(maps, checker, displacement_scale=34.0).save(OUT / "preview_v3_checker_refraction.png")
    render_optical_preview(maps, wallpaper("midtone", (SIZE, SIZE)), displacement_scale=30.0).save(OUT / "preview_v3_optical_stress.png")

    data = diagnostics_dict(new, maps)
    data.update({
        "renderer": "liquid_glass_v3_height_field_two_interface",
        "size": SIZE,
        "glyph_source": "primer/octicons mark-github-24 2026 negative-space Octocat",
        "legacy_used_for_material": False,
        "production_background_sampling": False,
        "front_back_interfaces": True,
    })
    save_diagnostics_json(OUT / "v3_diagnostics.json", data)

    print("Liquid Glass V3 GitHub master generated:", OUT)
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
