from __future__ import annotations

from io import BytesIO
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import shutil
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image, ImageFile

# A chunk of the upstream collection contains valid-looking PNGs with truncated
# streams. Pillow can recover most of them safely enough for icon use.
ImageFile.LOAD_TRUNCATED_IMAGES = True

ROOT = Path(__file__).resolve().parents[1]
DRAWABLE = ROOT / "app/src/main/res/drawable-nodpi"
ASSET_CATALOG = ROOT / "app/src/main/assets/drawable.xml"
RES_CATALOG = ROOT / "app/src/main/res/xml/drawable.xml"
REPORT = ROOT / "build/ios6-import-report.json"

UPSTREAM = os.environ.get(
    "IOS6_UPSTREAM_ZIP",
    "https://codeload.github.com/zagnut531/iOS-6-Icons/zip/refs/heads/main",
)
MAX_DIM = int(os.environ.get("IOS6_MAX_DIM", "512"))
VALID_EXTS = {".png", ".jpg", ".jpeg"}
TOP_LEVEL_DIRS = {
    "3rd-party icons",
    "Apple icons",
    "iPad",
    "iPhone & iPod touch",
}

CATEGORY_SCORE = {
    "iPhone & iPod touch": 40,
    "Apple icons": 35,
    "3rd-party icons": 30,
    "iPad": 20,
}

OVERLAYS = {
    "skeuo_phone": ["phone"],
    "skeuo_messages": ["messages", "message"],
    "skeuo_camera": ["camera"],
    "skeuo_photos": ["photos", "photo"],
    "skeuo_settings": ["settings", "preferences"],
    "skeuo_mail": ["mail"],
    "skeuo_maps": ["maps", "map"],
    "skeuo_clock": ["clock"],
    "skeuo_weather": ["weather"],
    "skeuo_notes": ["notes", "note"],
    "skeuo_calendar": ["calendar"],
    "skeuo_appstore": ["app store", "appstore"],
    "skeuo_facetime": ["facetime"],
    "skeuo_music": ["music", "ipod"],
    "skeuo_wallet": ["passbook", "wallet"],
    "skeuo_files": ["files"],
    "skeuo_calculator": ["calculator"],
    "skeuo_health": ["health"],
    "skeuo_compass": ["compass"],
    "skeuo_recorder": ["voice memos", "voice memo", "recorder"],
    "skeuo_chrome": ["chrome", "google chrome"],
    "skeuo_youtube": ["youtube"],
    "skeuo_telegram": ["telegram"],
    "skeuo_discord": ["discord"],
    "skeuo_instagram": ["instagram"],
    "skeuo_twitter": ["twitter"],
    "skeuo_whatsapp": ["whatsapp", "whats app"],
    "skeuo_facebook": ["facebook"],
    "skeuo_snapchat": ["snapchat"],
    "skeuo_reddit": ["reddit", "alien blue"],
    "skeuo_pinterest": ["pinterest"],
    "skeuo_spotify": ["spotify"],
    "skeuo_netflix": ["netflix"],
    "skeuo_amazon": ["amazon shopping", "amazon"],
    "skeuo_uber": ["uber"],
    "skeuo_paypal": ["paypal"],
    "skeuo_shazam": ["shazam"],
    "skeuo_soundcloud": ["soundcloud", "sound cloud"],
    "skeuo_steam": ["steam"],
}


def ascii_slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "icon"


def canonical_name(text: str) -> str:
    s = ascii_slug(text).replace("_", " ")
    noise = [
        "itunes artwork", "app icon", "icon", "2x", "3x",
        "iphone", "ipad", "ipod touch", "retina", "cropped",
    ]
    for token in noise:
        s = re.sub(rf"\b{re.escape(token)}\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def resource_name(rel: PurePosixPath) -> str:
    top = ascii_slug(rel.parts[0])[:18]
    stem = ascii_slug(rel.stem)[:46]
    digest = hashlib.sha1(str(rel).encode("utf-8")).hexdigest()[:8]
    return f"ios6_{top}_{stem}_{digest}"


def download_archive() -> bytes:
    req = urllib.request.Request(
        UPSTREAM,
        headers={"User-Agent": "SkeuoOS-OnePlus-CI/0.2"},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        data = response.read()
    print(f"Downloaded upstream archive: {len(data) / 1024 / 1024:.1f} MiB")
    return data


def clean_previous_import() -> None:
    DRAWABLE.mkdir(parents=True, exist_ok=True)
    for p in DRAWABLE.glob("ios6_*.png"):
        p.unlink()


def save_image(raw: bytes, out: Path) -> tuple[int, int]:
    with Image.open(BytesIO(raw)) as source:
        source.load()
        image = source.convert("RGBA")
    if max(image.size) > MAX_DIM:
        image.thumbnail((MAX_DIM, MAX_DIM), Image.Resampling.LANCZOS)
    image.save(out, format="PNG", optimize=True)
    return image.size


def score_overlay(record: dict, aliases: list[str]) -> int:
    name = record["canonical"]
    score = CATEGORY_SCORE.get(record["category"], 0)
    for alias in aliases:
        alias = canonical_name(alias)
        if name == alias:
            score += 200
        elif name.startswith(alias + " ") or name.endswith(" " + alias):
            score += 140
        elif alias in name:
            score += 80
    score += min(record["source_pixels"] // 10000, 25)
    return score


def update_catalog(records_by_category: dict[str, list[dict]]) -> None:
    tree = ET.parse(ASSET_CATALOG)
    root = tree.getroot()
    for child in list(root):
        if child.tag == "item" and child.attrib.get("drawable", "").startswith("ios6_"):
            root.remove(child)
        elif child.tag == "category" and child.attrib.get("title", "").startswith("iOS 6 —"):
            root.remove(child)

    for category in sorted(records_by_category):
        ET.SubElement(root, "category", {"title": f"iOS 6 — {category}"})
        for record in sorted(records_by_category[category], key=lambda r: r["source"].lower()):
            ET.SubElement(root, "item", {"drawable": record["resource"]})

    ET.indent(tree, space="    ")
    tree.write(ASSET_CATALOG, encoding="UTF-8", xml_declaration=True)
    shutil.copy2(ASSET_CATALOG, RES_CATALOG)


def main() -> None:
    clean_previous_import()
    archive = download_archive()
    records: list[dict] = []
    failures: list[dict] = []

    with zipfile.ZipFile(BytesIO(archive)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            path = PurePosixPath(info.filename)
            if len(path.parts) < 3:
                continue
            category = path.parts[1]
            if category not in TOP_LEVEL_DIRS or path.suffix.lower() not in VALID_EXTS:
                continue

            rel = PurePosixPath(*path.parts[1:])
            resource = resource_name(rel)
            out = DRAWABLE / f"{resource}.png"
            try:
                raw = zf.read(info)
                with Image.open(BytesIO(raw)) as probe:
                    source_size = probe.size
                final_size = save_image(raw, out)
            except Exception as exc:
                failures.append({"source": str(rel), "error": str(exc)})
                continue

            records.append({
                "source": str(rel),
                "category": category,
                "resource": resource,
                "canonical": canonical_name(rel.stem),
                "source_size": source_size,
                "source_pixels": source_size[0] * source_size[1],
                "final_size": final_size,
            })

    by_category: dict[str, list[dict]] = {}
    for record in records:
        by_category.setdefault(record["category"], []).append(record)
    update_catalog(by_category)

    overlay_report: dict[str, str] = {}
    for target, aliases in OVERLAYS.items():
        ranked = sorted(
            ((score_overlay(r, aliases), r) for r in records),
            key=lambda pair: pair[0],
            reverse=True,
        )
        if not ranked or ranked[0][0] < 100:
            continue
        best = ranked[0][1]
        shutil.copy2(DRAWABLE / f"{best['resource']}.png", DRAWABLE / f"{target}.png")
        overlay_report[target] = best["source"]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "upstream": "zagnut531/iOS-6-Icons",
        "upstream_url": "https://github.com/zagnut531/iOS-6-Icons",
        "imported_icons": len(records),
        "failed_images": failures,
        "categories": {k: len(v) for k, v in sorted(by_category.items())},
        "automatic_overlays": overlay_report,
        "max_dimension": MAX_DIM,
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Imported {len(records)} upstream icon files into the picker")
    for category, count in report["categories"].items():
        print(f"  {category}: {count}")
    print(f"Applied {len(overlay_report)} upstream icons to existing automatic mappings")
    for target, source in sorted(overlay_report.items()):
        print(f"  {target} <- {source}")
    if failures:
        print(f"Skipped {len(failures)} unreadable image files")

    if not records:
        raise SystemExit("No upstream iOS 6 icons were imported")


if __name__ == "__main__":
    main()
