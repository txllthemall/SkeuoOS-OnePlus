from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

import generate_liquid27_v41 as v41
import generate_liquid27 as gen
from liquid27.catalog import ICON_SPECS
from liquid27.material import FONT_REG

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/clear-v41-quick'
OUT.mkdir(parents=True, exist_ok=True)

NAMES = [
    'skeuo_phone', 'skeuo_messages', 'skeuo_camera', 'skeuo_photos',
    'skeuo_settings', 'skeuo_mail', 'skeuo_gmail', 'skeuo_maps',
    'skeuo_clock', 'skeuo_weather', 'skeuo_notes', 'skeuo_calendar',
    'skeuo_appstore', 'skeuo_telegram', 'skeuo_discord', 'skeuo_youtube',
    'skeuo_chrome', 'skeuo_spotify', 'skeuo_instagram', 'skeuo_chatgpt',
]

images = {}
for name in NAMES:
    bg, kind, _ = ICON_SPECS[name]
    images[name] = v41.render(name, bg, kind, 'clear')

# Dark colorful field to expose real alpha and reflection variation.
w, h = 1080, 1320
wall = Image.new('RGB', (w, h), '#182236')
d = ImageDraw.Draw(wall)
d.ellipse((-260, -180, 650, 650), fill='#603753')
d.ellipse((500, -220, 1370, 650), fill='#253d78')
d.ellipse((380, 690, 1280, 1550), fill='#75452d')
font = ImageFont.truetype(FONT_REG, 22)
for i, name in enumerate(NAMES):
    x = 74 + (i % 4) * 246
    y = 88 + (i // 4) * 230
    icon = images[name].resize((126, 126), Image.Resampling.LANCZOS)
    wall.paste(icon, (x, y), icon)
    label = name[6:].replace('_', ' ')[:13]
    bb = d.textbbox((0, 0), label, font=font)
    d.text((x + 63 - (bb[2] - bb[0]) / 2, y + 140), label, font=font, fill=(245, 245, 248))
wall.save(OUT / 'clear-v41-wallpaper.png')

# Flat field makes non-uniform density/reflection easy to diagnose.
flat = Image.new('RGB', (w, h), '#485165')
d = ImageDraw.Draw(flat)
for i, name in enumerate(NAMES):
    x = 74 + (i % 4) * 246
    y = 88 + (i // 4) * 230
    icon = images[name].resize((126, 126), Image.Resampling.LANCZOS)
    flat.paste(icon, (x, y), icon)
    label = name[6:].replace('_', ' ')[:13]
    bb = d.textbbox((0, 0), label, font=font)
    d.text((x + 63 - (bb[2] - bb[0]) / 2, y + 140), label, font=font, fill=(245, 245, 248))
flat.save(OUT / 'clear-v41-flat.png')

print(f'Wrote {len(images)}-icon quick Clear preview to {OUT}')
