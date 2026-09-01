from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from generate_liquid27 import (
    ROOT, FONT_REG, GEOMETRY_FOCUS, HOME_SHOW, QUICK_NAMES,
    _paste_wallpaper_icon, _foreground_mask, render,
)
from liquid27.catalog import ICON_SPECS
from liquid27.clear_material import preview_refract_patch, clear_background, finish_clear_enclosure
from liquid27.material import WORK

OUTDIR = ROOT / 'build/liquid27-v4/clear'


def _rails(d, w, h, light=(240,238,240), dark=(38,37,43)):
    d.arc((-320,-260,900,680),8,125,fill=light,width=6)
    d.arc((-200,300,1320,1200),6,126,fill=light,width=5)
    d.arc((250,790,1510,1820),194,316,fill=light,width=5)
    d.line((0,int(h*.53),w,int(h*.43)),fill=dark,width=11)


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
    }
    base,accent,low=palettes[kind]; wall=Image.new('RGB',(w,h),base); d=ImageDraw.Draw(wall)
    d.ellipse((-280,-220,int(w*.78),int(h*.62)),fill=accent); d.ellipse((int(w*.35),int(h*.42),int(w*1.28),int(h*1.08)),fill=low)
    light=(246,244,242) if kind!='bright' else (112,112,118); dark=(25,24,28) if kind!='dark' else (180,182,188); _rails(d,w,h,light,dark); return wall


def _stress_wallpaper(w=1080,h=1640):
    wall=Image.new('RGB',(w,h),(126,126,126)); d=ImageDraw.Draw(wall)
    d.rectangle((0,0,w//2,h//2),fill=(18,18,20)); d.rectangle((w//2,0,w,h//2),fill=(240,240,240)); d.rectangle((0,h//2,w//2,h),fill=(82,82,86)); d.rectangle((w//2,h//2,w,h),fill=(168,168,172))
    for x in range(22,w,54): d.line((x,0,x,h),fill=(245,245,245) if (x//54)%2==0 else (16,16,16),width=2)
    for y in range(35,h,75): d.line((0,y,w,y),fill=(238,238,238) if (y//75)%2==0 else (25,25,25),width=2)
    for x in range(-500,w+500,120): d.line((x,0,x+700,h),fill=(250,250,250) if (x//120)%2==0 else (12,12,12),width=3)
    for yy in range(80,430,44):
        for xx in range(650,1020,44):
            if ((xx//44)+(yy//44))%2==0: d.rectangle((xx,yy,xx+21,yy+21),fill=(20,20,20))
    d.arc((-320,190,1280,1120),4,174,fill=(255,255,255),width=7); d.arc((-180,610,1420,1540),186,352,fill=(12,12,12),width=7)
    d.text((70,1450),'EDGE / MID / CENTER / GLYPH',fill=(250,250,250)); return wall


def _images():
    out={}
    for name in QUICK_NAMES:
        if name in ICON_SPECS:
            bg,kind,_=ICON_SPECS[name]; out[name]=render(name,bg,kind,'clear')
    return out


def _render_grid(wall,images,names,home=False):
    d=ImageDraw.Draw(wall); font=ImageFont.truetype(FONT_REG,24 if home else 22); chosen=[n for n in names if n in images][:20]
    for i,name in enumerate(chosen):
        if home: x=92+(i%4)*245; y=270+(i//4)*245; size=122; ly=y+136
        else: x=72+(i%4)*250; y=90+(i//4)*270; size=126; ly=y+139
        _paste_wallpaper_icon(wall,images,name,x,y,size,'clear'); label=name[6:].replace('_',' ')[:14]; box=d.textbbox((0,0),label,font=font); d.text((x+size/2-(box[2]-box[0])/2,ly),label,font=font,fill=(248,248,248))
    return wall


def _container_icon(name,size):
    c=clear_background(name); finish_clear_enclosure(c,name); return c.resize((size,size),Image.Resampling.LANCZOS)


def _container_only_preview(images):
    wall=_stress_wallpaper(); d=ImageDraw.Draw(wall); font=ImageFont.truetype(FONT_REG,22)
    names=[n for n in GEOMETRY_FOCUS if n in images][:16]
    for i,name in enumerate(names):
        x=72+(i%4)*250; y=90+(i//4)*270; size=126
        patch=wall.crop((x,y,x+size,y+size)); wall.paste(preview_refract_patch(patch), (x,y)); ic=_container_icon(name,size); wall.paste(ic,(x,y),ic)
        lab='container'; b=d.textbbox((0,0),lab,font=font); d.text((x+63-(b[2]-b[0])/2,y+139),lab,font=font,fill=(248,248,248))
    return wall


def _glyph_only_preview(images):
    # Uses the true glyph refraction but intentionally omits the static enclosure layer.
    wall=_stress_wallpaper(); d=ImageDraw.Draw(wall); font=ImageFont.truetype(FONT_REG,22)
    names=['skeuo_github','skeuo_discord','skeuo_reddit','skeuo_google_drive','skeuo_revanced','skeuo_2gis','skeuo_gamehub','skeuo_telegram']
    for i,name in enumerate(names):
        x=72+(i%4)*250; y=180+(i//4)*500; size=126
        patch=wall.crop((x,y,x+size,y+size)); wall.paste(preview_refract_patch(patch,_foreground_mask(name)),(x,y))
        # Composite the glyph-bearing icon but remove most enclosure alpha by using foreground mask.
        ic=images[name].resize((size,size),Image.Resampling.LANCZOS); fm=_foreground_mask(name).resize((size,size),Image.Resampling.LANCZOS); wall.paste(ic,(x,y),fm)
        lab=name[6:].replace('_',' '); b=d.textbbox((0,0),lab,font=font); d.text((x+63-(b[2]-b[0])/2,y+139),lab,font=font,fill=(248,248,248))
    return wall


def _material_ab(images):
    base=_stress_wallpaper(1080,1120); left=base.copy(); right=base.copy(); names=['skeuo_github','skeuo_discord','skeuo_revanced','skeuo_2gis','skeuo_gamehub','skeuo_telegram','skeuo_reddit','skeuo_google_drive']
    # A: static alpha compositing only. B: current coherent live-background optics.
    for i,name in enumerate(names):
        x=70+(i%4)*250; y=120+(i//4)*420; size=126; ic=images[name].resize((size,size),Image.Resampling.LANCZOS); left.paste(ic,(x,y),ic); _paste_wallpaper_icon(right,images,name,x,y,size,'clear')
    out=Image.new('RGB',(2160,1120)); out.paste(left,(0,0)); out.paste(right,(1080,0)); d=ImageDraw.Draw(out); f=ImageFont.truetype(FONT_REG,34); d.text((40,35),'A  static compositing',font=f,fill=(255,255,255)); d.text((1120,35),'B  coherent Liquid Glass optics',font=f,fill=(255,255,255)); return out


def main():
    OUTDIR.mkdir(parents=True,exist_ok=True); images=_images(); focus=list(GEOMETRY_FOCUS); diag=['skeuo_2gis','skeuo_revanced']+[n for n in focus if n not in ('skeuo_2gis','skeuo_revanced')]
    _render_grid(_color_test_wallpaper(),images,focus).save(OUTDIR/'preview_color_wallpaper.png'); _render_grid(_color_test_wallpaper(1080,1920),images,HOME_SHOW,True).save(OUTDIR/'preview_home_color.png'); _render_grid(_neutral_test_wallpaper(),images,focus).save(OUTDIR/'preview_neutral_wallpaper.png')
    for kind in ('warm','blue','dark','bright','red','cyan'): _render_grid(_single_wallpaper(kind),images,focus).save(OUTDIR/f'preview_{kind}_wallpaper.png')
    _render_grid(_stress_wallpaper(),images,diag).save(OUTDIR/'preview_refraction_stress.png'); _render_grid(_stress_wallpaper(),images,focus).save(OUTDIR/'preview_highcontrast_wallpaper.png')
    _container_only_preview(images).save(OUTDIR/'preview_container_only.png'); _glyph_only_preview(images).save(OUTDIR/'preview_glyph_glass_only.png'); _material_ab(images).save(OUTDIR/'preview_material_ab.png')
    print('Generated expanded Clear optical/material diagnostics.')


if __name__=='__main__': main()
