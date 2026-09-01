from __future__ import annotations

"""Liquid Glass material bridge.

Preview mode uses a coherent normal/thickness/IOR optical model over the real
wallpaper. Production Android remains a neutral RGBA asset and encodes only
wallpaper-independent glass cues.
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
    s=enclosure_surface(WORK); flip=-1.0 if (_seed(key,409)&1) else 1.0
    lx,ly,lz=-.50*flip,-.72,.48; lm=(lx*lx+ly*ly+lz*lz)**.5; lx,ly,lz=lx/lm,ly/lm,lz/lm
    hx,hy,hz=lx,ly,lz+1.; hm=(hx*hx+hy*hy+hz*hz)**.5; hx,hy,hz=hx/hm,hy/hm,hz/hm
    ndoth=np.clip(s['nx']*hx+s['ny']*hy+s['nz']*hz,0,1); power=30. if reflection_style(key)==1 else 24.
    spec=(ndoth**power)*np.clip(s['fmid']*1.65+s['ftight']*1.90,0,1)
    return _mask(np.clip(spec*(.52 if reflection_style(key)==1 else .62),0,.46))


def clear_reflection_coverage_pct(key: str) -> float:
    return float((np.asarray(clear_reflection_mask(key),dtype=np.float32)/255.).mean()*100.)


@lru_cache(maxsize=1)
def _static_enclosure_fields():
    s=enclosure_surface(WORK)
    body=(.008+.020*s['mid']+.044*s['fsoft']+.088*s['fmid']+.150*s['ftight'])*s['inside']
    inner_interface=np.clip((s['edge']**1.35)*(.028+.068*s['fmid']),0,.10); density=np.clip(body+inner_interface,0,.23)
    lx,ly,lz=-.52,-.70,.49; lm=(lx*lx+ly*ly+lz*lz)**.5; lx,ly,lz=lx/lm,ly/lm,lz/lm
    hx,hy,hz=lx,ly,lz+1.; hm=(hx*hx+hy*hy+hz*hz)**.5; hx,hy,hz=hx/hm,hy/hm,hz/hm
    ndoth=np.clip(s['nx']*hx+s['ny']*hy+s['nz']*hz,0,1); spec=(ndoth**32.)*np.clip(s['fmid']*1.35+s['ftight']*2.0,0,1); spec=np.clip(spec*.50,0,.40)
    opposite=np.clip(-(s['nx']*lx+s['ny']*ly),0,1)**2.7; dark=np.clip(opposite*(.045*s['edge']+.13*s['fmid']+.075*s['ftight']),0,.16)
    return _mask(density),_mask(spec),_mask(dark)


def _glyph_static_density(mask: Image.Image):
    broad=mask.filter(ImageFilter.GaussianBlur(7.0)); inner=inner_edge(mask,11).filter(ImageFilter.GaussianBlur(4.5)); tight=inner_edge(mask,3.0).filter(ImageFilter.GaussianBlur(.8))
    body=Image.new('L',(WORK,WORK),54); field=ImageChops.add(body,inner.point(lambda v:int(v*.16))); field=ImageChops.add(field,tight.point(lambda v:int(v*.31))); field=ImageChops.add(field,broad.point(lambda v:int(v*.026)))
    return inter(field,mask)


def clearify_layers(layers,key:str):
    """Static Android glyphs use dual-contrast interfaces, not a white body."""
    result=[]
    for src in layers:
        item=dict(src); mask=item['mask']; src_luma=luminance(item.get('fill','#fff'))
        item['mask']=_glyph_static_density(mask); item['material']='glass'; item['fill']='#bcbcbc' if src_luma<145 else '#cecece'; item['opacity']=.068 if src_luma<145 else .080
        item['refraction']=max(.15,min(.22,float(item.get('refraction',.07))*1.8)); item['specular']='off'; item['shadow']=0.00004; item['blur']=0; item['blend']='normal'; result.append(item)
        top=top_facing_edge(mask,2.0).filter(ImageFilter.GaussianBlur(.42)).point(lambda v:int(v*.42))
        if top.getbbox(): result.append(layer(top,'#ffffff',.145,0,'off',0,'ink','screen',(0,0),0,0,0))
        inner=inner_edge(mask,1.8).filter(ImageFilter.GaussianBlur(.58)).point(lambda v:int(v*.15))
        if inner.getbbox(): result.append(layer(inner,'#ededed',.060,0,'off',0,'ink','screen',(0,0),0,0,0))
        low=bottom_facing_edge(mask,2.1).filter(ImageFilter.GaussianBlur(.42)).point(lambda v:int(v*.52))
        if low.getbbox(): result.append(layer(low,'#171717',.245,0,'off',0,'ink','multiply',(0,0),0,0,0))
    return result


def clear_background(key:str)->Image.Image:
    canvas=Image.new('RGBA',(WORK,WORK),(0,0,0,0)); density,spec,dark=_static_enclosure_fields()
    neutral=Image.new('RGBA',(WORK,WORK),(218,218,218,0)); neutral.putalpha(density); canvas.alpha_composite(neutral)
    white=Image.new('RGBA',(WORK,WORK),(255,255,255,0)); white.putalpha(ImageChops.lighter(spec,clear_reflection_mask(key))); canvas.alpha_composite(white)
    dk=Image.new('RGBA',(WORK,WORK),(24,24,24,0)); dk.putalpha(dark); canvas.alpha_composite(dk); return canvas


def finish_clear_enclosure(canvas:Image.Image,key:str)->None:
    hair=outer_edge(ENCL,.70).point(lambda v:int(v*.095)); h=Image.new('RGBA',(WORK,WORK),(246,246,246,0)); h.putalpha(hair); canvas.alpha_composite(h)
    # Two neutral interfaces are deliberately asymmetric so the same RGBA asset
    # keeps contrast on both near-black and near-white wallpapers.
    low=bottom_facing_edge(ENCL,1.35).filter(ImageFilter.GaussianBlur(.35)).point(lambda v:int(v*.22)); d=Image.new('RGBA',(WORK,WORK),(20,20,20,0)); d.putalpha(low); canvas.alpha_composite(d)
    dark=outer_edge(ENCL,.55).point(lambda v:int(v*.028)); dd=Image.new('RGBA',(WORK,WORK),(24,24,24,0)); dd.putalpha(dark); canvas.alpha_composite(dd)
    canvas.putalpha(inter(canvas.getchannel('A'),ENCL))


def preview_refract_patch(under:Image.Image,foreground_mask:Image.Image|None=None)->Image.Image:
    result,_,_,_=composite_container(under.convert('RGB'))
    if foreground_mask is not None and foreground_mask.getbbox(): result,_,_,_=composite_glyph(result,foreground_mask)
    return result


@lru_cache(maxsize=1)
def _metric_base():
    s=enclosure_surface(128); dummy=Image.new('RGB',(128,128),(128,128,128)); _,dx,dy,_=composite_container(dummy); disp=np.sqrt(dx*dx+dy*dy)
    center=s['q']<.34; mid=(s['q']>=.46)&(s['q']<.72); edge=(s['q']>=.84)&(s['q']<=1.0); dens=np.asarray(_static_enclosure_fields()[0].resize((128,128),Image.Resampling.LANCZOS),dtype=np.float32)
    return {'enclosure_center_density':float(dens[center].mean()),'enclosure_edge_density':float(dens[edge].mean()),'specular_coverage_pct':float((s['fmid']>.12).mean()*100),'refraction_displacement_mean':float(disp[s['inside']>0].mean()),'refraction_displacement_median':float(np.median(disp[s['inside']>0])),'refraction_displacement_max':float(disp.max()),'refraction_center_mean':float(disp[center].mean()),'refraction_mid_mean':float(disp[mid].mean()),'refraction_edge_mean':float(disp[edge].mean()),'fresnel_center_mean':float(s['fresnel'][center].mean()),'fresnel_edge_mean':float(s['fresnel'][edge].mean())}


def material_metrics(key:str)->dict:
    out=dict(_metric_base()); out['reflection_coverage_pct']=clear_reflection_coverage_pct(key); out['edge_center_density_ratio']=out['enclosure_edge_density']/max(out['enclosure_center_density'],1e-6); out['edge_mid_displacement_ratio']=out['refraction_edge_mean']/max(out['refraction_mid_mean'],1e-6); return out
