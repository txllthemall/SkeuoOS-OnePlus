# SkeuoOS Liquid27 for OnePlus

Android icon packs for the stock OnePlus / OxygenOS launcher, built around a shared SVG2048 geometry engine and a layer-based static Liquid Glass renderer.

## v4.0.0 — two APKs, one geometry system

### SkeuoOS Liquid27

The normal daily-use build:

- colored backgrounds and brand-aware glass
- stronger contrast and readability
- package id `io.github.txllthemall.skeuoos`

### SkeuoOS Liquid27 Clear

The transparent glass build:

- same glyph geometry and the same Android mappings
- low-chroma neutral glass instead of brand-colored material
- partially transparent enclosure and foreground layers
- lets the real OxygenOS wallpaper remain visible through PNG alpha
- separate package id `io.github.txllthemall.skeuoos.clear`, so Color and Clear can be installed together

A static Android PNG cannot perform real-time wallpaper refraction. Clear therefore uses actual transparency rather than pretending that a baked gradient is live wallpaper refraction.

## Geometry

The core reference set no longer uses the early v4 Pillow polygon/bitmap-rotation shortcuts. SVG paths and primitives are rasterized by Cairo at **2048×2048**, passed into the material renderer, and finally downsampled to **512×512** with Lanczos.

The SVG/Home Screen set includes Phone, Messages, Camera, Photos, Settings, Mail, Gmail, Telegram, Discord, YouTube, Spotify, Instagram, ChatGPT, Maps, Google Maps, Clock, Weather, Notes, Calendar, Google Calendar, App Store, ReVanced, Chrome, Recorder, SoundCloud, Kaspi, 2GIS, GameHub, Play Store and Google Photos. The remaining catalog is being migrated away from transitional geometry.

### Gmail is not Mail

Gmail has its own `gmail` geometry kind and its own Android mappings. In the Color build it is rendered as a dedicated multicolor glass **M**. Clear keeps that same M geometry but applies the neutral clear-glass material. It never reuses the generic `mail` envelope glyph.

## Pack coverage

- 66 generated icons
- 152 Android component mappings
- OnePlus discovery intent: `net.oneplus.launcher.icons.ACTION_PICK_ICON`
- `appfilter.xml` and `drawable.xml` in both `assets/` and `res/xml/`
- no ads, analytics, trackers, network permission or background service
- no `zagnut531/iOS-6-Icons` import in v4

## Install on OnePlus / OxygenOS

1. Download either or both APKs from Releases.
2. Install the APK.
3. Open **Settings → Wallpapers & style → Icons**.
4. Select **SkeuoOS Liquid27** or **SkeuoOS Liquid27 Clear**.
5. If an app does not match automatically, long-press its icon and choose a pack icon manually.

## Build

```bash
python3 -m pip install -r tools/requirements.txt
python3 tools/generate_liquid27.py --variant all
python3 tools/qa_liquid27.py --variant all
python3 tools/check_pack.py
gradle :app:assembleColorDebug :app:assembleClearDebug
```

Generated resources:

```text
app/src/color/res/
app/src/clear/res/
```

Previews and QA:

```text
build/liquid27-v4/color/
build/liquid27-v4/clear/
```

## Design notes

See `DESIGN_NOTES.md` for the official Apple documentation used as reference, material approximations, vector-source licensing, Clear-mode limitations and QA policy.

## License

MIT applies to project code and original generated artwork, subject to third-party licenses, trademarks and brand identifiers noted in `DESIGN_NOTES.md`. This project is not affiliated with Apple, OnePlus, Google or the represented apps.
