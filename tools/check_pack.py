from pathlib import Path
import re, sys, xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
for rel in ['app/src/main/AndroidManifest.xml','app/src/main/assets/appfilter.xml','app/src/main/assets/drawable.xml','app/src/main/res/xml/appfilter.xml','app/src/main/res/xml/drawable.xml']:
    ET.parse(root/rel)
icons={p.stem for p in (root/'app/src/main/res/drawable-nodpi').glob('*.png')}
text=(root/'app/src/main/assets/appfilter.xml').read_text(encoding='utf-8')
refs=set(re.findall(r'drawable="([a-zA-Z0-9_]+)"',text))
missing=sorted(refs-icons)
if missing:
    print('Missing drawable resources:', ', '.join(missing)); sys.exit(1)
cat=(root/'app/src/main/assets/drawable.xml').read_text(encoding='utf-8')
catrefs=set(re.findall(r'drawable="([a-zA-Z0-9_]+)"',cat))
if catrefs-icons:
    print('Catalog references missing icons:',sorted(catrefs-icons));sys.exit(1)
print(f'OK: {len(icons)} icons, {text.count("<item ")} component mappings, XML valid')
