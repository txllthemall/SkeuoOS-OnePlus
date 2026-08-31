from __future__ import annotations

from .material import *


def _ring(outer, inner):
    return sub(ellipse(outer), ellipse(inner))


def glyph_v4_extra(kind):
    L=[]
    def gl(mask, fill='#fff', opacity=.82, refraction=.065, specular='automatic', shadow=.030,
           material='glass', blend='normal', offset=(0,0), blur=0, shadow_offset=2.0, shadow_blur=5.0):
        L.append(layer(mask,fill,opacity,refraction,specular,shadow,material,blend,offset,blur,shadow_offset,shadow_blur))

    if kind=='facetime':
        gl(rr((238,352,662,688),96),'#fff',.78,.080,'outside',.020); gl(poly([(644,410),(822,330),(822,710),(644,630)]),'#fff',.74,.085,'outside',.016)
    elif kind=='music':
        gl(round_line([(552,312),(552,680)],46),'#fff',.78,.080,'outside',.014); gl(round_line([(552,334),(726,288)],46),'#fff',.78,.080,'outside',.014); gl(round_line([(726,288),(726,618)],46),'#fff',.78,.080,'outside',.014); gl(ellipse((426,626,574,768)),'#fff',.80,.075,'outside',.012); gl(ellipse((600,560,748,702)),'#fff',.80,.075,'outside',.012)
    elif kind=='wallet':
        for i,col in enumerate(['#ff4b48','#ff9d16','#35d266','#168df5']): gl(rr((184,240+i*70,840,486+i*70),86),col,.70,.080,'outside',.014)
        gl(rr((606,594,852,726),58),'#eef2f7',.62,.075,'outside',.012); gl(ellipse((750,635,785,670)),'#33363d',.94,0,'off',0,'ink')
    elif kind=='files':
        gl(rr((210,258,500,420),66),'#8ad3ff',.64,.070,'outside',.012); gl(rr((146,330,878,792),140),'#3ca9ff',.62,.085,'outside',.020); gl(rr((146,430,878,808),140),'#72c3ff',.58,.090,'inside',.012)
    elif kind=='health':
        heart=union(ellipse((270,332,514,576)),ellipse((510,332,754,576)),poly([(282,458),(742,458),(512,760)])); gl(heart,'#ff4f7b',.80,.075,'outside',.018)
    elif kind=='compass':
        gl(ellipse((206,206,818,818)),'#f2f4f6',.52,.080,'outside',.020); gl(poly([(512,256),(590,520),(512,768),(434,520)]),'#ff5148',.72,.080,'outside',.010); gl(poly([(512,768),(434,520),(512,544),(590,520)]),'#34373d',.68,.060,'inside',.008)
    elif kind=='facebook':
        gl(rr((470,230,590,790),42),'#fff',.78,.080,'outside',.014); gl(rr((470,230,720,346),42),'#fff',.78,.080,'outside',.014); gl(rr((360,442,676,556),40),'#fff',.78,.080,'outside',.012)
    elif kind=='whatsapp':
        bubble=union(ellipse((254,250,770,766)),poly([(330,690),(282,826),(432,734)])); gl(sub(bubble,ellipse((332,328,692,688))),'#fff',.74,.085,'outside',.016)
        handset=union(arc((340,330,684,694),24,152,50),rr((330,560,390,650),25),rr((626,390,686,480),25)); gl(handset,'#fff',.82,.070,'outside',.010)
    elif kind=='snapchat':
        ghost=union(ellipse((362,242,662,542)),rr((362,420,662,674),92),poly([(362,612),(312,724),(412,700),(512,760),(612,700),(712,724),(662,612)])); gl(ghost,'#fff',.76,.080,'outside',.018)
    elif kind=='reddit':
        gl(ellipse((260,330,764,734)),'#fff',.72,.085,'outside',.018); gl(ellipse((386,476,444,534)),'#ff4500',.96,0,'off',0,'ink'); gl(ellipse((580,476,638,534)),'#ff4500',.96,0,'off',0,'ink'); gl(arc((386,512,638,646),18,162,22),'#ff4500',.96,0,'off',0,'ink'); gl(round_line([(512,330),(560,246),(660,270)],20),'#fff',.76,.070,'outside',.008); gl(ellipse((640,242,700,302)),'#fff',.76,.070,'outside',.008)
    elif kind=='pinterest':
        gl(_ring((330,240,694,604),(418,328,606,516)),'#fff',.78,.080,'outside',.014); gl(round_line([(490,500),(422,790)],62),'#fff',.78,.075,'outside',.012)
    elif kind=='tiktok':
        stem=union(round_line([(520,286),(520,672)],62),round_line([(520,318),(684,390)],62),ellipse((378,598,550,770))); gl(shifted(stem,-9,2),'#25f4ee',.44,.055,'outside',.004,'glass','screen'); gl(shifted(stem,9,-2),'#fe2c55',.44,.055,'outside',.004,'glass','screen'); gl(stem,'#fff',.72,.075,'outside',.012)
    elif kind=='slack':
        cols=['#36c5f0','#2eb67d','#ecb22e','#e01e5a']; items=[rr((285,390,455,470),38),rr((390,285,470,455),38),rr((569,285,649,455),38),rr((569,390,739,470),38),rr((569,569,739,649),38),rr((569,569,649,739),38),rr((390,569,470,739),38),rr((285,569,455,649),38)]
        for i,m in enumerate(items): gl(m,cols[(i//2)%4],.70,.080,'outside',.009)
    elif kind=='netflix':
        gl(poly([(318,226),(458,226),(704,798),(564,798)]),'#e50914',.82,.070,'outside',.012); gl(poly([(564,226),(704,226),(458,798),(318,798)]),'#b20710',.72,.060,'inside',.010)
    elif kind=='amazon':
        gl(arc((292,410,732,690),20,155,32),'#202124',.98,0,'off',0,'ink'); gl(poly([(690,626),(772,610),(730,686)]),'#202124',.98,0,'off',0,'ink'); gl(rr((448,214,576,384),24),'#5f9b75',.56,.070,'outside',.010); gl(round_line([(448,214),(576,342)],18),'#275f40',.78,0,'off',0,'ink')
    elif kind=='uber':
        gl(arc((304,270,720,710),5,175,74),'#fff',.76,.080,'outside',.014); gl(round_line([(324,438),(324,612)],74),'#fff',.76,.080,'outside',.014); gl(round_line([(700,438),(700,612)],74),'#fff',.76,.080,'outside',.014)
    elif kind=='paypal':
        gl(rr((284,260,566,704),92),'#8fc4ff',.70,.085,'outside',.018); gl(rr((456,314,738,758),92),'#2c7bd1',.68,.095,'outside',.018)
    elif kind=='venmo':
        gl(round_line([(330,328),(472,708),(710,328)],82),'#fff',.76,.080,'outside',.016)
    elif kind=='robinhood':
        gl(poly([(304,732),(730,270),(658,552),(542,504),(556,650),(430,620)]),'#fff',.76,.080,'outside',.014); gl(round_line([(320,760),(622,450)],28),'#24562b',.90,0,'off',0,'ink')
    elif kind=='strava':
        gl(poly([(310,742),(474,278),(596,548),(686,350),(814,742),(690,742),(596,552),(514,742)]),'#fff',.76,.080,'outside',.014)
    elif kind=='zoom':
        gl(rr((246,352,650,678),96),'#fff',.76,.080,'outside',.016); gl(poly([(632,412),(814,330),(814,700),(632,618)]),'#fff',.72,.085,'outside',.014)
    elif kind=='shazam':
        gl(round_line([(342,426),(454,322),(572,438),(680,336)],56),'#fff',.76,.090,'outside',.014); gl(round_line([(682,598),(570,702),(452,586),(344,688)],56),'#fff',.76,.090,'outside',.014)
    elif kind=='twitter':
        gl(round_line([(336,276),(706,748)],64),'#fff',.76,.080,'outside',.014); gl(round_line([(706,276),(336,748)],64),'#fff',.76,.080,'outside',.014)
    elif kind=='github':
        head=union(ellipse((286,296,738,748)),poly([(330,388),(286,236),(430,318)]),poly([(694,388),(738,236),(594,318)])); gl(head,'#f3f4f6',.74,.085,'outside',.018); gl(ellipse((392,470,444,522)),'#1c2025',.94,0,'off',0,'ink'); gl(ellipse((580,470,632,522)),'#1c2025',.94,0,'off',0,'ink')
    elif kind=='steam':
        gl(_ring((526,308,790,572),(604,386,712,494)),'#eef5fb',.72,.090,'outside',.016); gl(round_line([(350,650),(606,500)],44),'#eef5fb',.72,.090,'outside',.014); gl(_ring((250,568,448,766),(306,624,392,710)),'#eef5fb',.72,.085,'outside',.014)
    elif kind=='keep':
        gl(rr((230,192,794,832),122),'#fff3a7',.66,.075,'inside',.018); gl(ellipse((432,360,592,520)),'#e8b91e',.68,.075,'outside',.010); gl(round_line([(512,500),(512,674)],38),'#e8b91e',.84,0,'off',0,'ink')
    elif kind=='meet':
        gl(rr((236,358,654,688),92),'#fff',.68,.080,'outside',.014); gl(poly([(638,416),(816,334),(816,712),(638,630)]),'#fff',.64,.085,'outside',.012)
    elif kind=='drive':
        gl(poly([(512,220),(704,548),(600,746),(408,418)]),'#fbbc05',.70,.080,'outside',.012); gl(poly([(512,220),(320,548),(424,746),(616,418)]),'#34a853',.70,.080,'outside',.012); gl(poly([(320,548),(704,548),(600,746),(424,746)]),'#4285f4',.70,.080,'outside',.012)
    elif kind=='docs':
        gl(rr((280,218,744,806),96),'#fff',.62,.080,'outside',.014)
        for y in (430,520,610): gl(round_line([(380,y),(650,y)],18),'#2e6dd3',.84,0,'off',0,'ink')
    elif kind=='sheets':
        gl(rr((272,220,752,808),96),'#fff',.62,.080,'outside',.014)
        for x in (404,532,660): gl(round_line([(x,430),(x,690)],15),'#2b8e49',.84,0,'off',0,'ink')
        for y in (500,590,680): gl(round_line([(360,y),(660,y)],15),'#2b8e49',.84,0,'off',0,'ink')
    elif kind=='slides':
        gl(rr((270,220,754,808),98),'#fff',.62,.080,'outside',.014); gl(rr((360,424,664,630),42),'#e6a900',.68,.070,'outside',.008)
    elif kind=='translate':
        gl(rr((198,268,520,646),82),'#fff',.58,.085,'outside',.014); gl(rr((500,402,824,780),82),'#fff',.58,.085,'outside',.014); gl(round_line([(280,420),(440,420)],22),'#2f71d8',.84,0,'off',0,'ink'); gl(round_line([(582,560),(744,560)],22),'#2f71d8',.84,0,'off',0,'ink')
    elif kind=='search':
        gl(_ring((278,278,674,674),(358,358,594,594)),'#fff',.70,.085,'outside',.016); gl(round_line([(620,622),(782,782)],66),'#fff',.70,.085,'outside',.016)
    elif kind=='classroom':
        gl(rr((238,316,786,698),100),'#fff',.58,.085,'outside',.014); gl(ellipse((448,390,576,518)),'#2c8f48',.90,0,'off',0,'ink'); gl(rr((360,526,664,650),54),'#2c8f48',.90,0,'off',0,'ink')
    elif kind=='one':
        cloud=union(ellipse((284,470,494,680)),ellipse((410,370,650,680)),ellipse((590,480,788,680)),rr((340,560,742,700),70)); gl(cloud,'#fff',.62,.090,'outside',.016)
    else:
        return None
    return L
