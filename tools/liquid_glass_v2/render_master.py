from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image, ImageChops

TOOLS=Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path: sys.path.insert(0,str(TOOLS))

from generate_liquid27 import render, _foreground_mask
from liquid27.catalog import ICON_SPECS
from liquid_glass_v2.static_android import render_static_icon
from liquid_glass_v2.preview_optics import render_optical_icon
from liquid_glass_v2.diagnostics import wallpaper, composite_center, make_lab

OUT=Path(__file__).resolve().parents[2]/'build/liquid-glass-v2'


def _old_github():
    bg,kind,_=ICON_SPECS['skeuo_github']
    return render('skeuo_github',bg,kind,'clear')


def _mask(size=512):
    return _foreground_mask('skeuo_github').resize((size,size),Image.Resampling.LANCZOS)


def _optical(kind='midtone', size=512, specular=True, rim=True):
    return render_optical_icon(wallpaper(kind,(size,size)),_mask(size),specular=specular,explicit_rim=rim)


def _side_by_side(old,new,bgkind='midtone'):
    bg=wallpaper(bgkind,(800,600)); left=bg.copy(); right=bg.copy()
    oldr=old.resize((260,260),Image.Resampling.LANCZOS); newr=new.resize((260,260),Image.Resampling.LANCZOS)
    left.paste(oldr,(270,170),oldr); right.paste(newr,(270,170),newr)
    board=Image.new('RGB',(1600,600)); board.paste(left,(0,0)); board.paste(right,(800,0)); return board


def _launcher_scale(icon):
    sizes=[48,64,72,96,128]
    board=Image.new('RGB',(900,660),(36,36,40))
    kinds=['dark','midtone','bright']
    for row,kind in enumerate(kinds):
        bg=wallpaper(kind,(900,220)); board.paste(bg,(0,row*220))
        for col,sz in enumerate(sizes):
            ic=icon.resize((sz,sz),Image.Resampling.LANCZOS)
            x=55+col*165+(128-sz)//2; y=row*220+(220-sz)//2
            board.paste(ic,(x,y),ic)
    return board


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    old=_old_github(); mask=_mask(512); new=render_static_icon(mask,512)

    make_lab(new).save(OUT/'preview_v2_master.png')
    for kind in ('dark','bright','midtone'):
        composite_center(wallpaper(kind,(900,900)),new,360).save(OUT/f'preview_v2_master_{kind}.png')

    nospec=render_static_icon(mask,512,no_specular=True)
    norim=render_static_icon(mask,512,no_rim=True)
    composite_center(wallpaper('midtone',(900,900)),nospec,360).save(OUT/'preview_v2_no_specular.png')
    composite_center(wallpaper('midtone',(900,900)),new,360).save(OUT/'preview_v2_no_shadow.png')
    composite_center(wallpaper('midtone',(900,900)),norim,360).save(OUT/'preview_v2_no_rim.png')
    new.save(OUT/'preview_v2_static_android.png')
    _launcher_scale(new).save(OUT/'preview_v2_launcher_scale.png')

    _side_by_side(old,new).save(OUT/'preview_v2_old_vs_new.png')
    _optical('midtone',768).save(OUT/'preview_v2_optical_midtone.png')
    _optical('highcontrast',768).save(OUT/'preview_v2_optical_stress.png')

    a=old.resize((512,512),Image.Resampling.LANCZOS).convert('RGBA')
    b=new.convert('RGBA')
    ImageChops.difference(a,b).convert('RGB').save(OUT/'preview_v2_difference_heatmap.png')
    print('Liquid Glass v2 GitHub master diagnostics generated:',OUT)


if __name__=='__main__': main()
