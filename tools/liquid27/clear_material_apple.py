from __future__ import annotations

"""Clear material: optical preview + deliberately separate static Android illusion.

The Android path never samples wallpaper.  It uses neutral dual-luminance
interfaces and alpha topology; the preview path uses the real dielectric optics.
"""

import hashlib
from functools import lru_cache
import numpy as np
from PIL import Image, ImageChops, ImageFilter

from .material import WORK, ENCL, inter, inner_edge, outer_edge, top_facing_edge, bottom_facing_edge, layer, luminance
from .glass_surface import enclosure_surface
from .glass_optics import composite_container, composite_glyph


def _seed(key: str, salt: int = 0) -> int:
    return int.from_bytes(hashlib.sha256(f'{key}:{salt}'.encode()).digest()[:4], 'big')


def _mask(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(np.round(arr * 255.0), 0, 255).astype(np.uint8), 'L')


def reflection_style(key: str) -> int:
    return 2 if (_seed(key, 401) % 5) == 0 else 1


@lru_cache(maxsize=256)
def clear_reflection_mask(key: str) -> Image.Image:
    s = enclosure_surface(WORK)
    flip = -1.0 if (_seed(key,409)&1) else 1.0
    lx,ly,lz=-.50*flip,-.72,.48; lm=(lx*lx+ly*ly+lz*lz)**.5; lx,ly,lz=lx/lm,ly/lm,lz/lm
    hx,hy,hz=lx,ly,lz+1.; hm=(hx*hx+hy*hy+hz*hz)**.5; hx,hy,hz=hx/hm,hy/hm,hz/hm
    ndoth=np.clip(s['nx']*hx+s['ny']*hy+s['nz']*hz,0,1)
    # Small sharp catch only. It cannot carry the material by itself.
    spec=(ndoth**38.)*np.clip(s['fmid']*1.2+s['ftight']*1.5,0,1)
    return _mask(np.clip(spec*.34,0,.30))


def clear_reflection_coverage_pct(key: str) -> float:
    return float((np.asarray(clear_reflection_mask(key),dtype=np.float32)/255.).mean()*100.)


@lru_cache(maxsize=1)
def _static_enclosure_fields():
    """Neutral RGBA topology for launchers: body, curved shell, lip and dark interface."""
    s=enclosure_surface(WORK)
    # This is intentionally a structural break from the old pale plate.  The
    # body is neutral middle-gray at low alpha, so it gently darkens bright
    # wallpapers and lifts dark wallpapers without knowing either wallpaper.
    body=(.030+.018*s['mid']+.035*s['fsoft'])*s['inside']
    shell=(.055*s['edge']+.105*s['rim']+.115*s['very_rim'])*s['inside']
    density=np.clip(body+shell,0,.27)
    lx,ly,lz=-.52,-.70,.49; lm=(lx*lx+ly*ly+lz*lz)**.5; lx,ly,lz=lx/lm,ly/lm,lz/lm
    hx,hy,hz=lx,ly,lz+1.; hm=(hx*hx+hy*hy+hz*hz)**.5; hx,hy,hz=hx/hm,hy/hm,hz/hm
    ndoth=np.clip(s['nx']*hx+s['ny']*hy+s['nz']*hz,0,1)
    spec=np.clip((ndoth**34.)*(s['fmid']*.75+s['ftight']*1.35)*.34,0,.28)
    opposite=np.clip(-(s['nx']*lx+s['ny']*ly),0,1)**2.3
    dark=np.clip(opposite*(.055*s['edge']+.125*s['rim']+.105*s['very_rim']),0,.19)
    # A second internal interface makes the shell read as volume, not outline.
    internal=np.clip(np.exp(-((s['q']-.78)/.055)**2)*(.035+.055*np.clip(-s['ny'],0,1)),0,.085)*s['inside']
    return _mask(density),_mask(spec),_mask(dark),_mask(internal)


def _glyph_static_masks(mask: Image.Image):
    """Build a translucent insert. No material='glass' clamp, no opaque white fill."""
    broad=mask.filter(ImageFilter.GaussianBlur(5.5))
    core=inter(broad,mask)
    edge_w=inner_edge(mask,10.0).filter(ImageFilter.GaussianBlur(2.8))
    edge_t=inner_edge(mask,2.3).filter(ImageFilter.GaussianBlur(.65))
    top=top_facing_edge(mask,2.3).filter(ImageFilter.GaussianBlur(.55))
    low=bottom_facing_edge(mask,2.7).filter(ImageFilter.GaussianBlur(.60))
    # body alpha around 7-10%, edges materially denser; still transparent.
    body=core.point(lambda v:int(v*.090))
    wide=edge_w.point(lambda v:int(v*.155))
    tight=edge_t.point(lambda v:int(v*.31))
    hi=top.point(lambda v:int(v*.42))
    dk=low.point(lambda v:int(v*.36))
    return body,wide,tight,hi,dk


def clearify_layers(layers,key:str):
    """Static glyph = neutral translucent dielectric illusion, never white SVG."""
    result=[]
    for src in layers:
        mask=src['mask']; body,wide,tight,hi,dk=_glyph_static_masks(mask)
        # Mid-gray body is intentionally dual-purpose: visible by contrast on
        # both bright and dark backgrounds while remaining chromatically neutral.
        result.append(layer(body,'#8e8e8e',1.0,0,'off',0,'ink','normal',(0,0),0,0,0))
        result.append(layer(wide,'#a8a8a8',.72,0,'off',0,'ink','normal',(0,0),0,0,0))
        result.append(layer(tight,'#d6d6d6',.58,0,'off',0,'ink','screen',(0,0),0,0,0))
        if hi.getbbox(): result.append(layer(hi,'#ffffff',.42,0,'off',0,'ink','screen',(0,0),0,0,0))
        if dk.getbbox(): result.append(layer(dk,'#151515',.58,0,'off',0,'ink','multiply',(0,0),0,0,0))
    return result


def clear_background(key:str)->Image.Image:
    canvas=Image.new('RGBA',(WORK,WORK),(0,0,0,0)); density,spec,dark,internal=_static_enclosure_fields()
    # Neutral middle-gray transmission body instead of the old pale white plate.
    neutral=Image.new('RGBA',(WORK,WORK),(142,142,142,0)); neutral.putalpha(density); canvas.alpha_composite(neutral)
    inside=Image.new('RGBA',(WORK,WORK),(205,205,205,0)); inside.putalpha(internal); canvas.alpha_composite(inside)
    white=Image.new('RGBA',(WORK,WORK),(255,255,255,0)); white.putalpha(ImageChops.lighter(spec,clear_reflection_mask(key))); canvas.alpha_composite(white)
    dk=Image.new('RGBA',(WORK,WORK),(22,22,22,0)); dk.putalpha(dark); canvas.alpha_composite(dk)
    return canvas


def finish_clear_enclosure(canvas:Image.Image,key:str)->None:
    # Three nested optical interfaces, deliberately low-area. The wide shell is
    # already encoded in clear_background; these are not the material itself.
    hair=outer_edge(ENCL,.65).point(lambda v:int(v*.10)); h=Image.new('RGBA',(WORK,WORK),(248,248,248,0)); h.putalpha(hair); canvas.alpha_composite(h)
    inner=inner_edge(ENCL,2.1).filter(ImageFilter.GaussianBlur(.55)).point(lambda v:int(v*.075)); ii=Image.new('RGBA',(WORK,WORK),(232,232,232,0)); ii.putalpha(inner); canvas.alpha_composite(ii)
    low=bottom_facing_edge(ENCL,2.0).filter(ImageFilter.GaussianBlur(.45)).point(lambda v:int(v*.26)); d=Image.new('RGBA',(WORK,WORK),(18,18,18,0)); d.putalpha(low); canvas.alpha_composite(d)
    canvas.putalpha(inter(canvas.getchannel('A'),ENCL))


def preview_refract_patch(under:Image.Image,foreground_mask:Image.Image|None=None)->Image.Image:
    result,_,_,_=composite_container(under.convert('RGB'))
    if foreground_mask is not None and foreground_mask.getbbox():
        result,_,_,_=composite_glyph(result,foreground_mask)
    return result


@lru_cache(maxsize=1)
def _metric_base():
    s=enclosure_surface(128); dummy=Image.new('RGB',(128,128),(128,128,128)); _,dx,dy,_=composite_container(dummy); disp=np.sqrt(dx*dx+dy*dy)
    center=s['q']<.34; mid=(s['q']>=.46)&(s['q']<.72); edge=(s['q']>=.84)&(s['q']<=1.0)
    dens=np.asarray(_static_enclosure_fields()[0].resize((128,128),Image.Resampling.LANCZOS),dtype=np.float32)
    return {'enclosure_center_density':float(dens[center].mean()),'enclosure_edge_density':float(dens[edge].mean()),'specular_coverage_pct':float((s['fmid']>.12).mean()*100),'refraction_displacement_mean':float(disp[s['inside']>0].mean()),'refraction_displacement_median':float(np.median(disp[s['inside']>0])),'refraction_displacement_max':float(disp.max()),'refraction_center_mean':float(disp[center].mean()),'refraction_mid_mean':float(disp[mid].mean()),'refraction_edge_mean':float(disp[edge].mean()),'fresnel_center_mean':float(s['fresnel'][center].mean()),'fresnel_edge_mean':float(s['fresnel'][edge].mean())}


def material_metrics(key:str)->dict:
    out=dict(_metric_base()); out['reflection_coverage_pct']=clear_reflection_coverage_pct(key); out['edge_center_density_ratio']=out['enclosure_edge_density']/max(out['enclosure_center_density'],1e-6); out['edge_mid_displacement_ratio']=out['refraction_edge_mean']/max(out['refraction_mid_mean'],1e-6); return out
