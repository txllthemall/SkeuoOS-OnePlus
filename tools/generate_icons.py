from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json, math, os

ROOT = Path(__file__).resolve().parents[1]

def find_font(bold=False):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'

FONT_BOLD = find_font(True)
FONT_REG = find_font(False)

def rgb(h):
    h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))

def mix(c1,c2,t): return tuple(int(a+(b-a)*t) for a,b in zip(c1,c2))

def rounded_icon(top, bottom, glyph='text', text='', fg='#ffffff', accent=None):
    S=512; pad=28; r=112
    base=Image.new('RGBA',(S,S),(0,0,0,0))
    # shadow
    shadow=Image.new('RGBA',(S,S),(0,0,0,0)); sd=ImageDraw.Draw(shadow)
    sd.rounded_rectangle((pad+3,pad+10,S-pad+3,S-pad+10), radius=r, fill=(0,0,0,150))
    shadow=shadow.filter(ImageFilter.GaussianBlur(18)); base.alpha_composite(shadow)
    # mask + gradient
    mask=Image.new('L',(S,S),0); md=ImageDraw.Draw(mask)
    md.rounded_rectangle((pad,pad,S-pad,S-pad), radius=r, fill=255)
    grad=Image.new('RGBA',(S,S))
    p=grad.load(); c1=rgb(top); c2=rgb(bottom)
    for y in range(S):
        t=max(0,min(1,(y-pad)/(S-2*pad)))
        c=mix(c1,c2,t)
        for x in range(S): p[x,y]=(*c,255)
    grad.putalpha(mask); base.alpha_composite(grad)
    d=ImageDraw.Draw(base)
    # inner bevel/border
    d.rounded_rectangle((pad+2,pad+2,S-pad-2,S-pad-2), radius=r-2, outline=(255,255,255,105), width=4)
    d.rounded_rectangle((pad+8,pad+8,S-pad-8,S-pad-8), radius=r-8, outline=(0,0,0,70), width=3)
    # glossy top
    gloss=Image.new('RGBA',(S,S),(0,0,0,0)); gd=ImageDraw.Draw(gloss)
    gloss_mask=Image.new('L',(S,S),0); gm=ImageDraw.Draw(gloss_mask)
    gm.rounded_rectangle((pad+12,pad+10,S-pad-12,S//2+40), radius=r-15, fill=170)
    gloss_mask=gloss_mask.filter(ImageFilter.GaussianBlur(10))
    gloss.putalpha(gloss_mask)
    white=Image.new('RGBA',(S,S),(255,255,255,65)); white.putalpha(gloss_mask.point(lambda v:int(v*0.26)))
    base.alpha_composite(white)
    # glyph shadow layer
    gshadow=Image.new('RGBA',(S,S),(0,0,0,0)); gs=ImageDraw.Draw(gshadow)
    g=ImageDraw.Draw(base)
    F=rgb(fg)
    def text_center(txt, size=180, yoff=0, font_path=FONT_BOLD, fill=F):
        font=ImageFont.truetype(font_path,size)
        bbox=g.textbbox((0,0),txt,font=font,stroke_width=0)
        x=(S-(bbox[2]-bbox[0]))/2; y=(S-(bbox[3]-bbox[1]))/2-bbox[1]+yoff
        # shadow
        gs.text((x+5,y+7),txt,font=font,fill=(0,0,0,100))
        g.text((x,y),txt,font=font,fill=(*fill,255))
    # shape glyphs
    if glyph=='text': text_center(text or '?', 180 if len(text)<=2 else 105)
    elif glyph=='play':
        pts=[(218,174),(218,340),(350,257)]; gs.polygon([(x+5,y+7) for x,y in pts],fill=(0,0,0,100)); g.polygon(pts,fill=(*F,255))
    elif glyph=='plane':
        pts=[(126,252),(384,145),(303,377),(248,291),(198,330),(205,276)]
        gs.polygon([(x+5,y+7) for x,y in pts],fill=(0,0,0,90)); g.polygon(pts,fill=(*F,255))
    elif glyph=='bubble':
        box=(125,150,387,330); gs.rounded_rectangle((130,157,392,337),70,fill=(0,0,0,90)); g.rounded_rectangle(box,70,fill=(*F,255)); g.polygon([(205,320),(185,382),(255,326)],fill=(*F,255))
        for cx in (205,256,307): g.ellipse((cx-12,235,cx+12,259),fill=(100,170,115,255))
    elif glyph=='camera':
        g.rounded_rectangle((118,164,394,346),48,fill=(235,235,228,255),outline=(255,255,255,255),width=5)
        g.ellipse((173,177,339,343),fill=(40,45,52,255)); g.ellipse((195,199,317,321),fill=(25,28,38,255)); g.ellipse((220,224,292,296),fill=(70,120,210,255)); g.ellipse((238,238,275,275),fill=(190,230,255,220)); g.ellipse((332,188,361,217),fill=(255,255,255,180))
    elif glyph=='mail':
        g.rounded_rectangle((110,170,402,340),35,fill=(238,244,250,255)); g.polygon([(112,185),(256,292),(400,185)],fill=(210,224,239,255)); g.line((112,330,224,245),fill=(180,201,222,255),width=8); g.line((400,330,288,245),fill=(180,201,222,255),width=8)
    elif glyph=='gmail':
        g.rounded_rectangle((105,160,407,348),34,fill=(250,250,247,255));
        g.line((120,185,256,286,392,185),fill=(218,58,54,255),width=30); g.line((120,185,120,330),fill=(190,45,45,255),width=22); g.line((392,185,392,330),fill=(190,45,45,255),width=22)
    elif glyph=='wave':
        xs=[148,180,212,244,276,308,340,372]; hs=[60,115,155,90,170,125,82,45]
        for x,h in zip(xs,hs): g.rounded_rectangle((x-9,256-h//2,x+9,256+h//2),9,fill=(*F,255))
    elif glyph=='music':
        g.line((274,155,274,320),fill=(*F,255),width=24); g.line((274,165,362,142),fill=(*F,255),width=24); g.ellipse((211,295,285,365),fill=(*F,255)); g.ellipse((313,265,387,335),fill=(*F,255)); g.line((362,150,362,295),fill=(*F,255),width=24)
    elif glyph=='phone':
        # stylized handset
        g.arc((145,118,380,385),20,150,fill=(*F,255),width=45)
        g.rounded_rectangle((125,268,190,355),24,fill=(*F,255)); g.rounded_rectangle((320,155,385,242),24,fill=(*F,255))
    elif glyph=='gear':
        cx=256; cy=256
        for a in range(0,360,45):
            rad=math.radians(a); x=cx+112*math.cos(rad); y=cy+112*math.sin(rad)
            g.rounded_rectangle((x-24,y-46,x+24,y+46),18,fill=(*F,255))
        g.ellipse((150,150,362,362),fill=(*F,255)); g.ellipse((215,215,297,297),fill=(115,120,128,255))
    elif glyph=='clock':
        g.ellipse((124,124,388,388),fill=(242,242,239,255),outline=(30,30,30,255),width=10)
        g.line((256,256,256,166),fill=(35,35,35,255),width=12); g.line((256,256,320,288),fill=(35,35,35,255),width=12); g.ellipse((244,244,268,268),fill=(220,45,45,255))
    elif glyph=='calendar':
        g.rounded_rectangle((120,130,392,372),32,fill=(249,249,247,255)); g.rounded_rectangle((120,130,392,200),32,fill=(220,48,55,255)); text_center(text or '31',140,35,fill=(45,45,45))
    elif glyph=='photos':
        cols=['#ff3b30','#ff9500','#ffcc00','#34c759','#00c7be','#0a84ff','#5856d6','#af52de']
        for i,c in enumerate(cols):
            a=math.radians(i*45); cx=256+72*math.cos(a); cy=256+72*math.sin(a); g.ellipse((cx-48,cy-48,cx+48,cy+48),fill=(*rgb(c),225))
        g.ellipse((220,220,292,292),fill=(255,255,255,235))
    elif glyph=='chrome':
        g.ellipse((128,128,384,384),fill=(245,245,245,255));
        g.pieslice((128,128,384,384),210,330,fill=(234,67,53,255)); g.pieslice((128,128,384,384),330,90,fill=(251,188,5,255)); g.pieslice((128,128,384,384),90,210,fill=(52,168,83,255)); g.ellipse((190,190,322,322),fill=(66,133,244,255),outline=(235,235,235,255),width=10)
    elif glyph=='photos_flower':
        return rounded_icon(top,bottom,'photos',text,fg,accent)
    elif glyph=='cloud':
        g.ellipse((150,225,260,330),fill=(*F,255)); g.ellipse((210,190,330,330),fill=(*F,255)); g.ellipse((285,230,382,330),fill=(*F,255)); g.rectangle((165,270,370,330),fill=(*F,255));
        for i,h in enumerate([45,75,105,135,165]): g.rounded_rectangle((105+i*18,290-h,115+i*18,330),5,fill=(*F,255))
    elif glyph=='bag':
        g.rounded_rectangle((145,175,367,365),36,fill=(235,244,250,235)); g.arc((195,115,317,245),190,350,fill=(255,255,255,255),width=18); text_center('A',112,30,fill=(85,150,210))
    elif glyph=='map':
        g.rounded_rectangle((125,145,387,367),42,fill=(240,245,225,255)); g.line((180,145,180,367),fill=(120,190,120,255),width=18); g.line((310,145,310,367),fill=(245,210,110,255),width=18); g.line((125,260,387,230),fill=(255,255,255,255),width=36); g.ellipse((230,190,290,250),fill=(226,57,57,255)); g.polygon([(230,220),(290,220),(260,300)],fill=(226,57,57,255))
    elif glyph=='folder':
        g.rounded_rectangle((104,190,408,354),30,fill=(85,166,244,255)); g.rounded_rectangle((120,158,260,225),20,fill=(110,188,252,255)); g.rounded_rectangle((104,214,408,354),30,fill=(112,190,252,255))
    elif glyph=='wallet':
        g.rounded_rectangle((105,172,407,350),42,fill=(238,223,194,255)); g.rounded_rectangle((260,220,420,310),30,fill=(126,91,61,255)); g.ellipse((355,248,380,273),fill=(245,210,80,255))
    elif glyph=='calculator':
        g.rounded_rectangle((140,115,372,397),42,fill=(42,42,45,255)); g.rounded_rectangle((168,145,344,205),18,fill=(105,110,115,255));
        for r0 in range(3):
            for c0 in range(3):
                col=(238,149,54,255) if c0==2 else (112,112,116,255)
                g.rounded_rectangle((165+c0*63,230+r0*55,210+c0*63,270+r0*55),12,fill=col)
    elif glyph=='heart':
        g.polygon([(256,360),(115,224),(120,175),(155,140),(210,145),(256,195),(302,145),(357,140),(392,175),(397,224)],fill=(*F,255)); g.polygon([(397,224),(256,360),(115,224),(170,235),(256,310),(342,235)],fill=(*F,255))
    elif glyph=='pin':
        g.ellipse((170,125,342,297),fill=(*F,255)); g.polygon([(185,250),(327,250),(256,385)],fill=(*F,255)); g.ellipse((220,175,292,247),fill=rgb(top)+(255,))
    elif glyph=='gamepad':
        g.rounded_rectangle((110,205,402,330),55,fill=(*F,255)); g.rectangle((175,238,195,298),fill=(60,60,65,255)); g.rectangle((155,258,215,278),fill=(60,60,65,255)); g.ellipse((315,245,345,275),fill=(60,60,65,255)); g.ellipse((350,275,380,305),fill=(60,60,65,255))
    elif glyph=='discord':
        g.rounded_rectangle((125,180,387,332),70,fill=(*F,255)); g.ellipse((180,230,220,270),fill=rgb(top)+(255,)); g.ellipse((292,230,332,270),fill=rgb(top)+(255,)); g.arc((170,220,342,320),20,160,fill=rgb(top)+(255,),width=14)
    else: text_center(text or '?',150)
    if gshadow.getbbox():
        gshadow=gshadow.filter(ImageFilter.GaussianBlur(4)); base.alpha_composite(gshadow,(0,0))
    return base


def main():
    defs = json.loads((ROOT / 'tools/icons.json').read_text(encoding='utf-8'))
    res_dir = ROOT / 'app/src/main/res/drawable-nodpi'
    res_dir.mkdir(parents=True, exist_ok=True)
    for old in res_dir.glob('skeuo_*.png'):
        old.unlink()
    for name, spec in defs.items():
        img = rounded_icon(spec['top'], spec['bottom'], spec.get('glyph','text'), spec.get('text',''), spec.get('foreground','#ffffff'))
        img.save(res_dir / f'{name}.png', optimize=True)

    launcher = rounded_icon('#92a0aa','#424a51','text','S','#ffffff')
    for dens,size in [('mdpi',48),('hdpi',72),('xhdpi',96),('xxhdpi',144),('xxxhdpi',192)]:
        out = ROOT / f'app/src/main/res/mipmap-{dens}'
        out.mkdir(parents=True, exist_ok=True)
        launcher.resize((size,size),Image.Resampling.LANCZOS).save(out/'ic_launcher.png')

    docs = ROOT / 'docs'
    docs.mkdir(parents=True, exist_ok=True)
    names=list(defs.keys())[:24]
    thumb=120; gap=18; cols=6; rows=4
    prev=Image.new('RGB',(cols*(thumb+gap)+gap, rows*(thumb+38+gap)+gap),(24,25,28))
    d=ImageDraw.Draw(prev); font=ImageFont.truetype(FONT_REG,13)
    for i,n in enumerate(names):
        r=i//cols; c=i%cols; x=gap+c*(thumb+gap); y=gap+r*(thumb+38+gap)
        im=Image.open(res_dir/f'{n}.png').convert('RGBA').resize((thumb,thumb),Image.Resampling.LANCZOS)
        prev.paste(im,(x,y),im)
        label=n.replace('skeuo_','')[:15]
        bb=d.textbbox((0,0),label,font=font)
        d.text((x+(thumb-(bb[2]-bb[0]))/2,y+thumb+4),label,font=font,fill=(230,230,230))
    prev.save(docs/'preview.png')
    print(f'Generated {len(defs)} icons')

if __name__ == '__main__':
    main()
