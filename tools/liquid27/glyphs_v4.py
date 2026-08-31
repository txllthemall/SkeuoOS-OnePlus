from __future__ import annotations

import math
from .material import *


def _ring(outer, inner):
    return sub(ellipse(outer), ellipse(inner))


def _petal(cx, cy, w, h, deg):
    return rotate(ellipse((cx-w/2, cy-h/2, cx+w/2, cy+h/2)), deg, (cx,cy))


def glyph_v4(kind):
    """Curated v4 geometry. Return None to fall back to the legacy semantic glyph."""
    L=[]
    def gl(mask, fill='#fff', opacity=.82, refraction=.065, specular='automatic', shadow=.035,
           material='glass', blend='normal', offset=(0,0), blur=0, shadow_offset=2.0, shadow_blur=5.0):
        L.append(layer(mask,fill,opacity,refraction,specular,shadow,material,blend,offset,blur,shadow_offset,shadow_blur))

    if kind=='phone':
        tube=bezier((330,682),(382,806),(632,666),(690,450),126)
        lower=rotate(rr((250,625,448,790),74),36,(349,708)); upper=rotate(rr((618,318,816,483),74),36,(717,400))
        receiver=sub(union(tube,lower,upper),bezier((390,658),(450,710),(572,612),(620,474),48))
        gl(receiver,'#fff',.82,.085,'outside',.035,offset=(0,-2))
    elif kind=='messages':
        gl(union(rr((185,245,839,696),170),poly([(370,650),(315,820),(500,688)])),'#fff',.84,.080,'outside',.030,offset=(0,-2))
    elif kind=='camera':
        gl(rr((155,260,869,752),128),'#f6f8fb',.74,.055,'inside',.025)
        gl(ellipse((280,250,744,714)),'#3b424d',.66,.070,'outside',.030)
        gl(ellipse((332,302,692,662)),'#111722',.98,0,'off',0,'solid')
        gl(ellipse((392,362,632,602)),'#246ee8',.72,.105,'outside',.012)
        gl(ellipse((428,396,565,533)),'#8fd9ff',.34,.125,'outside',.005)
        gl(ellipse((456,416,512,472)),'#fff',.60,.035,'inside',0)
        gl(ellipse((766,300,824,358)),'#fff',.52,.055,'inside',.003)
    elif kind in ('photos','google_photos'):
        cols=['#ff5864','#ff8a00','#ffd000','#7fd800','#00ce83','#08afe8','#4478e1','#a23faa']
        for i,col in enumerate(cols):
            a=math.radians(i*45-90); cx=512+158*math.cos(a); cy=512+158*math.sin(a)
            gl(_petal(cx,cy,244,370,i*45),col,.74,.095,'outside',.010,offset=(0,-3))
        gl(ellipse((428,428,596,596)),'#fff',.36,.070,'inside',.002)
    elif kind=='settings':
        teeth=blank_mask()
        for a in range(0,360,30):
            x=512+228*math.cos(math.radians(a)); y=512+228*math.sin(math.radians(a))
            teeth=union(teeth,rotate(rr((x-33,y-72,x+33,y+72),22),a,(x,y)))
        gear=sub(union(teeth,ellipse((292,292,732,732))),ellipse((430,430,594,594)))
        gl(gear,'#f3f5f8',.72,.072,'outside',.030); gl(ellipse((447,447,577,577)),'#66707b',.30,.060,'inside',.008)
    elif kind=='mail':
        gl(rr((160,300,864,748),112),'#fff',.76,.085,'outside',.026)
        gl(poly([(190,332),(512,560),(834,332),(834,388),(512,620),(190,388)]),'#e5f2ff',.62,.095,'inside',.010)
        gl(round_line([(188,704),(392,530)],22),'#d3e9ff',.44,.050,'inside',0)
        gl(round_line([(836,704),(632,530)],22),'#d3e9ff',.44,.050,'inside',0)
    elif kind=='gmail':
        gl(rr((165,295,859,754),110),'#fff',.78,.060,'inside',.020)
        gl(round_line([(198,346),(512,572),(826,346)],48),'#ea4335',.82,.055,'outside',.010)
        gl(round_line([(198,346),(198,708)],34),'#c5221f',.88,.025,'outside',.006)
        gl(round_line([(826,346),(826,708)],34),'#c5221f',.88,.025,'outside',.006)
    elif kind in ('maps','google_maps'):
        gl(rr((145,155,879,869),154),'#eef5e8',.52,.060,'inside',.020)
        gl(round_line([(165,690),(350,560),(560,595),(856,382)],72),'#fff',.68,.070,'outside',.008)
        gl(round_line([(402,172),(430,420),(384,850)],56),'#5fb7ff',.68,.072,'outside',.008)
        gl(round_line([(650,172),(628,850)],52),'#f3d35a',.52,.065,'inside',.006)
        gl(ellipse((368,326,656,614)),'#178cf6',.72,.105,'outside',.028)
        gl(poly([(512,374),(626,578),(514,530),(412,600)]),'#fff',.78,.060,'outside',.006)
    elif kind=='clock':
        gl(ellipse((194,194,830,830)),'#f8f8fa',.78,.055,'outside',.022)
        ticks=blank_mask()
        for a in range(0,360,30):
            z=math.radians(a-90); ticks=union(ticks,round_line([(512+248*math.cos(z),512+248*math.sin(z)),(512+278*math.cos(z),512+278*math.sin(z))],9))
        gl(ticks,'#232429',1,0,'off',0,'ink'); gl(round_line([(512,512),(512,335)],18),'#202126',1,0,'off',0,'ink')
        gl(round_line([(512,512),(655,578)],18),'#202126',1,0,'off',0,'ink'); gl(ellipse((497,497,527,527)),'#ff453a',1,0,'off',0,'ink')
    elif kind=='weather':
        gl(ellipse((530,244,766,480)),'#ffd21a',.78,.090,'outside',.012)
        cloud=union(ellipse((234,492,522,740)),ellipse((386,390,690,742)),ellipse((606,500,814,742)),rr((278,598,774,748),76))
        gl(cloud,'#fff',.77,.095,'outside',.032,offset=(0,-2))
    elif kind=='notes':
        gl(rr((198,182,826,842),132),'#fff7d3',.70,.065,'inside',.022)
        gl(rr((198,182,826,320),132),'#fff',.30,.075,'inside',.004)
        for y in (460,566,672): gl(round_line([(300,y),(720,y)],14),'#7a693b',.56,0,'off',0,'ink')
        gl(rotate(rr((500,372,770,448),38),-42,(635,410)),'#fff',.68,.075,'outside',.010)
    elif kind in ('calendar','google_calendar'):
        gl(rr((192,150,832,862),142),'#fff',.78,.055,'inside',.022)
        top=union(rr((192,150,832,310),142),rr((192,250,832,332),12)); gl(top,'#ff5148' if kind=='calendar' else '#4285f4',.88,.035,'outside',.006)
        gl(text_mask('31',280,78,False),'#222328',1,0,'off',0,'ink')
    elif kind=='appstore':
        for pts in [[(350,718),(500,438)],[(524,438),(680,718)],[(382,650),(648,650)]]:
            gl(round_line(pts,62),'#fff',.79,.085,'outside',.018,'glass','plus_lighter')
    elif kind=='calculator':
        gl(rr((186,136,838,888),150),'#3b3c42',.70,.065,'outside',.026)
        gl(rr((278,230,746,358),42),'#8a8f98',.54,.070,'inside',.006)
        for r in range(3):
            for c in range(3): gl(rr((264+c*172,448+r*126,374+c*172,548+r*126),35),'#ff9f0a' if c==2 else '#8f9096',.72,.060,'outside',.006)
    elif kind=='recorder':
        for i,h in enumerate([86,146,220,126,274,196,124,72]): gl(rr((310+i*58,512-h/2,332+i*58,512+h/2),11),'#ff5b5f',.76,.060,'outside',.006)
    elif kind=='telegram':
        main=poly([(190,500),(838,246),(702,812),(510,606),(370,724),(398,566)])
        gl(main,'#fff',.79,.092,'outside',.024,offset=(0,-2))
        gl(poly([(510,606),(702,812),(548,542)]),'#d9f4ff',.36,.090,'inside',.004,'glass','multiply',offset=(0,-2))
        gl(round_line([(402,567),(548,542),(704,810)],10),'#fff',.34,.025,'inside',0)
    elif kind=='discord':
        body=union(rr((218,326,806,694),170),poly([(270,420),(330,300),(430,350)]),poly([(754,420),(694,300),(594,350)]))
        gl(body,'#fff',.76,.080,'outside',.024)
        gl(ellipse((352,438,420,506)),'#5865f2',.95,0,'off',0,'ink'); gl(ellipse((604,438,672,506)),'#5865f2',.95,0,'off',0,'ink')
        gl(arc((350,430,674,640),26,154,25),'#5865f2',.95,0,'off',0,'ink')
    elif kind=='youtube':
        gl(rr((205,338,819,686),112),'#fff',.74,.085,'outside',.026); gl(poly([(448,405),(448,619),(628,512)]),'#ef1724',.96,0,'off',0,'ink')
    elif kind=='revanced':
        gl(poly([(328,290),(752,512),(328,734)]),'#ff4d57',.76,.085,'outside',.020); gl(round_line([(244,330),(244,694)],54),'#fff',.50,.075,'outside',.008)
    elif kind=='chrome':
        for col,start,end in [('#ea4335',210,330),('#fbbc05',330,90),('#34a853',90,210)]:
            m=blank_mask(); ImageDraw.Draw(m).pieslice(sbox((190,190,834,834)),start,end,fill=255); gl(m,col,.72,.080,'outside',.010)
        gl(ellipse((372,372,652,652)),'#4285f4',.76,.100,'outside',.018); gl(ellipse((418,418,512,512)),'#b9dcff',.30,.110,'inside',.002)
    elif kind=='spotify':
        for pts,w in [([(300,390),(420,348),(560,356),(720,390)],34), ([(330,500),(440,468),(560,474),(690,510)],30), ([(365,610),(465,586),(560,590),(660,624)],26)]: gl(round_line(pts,w),'#111315',.90,.020,'off',0,'ink')
    elif kind=='instagram':
        gl(sub(rr((246,246,778,778),154),rr((322,322,702,702),112)),'#fff',.70,.082,'outside',.024)
        gl(sub(ellipse((356,356,668,668)),ellipse((430,430,594,594))),'#fff',.76,.075,'outside',.015)
        gl(ellipse((662,326,738,402)),'#fff',.82,.050,'outside',.008)
    elif kind=='soundcloud':
        cloud=union(ellipse((460,430,734,704)),ellipse((635,505,840,704)),rr((470,594,806,712),56)); gl(cloud,'#fff',.76,.085,'outside',.022)
        for i,h in enumerate([80,130,190,240,180,120]): gl(rr((212+i*38,594-h/2,229+i*38,594+h/2),8),'#fff',.72,.070,'outside',.004)
    elif kind=='kaspi':
        gl(ellipse((386,254,538,406)),'#fff',.78,.075,'outside',.010)
        gl(union(rr((300,420,620,724),128),ellipse((284,378,636,728))),'#fff',.72,.085,'outside',.020)
        gl(rr((588,450,790,690),64),'#fff',.64,.085,'outside',.016); gl(arc((620,386,758,536),190,350,24),'#f24034',.96,0,'off',0,'ink')
    elif kind=='twogis':
        gl(poly([(512,230),(734,356),(734,612),(512,794),(290,612),(290,356)]),'#fff',.60,.095,'outside',.024)
        pin=sub(union(ellipse((430,350,594,514)),poly([(445,474),(579,474),(512,674)])),ellipse((480,400,544,464)))
        gl(pin,'#4ab54a',.86,.055,'outside',.006)
    elif kind=='chatgpt':
        for i in range(6):
            ang=i*60; a=math.radians(ang-90); cx=512+150*math.cos(a); cy=512+150*math.sin(a)
            outer=rotate(rr((cx-150,cy-74,cx+150,cy+74),72),ang+30,(cx,cy)); inner=rotate(rr((cx-88,cy-28,cx+88,cy+28),28),ang+30,(cx,cy))
            gl(sub(outer,inner),'#eaf7f1',.58,.100,'outside',.008,'glass','plus_lighter',offset=(0,-2))
        gl(poly([(512,430),(583,471),(583,553),(512,594),(441,553),(441,471)]),'#0b1714',.62,.020,'inside',0)
    elif kind=='gamehub':
        gl(round_line([(284,330),(420,226),(744,226),(842,352),(736,470),(452,470)],54),'#f0f3f5',.66,.090,'outside',.018)
        gl(rr((340,500,724,720),92),'#f0f3f5',.60,.085,'outside',.018)
        gl(round_line([(430,610),(520,610)],28),'#20242a',.96,0,'off',0,'ink'); gl(round_line([(475,565),(475,655)],28),'#20242a',.96,0,'off',0,'ink')
        gl(ellipse((612,560,654,602)),'#20242a',.96,0,'off',0,'ink'); gl(ellipse((662,618,704,660)),'#20242a',.96,0,'off',0,'ink')
    elif kind=='playstore':
        gl(poly([(314,228),(314,796),(762,512)]),'#fff',.62,.085,'outside',.018)
        gl(poly([(332,260),(332,492),(520,512)]),'#34a853',.60,.060,'inside',.004)
        gl(poly([(332,764),(332,532),(520,512)]),'#4285f4',.60,.060,'inside',.004)
        gl(poly([(520,512),(740,512),(620,438)]),'#fbbc05',.60,.060,'inside',.004)
        gl(poly([(520,512),(740,512),(620,586)]),'#ea4335',.60,.060,'inside',.004)
    else:
        return None
    return L
