from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps, ImageFont
import math
import numpy as np

DESIGN=1536.0
WORK=1024
OUT=512
K=WORK/DESIGN
C=DESIGN/2
FONT_REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def sx(v): return int(round(v*K))
def sbox(b): return tuple(sx(v) for v in b)
def spts(pts): return [(sx(x),sx(y)) for x,y in pts]
def rgb(v):
    if isinstance(v,(tuple,list)): return tuple(v[:3])
    v=v.lstrip('#'); v=''.join(ch*2 for ch in v) if len(v)==3 else v; return tuple(int(v[i:i+2],16) for i in (0,2,4))
def mix(a,b,t):
    a,b=rgb(a),rgb(b); return tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3))
def luminance(c):
    r,g,b=rgb(c); return .2126*r+.7152*g+.0722*b


def blank_mask(): return Image.new('L',(WORK,WORK),0)
def rr(box,radius):
    m=blank_mask(); ImageDraw.Draw(m).rounded_rectangle(sbox(box),radius=sx(radius),fill=255); return m
def ellipse(box):
    m=blank_mask(); ImageDraw.Draw(m).ellipse(sbox(box),fill=255); return m
def poly(points):
    m=blank_mask(); ImageDraw.Draw(m).polygon(spts(points),fill=255); return m
def line(points,width):
    m=blank_mask(); ImageDraw.Draw(m).line(spts(points),fill=255,width=max(1,sx(width)),joint='curve'); return m
def arc(box,start,end,width):
    m=blank_mask(); ImageDraw.Draw(m).arc(sbox(box),start,end,fill=255,width=max(1,sx(width))); return m
def union(*masks):
    out=blank_mask()
    for m in masks: out=ImageChops.lighter(out,m)
    return out
def sub(a,b): return ImageChops.subtract(a,b)
def inter(a,b): return ImageChops.multiply(a,b)
def rotate(m,deg,center=(C,C)):
    return m.rotate(deg,center=(sx(center[0]),sx(center[1])),resample=Image.Resampling.BICUBIC)

def scale_mask(mask,factor):
    if abs(factor-1.0)<1e-6: return mask
    size=max(1,int(WORK*factor)); r=mask.resize((size,size),Image.Resampling.BICUBIC)
    out=blank_mask(); x=(WORK-size)//2; y=(WORK-size)//2
    if size<=WORK: out.paste(r,(x,y)); return out
    crop=(-x,-y,-x+WORK,-y+WORK); return r.crop(crop)

def shifted(m,dx=0,dy=0):
    # Non-wrapping shift.
    out=blank_mask(); dx=sx(dx); dy=sx(dy)
    src=(max(0,-dx),max(0,-dy),min(WORK,WORK-dx),min(WORK,WORK-dy))
    if src[2] > src[0] and src[3] > src[1]:
        out.paste(m.crop(src),(max(0,dx),max(0,dy)))
    return out

# Apple applies enclosure shape dynamically. Android needs a flattened asset, so this is only an alpha crop.
# No visible frame, bevel, stroke, or shell is baked into the icon.
ENCL = rr((54,54,1482,1482),340)


def solid_bg(color):
    im=Image.new('RGBA',(WORK,WORK),(*rgb(color),255)); im.putalpha(ENCL); return im

def linear_bg(a,b,angle=0):
    grad=Image.linear_gradient('L').resize((WORK,WORK),Image.Resampling.BICUBIC)
    if angle: grad=grad.rotate(angle,resample=Image.Resampling.BICUBIC)
    im=ImageOps.colorize(grad,rgb(a),rgb(b)).convert('RGBA'); im.putalpha(ENCL); return im

def radial_bg(colors):
    # Full-canvas Gaussian color pools: no clipped rectangles or hard seams.
    h=w=WORK
    yy,xx=np.mgrid[0:h,0:w]
    arr=np.zeros((h,w,3),dtype=np.float32)
    arr[:]=np.array(rgb(colors[0]),dtype=np.float32)
    centers=[(.30,.20,.36),(.78,.30,.34),(.48,.82,.36)]
    for idx,col in enumerate(colors[1:]):
        cx,cy,sigma=centers[idx%len(centers)]
        dx=(xx/w-cx); dy=(yy/h-cy)
        weight=np.exp(-(dx*dx+dy*dy)/(2*sigma*sigma))*0.76
        c=np.array(rgb(col),dtype=np.float32)
        arr=arr*(1-weight[...,None])+c*weight[...,None]
    arr=np.clip(arr,0,255).astype(np.uint8)
    im=Image.fromarray(arr,'RGB').convert('RGBA'); im.putalpha(ENCL); return im

def background(spec):
    kind=spec.get('type','solid'); cols=spec.get('colors',[spec.get('color','#777')])
    if kind=='linear': return linear_bg(cols[0],cols[-1],spec.get('angle',0))
    if kind=='radial': return radial_bg(cols)
    return solid_bg(cols[0])


def affine_refract(under, mask, strength=.045, offset=(0,0), blur=0):
    # Static approximation of Icon Composer refraction using the ACTUAL composited pixels beneath a layer.
    bb=mask.getbbox()
    if not bb: return Image.new('RGBA',(WORK,WORK),(0,0,0,0))
    cx=(bb[0]+bb[2])/2; cy=(bb[1]+bb[3])/2
    scale=1+max(0,strength)
    a=1/scale; e=1/scale
    c=cx-cx*a-sx(offset[0]); f=cy-cy*e-sx(offset[1])
    refr=under.transform((WORK,WORK),Image.Transform.AFFINE,(a,0,c,0,e,f),resample=Image.Resampling.BICUBIC)
    if blur: refr=refr.filter(ImageFilter.GaussianBlur(max(.1,sx(blur))))
    refr.putalpha(mask)
    return refr

def top_edge(mask,width=7): return sub(mask,shifted(mask,0,width))
def bottom_edge(mask,width=4): return sub(mask,shifted(mask,0,-width))
def outer_edge(mask,width=5):
    w=max(3,sx(width)*2+1); w=w if w%2 else w+1
    return sub(mask.filter(ImageFilter.MaxFilter(w)),mask)
def inner_edge(mask,width=5):
    w=max(3,sx(width)*2+1); w=w if w%2 else w+1
    return sub(mask,mask.filter(ImageFilter.MinFilter(w)))

def composite_layer(canvas, mask, *, fill='#ffffff', material='glass', opacity=.78,
                    refraction=.045, refract_offset=(0,0), blur=0, specular='automatic',
                    shadow=.055, blend='normal'):
    under=canvas.copy()
    if shadow:
        sm=shifted(mask,0,9).filter(ImageFilter.GaussianBlur(max(1,sx(11))))
        sm=sm.point(lambda v:int(v*shadow*1.10))
        s=Image.new('RGBA',(WORK,WORK),(0,0,0,0)); sh=Image.new('RGBA',(WORK,WORK),(0,0,0,255)); sh.putalpha(sm); s.alpha_composite(sh); canvas.alpha_composite(s)

    layer=Image.new('RGBA',(WORK,WORK),(0,0,0,0))
    if material=='glass':
        layer.alpha_composite(affine_refract(under,mask,refraction,refract_offset,blur))
        # iOS 27 is less translucent than iOS 26. Tint remains saturated, without milky white overlay.
        tint=Image.new('RGBA',(WORK,WORK),(*rgb(fill),0)); tint.putalpha(mask.point(lambda v:int(v*opacity))); layer.alpha_composite(tint)
        mode=specular
        if mode=='automatic': mode='inside' if luminance(fill)>145 else 'outside'
        if mode!='off':
            if mode=='inside': hi=top_edge(mask,7)
            else:
                hi=outer_edge(mask,5)
                vertical=Image.linear_gradient('L').resize((WORK,WORK))
                vertical=ImageOps.invert(vertical).point(lambda v:int(v*.82))
                hi=inter(hi,vertical)
            hi=hi.point(lambda v:int(v*.58))
            white=Image.new('RGBA',(WORK,WORK),(255,255,255,0)); white.putalpha(hi); layer.alpha_composite(white)
            lo=bottom_edge(mask,4).point(lambda v:int(v*.11))
            dk=Image.new('RGBA',(WORK,WORK),(0,0,0,0)); dk.putalpha(lo); layer.alpha_composite(dk)
    else:
        tint=Image.new('RGBA',(WORK,WORK),(*rgb(fill),0)); tint.putalpha(mask.point(lambda v:int(v*opacity))); layer.alpha_composite(tint)

    alpha=layer.getchannel('A')
    if blend=='screen': canvas.paste(ImageChops.screen(canvas,layer),(0,0),alpha)
    elif blend=='multiply': canvas.paste(ImageChops.multiply(canvas,layer),(0,0),alpha)
    else: canvas.alpha_composite(layer)


def text_mask(text,size=420,yoff=0,bold=True):
    f=ImageFont.truetype(FONT_BOLD if bold else FONT_REG,sx(size))
    m=blank_mask(); d=ImageDraw.Draw(m); box=d.textbbox((0,0),text,font=f)
    x=(WORK-(box[2]-box[0]))/2-box[0]; y=(WORK-(box[3]-box[1]))/2-box[1]+sx(yoff)
    d.text((x,y),text,font=f,fill=255); return m


def layer(mask,fill='#fff',opacity=.78,refraction=.045,specular='automatic',shadow=.055,material='glass',blend='normal',offset=(0,0),blur=0):
    return dict(mask=mask,fill=fill,opacity=opacity,refraction=refraction,specular=specular,shadow=shadow,material=material,blend=blend,refract_offset=offset,blur=blur)
