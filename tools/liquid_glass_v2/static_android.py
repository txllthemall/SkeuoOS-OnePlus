from __future__ import annotations

import numpy as np
from PIL import Image

from .surface import superellipse_surface
from .glyph import static_glyph_layers


def _to_mask(arr):
    return Image.fromarray(np.clip(arr*255,0,255).astype(np.uint8),'L')


def _overlay(canvas: Image.Image, rgb, alpha):
    layer=Image.new('RGBA',canvas.size,(*rgb,0)); layer.putalpha(_to_mask(alpha)); canvas.alpha_composite(layer)


def render_static_icon(glyph_mask: Image.Image, size: int=512, *, no_specular=False, no_rim=False):
    """Wallpaper-agnostic RGBA illusion. No backdrop sampling or legacy renderer."""
    s=superellipse_surface(size)
    canvas=Image.new('RGBA',(size,size),(0,0,0,0))

    # Container remains lighter than the glyph. A broad shell provides volume;
    # the core stays nearly transparent.
    center=np.clip((0.014+0.008*s['shoulder'])*s['inside'],0,0.024)
    shell=np.clip((0.035*s['shoulder']+0.080*s['lip']+0.075*s['very_lip'])*s['inside'],0,0.15)
    _overlay(canvas,(154,154,154),center+shell)

    lx,ly,lz=-0.50,-0.72,0.50
    hm=np.sqrt(lx*lx+ly*ly+(lz+1)**2)
    hx,hy,hz=lx/hm,ly/hm,(lz+1)/hm
    ndoth=np.clip(s['nx']*hx+s['ny']*hy+s['nz']*hz,0,1)
    light=np.clip(s['shoulder']*(0.030+0.045*ndoth)+s['lip']*(0.060+0.085*ndoth),0,0.16)
    dark=np.clip(np.maximum(0,-(s['nx']*lx+s['ny']*ly))**2.2*(0.045*s['shoulder']+0.12*s['lip']),0,0.15)
    if not no_rim: _overlay(canvas,(242,242,242),light)
    _overlay(canvas,(20,20,20),dark)
    internal=np.clip(np.exp(-((s['q']-.75)/.075)**2)*0.065*s['inside'],0,0.065)
    _overlay(canvas,(208,208,208),internal)
    if not no_specular:
        spec=np.clip((ndoth**30)*(0.07*s['shoulder']+0.16*s['lip']),0,0.16)
        _overlay(canvas,(255,255,255),spec)

    # Glyph: a visibly denser second material with a directional body, not an
    # outline and not a flat white/gray SVG.
    gm=glyph_mask.resize((size,size),Image.Resampling.LANCZOS)
    body,body_light,body_dark,wide,tight,gdark=static_glyph_layers(gm)
    _overlay(canvas,(156,156,156),body)
    _overlay(canvas,(222,222,222),body_light)
    _overlay(canvas,(56,56,56),body_dark)
    _overlay(canvas,(224,224,224),wide)
    if not no_rim: _overlay(canvas,(250,250,250),tight)
    _overlay(canvas,(20,20,20),gdark)
    if not no_specular:
        y=np.linspace(1,0,size,dtype=np.float32)[:,None]
        x=np.linspace(1,0,size,dtype=np.float32)[None,:]
        directional=np.clip((0.68*y+0.32*x),0,1)
        _overlay(canvas,(255,255,255),np.clip(tight*directional*0.12,0,0.12))
    return canvas
