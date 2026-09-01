from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .clear_material import _bilinear_warp
from .glass_surface import enclosure_surface, glyph_surface


def _local_stats(img: Image.Image):
    gray=img.convert('L'); size=img.size[0]
    low=np.asarray(gray.filter(ImageFilter.GaussianBlur(max(1.0,size*.055))),dtype=np.float32)/255.0
    med=np.asarray(gray.filter(ImageFilter.GaussianBlur(max(.7,size*.020))),dtype=np.float32)/255.0
    raw=np.asarray(gray,dtype=np.float32)/255.0
    contrast=np.clip(np.abs(raw-med)*3.0+np.abs(med-low)*1.5,0.0,1.0)
    return low,med,contrast


def _snell_flow(surface:dict,size:int,ior:float=1.48):
    nx,ny,nz=surface['nx'],surface['ny'],surface['nz']; eta=1.0/ior
    cosi=np.clip(nz,0.0,1.0); k=np.clip(1.0-eta*eta*(1.0-cosi*cosi),0.0,1.0)
    scalar=eta+(eta*cosi-np.sqrt(k)); tx=nx*scalar; ty=ny*scalar
    # Surface-derived optical path. Normal response supplies direction while
    # thickness and curvature supply magnitude.
    optical_scale=size*.070
    dx=tx*surface['thickness']*optical_scale
    dy=ty*surface['thickness']*optical_scale
    # A small slope-derived magnification term changes local scale without
    # becoming a uniform radial warp.
    dx+=surface['gx']*(.55+.80*surface['curvature'])
    dy+=surface['gy']*(.55+.80*surface['curvature'])
    return dx.astype(np.float32),dy.astype(np.float32)


def _multisample(arr,dx,dy,weight):
    primary=_bilinear_warp(arr,dx,dy).astype(np.float32)
    a=_bilinear_warp(arr,dx*.84-dy*.040,dy*.84+dx*.040).astype(np.float32)
    b=_bilinear_warp(arr,dx*1.11+dy*.028,dy*1.11-dx*.028).astype(np.float32)
    integrated=primary*.64+a*.20+b*.16; w=np.clip(weight,0,.68)[...,None]
    return np.clip(primary*(1-w)+integrated*w,0,255)


def _environment_reflection(arr,surface,dx,dy):
    env=_bilinear_warp(arr,-dx*.38,-dy*.38).astype(np.float32)
    env=np.asarray(Image.fromarray(env.astype(np.uint8),'RGB').filter(ImageFilter.GaussianBlur(2.0)),dtype=np.float32)
    f=np.clip(surface['fsoft']*.16+surface['fmid']*.27,0,.32)[...,None]
    return env,f


def _specular(surface,light=(-.54,-.68,.50)):
    lx,ly,lz=light; lm=max((lx*lx+ly*ly+lz*lz)**.5,1e-6); lx,ly,lz=lx/lm,ly/lm,lz/lm
    hx,hy,hz=lx,ly,lz+1.; hm=max((hx*hx+hy*hy+hz*hz)**.5,1e-6); hx,hy,hz=hx/hm,hy/hm,hz/hm
    ndoth=np.clip(surface['nx']*hx+surface['ny']*hy+surface['nz']*hz,0,1)
    return np.clip((ndoth**34.)*np.clip(surface['fmid']*2.0+surface['ftight']*2.2,0,1),0,.76)


def _caustic(dx,dy,inside):
    _,ddx=np.gradient(dx); edy,_=np.gradient(dy); div=ddx+edy
    return np.clip(-div*.060,-.040,.060)*inside


def composite_container(base:Image.Image):
    if base.size[0]!=base.size[1]: raise ValueError('Liquid Glass preview expects a square patch')
    size=base.size[0]; s=enclosure_surface(size); arr=np.asarray(base.convert('RGB'),dtype=np.float32)
    dx,dy=_snell_flow(s,size); refracted=_multisample(arr,dx,dy,s['curvature']*s['edge'])
    env,env_w=_environment_reflection(arr,s,dx,dy); out=refracted*(1-env_w)+env*env_w
    spec=_specular(s)[...,None]; out=out*(1-spec*.38)+255.*spec*.38
    lx,ly=-.54,-.68; opposite=np.clip(s['nx']*(-lx)+s['ny']*(-ly),0,1)**3.0*s['fmid']; out*=1-opposite[...,None]*.11
    secondary=np.clip(s['fsoft']*s['edge']*.12+s['fmid']*.070,0,.13); out=out*(1-secondary[...,None])+232.*secondary[...,None]
    out*=1+_caustic(dx,dy,s['inside'])[...,None]
    tmp=Image.fromarray(np.clip(out,0,255).astype(np.uint8),'RGB'); low,_,lc=_local_stats(tmp); rr=np.asarray(tmp,dtype=np.float32)/255.
    bright=np.clip((low-.70)/.25,0,1)*s['edge']*.060; dark=np.clip((.34-low)/.34,0,1)*s['fmid']*.070
    gain=1.+(1.-lc)*s['edge']*.075; rr=(rr-low[...,None])*gain[...,None]+low[...,None]; rr=np.clip(rr-bright[...,None]+dark[...,None],0,1)
    processed=np.round(rr*255).astype(np.uint8); inside=s['inside'][...,None]; final=arr*(1-inside)+processed*inside
    return Image.fromarray(np.clip(final,0,255).astype(np.uint8),'RGB'),dx,dy,s


def composite_glyph(base:Image.Image,glyph_mask:Image.Image):
    size=base.size[0]; s=glyph_surface(glyph_mask,size); arr=np.asarray(base.convert('RGB'),dtype=np.float32)
    eta=1./1.50; cosi=np.clip(s['nz'],0,1); k=np.clip(1.-eta*eta*(1.-cosi*cosi),0,1); scalar=eta+(eta*cosi-np.sqrt(k))
    dx=s['nx']*scalar*s['thickness']*size*.092+s['gx']*.72
    dy=s['ny']*scalar*s['thickness']*size*.092+s['gy']*.72
    warped=_multisample(arr,dx,dy,s['curvature']*.64)
    alpha=np.clip(s['alpha'],0,1); edge=np.clip(s['edge'],0,1); fresnel=np.clip(s['fresnel']+edge*.20,0,.78)
    env=_bilinear_warp(arr,-dx*.30,-dy*.30).astype(np.float32); env_w=(fresnel*.19)[...,None]; glass=warped*(1-env_w)+env*env_w
    lx,ly,lz=-.50,-.72,.48; lm=(lx*lx+ly*ly+lz*lz)**.5; lx,ly,lz=lx/lm,ly/lm,lz/lm
    ndotl=np.clip(s['nx']*lx+s['ny']*ly+s['nz']*lz,0,1); spec=(ndotl**28.)*np.clip(fresnel*1.8+edge*.22,0,.68)
    glass=glass*(1-spec[...,None]*.34)+255.*spec[...,None]*.34
    opposite=np.clip(-(s['nx']*lx+s['ny']*ly),0,1)**2.6*edge; glass*=1-opposite[...,None]*.11
    # Less body coverage than before: large glyphs reveal wallpaper and obtain
    # identity from their own optical flow/Fresnel instead of a pale fill.
    body_mix=np.clip(alpha*(.56+.22*edge),0,.80)[...,None]
    out=arr*(1-body_mix)+glass*body_mix
    return Image.fromarray(np.clip(out,0,255).astype(np.uint8),'RGB'),dx,dy,s
