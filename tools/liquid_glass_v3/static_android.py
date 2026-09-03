from __future__ import annotations

from dataclasses import replace

import numpy as np
from PIL import Image

from .material import BakeFlags, MaterialParams, bake_static_rgba
from .surface import SurfaceMaps, SurfaceParams, build_surface_maps, squircle_mask


def bake_android_rgba(
    glyph_mask: Image.Image,
    *,
    size: int = 1024,
    surface_params: SurfaceParams = SurfaceParams(),
    material_params: MaterialParams = MaterialParams(),
    flags: BakeFlags = BakeFlags(),
) -> tuple[Image.Image, SurfaceMaps]:
    container = squircle_mask(size)
    gm = glyph_mask.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    maps = build_surface_maps(container, gm, surface_params, size=size)
    rgba = bake_static_rgba(maps, material_params, flags)
    return Image.fromarray(rgba, "RGBA"), maps


def launcher_scale_suite(
    icon: Image.Image,
    *,
    sizes=(48, 64, 72, 96, 128),
    background=(92, 78, 96),
) -> Image.Image:
    cell_w = 170
    cell_h = 190
    board = Image.new("RGB", (cell_w * len(sizes), cell_h), background)
    for i, sz in enumerate(sizes):
        canvas = Image.new("RGB", (cell_w, cell_h), background)
        ic = icon.resize((sz, sz), Image.Resampling.LANCZOS)
        x = (cell_w - sz) // 2
        y = (cell_h - sz) // 2 - 8
        canvas.paste(ic, (x, y), ic)
        board.paste(canvas, (i * cell_w, 0))
    return board


def variant(
    glyph_mask: Image.Image,
    *,
    size: int,
    no_specular: bool = False,
    no_shadow: bool = False,
    no_rim: bool = False,
    surface_params: SurfaceParams = SurfaceParams(),
    material_params: MaterialParams = MaterialParams(),
) -> Image.Image:
    flags = BakeFlags(
        specular=not no_specular,
        shadow=not no_shadow,
        explicit_rim=not no_rim,
    )
    icon, _ = bake_android_rgba(
        glyph_mask,
        size=size,
        surface_params=surface_params,
        material_params=material_params,
        flags=flags,
    )
    return icon
