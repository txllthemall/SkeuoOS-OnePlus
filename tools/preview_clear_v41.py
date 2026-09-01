from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Importing the release driver patches generate_liquid27 so every icon resolves
# through the full SVG2048 geometry stack.
import generate_liquid27_release  # noqa: F401
import generate_liquid27 as gen
from liquid27.catalog import ICON_SPECS
from liquid27.material import FONT_REG

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/clear-v41-quick'
OUT.mkdir(parents=True, exist_ok=True)

NAMES = [
    'skeuo_gamehub', 'skeuo_github', 'skeuo_playstore', 'skeuo_kaspi',
    'skeuo_pinterest', 'skeuo_telegram', 'skeuo_gmail', 'skeuo_discord',
    'skeuo_facebook', 'skeuo_reddit', 'skeuo_tiktok', 'skeuo_whatsapp',
    'skeuo_twitter', 'skeuo_steam', 'skeuo_snapchat', 'skeuo_instagram',
    'skeuo_amazon', 'skeuo_paypal', 'skeuo_strava', 'skeuo_google_drive',
]

images = {}
for name in NAMES:
    bg, kind, _ = ICON_SPECS[name]
    images[name] = gen.render(name, bg, kind, 'clear')

w, h = 1080, 1320
font = ImageFont.truetype(FONT_REG, 22)


def draw_sheet(path, base, wallpaper=False):
    can = Image.new('RGB', (w, h), base)
    d = ImageDraw.Draw(can)
    if wallpaper:
        d.ellipse((-300, -250, 720, 650), fill='#c68f99')
        d.ellipse((520, -170, 1440, 690), fill='#7f789c')
        d.ellipse((360, 650, 1320, 1550), fill='#57485f')
        d.arc((-340, -280, 900, 700), 4, 132, fill=(244, 230, 234), width=5)
        d.arc((-180, 280, 1380, 1180), 4, 132, fill=(232, 220, 228), width=4)
    for i, name in enumerate(NAMES):
        x = 74 + (i % 4) * 246
        y = 70 + (i // 4) * 238
        icon = images[name].resize((126, 126), Image.Resampling.LANCZOS)
        can.paste(icon, (x, y), icon)
        label = name[6:].replace('_', ' ')[:14]
        bb = d.textbbox((0, 0), label, font=font)
        d.text((x + 63 - (bb[2] - bb[0]) / 2, y + 140), label, font=font, fill=(246, 245, 248))
    can.save(path)


draw_sheet(OUT / 'clear-v41-wallpaper.png', '#705d6d', wallpaper=True)
draw_sheet(OUT / 'clear-v41-flat.png', '#485165', wallpaper=False)
print(f'Wrote {len(images)} corrected-geometry Clear icons to {OUT}')
