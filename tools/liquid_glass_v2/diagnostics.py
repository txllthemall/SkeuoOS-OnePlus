from __future__ import annotations

from PIL import Image, ImageDraw


def wallpaper(kind: str, size=(640,640)):
    w,h=size
    palettes={
        'warm':((106,70,54),(185,126,86),(69,46,39)),
        'midtone':((111,88,112),(158,112,125),(86,72,96)),
        'blue':((34,63,118),(63,127,194),(22,41,79)),
        'dark':((14,15,19),(42,45,55),(5,6,9)),
        'bright':((236,233,227),(255,252,246),(205,211,220)),
        'highcontrast':((26,27,31),(225,225,226),(93,94,101)),
    }
    base,accent,low=palettes[kind]
    im=Image.new('RGB',(w,h),base); d=ImageDraw.Draw(im)
    d.ellipse((-int(w*.28),-int(h*.22),int(w*.86),int(h*.76)),fill=accent)
    d.ellipse((int(w*.34),int(h*.40),int(w*1.25),int(h*1.18)),fill=low)
    if kind=='highcontrast':
        for x in range(0,w,30): d.line((x,0,x,h),fill=(245,245,245) if (x//30)%2 else (10,10,10),width=2)
        for y in range(0,h,42): d.line((0,y,w,y),fill=(20,20,20) if (y//42)%2 else (240,240,240),width=2)
        d.arc((-180,90,w+220,h+80),4,178,fill=(255,255,255),width=5)
    return im


def composite_center(bg: Image.Image, icon: Image.Image, box=320):
    out=bg.copy(); ic=icon.resize((box,box),Image.Resampling.LANCZOS)
    x=(out.width-box)//2; y=(out.height-box)//2
    out.paste(ic,(x,y),ic)
    return out


def make_lab(icon: Image.Image):
    kinds=['warm','midtone','blue','dark','bright','highcontrast']
    tile=420; board=Image.new('RGB',(tile*3,tile*2),(20,20,20))
    for i,k in enumerate(kinds): board.paste(composite_center(wallpaper(k,(tile,tile)),icon,220),((i%3)*tile,(i//3)*tile))
    return board
