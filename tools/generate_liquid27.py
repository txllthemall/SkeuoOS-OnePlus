from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageEnhance, ImageOps
import json, math

ROOT = Path(__file__).resolve().parents[1]
S, OUT, PAD = 768, 512, 36
FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def rgb(h):
    h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))

def mix(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
def lum(c): return .2126*c[0]+.7152*c[1]+.0722*c[2]

def rr(box,radius,fill=255):
    m=Image.new('L',(S,S),0); ImageDraw.Draw(m).rounded_rectangle(box,radius=radius,fill=fill); return m

def ellipse(box):
    m=Image.new('L',(S,S),0); ImageDraw.Draw(m).ellipse(box,fill=255); return m

def poly(points):
    m=Image.new('L',(S,S),0); ImageDraw.Draw(m).polygon(points,fill=255); return m

def line(points,width):
    m=Image.new('L',(S,S),0); ImageDraw.Draw(m).line(points,fill=255,width=width,joint='curve'); return m

def offset(im,dx=0,dy=0):
    out=Image.new(im.mode,im.size,0)
    src=(max(0,-dx),max(0,-dy),min(S,S-dx),min(S,S-dy)); dst=(max(0,dx),max(0,dy))
    if src[2]>src[0] and src[3]>src[1]: out.paste(im.crop(src),dst)
    return out

ICON_MASK=rr((PAD,PAD,S-PAD,S-PAD),168)


def gradient(top,bottom):
    g=Image.linear_gradient('L').resize((S,S))
    base=ImageOps.colorize(g,rgb(top),rgb(bottom)).convert('RGBA')
    # brighter upper-left pool and deeper lower-right pool; subtle, not iOS 26 milkiness
    rad=Image.radial_gradient('L').resize((S,S))
    light=Image.new('RGBA',(S,S),(255,255,255,0)); light.putalpha(rad.rotate(180).point(lambda v:int(v*.16)))
    dark=Image.new('RGBA',(S,S),(0,0,0,0)); dark.putalpha(rad.point(lambda v:int(v*.13)))
    base.alpha_composite(light); base.alpha_composite(dark); base.putalpha(ICON_MASK)
    return base


def shell(bg):
    out=Image.new('RGBA',(S,S),(0,0,0,0))
    sh=offset(ICON_MASK,0,11).filter(ImageFilter.GaussianBlur(18)).point(lambda v:int(v*.34))
    s=Image.new('RGBA',(S,S),(0,0,0,0)); s.putalpha(sh); black=Image.new('RGBA',(S,S),(0,0,0,80)); black.putalpha(sh); out.alpha_composite(black)
    out.alpha_composite(bg)
    # broad internal material layers
    hi=rr((104,72,664,382),160).filter(ImageFilter.GaussianBlur(22)); hi=ImageChops.multiply(hi,ICON_MASK)
    w=Image.new('RGBA',(S,S),(255,255,255,0)); w.putalpha(hi.point(lambda v:int(v*.08))); out.alpha_composite(w)
    lo=rr((126,430,690,708),148).filter(ImageFilter.GaussianBlur(24)); lo=ImageChops.multiply(lo,ICON_MASK)
    b=Image.new('RGBA',(S,S),(0,0,0,0)); b.putalpha(lo.point(lambda v:int(v*.065))); out.alpha_composite(b)
    # iOS 27 style fixed vertical specular edge
    topedge=ImageChops.subtract(ICON_MASK,offset(ICON_MASK,0,8)); botedge=ImageChops.subtract(ICON_MASK,offset(ICON_MASK,0,-8))
    a=Image.new('RGBA',(S,S),(255,255,255,0)); a.putalpha(topedge.point(lambda v:int(v*.56))); out.alpha_composite(a)
    a=Image.new('RGBA',(S,S),(0,0,0,0)); a.putalpha(botedge.point(lambda v:int(v*.25))); out.alpha_composite(a)
    return out


def glass(bg,mask,color=(255,255,255),opacity=118):
    out=Image.new('RGBA',(S,S),(0,0,0,0))
    sh=offset(mask,0,9).filter(ImageFilter.GaussianBlur(11)).point(lambda v:int(v*.27))
    q=Image.new('RGBA',(S,S),(0,0,0,0)); q.putalpha(sh); black=Image.new('RGBA',(S,S),(0,0,0,68)); black.putalpha(sh); out.alpha_composite(black)
    refr=offset(bg,-4,8).filter(ImageFilter.GaussianBlur(4)); refr=ImageEnhance.Contrast(refr).enhance(1.08); refr=ImageEnhance.Brightness(refr).enhance(1.10); refr.putalpha(mask.point(lambda v:int(v*.86))); out.alpha_composite(refr)
    tint=Image.new('RGBA',(S,S),(*color,0)); tint.putalpha(mask.point(lambda v:int(v*opacity/255))); out.alpha_composite(tint)
    top=ImageChops.subtract(mask,offset(mask,0,7)); bot=ImageChops.subtract(mask,offset(mask,0,-7))
    e=Image.new('RGBA',(S,S),(255,255,255,0)); e.putalpha(top.point(lambda v:int(v*.72))); out.alpha_composite(e)
    e=Image.new('RGBA',(S,S),(0,0,0,0)); e.putalpha(bot.point(lambda v:int(v*.28))); out.alpha_composite(e)
    return out


def solid(mask,color,alpha=245):
    out=Image.new('RGBA',(S,S),(0,0,0,0)); c=Image.new('RGBA',(S,S),(*color,0)); c.putalpha(mask.point(lambda v:int(v*alpha/255))); out.alpha_composite(c)
    top=ImageChops.subtract(mask,offset(mask,0,5)); e=Image.new('RGBA',(S,S),(255,255,255,0)); e.putalpha(top.point(lambda v:int(v*.38))); out.alpha_composite(e)
    return out


def add(canvas,bg,mask,color,as_glass=True,opacity=118):
    if isinstance(color,str): color=rgb(color)
    canvas.alpha_composite(glass(bg,mask,color,opacity) if as_glass else solid(mask,color))


def textmask(text,size=230,yoff=0,bold=True):
    m=Image.new('L',(S,S),0); d=ImageDraw.Draw(m); f=ImageFont.truetype(FONT_BOLD if bold else FONT_REG,size)
    b=d.textbbox((0,0),text,font=f); x=(S-(b[2]-b[0]))/2-b[0]; y=(S-(b[3]-b[1]))/2-b[1]+yoff; d.text((x,y),text,font=f,fill=255); return m


def render(spec,name):
    top,bottom=spec['top'],spec['bottom']; fg=spec.get('foreground','#fff'); glyph=spec.get('glyph','text'); txt=spec.get('text','')
    bg=gradient(top,bottom); c=shell(bg); dark=mix(rgb(bottom),(0,0,0),.42)

    if glyph=='phone':
        m=Image.new('L',(S,S),0); d=ImageDraw.Draw(m); d.arc((172,132,598,620),24,151,fill=255,width=72); d.rounded_rectangle((152,422,246,560),34,fill=255); d.rounded_rectangle((512,206,606,344),34,fill=255); add(c,bg,m,fg)
    elif glyph=='bubble':
        m=ImageChops.lighter(rr((164,204,604,500),126),poly([(300,470),(250,592),(390,494)])); add(c,bg,m,fg)
        for x in (310,384,458): add(c,bg,ellipse((x-17,337,x+17,371)),dark,False)
    elif glyph=='camera':
        add(c,bg,rr((150,210,618,530),92),(244,247,250)); add(c,bg,ellipse((246,228,522,504)),(45,48,58)); add(c,bg,ellipse((286,268,482,464)),(22,27,40),False); add(c,bg,ellipse((330,312,438,420)),(82,157,255)); add(c,bg,ellipse((370,330,402,362)),(230,250,255),False); add(c,bg,ellipse((516,238,558,280)),(255,255,255))
    elif glyph=='photos':
        cols=['#ff453a','#ff9f0a','#ffd60a','#30d158','#64d2ff','#0a84ff','#5e5ce6','#bf5af2']
        for i,col in enumerate(cols):
            a=math.radians(i*45-90); x=384+100*math.cos(a); y=384+100*math.sin(a); add(c,bg,ellipse((x-74,y-94,x+74,y+94)).rotate(i*45,center=(x,y),resample=Image.Resampling.BICUBIC),col)
        add(c,bg,ellipse((330,330,438,438)),(255,255,255))
    elif glyph=='gear':
        m=Image.new('L',(S,S),0); d=ImageDraw.Draw(m)
        for a in range(0,360,30):
            x=384+160*math.cos(math.radians(a)); y=384+160*math.sin(math.radians(a)); d.rounded_rectangle((x-28,y-62,x+28,y+62),18,fill=255)
        d.ellipse((230,230,538,538),fill=255); m=ImageChops.subtract(m,ellipse((328,328,440,440))); add(c,bg,m,fg)
    elif glyph in ('mail','gmail'):
        add(c,bg,rr((142,226,626,526),70),(248,250,255)); m=poly([(154,250),(384,414),(614,250),(614,290),(384,456),(154,290)]); add(c,bg,m,(214,231,250) if glyph=='mail' else (234,67,53),glyph=='mail')
        if glyph=='gmail': add(c,bg,line([(164,282),(164,500)],38),(210,45,45),False); add(c,bg,line([(604,282),(604,500)],38),(210,45,45),False)
    elif glyph=='map':
        add(c,bg,rr((154,180,614,560),94),(210,238,198)); add(c,bg,line([(165,438),(290,362),(435,384),(610,278)],52),(255,255,255)); add(c,bg,line([(330,190),(352,330),(310,552)],44),(95,180,250)); pin=ImageChops.subtract(ImageChops.lighter(ellipse((330,250,438,358)),poly([(340,332),(428,332),(384,450)])),ellipse((364,284,404,324))); add(c,bg,pin,(255,69,58),False)
    elif glyph=='clock':
        add(c,bg,ellipse((154,154,614,614)),(247,247,248)); t=Image.new('L',(S,S),0); d=ImageDraw.Draw(t)
        for a in range(0,360,30):
            z=math.radians(a-90); d.line([(384+184*math.cos(z),384+184*math.sin(z)),(384+205*math.cos(z),384+205*math.sin(z))],fill=255,width=10)
        add(c,bg,t,(40,40,44),False); add(c,bg,line([(384,384),(384,247)],17),(34,34,38),False); add(c,bg,line([(384,384),(487,433)],17),(34,34,38),False); add(c,bg,ellipse((367,367,401,401)),(255,69,58),False)
    elif glyph=='calendar':
        add(c,bg,rr((156,164,612,590),86),(249,249,250)); head=ImageChops.lighter(rr((156,164,612,278),86),rr((156,226,612,306),2)); add(c,bg,head,(255,69,58)); add(c,bg,textmask(txt or '31',220,65,False),(42,42,46),False)
    elif glyph=='bag':
        for pts in [[(275,500),(383,282),(417,282),(527,500)],[(246,470),(522,470)],[(322,380),(470,380)]]: add(c,bg,line(pts,38),(245,251,255))
    elif glyph=='music':
        m=Image.new('L',(S,S),0); d=ImageDraw.Draw(m); d.line([(410,205),(410,480)],fill=255,width=42); d.line([(410,220),(548,185)],fill=255,width=42); d.line([(548,185),(548,430)],fill=255,width=42); d.ellipse((300,438,426,558),fill=255); d.ellipse((438,388,564,508),fill=255); add(c,bg,m,fg)
    elif glyph=='wallet':
        for i,col in enumerate([(255,69,58),(255,159,10),(48,209,88),(10,132,255)]): add(c,bg,rr((156,188+i*54,612,346+i*54),55),col)
        add(c,bg,rr((420,386,626,500),48),(235,238,245)); add(c,bg,ellipse((548,422,578,452)),(45,45,50),False)
    elif glyph=='folder':
        add(c,bg,rr((132,240,636,554),82),(58,168,255)); add(c,bg,rr((170,192,378,300),45),(100,196,255)); add(c,bg,rr((132,302,636,570),82),(93,190,255))
    elif glyph=='calculator':
        add(c,bg,rr((176,142,592,626),92),(50,50,55)); add(c,bg,rr((222,190,546,292),34),(112,116,126))
        for r in range(3):
            for x in range(3): add(c,bg,rr((220+x*110,340+r*92,292+x*110,410+r*92),28),(255,159,10) if x==2 else (150,151,158))
    elif glyph=='heart':
        m=Image.new('L',(S,S),0); d=ImageDraw.Draw(m); d.ellipse((202,218,392,408),fill=255); d.ellipse((376,218,566,408),fill=255); d.polygon([(215,324),(553,324),(384,566)],fill=255); add(c,bg,m,fg)
    elif glyph=='wave':
        for i,h in enumerate([80,135,190,120,235,176,112,68]): add(c,bg,rr((224+i*46,384-h//2,248+i*46,384+h//2),12),fg)
    elif glyph=='chrome':
        add(c,bg,ellipse((166,166,602,602)),(245,247,250));
        for col,a0,a1 in [((234,67,53),210,330),((251,188,5),330,90),((52,168,83),90,210)]:
            m=Image.new('L',(S,S),0); ImageDraw.Draw(m).pieslice((182,182,586,586),a0,a1,fill=255); add(c,bg,m,col)
        add(c,bg,ellipse((294,294,474,474)),(66,133,244))
    elif glyph=='play':
        add(c,bg,rr((172,250,596,518),90),fg); add(c,bg,poly([(348,306),(348,462),(480,384)]),(255,255,255) if lum(rgb(fg))<160 else dark,False)
    elif glyph=='plane':
        add(c,bg,poly([(154,371),(620,188),(484,590),(382,438),(292,512),(308,416)]),fg)
    elif glyph=='cloud':
        m=Image.new('L',(S,S),0); d=ImageDraw.Draw(m); d.ellipse((318,250,505,455),fill=255); d.ellipse((408,300,578,458),fill=255); d.rectangle((300,350,560,458),fill=255)
        for i,h in enumerate([70,110,160,220,180,130,90]): d.rounded_rectangle((178+i*28,384-h//2,194+i*28,384+h//2),8,fill=255)
        add(c,bg,m,fg)
    elif glyph in ('gamepad','discord'):
        add(c,bg,rr((150,280,618,498),96),fg); dcol=dark
        if glyph=='gamepad': add(c,bg,ImageChops.lighter(line([(234,337),(234,430)],24),line([(187,383),(281,383)],24)),dcol,False); add(c,bg,ellipse((472,337,510,375)),dcol,False); add(c,bg,ellipse((520,385,558,423)),dcol,False)
        else: add(c,bg,ellipse((262,340,318,396)),dcol,False); add(c,bg,ellipse((450,340,506,396)),dcol,False); m=Image.new('L',(S,S),0); ImageDraw.Draw(m).arc((260,330,508,480),10,170,fill=255,width=22); add(c,bg,m,dcol,False)
    else:
        # name-aware symbols for icons that were previously just letters
        if name=='skeuo_weather':
            add(c,bg,ellipse((230,190,438,398)),(255,214,10)); cloud=Image.new('L',(S,S),0); d=ImageDraw.Draw(cloud); d.ellipse((308,332,450,474),fill=255); d.ellipse((388,294,548,474),fill=255); d.ellipse((470,344,602,474),fill=255); d.rectangle((334,400,578,474),fill=255); add(c,bg,cloud,(245,250,255))
        elif name=='skeuo_notes':
            add(c,bg,rr((180,150,588,614),74),(255,248,205)); add(c,bg,rr((180,150,588,250),74),(255,214,10));
            for y in (300,364,428,492): add(c,bg,line([(238,y),(530,y)],12),(170,145,58),False)
        elif name in ('skeuo_facetime','skeuo_zoom','skeuo_google_meet'):
            add(c,bg,rr((190,270,475,482),68),fg); add(c,bg,poly([(470,322),(592,260),(592,492),(470,430)]),fg)
        elif name=='skeuo_compass':
            add(c,bg,ellipse((170,170,598,598)),(228,232,236)); add(c,bg,poly([(384,208),(446,414),(384,376),(322,414)]),(255,69,58)); add(c,bg,poly([(384,560),(322,354),(384,392),(446,354)]),(64,69,78))
        elif name=='skeuo_spotify':
            for box,w in [((214,278,554,500),20),((236,326,532,486),18),((258,370,510,474),16)]:
                m=Image.new('L',(S,S),0); ImageDraw.Draw(m).arc(box,205,335,fill=255,width=w); add(c,bg,m,(22,24,24),False)
        elif name=='skeuo_tiktok':
            m=textmask('♪',260); add(c,bg,offset(m,-13,8),(37,244,238),False); add(c,bg,offset(m,13,-6),(255,45,85),False); add(c,bg,m,(248,248,250))
        elif name=='skeuo_google_drive':
            add(c,bg,poly([(384,170),(520,420),(452,420),(348,238)]),(66,133,244)); add(c,bg,poly([(384,170),(248,420),(316,420),(420,238)]),(52,168,83)); add(c,bg,poly([(248,420),(520,420),(486,484),(282,484)]),(251,188,5))
        elif name in ('skeuo_google_docs','skeuo_google_sheets','skeuo_google_slides'):
            add(c,bg,rr((240,156,528,612),56),fg); add(c,bg,textmask(txt or name[-1].upper(),130,40),(255,255,255),False)
        elif name=='skeuo_chatgpt':
            m=Image.new('L',(S,S),0); d=ImageDraw.Draw(m)
            for a in range(0,360,60):
                z=math.radians(a); x=384+96*math.cos(z); y=384+96*math.sin(z); d.rounded_rectangle((x-30,y-98,x+30,y+98),30,fill=255)
            m=ImageChops.subtract(m,ellipse((326,326,442,442))); add(c,bg,m,(242,246,245))
        else:
            size=230 if len(txt)<=2 else 135; add(c,bg,textmask(txt or '?',size),fg)

    c.putalpha(ImageChops.multiply(c.getchannel('A'),ICON_MASK))
    return c.resize((OUT,OUT),Image.Resampling.LANCZOS)


def preview(specs,path):
    keys=[k for k in ['skeuo_phone','skeuo_messages','skeuo_camera','skeuo_photos','skeuo_settings','skeuo_mail','skeuo_maps','skeuo_weather','skeuo_calendar','skeuo_appstore','skeuo_music','skeuo_wallet','skeuo_files','skeuo_health','skeuo_youtube','skeuo_telegram','skeuo_discord','skeuo_spotify','skeuo_chatgpt','skeuo_google_drive'] if k in specs]
    cell=540; sheet=Image.new('RGB',(cell*5,cell*4),(31,31,35)); d=ImageDraw.Draw(sheet); f=ImageFont.truetype(FONT_REG,20)
    for i,k in enumerate(keys):
        im=render(specs[k],k); x=(i%5)*cell+14; y=(i//5)*cell+8; sheet.paste(im,(x,y),im); d.text((x+4,y+508),k.replace('skeuo_',''),font=f,fill=(235,235,240))
    sheet.save(path)


def main():
    specs=json.loads((ROOT/'tools/icons.json').read_text(encoding='utf-8'))
    out=ROOT/'app/src/main/res/drawable-nodpi'; out.mkdir(parents=True,exist_ok=True)
    for p in out.glob('skeuo_*.png'): p.unlink()
    for name,spec in specs.items(): render(spec,name).save(out/f'{name}.png',optimize=True)
    launcher=render({'top':'#9bd8ff','bottom':'#3c64d9','glyph':'text','text':'27','foreground':'#ffffff'},'launcher')
    for den,size in [('mdpi',48),('hdpi',72),('xhdpi',96),('xxhdpi',144),('xxxhdpi',192)]:
        p=ROOT/f'app/src/main/res/mipmap-{den}'; p.mkdir(parents=True,exist_ok=True); icon=launcher.resize((size,size),Image.Resampling.LANCZOS); icon.save(p/'ic_launcher.png',optimize=True); icon.save(p/'ic_launcher_round.png',optimize=True)
    b=ROOT/'build'; b.mkdir(exist_ok=True); preview(specs,b/'liquid27-preview.png'); print(f'Generated {len(specs)} Liquid27 icons')

if __name__=='__main__': main()
