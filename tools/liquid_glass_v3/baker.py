from __future__ import annotations

from PIL import Image

from .material import BakeFlags, MaterialParams, bake_static_rgba
from .surface import SurfaceMaps, SurfaceParams, build_surface_maps


def bake_maps(
    container_mask: Image.Image,
    glyph_mask: Image.Image,
    params: SurfaceParams = SurfaceParams(),
    *,
    size: int | None = None,
) -> SurfaceMaps:
    return build_surface_maps(container_mask, glyph_mask, params, size=size)


def bake_material(
    maps: SurfaceMaps,
    params: MaterialParams = MaterialParams(),
    flags: BakeFlags = BakeFlags(),
):
    return bake_static_rgba(maps, params, flags)
