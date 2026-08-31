from pathlib import Path
import json, sys, statistics
ROOT=Path(__file__).resolve().parents[1]
report=ROOT/'build/liquid27-v4/qa.json'
if not report.exists(): raise SystemExit('Missing v4 QA report; run tools/generate_liquid27.py first')
rows=json.loads(report.read_text(encoding='utf-8'))
if len(rows)<30: raise SystemExit(f'Only {len(rows)} QA rows; expected complete icon pack')
coverage=[r['coverage_pct'] for r in rows]; contrast=[r['contrast_estimate'] for r in rows]; median=statistics.median(coverage)
errors=[]; warnings=[]
for r in rows:
    x,y=r['center_offset_pct']; c=r['coverage_pct']; k=r['contrast_estimate']
    if abs(x)>15 or abs(y)>15: errors.append(f"{r['icon']}: optical center offset {x},{y}%")
    if c<2.5 or c>70: errors.append(f"{r['icon']}: extreme foreground coverage {c}%")
    elif c<5.5 or c>55: warnings.append(f"{r['icon']}: foreground coverage {c}% vs median {median}%")
    if k<0.18: warnings.append(f"{r['icon']}: low contrast estimate {k}")
for name in ['preview_full.png','preview_light.png','preview_dark.png','preview_wallpaper.png','preview_home.png']:
    p=ROOT/'build/liquid27-v4'/name
    if not p.exists() or p.stat().st_size<10000: errors.append(f'Missing/invalid preview {name}')
print(f'Liquid27 QA: {len(rows)} icons; median coverage {median:.1f}%; mean contrast {statistics.mean(contrast):.3f}')
for w in warnings: print('WARN',w)
if errors:
    for e in errors: print('ERROR',e)
    sys.exit(1)
print('Liquid27 QA passed')
