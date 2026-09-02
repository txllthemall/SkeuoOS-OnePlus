from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .material import _bilinear


def _arr(mask: Image.Image) -> np.ndarray:
    return np.asarray(mask.convert('L'), dtype=np.float32) / 255.0


def _edge_maps(mask: Image.Image):
    a=_arr(mask)
    soft=_arr(mask.filter(ImageFilter.GaussianBlur(5.0)))
    inner=np.clip(a-_arr(mask.filter(ImageFilter.MinFilter(11))),0,1)
    tight=np.clip(a-_arr(mask.filter(ImageFilter.MinFilter(5))),0,1)
    broad=np.clip(soft*a,0,1)
    return a,broad,inner,tight


def render_glyph_optical(base: Image.Image, mask: Image.Image, *, specular=True):
    size=base.size[0]
    m=mask.resize((size,size),Image.Resampling.LANCZOS)
    a,broad,inner,tight=_edge_maps(m)
    arr=np.asarray(base.convert('RGB'),dtype=np.float32)

    spacing=2.0/max(size-1,1)
    gy,gx=np.gradient(broad,spacing,spacing)
    nx,ny,nz=-gx*0.40,-gy*0.40,np.ones_like(gx)
    mag=np.maximum(np.sqrt(nx*nx+ny*ny+nz*nz),1e-6)
    nx,ny,nz=nx/mag,ny/mag,nz/mag
    local_thickness=np.clip(0.22*a+0.56*broad+0.58*inner+0.34*tight,0,1.25)
    dx=nx*local_thickness*size*0.052
    dy=ny*local_thickness*size*0.052
    refr=_bilinear(arr,dx,dy)
    reverse=_bilinear(arr,-dx*0.15,-dy*0.15)
    glass=refr*0.90+reverse*0.10

    # A true optical body, not a contour. The luminance varies across the body,
    # so the logo survives both dark and bright surroundings without becoming a
    # flat white/gray SVG.
    yy,xx=np.indices((size,size),dtype=np.float32)
    directional=np.clip(0.64*(1.0-yy/max(size-1,1))+0.36*(1.0-xx/max(size-1,1)),0,1)
    body_alpha=np.clip(a*(0.28+0.12*broad),0,0.40)[...,None]
    body_luma=(82.0+150.0*directional)[...,None]
    body_rgb=np.repeat(body_luma,3,axis=2)
    glass=glass*(1-body_alpha)+body_rgb*body_alpha

    lx,ly,lz=-0.44,-0.76,0.47
    hm=np.sqrt(lx*lx+ly*ly+(lz+1)**2)
    hx,hy,hz=lx/hm,ly/hm,(lz+1)/hm
    ndoth=np.clip(nx*hx+ny*hy+nz*hz,0,1)
    light=np.clip((0.13*inner+0.21*tight)*(0.30+0.70*ndoth),0,0.27)
    dark=np.clip((0.12*inner+0.18*tight)*(0.28+0.72*np.clip(-ny,0,1)),0,0.24)
    if specular:
        sp=np.clip((ndoth**30)*(0.14*inner+0.25*tight),0,0.20)
        light=np.clip(light+sp,0,0.30)
    glass=glass*(1-light[...,None])+255*light[...,None]
    glass*=1-dark[...,None]

    coverage=np.clip(a*(0.82+0.12*inner),0,0.94)[...,None]
    out=arr*(1-coverage)+glass*coverage
    return Image.fromarray(np.clip(out,0,255).astype(np.uint8),'RGB')


def static_glyph_layers(mask: Image.Image):
    """Return filled, directional dual-luminance body + interfaces."""
    a,broad,inner,tight=_edge_maps(mask)
    h,w=a.shape
    yy,xx=np.indices((h,w),dtype=np.float32)
    directional=np.clip(0.64*(1.0-yy/max(h-1,1))+0.36*(1.0-xx/max(w-1,1)),0,1)

    body=np.clip(a*(0.28+0.10*broad),0,0.38)
    body_light=np.clip(a*(0.09+0.16*directional)+inner*0.04,0,0.24)
    body_dark=np.clip(a*(0.07+0.14*(1.0-directional))+inner*0.04,0,0.22)
    wide_light=np.clip(inner*0.21+tight*0.08,0,0.25)
    tight_light=np.clip(tight*0.25,0,0.26)
    shifted=np.roll(tight,2,axis=0)
    dark=np.clip(shifted*0.25+inner*0.10,0,0.29)
    return body,body_light,body_dark,wide_light,tight_light,dark
