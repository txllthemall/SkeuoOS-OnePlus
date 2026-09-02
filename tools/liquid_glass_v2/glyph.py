from __future__ import annotations

import numpy as np
from PIL import Image, ImageChops, ImageFilter

from .material import _bilinear


def _arr(mask: Image.Image) -> np.ndarray:
    return np.asarray(mask.convert('L'), dtype=np.float32) / 255.0


def _edge_maps(mask: Image.Image):
    a = _arr(mask)
    soft = _arr(mask.filter(ImageFilter.GaussianBlur(5.0)))
    inner = np.clip(a - _arr(mask.filter(ImageFilter.MinFilter(11))), 0, 1)
    tight = np.clip(a - _arr(mask.filter(ImageFilter.MinFilter(5))), 0, 1)
    broad = np.clip(soft * a, 0, 1)
    return a, broad, inner, tight


def render_glyph_optical(base: Image.Image, mask: Image.Image, *, specular=True):
    size = base.size[0]
    m = mask.resize((size,size), Image.Resampling.LANCZOS)
    a, broad, inner, tight = _edge_maps(m)
    arr = np.asarray(base.convert('RGB'), dtype=np.float32)

    # Build a second convex dielectric from the glyph geometry itself. Gradient
    # of a softened interior determines local normal direction.
    spacing = 2.0 / max(size-1, 1)
    gy, gx = np.gradient(broad, spacing, spacing)
    nx, ny, nz = -gx*0.40, -gy*0.40, np.ones_like(gx)
    mag = np.maximum(np.sqrt(nx*nx+ny*ny+nz*nz), 1e-6)
    nx, ny, nz = nx/mag, ny/mag, nz/mag
    local_thickness = np.clip(0.16*a + 0.48*broad + 0.68*inner + 0.42*tight, 0, 1.25)
    dx = nx * local_thickness * size * 0.082
    dy = ny * local_thickness * size * 0.082
    refr = _bilinear(arr, dx, dy)
    reverse = _bilinear(arr, -dx*0.22, -dy*0.22)
    glass = refr*0.86 + reverse*0.14

    # Denser than the enclosure, but still transmissive. Recognition is carried
    # by dual interfaces + body mass rather than a flat white silhouette.
    body = np.clip(a*(0.18 + 0.12*broad),0,0.30)[...,None]
    neutral = np.full_like(arr, 166.0)
    glass = glass*(1-body) + neutral*body

    lx,ly,lz=-0.44,-0.76,0.47
    hm=np.sqrt(lx*lx+ly*ly+(lz+1)**2)
    hx,hy,hz=lx/hm,ly/hm,(lz+1)/hm
    ndoth=np.clip(nx*hx+ny*hy+nz*hz,0,1)
    light=np.clip((0.10*inner+0.18*tight)*(0.35+0.65*ndoth),0,0.24)
    dark=np.clip((0.08*inner+0.15*tight)*(0.35+0.65*np.clip(-ny,0,1)),0,0.20)
    if specular:
        sp=np.clip((ndoth**26)*(0.20*inner+0.36*tight),0,0.30)
        light=np.clip(light+sp,0,0.34)
    glass=glass*(1-light[...,None])+255*light[...,None]
    glass*=1-dark[...,None]

    coverage=np.clip(a*(0.72+0.22*inner),0,0.94)[...,None]
    out=arr*(1-coverage)+glass*coverage
    return Image.fromarray(np.clip(out,0,255).astype(np.uint8),'RGB')


def static_glyph_layers(mask: Image.Image):
    """Return spatial RGBA cues for a wallpaper-agnostic glass insert."""
    a,broad,inner,tight=_edge_maps(mask)
    # Body mass is intentionally real and readable, not outline-only.
    core_alpha=np.clip(0.16*a + 0.06*broad,0,0.20)
    wide_light=np.clip(inner*0.18 + tight*0.10,0,0.24)
    tight_light=np.clip(tight*0.26,0,0.28)
    # opposite dark interface remains spatially adjacent to the bright cue.
    shifted=np.roll(tight, 2, axis=0)
    dark=np.clip(shifted*0.22 + inner*0.08,0,0.26)
    return core_alpha,wide_light,tight_light,dark
