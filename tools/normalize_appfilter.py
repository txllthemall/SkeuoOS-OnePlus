from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'app/src/main/res/xml/appfilter.xml'
DESTINATIONS = [SOURCE, ROOT / 'app/src/main/assets/appfilter.xml']

# Explicit corrections for apps that have dedicated artwork in this pack.
FORCE = {
    'com.android.vending/com.google.android.finsky.activities.MainActivity': 'skeuo_playstore',
    'com.android.vending/com.android.vending.AssetBrowserActivity': 'skeuo_playstore',
    'com.google.android.keep/com.google.android.keep.activities.BrowseActivity': 'skeuo_google_keep',
    'com.google.android.calendar/com.android.calendar.AllInOneActivity': 'skeuo_google_calendar',
    'com.strava/com.strava.ui.splash.SplashActivity': 'skeuo_strava',
    'com.strava/com.strava.activityrecording.startup.LaunchActivity': 'skeuo_strava',
    'com.strava/com.strava.app.ui.splash.SplashActivity': 'skeuo_strava',
}

# A themed icon must represent the actual app. These previous aliases were
# semantically related but visually wrong on-device. Until they get dedicated
# artwork, OxygenOS should display the original app icon instead.
REMOVE_PACKAGES = {
    'md.obsidian',
    'notion.id',
    'com.microsoft.office.onenote',
    'com.microsoft.office.outlook',
    'me.proton.android.mail',
    'org.thunderbird.android',
    'com.waze',
    'net.osmand.plus',
    'com.aurora.store',
    'org.fdroid.fdroid',
    'deezer.android.app',
    'com.pandora.android',
    'xyz.blueskyweb.app',
}


def component_value(item):
    raw = item.attrib.get('component', '')
    if raw.startswith('ComponentInfo{') and raw.endswith('}'):
        return raw[len('ComponentInfo{'):-1]
    return raw


def main():
    tree = ET.parse(SOURCE)
    root = tree.getroot()
    removed = 0
    forced = 0

    for item in list(root.findall('item')):
        component = component_value(item)
        package = component.split('/', 1)[0]
        if package in REMOVE_PACKAGES:
            root.remove(item)
            removed += 1
            continue
        if component in FORCE:
            if item.attrib.get('drawable') != FORCE[component]:
                item.set('drawable', FORCE[component])
                forced += 1

    ET.indent(tree, space='    ')
    body = ET.tostring(root, encoding='unicode', short_empty_elements=True)
    text = '<?xml version="1.0" encoding="UTF-8"?>\n' + body + '\n'
    for path in DESTINATIONS:
        path.write_text(text, encoding='utf-8')

    print(f'Normalized appfilter: removed {removed} cross-brand aliases; corrected {forced} dedicated mappings')


if __name__ == '__main__':
    main()
