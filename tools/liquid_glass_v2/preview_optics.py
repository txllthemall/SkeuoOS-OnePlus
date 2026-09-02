from __future__ import annotations

from PIL import Image

from .material import render_container_optical
from .glyph import render_glyph_optical


def render_optical_icon(background_patch: Image.Image, glyph_mask: Image.Image, *, specular=True, explicit_rim=True):
    base=background_patch.convert('RGB')
    container,_,_,_=render_container_optical(base,specular=specular,explicit_rim=explicit_rim)
    return render_glyph_optical(container,glyph_mask,specular=specular)
