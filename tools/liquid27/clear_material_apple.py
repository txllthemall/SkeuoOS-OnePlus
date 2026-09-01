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
from .glass_surface import enclosure_surface, glyph_surface
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
    flip = -1.0 if (_seed(key, 409) & 1) else 1.0
    lx, ly, lz = -.50 * flip, -.72, .48
    lm = (lx*lx + ly*ly + lz*lz) ** .5
    lx,ly,lz = lx/lm,ly/lm,lz/lm
    hx,hy,hz = lx,ly,lz+1.0
    hm=(hx*hx+hy*hy+hz*hz)**.5
    hx,hy,hz=hx/hm,hy/hm,hz/hm
    ndoth=np.clip(s['nx']*hx+s['ny']*hy+s['nz']*hz,0,1)
    power=28.0 if reflection_style(key)==1 else 22.0
    spec=(ndoth**power)*np.clip(s['fmid']*1.7+s['ftight']*1.9,0,1)
    return _mask(np.clip(spec*.62,0,.48))


def clear_reflection_coverage_pct(key: str) -> float:
    a=np.asarray(clear_reflection_mask(key),dtype=np.float32)/255.0
    return float(a.mean()*100.0)


@lru_cache(maxsize=1)
def _static_enclosure_fields():
    """Wallpaper-independent Android illusion of thick neutral glass."""
    s=enclosure_surface(WORK)
    # The body is intentionally extremely clear. Optical thickness is encoded
    # mostly in alpha topology around curved regions instead of a white plate.
    body=(.010 + .024*s['mid'] + .050*s['fsoft'] + .095*s['fmid'] + .165*s['ftight']) * s['inside']
    inner_interface=np.clip((s['edge']**1.35)*(.030+.070*s['fmid']),0,.105)
    density=np.clip(body+inner_interface,0,.25)

    lx,ly,lz=-.52,-.70,.49
    lm=(lx*lx+ly*ly+lz*lz)**.5; lx,ly,lz=lx/lm,ly/lm,lz/lm
    hx,hy,hz=lx,ly,lz+1.; hm=(hx*hx+hy*hy+hz*hz)**.5; hx,hy,hz=hx/hm,hy/hm,hz/hm
    ndoth=np.clip(s['nx']*hx+s['ny']*hy+s['nz']*hz,0,1)
    spec=(ndoth**30.)*np.clip(s['fmid']*1.4+s['ftight']*2.0,0,1)
    spec=np.clip(spec*.55,0,.42)

    opposite=np.clip(-(s['nx']*lx+s['ny']*ly),0,1)**2.8
    dark=np.clip(opposite*(.025*s['edge']+.095*s['fmid']+.060*s['ftight']),0,.12)
    return _mask(density), _mask(spec), _mask(dark)


def _glyph_static_density(mask: Image.Image):
    """Static Android glyph: low-alpha interior, denser curved boundary."""
    broad=mask.filter(ImageFilter.GaussianBlur(7.0))
    inner=inner_edge(mask,11).filter(ImageFilter.GaussianBlur(4.5))
    tight=inner_edge(mask,3.0).filter(ImageFilter.GaussianBlur(.8))
    body=Image.new('L',(WORK,WORK),70)
    field=ImageChops.add(body,inner.point(lambda v:int(v*.22)))
    field=ImageChops.add(field,tight.point(lambda v:int(v*.42)))
    # Broad interior remains translucent rather than becoming an opaque logo.
    field=ImageChops.add(field,broad.point(lambda v:int(v*.035)))
    return inter(field,mask)


def clearify_layers(layers, key: str):
    """Convert logo geometry into a wallpaper-agnostic static glass glyph."""
    result=[]
    flip=-1 if (_seed(key,503)&1) else 1
    for src in layers:
        item=dict(src); mask=item['mask']; src_luma=luminance(item.get('fill','#fff'))
        item['mask']=_glyph_static_density(mask)
        item['material']='glass'
        item['fill']='#cfcfcf' if src_luma<145 else '#dedede'
        item['opacity']=.090 if src_luma<145 else .105
        item['refraction']=max(.16,min(.23,float(item.get('refraction',.07))*1.9))
        item['specular']='off'; item['shadow']=0.00005; item['blur']=0; item['blend']='normal'
        result.append(item)

        # Thin directional interface cues survive launcher scaling. These are
        # geometry-linked edges, not a white body or decorative shine blob.
        top=top_facing_edge(mask,2.2).filter(ImageFilter.GaussianBlur(.45)).point(lambda v:int(v*.48))
        if top.getbbox(): result.append(layer(top,'#ffffff',.20,0,'off',0,'ink','screen',(0,0),0,0,0))
        inner=inner_edge(mask,2.0).filter(ImageFilter.GaussianBlur(.6)).point(lambda v:int(v*.18))
        if inner.getbbox(): result.append(layer(inner,'#f0f0f0',.085,0,'off',0,'ink','screen',(0,0),0,0,0))
        low=bottom_facing_edge(mask,1.7).filter(ImageFilter.GaussianBlur(.35)).point(lambda v:int(v*.34))
        if low.getbbox(): result.append(layer(low,'#242424',.13,0,'off',0,'ink','multiply',(0,0),0,0,0))
    return result


def clear_background(key: str) -> Image.Image:
    canvas=Image.new('RGBA',(WORK,WORK),(0,0,0,0))
    density,spec,dark=_static_enclosure_fields()
    neutral=Image.new('RGBA',(WORK,WORK),(224,224,224,0)); neutral.putalpha(density); canvas.alpha_composite(neutral)
    # Base directional specular from surface normals, then a small per-icon
    # variation of the same physical light model.
    white=Image.new('RGBA',(WORK,WORK),(255,255,255,0)); white.putalpha(ImageChops.lighter(spec,clear_reflection_mask(key))); canvas.alpha_composite(white)
    dk=Image.new('RGBA',(WORK,WORK),(28,28,28,0)); dk.putalpha(dark); canvas.alpha_composite(dk)
    return canvas


def finish_clear_enclosure(canvas: Image.Image, key: str) -> None:
    # Hairline is restrained; glass thickness must read from alpha topology,
    # not from a thick white outline.
    hair=outer_edge(ENCL,.72).point(lambda v:int(v*.115))
    h=Image.new('RGBA',(WORK,WORK),(246,246,246,0)); h.putalpha(hair); canvas.alpha_composite(h)
    dark=outer_edge(ENCL,.58).point(lambda v:int(v*.034))
    d=Image.new('RGBA',(WORK,WORK),(28,28,28,0)); d.putalpha(dark); canvas.alpha_composite(d)
    canvas.putalpha(inter(canvas.getchannel('A'),ENCL))


def preview_refract_patch(under: Image.Image, foreground_mask: Image.Image | None = None) -> Image.Image:
    result,_,_,_=composite_container(under.convert('RGB'))
    if foreground_mask is not None and foreground_mask.getbbox():
        result,_,_,_=composite_glyph(result,foreground_mask)
    return result


@lru_cache(maxsize=1)
def _metric_base():
    s=enclosure_surface(128)
    # Recreate the actual normal-derived preview flow once for QA metrics.
    dummy=Image.new('RGB',(128,128),(128,128,128))
    _,dx,dy,_=composite_container(dummy)
    disp=np.sqrt(dx*dx+dy*dy)
    center=s['q']<.34; mid=(s['q']>=.46)&(s['q']<.72); edge=(s['q']>=.84)&(s['q']<=1.0)
    dens=np.asarray(_static_enclosure_fields()[0].resize((128,128),Image.Resampling.LANCZOS),dtype=np.float32)
    return {
        'enclosure_center_density':float(dens[center].mean()),
        'enclosure_edge_density':float(dens[edge].mean()),
        'specular_coverage_pct':float((s['fmid']>.12).mean()*100),
        'refraction_displacement_mean':float(disp[s['inside']>0].mean()),
        'refraction_displacement_median':float(np.median(disp[s['inside']>0])),
        'refraction_displacement_max':float(disp.max()),
        'refraction_center_mean':float(disp[center].mean()),
        'refraction_mid_mean':float(disp[mid].mean()),
        'refraction_edge_mean':float(disp[edge].mean()),
        'fresnel_center_mean':float(s['fresnel'][center].mean()),
        'fresnel_edge_mean':float(s['fresnel'][edge].mean()),
    }


def material_metrics(key: str) -> dict:
    out=dict(_metric_base())
    out['reflection_coverage_pct']=clear_reflection_coverage_pct(key)
    out['edge_center_density_ratio']=out['enclosure_edge_density']/max(out['enclosure_center_density'],1e-6)
    out['edge_mid_displacement_ratio']=out['refraction_edge_mean']/max(out['refraction_mid_mean'],1e-6)
    return out
