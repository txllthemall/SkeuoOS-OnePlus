from __future__ import annotations

# Geometry provenance is explicit for release-gate brands. optical_* documents
# the intentional launcher-scale correction applied before Cairo rasterisation.
META = {
    'gamehub': dict(source='GameSir official current GameHub app icon; filled compound-SVG reconstruction', optical_dx=0.0, optical_dy=0.0, optical_scale=1.08),
    'github': dict(source='Simple Icons GitHub mark (CC0)', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'playstore': dict(source='Google Play four-face product mark; canonical vector sections', optical_dx=5.7, optical_dy=0.0, optical_scale=1.02),
    'kaspi': dict(source='Kaspi.kz circular brand artwork; verified vector emblem', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'pinterest': dict(source='Simple Icons Pinterest mark (CC0)', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'telegram': dict(source='Telegram paper-plane brand silhouette; SVG path', optical_dx=-6.0, optical_dy=0.0, optical_scale=1.04),
    'gmail': dict(source='Gmail M-envelope product mark; SVG silhouette', optical_dx=0.0, optical_dy=0.2, optical_scale=1.06),
    'discord': dict(source='Discord brand controller mark; continuous SVG geometry', optical_dx=0.0, optical_dy=0.3, optical_scale=1.00),
    'facebook': dict(source='Simple Icons Facebook mark (CC0)', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'reddit': dict(source='Simple Icons Reddit mark (CC0)', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'tiktok': dict(source='Simple Icons TikTok mark (CC0)', optical_dx=0.0, optical_dy=0.0, optical_scale=.98),
    'whatsapp': dict(source='Simple Icons WhatsApp mark (CC0)', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'twitter': dict(source='Simple Icons X mark (CC0)', optical_dx=0.0, optical_dy=0.0, optical_scale=.98),
    'steam': dict(source='Simple Icons Steam mark (CC0)', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'snapchat': dict(source='Simple Icons Snapchat ghost mark (CC0)', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'instagram': dict(source='Instagram camera brand silhouette; SVG geometry', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'amazon': dict(source='Amazon full a + smile/arrow vector mark', optical_dx=0.0, optical_dy=0.5, optical_scale=1.10),
    'paypal': dict(source='PayPal brand P silhouette; SVG path', optical_dx=0.0, optical_dy=0.0, optical_scale=.94),
    'strava': dict(source='Strava brand chevrons; SVG path', optical_dx=0.0, optical_dy=0.0, optical_scale=1.08),
    'drive': dict(source='Google Drive three-face product mark; SVG geometry', optical_dx=0.0, optical_dy=-1.6, optical_scale=1.00),
    'chatgpt': dict(source='OpenAI knot semantic mark; project continuous SVG adaptation', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'spotify': dict(source='Spotify wave semantic mark; project SVG geometry', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'youtube': dict(source='YouTube play-button product mark; project SVG geometry', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'revanced': dict(source='ReVanced play-chevron semantic mark; project SVG geometry', optical_dx=5.3, optical_dy=0.0, optical_scale=1.00),
    'chrome': dict(source='Chromium/Chrome circular product mark; SVG path', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'soundcloud': dict(source='Simple Icons SoundCloud mark (CC0)', optical_dx=0.0, optical_dy=0.0, optical_scale=1.13),
    'twogis': dict(source='2GIS map-pin semantic mark; project SVG geometry', optical_dx=0.0, optical_dy=0.0, optical_scale=1.00),
    'weather': dict(source='System weather semantic SVG layers', optical_dx=0.0, optical_dy=-8.5, optical_scale=1.00),
    'appstore': dict(source='System App Store semantic SVG construction', optical_dx=0.0, optical_dy=0.0, optical_scale=1.12),
}


def geometry_meta(kind: str) -> dict:
    meta = META.get(kind)
    if meta is None:
        meta = dict(
            source='SkeuoOS original SVG2048 geometry',
            optical_dx=0.0,
            optical_dy=0.0,
            optical_scale=1.0,
        )
    return dict(meta)
