from pathlib import Path
from PIL import Image, ImageDraw, ImageOps, ImageFont
import math, json
from liquid27.material import *
from liquid27.glyphs import glyph
from liquid27.glyphs_v4 import glyph_v4
from liquid27.glyphs_v4_extra import glyph_v4_extra
from liquid27.glyphs_vector import glyph_vector, VECTOR_KINDS
from liquid27.glyphs_vector_tuned import glyph_vector_tuned
from liquid27.catalog import ICON_SPECS

ROOT=Path(__file__).resolve().parents[1]


def layers_for(kind):
    return glyph_vector_tuned(kind) or glyph_vector(kind) or glyph_v4(kind) or glyph_v4_extra(kind) or glyph(kind)


def render(name,bgspec,kind):
    canvas=Image.new('RGBA',(WORK,WORK),(0,0,0,0))
    canvas.alpha_composite(background(bgspec))
    for lay in layers_for(kind):
        composite_layer(canvas,**lay)
    finish_enclosure(canvas)
    canvas.putalpha(ENCL)
    return canvas.resize((OUT,OUT),Image.Resampling.LANCZOS)


def output_paths():
    return ROOT/'app/src/main/res/drawable-nodpi', ROOT/'build/liquid27-v4', ROOT/'docs'


def preview(images, outdir):
    show=['skeuo_phone','skeuo_messages','skeuo_camera','skeuo_photos','skeuo_settings','skeuo_mail','skeuo_gmail','skeuo_maps','skeuo_clock','skeuo_weather','skeuo_notes','skeuo_calendar','skeuo_appstore','skeuo_telegram','skeuo_discord','skeuo_youtube','skeuo_revanced','skeuo_chrome','skeuo_spotify','skeuo_instagram','skeuo_soundcloud','skeuo_kaspi','skeuo_2gis','skeuo_chatgpt','skeuo_gamehub']
    font=ImageFont.truetype(FONT_REG,18)
    def sheet(name,bg,names=show,cols=5,icon_size=132):
        cell=190; rows=math.ceil(len(names)/cols); W=cols*cell+60; H=rows*210+60
        can=Image.new('RGB',(W,H),rgb(bg)); d=ImageDraw.Draw(can); fg=(235,235,238) if luminance(bg)<128 else (34,34,38)
        for i,n in enumerate(names):
            x=30+(i%cols)*cell; y=30+(i//cols)*210; ic=images[n].resize((icon_size,icon_size),Image.Resampling.LANCZOS); can.paste(ic,(x+(cell-icon_size)//2,y),ic)
            label=n[6:].replace('_',' ')[:16]; b=d.textbbox((0,0),label,font=font); d.text((x+cell/2-(b[2]-b[0])/2,y+145),label,font=font,fill=fg)
        can.save(outdir/name)
    sheet('preview_light.png','#eff0f3'); sheet('preview_dark.png','#17181c')

    vector_names=[name for name,(_,kind,_) in ICON_SPECS.items() if kind in VECTOR_KINDS]
    sheet('preview_vector_reference.png','#17181c',vector_names,cols=4,icon_size=144)

    all_names=list(images.keys()); cols_all=6; cell_all=170; row_h=190; rows_all=math.ceil(len(all_names)/cols_all)
    full=Image.new('RGB',(cols_all*cell_all+60,rows_all*row_h+60),rgb('#17181c')); fd=ImageDraw.Draw(full); ff=ImageFont.truetype(FONT_REG,16)
    for i,n in enumerate(all_names):
        x=30+(i%cols_all)*cell_all; y=30+(i//cols_all)*row_h; ic=images[n].resize((118,118),Image.Resampling.LANCZOS); full.paste(ic,(x+26,y),ic)
        label=n[6:].replace('_',' ')[:17]; b=fd.textbbox((0,0),label,font=ff); fd.text((x+85-(b[2]-b[0])/2,y+132),label,font=ff,fill=(238,238,242))
    full.save(outdir/'preview_full.png')

    W,H=1080,1280; wall=Image.new('RGB',(W,H),'#171326')
    for col,xy,rad in [('#7f335f',(240,280),600),('#233b8a',(850,260),650),('#693b22',(800,970),650)]:
        m=Image.radial_gradient('L').resize((rad,rad)); m=ImageOps.invert(m).point(lambda v:int(v*.65))
        fm=Image.new('L',(W,H),0); fm.paste(m,(xy[0]-rad//2,xy[1]-rad//2)); wall=Image.composite(Image.new('RGB',(W,H),rgb(col)),wall,fm)
    d=ImageDraw.Draw(wall); font2=ImageFont.truetype(FONT_REG,22)
    for i,n in enumerate(show[:20]):
        x=75+(i%4)*245; y=110+(i//4)*220; ic=images[n].resize((116,116),Image.Resampling.LANCZOS); wall.paste(ic,(x,y),ic)
        label=n[6:].replace('_',' ')[:12]; b=d.textbbox((0,0),label,font=font2); d.text((x+58-(b[2]-b[0])/2,y+126),label,font=font2,fill=(245,245,248))
    wall.save(outdir/'preview_wallpaper.png')

    hs=Image.new('RGB',(1080,1920),(235,236,240)); d=ImageDraw.Draw(hs); f=ImageFont.truetype(FONT_REG,24)
    for i,n in enumerate(show[:20]):
        x=93+(i%4)*245; y=300+(i//4)*240; ic=images[n].resize((122,122),Image.Resampling.LANCZOS); hs.paste(ic,(x,y),ic)
        label=n[6:].replace('_',' ')[:12]; b=d.textbbox((0,0),label,font=f); d.text((x+61-(b[2]-b[0])/2,y+135),label,font=f,fill=(35,35,40))
    hs.save(outdir/'preview_home.png')


def qa(images, outdir):
    rows=[]
    for name,(bg,kind,defaults) in ICON_SPECS.items():
        layers=layers_for(kind); fg=blank_mask()
        for l in layers: fg=union(fg,l['mask'])
        bb=fg.getbbox(); coverage=sum(fg.getdata())/(255*WORK*WORK)
        if bb:
            cx=(bb[0]+bb[2])/2; cy=(bb[1]+bb[3])/2; off=((cx-WORK/2)/WORK,(cy-WORK/2)/WORK)
        else: off=(0,0)
        im=images[name].convert('RGB').resize((64,64)); vals=[.2126*r+.7152*g+.0722*b for r,g,b in im.getdata()]
        rows.append({'icon':name,'kind':kind,'geometry_engine':'svg2048' if kind in VECTOR_KINDS else 'legacy','foreground_bbox':bb,'coverage_pct':round(coverage*100,1),'center_offset_pct':[round(off[0]*100,1),round(off[1]*100,1)],'mean_luminance':round(sum(vals)/len(vals),1),'contrast_estimate':round((max(vals)-min(vals))/255,3)})
    (outdir/'qa.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    with (outdir/'qa.tsv').open('w',encoding='utf-8') as f:
        f.write('icon\tkind\tgeometry_engine\tforeground_bbox\tcoverage_pct\tcenter_offset_pct\tmean_luminance\tcontrast_estimate\n')
        for r in rows: f.write(f"{r['icon']}\t{r['kind']}\t{r['geometry_engine']}\t{r['foreground_bbox']}\t{r['coverage_pct']}\t{r['center_offset_pct']}\t{r['mean_luminance']}\t{r['contrast_estimate']}\n")
    bad=[r for r in rows if r['coverage_pct']<5 or r['coverage_pct']>70 or abs(r['center_offset_pct'][0])>16 or abs(r['center_offset_pct'][1])>16]
    if bad: print('QA WARN:',len(bad),'composition outliers; see qa.tsv')
    return rows


def main():
    res,outdir,docs=output_paths(); res.mkdir(parents=True,exist_ok=True); outdir.mkdir(parents=True,exist_ok=True); docs.mkdir(parents=True,exist_ok=True)
    for p in res.glob('skeuo_*.png'): p.unlink()
    images={}
    for name,(bg,kind,defaults) in ICON_SPECS.items():
        im=render(name,bg,kind); im.save(res/f'{name}.png',optimize=True); images[name]=im
    preview(images,outdir); rows=qa(images,outdir)
    launch=render('skeuo_settings',ICON_SPECS['skeuo_settings'][0],'settings')
    for dens,size in [('mdpi',48),('hdpi',72),('xhdpi',96),('xxhdpi',144),('xxxhdpi',192)]:
        d=ROOT/f'app/src/main/res/mipmap-{dens}'; d.mkdir(parents=True,exist_ok=True); launch.resize((size,size),Image.Resampling.LANCZOS).save(d/'ic_launcher.png')
    vector_count=sum(1 for r in rows if r['geometry_engine']=='svg2048')
    print(f'Liquid27 v4: generated {len(images)} icons; {vector_count} true SVG reference glyphs; previews + QA in {outdir}')


if __name__=='__main__':
    main()
