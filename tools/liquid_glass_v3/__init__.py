"""Independent Liquid Glass V3 height-field renderer.

V3 intentionally does not import the legacy Clear/V2 material renderers.
"""

from .surface import SurfaceMaps, SurfaceParams, build_surface_maps, squircle_mask
from .material import BakeFlags, MaterialParams, bake_static_rgba

__all__ = [
    "SurfaceMaps",
    "SurfaceParams",
    "build_surface_maps",
    "squircle_mask",
    "BakeFlags",
    "MaterialParams",
    "bake_static_rgba",
]
