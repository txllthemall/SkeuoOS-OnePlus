# SkeuoOS OnePlus

A self-contained skeuomorphic Android icon pack designed first for the stock OnePlus / OxygenOS launcher.

![preview](docs/preview.png)

## Current pack

- **66 original skeuomorphic icons** generated for this project
- **152 Android component mappings** including OnePlus/Oppo/ColorOS and common third-party apps
- OnePlus discovery intent: `net.oneplus.launcher.icons.ACTION_PICK_ICON`
- Standard `appfilter.xml` + `drawable.xml` in both `assets/` and `res/xml/`
- No ads, analytics, trackers, network permission, or background service
- Stock-launcher first; Nova/Lawnchair/Smart Launcher compatibility signals are also present

## Install on OnePlus / OxygenOS

1. Download the APK produced by GitHub Actions.
2. Install it.
3. Open **Settings → Wallpapers & style → Icons**.
4. Select **SkeuoOS**.
5. For an app whose exact activity is not known, long-press its icon and choose a SkeuoOS icon manually once.

## Build

The repository is intentionally dependency-light. You do not need Android Studio in CI.

```bash
python3 tools/check_pack.py
gradle :app:assembleDebug
```

GitHub Actions installs Android API 36 and Gradle 8.13 and publishes the installable APK as an artifact on every push. Tags matching `v*` create a GitHub Release.

## Adding icons

Generated artwork lives in `app/src/main/res/drawable-nodpi`. Add its resource name to `assets/drawable.xml` and add app components to `appfilter.xml`. Run `python3 tools/check_pack.py` before pushing.

The starter set includes mappings for the apps visible in the target OnePlus setup: Discord, Google Play, YouTube/ReVanced, Kaspi, 2GIS, Photos/Gallery, Gmail, SoundCloud, Telegram, Recorder, Phone, Messages, Camera and Chrome, plus a wider common-app catalog.

## Artwork / provenance

All PNG artwork in this repository is generated specifically for SkeuoOS and is not copied from Apple's iOS asset files or the unlicensed `zagnut531/iOS-6-Icons` repository. The visual direction is generic early-2010s skeuomorphism: rounded glossy tiles, bevels, shadows and dimensional glyphs. Brand names may be trademarks of their owners; this project is not affiliated with Apple, OnePlus, Google or the mapped apps.

## License

MIT for code and generated project artwork, subject to third-party trademarks.
