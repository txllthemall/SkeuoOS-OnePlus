from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
for rel in [
    'app/src/main/AndroidManifest.xml',
    'app/src/main/assets/appfilter.xml',
    'app/src/main/assets/drawable.xml',
    'app/src/main/res/xml/appfilter.xml',
    'app/src/main/res/xml/drawable.xml',
]:
    ET.parse(root / rel)

text = (root / 'app/src/main/assets/appfilter.xml').read_text(encoding='utf-8')
refs = set(re.findall(r'drawable="([a-zA-Z0-9_]+)"', text))
cat = (root / 'app/src/main/assets/drawable.xml').read_text(encoding='utf-8')
catrefs = set(re.findall(r'drawable="([a-zA-Z0-9_]+)"', cat))
required = refs | catrefs

errors = []
counts = {}
for variant in ('color', 'clear'):
    icon_dir = root / f'app/src/{variant}/res/drawable-nodpi'
    icons = {p.stem for p in icon_dir.glob('*.png')}
    counts[variant] = len(icons)
    missing = sorted(required - icons)
    if missing:
        errors.append(f'{variant}: missing drawable resources: {", ".join(missing)}')
    for dens in ('mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi'):
        launcher = root / f'app/src/{variant}/res/mipmap-{dens}/ic_launcher.png'
        if not launcher.exists():
            errors.append(f'{variant}: missing launcher icon for {dens}')

if counts.get('color') != counts.get('clear'):
    errors.append(f'variant icon counts differ: color={counts.get("color")} clear={counts.get("clear")}')

if errors:
    for error in errors:
        print('ERROR', error)
    sys.exit(1)

print(f'OK: color={counts["color"]} icons, clear={counts["clear"]} icons, {text.count("<item ")} component mappings, XML valid')
