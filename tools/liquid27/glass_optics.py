from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .clear_material import _bilinear_warp
from .glass_surface import enclosure_surface, glyph_surface


def _local_stats(img: Image.Image):
    gray = img.convert('L'); size = img.size[0]
    low = np.asarray(gray.filter(ImageFilter.GaussianBlur(max(1.0, size*.055))), dtype=np.float32) / 255.0
    med = np.asarray(gray.filter(ImageFilter.GaussianBlur(max(.7, size*.020))), dtype=np.float32) / 255.0
    raw = np.asarray(gray, dtype=np.float32) / 255.0
    contrast = np.clip(np.abs(raw-med)*3.0 + np.abs(med-low)*1.5, 0.0, 1.0)
    return low, med, contrast


def _snell_flow(surface: dict, size: int, ior: float = 1.49):
    nx, ny, nz = surface['nx'], surface['ny'], surface['nz']; eta = 1.0 / ior
    cosi = np.clip(nz, 0.0, 1.0); k = np.clip(1.0 - eta*eta*(1.0-cosi*cosi), 0.0, 1.0)
    scalar = eta + (eta*cosi - np.sqrt(k)); tx = nx*scalar; ty = ny*scalar
    shell = np.clip(surface['edge']*.55 + surface['rim']*.80 + surface['very_rim']*1.25, 0, 1.8)
    optical_scale = size * (.092 + .040*shell)
    dx = tx*surface['thickness']*optical_scale
    dy = ty*surface['thickness']*optical_scale
    dx += surface['gx']*(.80 + 1.55*surface['curvature'] + 1.15*shell)
    dy += surface['gy']*(.80 + 1.55*surface['curvature'] + 1.15*shell)
    return dx.astype(np.float32), dy.astype(np.float32)


def _multisample(arr, dx, dy, weight):
    primary = _bilinear_warp(arr, dx, dy).astype(np.float32)
    a = _bilinear_warp(arr, dx*.78-dy*.055, dy*.78+dx*.055).astype(np.float32)
    b = _bilinear_warp(arr, dx*1.18+dy*.038, dy*1.18-dx*.038).astype(np.float32)
    integrated = primary*.56 + a*.24 + b*.20
    w = np.clip(weight, 0, .76)[..., None]
    return np.clip(primary*(1-w) + integrated*w, 0, 255)


def _environment_reflection(arr, surface, dx, dy):
    env = _bilinear_warp(arr, -dx*.48, -dy*.48).astype(np.float32)
    env = np.asarray(Image.fromarray(env.astype(np.uint8), 'RGB').filter(ImageFilter.GaussianBlur(2.4)), dtype=np.float32)
    f = np.clip(surface['fsoft']*.13 + surface['fmid']*.20 + surface['edge']*.035, 0, .28)[..., None]
    return env, f


def _specular(surface, light=(-.54,-.68,.50)):
    lx,ly,lz = light; lm = max((lx*lx+ly*ly+lz*lz)**.5,1e-6); lx,ly,lz = lx/lm,ly/lm,lz/lm
    hx,hy,hz = lx,ly,lz+1.; hm = max((hx*hx+hy*hy+hz*hz)**.5,1e-6); hx,hy,hz = hx/hm,hy/hm,hz/hm
    ndoth = np.clip(surface['nx']*hx + surface['ny']*hy + surface['nz']*hz,0,1)
    return np.clip((ndoth**42.) * np.clip(surface['fmid']*1.35 + surface['ftight']*1.55,0,1),0,.58)


def _caustic(dx,dy,inside):
    _, ddx = np.gradient(dx); edy, _ = np.gradient(dy); div = ddx + edy
    return np.clip(-div*.085, -.060, .075) * inside


def composite_container(base: Image.Image):
    if base.size[0] != base.size[1]:
        raise ValueError('Liquid Glass preview expects a square patch')
    size = base.size[0]; s = enclosure_surface(size); arr = np.asarray(base.convert('RGB'), dtype=np.float32)
    dx,dy = _snell_flow(s,size)
    refracted = _multisample(arr,dx,dy,s['curvature']*(.35+.65*s['edge']))

    secondary_sample = _bilinear_warp(arr,-dx*.20,-dy*.20).astype(np.float32)
    interface = np.clip(np.exp(-((s['q']-.79)/.055)**2)*(.07+.08*s['fmid']),0,.13)[...,None]
    refracted = refracted*(1-interface)+secondary_sample*interface

    env, env_w = _environment_reflection(arr,s,dx,dy)
    out = refracted*(1-env_w)+env*env_w
    spec = _specular(s)[...,None]
    out = out*(1-spec*.30)+255.*spec*.30

    lx,ly = -.54,-.68
    opposite = np.clip(s['nx']*(-lx)+s['ny']*(-ly),0,1)**2.6*np.clip(s['edge']*.45+s['fmid'],0,1)
    out *= 1-opposite[...,None]*.10
    out *= 1+_caustic(dx,dy,s['inside'])[...,None]

    # Broad, local, wallpaper-derived body response. This is what keeps the
    # lens perceptible away from the highlight without turning it milky.
    tmp = Image.fromarray(np.clip(out,0,255).astype(np.uint8),'RGB')
    low,_,lc = _local_stats(tmp)
    rr = np.asarray(tmp,dtype=np.float32)/255.
    adaptive = np.tanh((.50-low)*3.2) * (.018*s['inside'] + .030*s['mid'] + .045*s['edge'])
    bright = np.clip((low-.70)/.25,0,1)*s['edge']*.070
    dark = np.clip((.34-low)/.34,0,1)*s['fmid']*.065
    gain = 1.+(1.-lc)*(s['mid']*.030+s['edge']*.11)
    rr = (rr-low[...,None])*gain[...,None]+low[...,None]
    rr = np.clip(rr + adaptive[...,None] - bright[...,None] + dark[...,None],0,1)

    processed = np.round(rr*255).astype(np.uint8); inside = s['inside'][...,None]
    final = arr*(1-inside)+processed*inside
    return Image.fromarray(np.clip(final,0,255).astype(np.uint8),'RGB'),dx,dy,s


def composite_glyph(base: Image.Image, glyph_mask: Image.Image):
    """Second dielectric with explicit perceptual separation from the container.

    The wallpaper remains visible, but local luminance is pushed away from its
    neighbourhood so the logo never becomes the run-60 ghost on midtones.
    """
    size = base.size[0]; s = glyph_surface(glyph_mask,size); arr = np.asarray(base.convert('RGB'),dtype=np.float32)
    eta = 1./1.52; cosi = np.clip(s['nz'],0,1); k = np.clip(1.-eta*eta*(1.-cosi*cosi),0,1)
    scalar = eta+(eta*cosi-np.sqrt(k))
    dx = s['nx']*scalar*s['thickness']*size*.145 + s['gx']*(1.05+1.2*s['edge'])
    dy = s['ny']*scalar*s['thickness']*size*.145 + s['gy']*(1.05+1.2*s['edge'])
    warped = _multisample(arr,dx,dy,np.clip(s['curvature']*.82+s['edge']*.25,0,.78))

    alpha = np.clip(s['alpha'],0,1); edge = np.clip(s['edge'],0,1)
    fresnel = np.clip(s['fresnel']+edge*.24,0,.80)
    inner = _bilinear_warp(arr,-dx*.22,-dy*.22).astype(np.float32)
    iw = (edge*.10)[...,None]
    glass = warped*(1-iw)+inner*iw

    env = _bilinear_warp(arr,-dx*.34,-dy*.34).astype(np.float32)
    env_w = (fresnel*.15)[...,None]
    glass = glass*(1-env_w)+env*env_w

    lx,ly,lz = -.50,-.72,.48; lm=(lx*lx+ly*ly+lz*lz)**.5; lx,ly,lz=lx/lm,ly/lm,lz/lm
    ndotl = np.clip(s['nx']*lx+s['ny']*ly+s['nz']*lz,0,1)
    spec = (ndotl**34.)*np.clip(fresnel*1.25+edge*.18,0,.55)
    glass = glass*(1-spec[...,None]*.24)+255.*spec[...,None]*.24
    opposite = np.clip(-(s['nx']*lx+s['ny']*ly),0,1)**2.5*edge
    glass *= 1-opposite[...,None]*.12

    # Apple-like perceptual hierarchy: the glyph is denser than the shell and
    # adapts locally. Dark wallpaper gets a gentle lift; bright wallpaper gets
    # a neutral darkening. Midtones receive enough separation to remain legible.
    gimg = Image.fromarray(np.clip(glass,0,255).astype(np.uint8),'RGB')
    low,_,lc = _local_stats(gimg)
    gr = np.asarray(gimg,dtype=np.float32)/255.
    direction = np.tanh((.50-low)*4.4)
    support = alpha*(.105 + .070*(1-lc) + .060*edge)
    gr = np.clip(gr + direction[...,None]*support[...,None],0,1)

    # A broad thickness term makes solid glyph areas read as glass mass rather
    # than an outline. It remains neutral and is weaker than the local support.
    thickness_bias = (s['thickness'] / 1.35) * alpha * .035
    gr = np.clip(gr + direction[...,None]*thickness_bias[...,None],0,1)
    glass = gr*255.

    body_mix = np.clip(alpha*(.88+.08*edge),0,.96)[...,None]
    out = arr*(1-body_mix)+glass*body_mix
    return Image.fromarray(np.clip(out,0,255).astype(np.uint8),'RGB'),dx,dy,s
