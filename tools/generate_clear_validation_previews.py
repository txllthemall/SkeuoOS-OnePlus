from __future__ import annotations

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

from generate_liquid27 import (
    ROOT, FONT_REG, GEOMETRY_FOCUS, HOME_SHOW, QUICK_NAMES,
    _paste_wallpaper_icon, _foreground_mask, render,
)
from liquid27.catalog import ICON_SPECS
from liquid27.clear_material import preview_refract_patch, clear_background, finish_clear_enclosure
from liquid27.glass_surface import enclosure_surface
from liquid27.glass_optics import composite_container

OUTDIR = ROOT / 'build/liquid27-v4/clear'


def _rails(d,w,h,light=(240,238,240),dark=(38,37,43)):
    d.arc((-320,-260,900,680),8,125,fill=light,width=6); d.arc((-200,300,1320,1200),6,126,fill=light,width=5); d.arc((250,790,1510,1820),194,316,fill=light,width=5); d.line((0,int(h*.53),w,int(h*.43)),fill=dark,width=11)


def _color_test_wallpaper(w=1080,h=1640):
    wall=Image.new('RGB',(w,h),(92,70,104)); d=ImageDraw.Draw(wall); hw=w//2; hh=h//2
    d.rectangle((0,0,hw,hh),fill=(111,75,144)); d.rectangle((hw,0,w,hh),fill=(181,70,91)); d.rectangle((0,hh,hw,h),fill=(52,102,166)); d.rectangle((hw,hh,w,h),fill=(190,112,48)); _rails(d,w,h); return wall


def _neutral_test_wallpaper(w=1080,h=1640):
    wall=Image.new('RGB',(w,h),(128,128,128)); d=ImageDraw.Draw(wall); d.rectangle((0,0,w//2,h),fill=(104,104,104)); d.rectangle((w//2,0,w,h),fill=(152,152,152)); _rails(d,w,h,light=(224,224,224),dark=(66,66,66)); return wall


def _single_wallpaper(kind,w=1080,h=1640):
    palettes={
        'warm':((102,69,49),(186,124,70),(75,49,39)), 'blue':((29,63,120),(54,112,190),(21,43,82)),
        'dark':((18,18,21),(42,43,49),(8,9,12)), 'bright':((232,229,224),(250,247,240),(207,211,218)),
        'red':((102,32,42),(198,67,78),(73,24,32)), 'cyan':((24,86,96),(53,151,165),(16,59,69)),
        'midtone':((111,91,111),(151,116,126),(84,75,91)),
    }
    base,accent,low=palettes[kind]; wall=Image.new('RGB',(w,h),base); d=ImageDraw.Draw(wall)
    d.ellipse((-280,-220,int(w*.78),int(h*.62)),fill=accent); d.ellipse((int(w*.35),int(h*.42),int(w*1.28),int(h*1.08)),fill=low)
    light=(246,244,242) if kind!='bright' else (112,112,118); dark=(25,24,28) if kind!='dark' else (180,182,188); _rails(d,w,h,light,dark); return wall


def _stress_wallpaper(w=1080,h=1640):
    wall=Image.new('RGB',(w,h),(126,126,126)); d=ImageDraw.Draw(wall)
    d.rectangle((0,0,w//2,h//2),fill=(18,18,20)); d.rectangle((w//2,0,w,h//2),fill=(240,240,240)); d.rectangle((0,h//2,w//2,h),fill=(82,82,86)); d.rectangle((w//2,h//2,w,h),fill=(168,168,172))
    for x in range(22,w,42): d.line((x,0,x,h),fill=(245,245,245) if (x//42)%2==0 else (16,16,16),width=1 if (x//42)%3 else 3)
    for y in range(35,h,65): d.line((0,y,w,y),fill=(238,238,238) if (y//65)%2==0 else (25,25,25),width=2)
    for x in range(-600,w+600,105): d.line((x,0,x+760,h),fill=(250,250,250) if (x//105)%2==0 else (12,12,12),width=2)
    for yy in range(80,430,36):
        for xx in range(650,1020,36):
            c=(18,18,18) if ((xx//36)+(yy//36))%2==0 else (238,238,238); d.rectangle((xx,yy,xx+18,yy+18),fill=c)
    for yy in range(930,1280,45):
        for xx in range(90,450,45): d.ellipse((xx,yy,xx+5,yy+5),fill=(250,250,250))
    d.arc((-320,190,1280,1120),4,174,fill=(255,255,255),width=6); d.arc((-180,610,1420,1540),186,352,fill=(12,12,12),width=6)
    d.text((70,1450),'EDGE / MID / CENTER / GLYPH',fill=(250,250,250)); return wall


def _images():
    out={}
    for name in QUICK_NAMES:
        if name in ICON_SPECS:
            bg,kind,_=ICON_SPECS[name]; out[name]=render(name,bg,kind,'clear')
    return out


def _render_grid(wall,images,names,home=False,optical=True,labels=True):
    d=ImageDraw.Draw(wall); font=ImageFont.truetype(FONT_REG,24 if home else 22); chosen=[n for n in names if n in images][:20]
    for i,name in enumerate(chosen):
        if home: x=92+(i%4)*245; y=270+(i//4)*245; size=122; ly=y+136
        else: x=72+(i%4)*250; y=90+(i//4)*270; size=126; ly=y+139
        if optical: _paste_wallpaper_icon(wall,images,name,x,y,size,'clear')
        else:
            ic=images[name].resize((size,size),Image.Resampling.LANCZOS); wall.paste(ic,(x,y),ic)
        if labels:
            label=name[6:].replace('_',' ')[:14]; box=d.textbbox((0,0),label,font=font); d.text((x+size/2-(box[2]-box[0])/2,ly),label,font=font,fill=(248,248,248))
    return wall


def _container_icon(name,size):
    c=clear_background(name); finish_clear_enclosure(c,name); return c.resize((size,size),Image.Resampling.LANCZOS)


def _container_only(optical=True):
    wall=_stress_wallpaper(); d=ImageDraw.Draw(wall); font=ImageFont.truetype(FONT_REG,22)
    for i,name in enumerate(GEOMETRY_FOCUS[:16]):
        x=72+(i%4)*250; y=90+(i//4)*270; size=126
        if optical:
            patch=wall.crop((x,y,x+size,y+size)); wall.paste(preview_refract_patch(patch),(x,y))
        ic=_container_icon(name,size); wall.paste(ic,(x,y),ic)
        lab='container'; b=d.textbbox((0,0),lab,font=font); d.text((x+63-(b[2]-b[0])/2,y+139),lab,font=font,fill=(248,248,248))
    return wall


def _glyph_only(images,optical=True):
    wall=_stress_wallpaper(); d=ImageDraw.Draw(wall); font=ImageFont.truetype(FONT_REG,22)
    names=['skeuo_github','skeuo_discord','skeuo_reddit','skeuo_google_drive','skeuo_revanced','skeuo_2gis','skeuo_gamehub','skeuo_telegram']
    for i,name in enumerate(names):
        x=72+(i%4)*250; y=180+(i//4)*500; size=126; source_mask=_foreground_mask(name); fm=source_mask.resize((size,size),Image.Resampling.LANCZOS)
        if optical:
            patch=wall.crop((x,y,x+size,y+size)); wall.paste(preview_refract_patch(patch,source_mask),(x,y))
        else:
            ic=images[name].resize((size,size),Image.Resampling.LANCZOS); actual_alpha=ImageChops.multiply(ic.getchannel('A'),fm); wall.paste(ic.convert('RGB'),(x,y),actual_alpha)
        lab=name[6:].replace('_',' '); b=d.textbbox((0,0),lab,font=font); d.text((x+63-(b[2]-b[0])/2,y+139),lab,font=font,fill=(248,248,248))
    return wall


def _material_ab(images):
    base=_stress_wallpaper(1080,1120); left=base.copy(); right=base.copy(); names=['skeuo_github','skeuo_discord','skeuo_revanced','skeuo_2gis','skeuo_gamehub','skeuo_telegram','skeuo_reddit','skeuo_google_drive']
    for i,name in enumerate(names):
        x=70+(i%4)*250; y=120+(i//4)*420; size=126; ic=images[name].resize((size,size),Image.Resampling.LANCZOS); left.paste(ic,(x,y),ic); _paste_wallpaper_icon(right,images,name,x,y,size,'clear')
    out=Image.new('RGB',(2160,1120)); out.paste(left,(0,0)); out.paste(right,(1080,0)); d=ImageDraw.Draw(out); f=ImageFont.truetype(FONT_REG,30); d.text((38,35),'STATIC ANDROID RGBA',font=f,fill=(255,255,255)); d.text((1118,35),'FULL OPTICAL SIMULATION',font=f,fill=(255,255,255)); return out


def _android_reality(images): return _material_ab(images)
def _android_static(images,kind,labels=True): return _render_grid(_single_wallpaper(kind),images,GEOMETRY_FOCUS,optical=False,labels=labels)


def _launcher_scale(images):
    wall=_neutral_test_wallpaper(1080,900); d=ImageDraw.Draw(wall); f=ImageFont.truetype(FONT_REG,24); names=['skeuo_github','skeuo_discord','skeuo_2gis','skeuo_revanced']; sizes=[48,64,72,96,128]
    for row,name in enumerate(names):
        y=90+row*190
        for col,size in enumerate(sizes):
            x=70+col*195; ic=images[name].resize((size,size),Image.Resampling.LANCZOS); wall.paste(ic,(x,y),ic); d.text((x,y+size+10),f'{size}px',font=f,fill=(245,245,245))
    return wall


def _github_lab(images):
    out=Image.new('RGB',(1080,1080),(72,72,72)); kinds=['warm','midtone','blue','dark','bright']
    names=['skeuo_github']
    for i,kind in enumerate(kinds):
        panel=_single_wallpaper(kind,360,360); ic=images['skeuo_github'].resize((190,190),Image.Resampling.LANCZOS); panel.paste(ic,(85,85),ic); out.paste(panel,((i%3)*360,(i//3)*360))
    panel=_stress_wallpaper(360,360); ic=images['skeuo_github'].resize((190,190),Image.Resampling.LANCZOS); panel.paste(ic,(85,85),ic); out.paste(panel,(720,360))
    return out


def _debug_surface(kind,size=768):
    s=enclosure_surface(size)
    if kind=='normals':
        rgb=np.stack(((s['nx']*.5+.5)*255,(s['ny']*.5+.5)*255,s['nz']*255),axis=-1); rgb*=s['inside'][...,None]; return Image.fromarray(np.clip(rgb,0,255).astype(np.uint8),'RGB')
    if kind=='fresnel':
        v=np.clip(s['fresnel']*2.4+s['fmid']*.30,0,1); return Image.fromarray(np.repeat((v*255).astype(np.uint8)[...,None],3,axis=2),'RGB')
    dummy=Image.new('RGB',(size,size),(128,128,128)); _,dx,dy,_=composite_container(dummy); mag=np.sqrt(dx*dx+dy*dy); m=np.percentile(mag[s['inside']>0],99.5); nx=np.clip(dx/max(m,1e-6),-.5,.5)+.5; ny=np.clip(dy/max(m,1e-6),-.5,.5)+.5; b=np.clip(mag/max(m,1e-6),0,1); rgb=np.stack((nx,ny,b),axis=-1)*255; rgb*=s['inside'][...,None]; return Image.fromarray(np.clip(rgb,0,255).astype(np.uint8),'RGB')


def main():
    OUTDIR.mkdir(parents=True,exist_ok=True); images=_images(); focus=list(GEOMETRY_FOCUS); diag=['skeuo_2gis','skeuo_revanced']+[n for n in focus if n not in ('skeuo_2gis','skeuo_revanced')]
    _render_grid(_color_test_wallpaper(),images,focus).save(OUTDIR/'preview_color_wallpaper.png'); _render_grid(_color_test_wallpaper(1080,1920),images,HOME_SHOW,True).save(OUTDIR/'preview_home_color.png'); _render_grid(_neutral_test_wallpaper(),images,focus).save(OUTDIR/'preview_neutral_wallpaper.png')
    for kind in ('warm','blue','dark','bright','red','cyan','midtone'): _render_grid(_single_wallpaper(kind),images,focus).save(OUTDIR/f'preview_{kind}_wallpaper.png')
    _render_grid(_stress_wallpaper(),images,diag).save(OUTDIR/'preview_refraction_stress.png'); _render_grid(_stress_wallpaper(),images,focus).save(OUTDIR/'preview_highcontrast_wallpaper.png')
    _container_only(True).save(OUTDIR/'preview_container_only.png'); _glyph_only(images,True).save(OUTDIR/'preview_glyph_glass_only.png'); _glyph_only(images,True).save(OUTDIR/'preview_glyph_secondary_lensing.png'); _material_ab(images).save(OUTDIR/'preview_material_ab.png')
    _android_reality(images).save(OUTDIR/'preview_android_reality_check.png'); _container_only(False).save(OUTDIR/'preview_android_container_only.png'); _glyph_only(images,False).save(OUTDIR/'preview_android_glyph_only.png'); _launcher_scale(images).save(OUTDIR/'preview_android_launcher_scale.png')
    for kind in ('warm','blue','dark','bright'): _android_static(images,kind).save(OUTDIR/f'preview_android_static_{kind}.png')
    _render_grid(_stress_wallpaper(),images,focus,optical=False).save(OUTDIR/'preview_android_static_highcontrast.png'); _android_reality(images).save(OUTDIR/'preview_android_material_ab.png')

    # Readability gates: real production RGBA only, no labels and no optical simulation.
    _github_lab(images).save(OUTDIR/'preview_github_material_lab.png')
    reps=['skeuo_github','skeuo_telegram','skeuo_discord','skeuo_reddit','skeuo_google_drive','skeuo_gmail','skeuo_twitter','skeuo_snapchat','skeuo_gamehub']
    _render_grid(_single_wallpaper('midtone'),images,reps,optical=False,labels=False).save(OUTDIR/'preview_representative_NO_LABELS.png')
    for kind in ('dark','bright','midtone','warm','blue'):
        _render_grid(_single_wallpaper(kind),images,focus,optical=False,labels=False).save(OUTDIR/f'preview_pack_{kind}_NO_LABELS.png')
    _render_grid(_single_wallpaper('midtone',1080,1920),images,HOME_SHOW,True,optical=False,labels=False).save(OUTDIR/'preview_android_realistic_home_NO_LABELS.png')

    _debug_surface('normals').save(OUTDIR/'preview_surface_normals.png'); _debug_surface('flow').save(OUTDIR/'preview_optical_flow.png'); _debug_surface('fresnel').save(OUTDIR/'preview_fresnel_field.png')
    print('Generated full optical + static Android + no-label readability diagnostics.')


if __name__=='__main__': main()
