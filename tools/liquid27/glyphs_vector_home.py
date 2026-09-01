from __future__ import annotations

from .material import layer, text_mask
from .vector import (
    circle_mask,
    path_mask,
    rounded_rect_mask,
    stroked_path_mask,
    svg_mask,
)
from .glyphs_vector import glyph_vector

HOME_VECTOR_KINDS = {
    'gmail', 'maps', 'google_maps', 'clock', 'weather', 'notes', 'calendar',
    'google_calendar', 'appstore', 'revanced', 'chrome', 'recorder',
    'soundcloud', 'kaspi', 'twogis', 'gamehub', 'playstore', 'google_photos',
}

GMAIL_D = 'M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z'
GOOGLE_MAPS_D = 'M19.527 4.799c1.212 2.608.937 5.678-.405 8.173-1.101 2.047-2.744 3.74-4.098 5.614-.619.858-1.244 1.75-1.669 2.727-.141.325-.263.658-.383.992-.121.333-.224.673-.34 1.008-.109.314-.236.684-.627.687h-.007c-.466-.001-.579-.53-.695-.887-.284-.874-.581-1.713-1.019-2.525-.51-.944-1.145-1.817-1.79-2.671L19.527 4.799zM8.545 7.705l-3.959 4.707c.724 1.54 1.821 2.863 2.871 4.18.247.31.494.622.737.936l4.984-5.925-.029.01c-1.741.601-3.691-.291-4.392-1.987a3.377 3.377 0 0 1-.209-.716c-.063-.437-.077-.761-.004-1.198l.001-.007zM5.492 3.149l-.003.004c-1.947 2.466-2.281 5.88-1.117 8.77l4.785-5.689-.058-.05-3.607-3.035zM14.661.436l-3.838 4.563a.295.295 0 0 1 .027-.01c1.6-.551 3.403.15 4.22 1.626.176.319.323.683.377 1.045.068.446.085.773.012 1.22l-.003.016 3.836-4.561A8.382 8.382 0 0 0 14.67.439l-.009-.003zM9.466 5.868L14.162.285l-.047-.012A8.31 8.31 0 0 0 11.986 0a8.439 8.439 0 0 0-6.169 2.766l-.016.018 3.665 3.084z'
CHROME_D = 'M12 0C8.21 0 4.831 1.757 2.632 4.501l3.953 6.848A5.454 5.454 0 0 1 12 6.545h10.691A12 12 0 0 0 12 0zM1.931 5.47A11.943 11.943 0 0 0 0 12c0 6.012 4.42 10.991 10.189 11.864l3.953-6.847a5.45 5.45 0 0 1-6.865-2.29zm13.342 2.166a5.446 5.446 0 0 1 1.45 7.09l.002.001h-.002l-5.344 9.257c.206.01.413.016.621.016 6.627 0 12-5.373 12-12 0-1.54-.29-3.011-.818-4.364zM12 16.364a4.364 4.364 0 1 1 0-8.728 4.364 4.364 0 0 1 0 8.728Z'
SOUNDCLOUD_D = 'M23.999 14.165c-.052 1.796-1.612 3.169-3.4 3.169h-8.18a.68.68 0 0 1-.675-.683V7.862a.747.747 0 0 1 .452-.724s.75-.513 2.333-.513a5.364 5.364 0 0 1 2.763.755 5.433 5.433 0 0 1 2.57 3.54c.282-.08.574-.121.868-.12.884 0 1.73.358 2.347.992s.948 1.49.922 2.373ZM10.721 8.421c.247 2.98.427 5.697 0 8.672a.264.264 0 0 1-.53 0c-.395-2.946-.22-5.718 0-8.672a.264.264 0 0 1 .53 0ZM9.072 9.448c.285 2.659.37 4.986-.006 7.655a.277.277 0 0 1-.55 0c-.331-2.63-.256-5.02 0-7.655a.277.277 0 0 1 .556 0Zm-1.663-.257c.27 2.726.39 5.171 0 7.904a.266.266 0 0 1-.532 0c-.38-2.69-.257-5.21 0-7.904a.266.266 0 0 1 .532 0Zm-1.647.77a26.108 26.108 0 0 1-.008 7.147.272.272 0 0 1-.542 0 27.955 27.955 0 0 1 0-7.147.275.275 0 0 1 .55 0Zm-1.67 1.769c.421 1.865.228 3.5-.029 5.388a.257.257 0 0 1-.514 0c-.21-1.858-.398-3.549 0-5.389a.272.272 0 0 1 .543 0Zm-1.655-.273c.388 1.897.26 3.508-.01 5.412-.026.28-.514.283-.54 0-.244-1.878-.347-3.54-.01-5.412a.283.283 0 0 1 .56 0Zm-1.668.911c.4 1.268.257 2.292-.026 3.572a.257.257 0 0 1-.514 0c-.241-1.262-.354-2.312-.023-3.572a.283.283 0 0 1 .563 0Z'
GOOGLE_PLAY_D = 'M22.018 13.298l-3.919 2.218-3.515-3.493 3.543-3.521 3.891 2.202a1.49 1.49 0 0 1 0 2.594zM1.337.924a1.486 1.486 0 0 0-.112.568v21.017c0 .217.045.419.124.6l11.155-11.087L1.337.924zm12.207 10.065l3.258-3.238L3.45.195a1.466 1.466 0 0 0-.946-.179l11.04 10.973zm0 2.067l-11 10.933c.298.036.612-.016.906-.183l13.324-7.54-3.23-3.21z'
CLOUD_D = 'M11.473 11a4.5 4.5 0 0 0-8.72-.99A3 3 0 0 0 3 16h8.5a2.5 2.5 0 0 0 0-5z'
SUN_D = 'M10.5 1.5a.5.5 0 0 0-1 0v1a.5.5 0 0 0 1 0zm3.743 1.964a.5.5 0 1 0-.707-.707l-.708.707a.5.5 0 0 0 .708.708zm-7.779-.707a.5.5 0 0 0-.707.707l.707.708a.5.5 0 1 0 .708-.708zm1.734 3.374a2 2 0 1 1 3.296 2.198q.3.423.516.898a3 3 0 1 0-4.84-3.225q.529.017 1.028.129m4.484 4.074c.6.215 1.125.59 1.522 1.072a.5.5 0 0 0 .039-.742l-.707-.707a.5.5 0 0 0-.854.377M14.5 6.5a.5.5 0 0 0 0 1h1a.5.5 0 0 0 0-1z'


def glass(mask, fill='#fff', opacity=.84, refraction=.084, specular='outside', shadow=.018,
          material='glass', blend='normal', offset=(0, -2)):
    return layer(mask, fill, opacity, refraction, specular, shadow, material, blend, offset, 0, 2.0, 5.0)


def glyph_vector_home(kind):
    if kind not in HOME_VECTOR_KINDS:
        return None

    if kind == 'gmail':
        m = path_mask(GMAIL_D, viewbox=(0, 0, 24, 24), target=(185, 245, 839, 779))
        return [layer(m, '#e94b45', .90, 0, 'off', 0, 'ink')]

    if kind in ('maps', 'google_maps'):
        m = path_mask(GOOGLE_MAPS_D, viewbox=(0, 0, 24, 24), target=(238, 150, 786, 856))
        return [glass(m, '#2c8cf4', .78, .095, 'outside', .015)]

    if kind == 'clock':
        face = circle_mask(512, 512, 286)
        hour = stroked_path_mask('M512 512 L512 350', width=28)
        minute = stroked_path_mask('M512 512 L666 590', width=24)
        second = stroked_path_mask('M512 512 L416 300', width=10)
        return [
            glass(face, '#f5f5f6', .75, .058, 'outside', .020),
            layer(hour, '#222428', 1, 0, 'off', 0, 'ink'),
            layer(minute, '#222428', 1, 0, 'off', 0, 'ink'),
            layer(second, '#ff453a', 1, 0, 'off', 0, 'ink'),
        ]

    if kind == 'weather':
        sun = path_mask(SUN_D, viewbox=(0, 0, 16, 16), target=(410, 165, 850, 605))
        cloud = path_mask(CLOUD_D, viewbox=(0, 0, 16, 16), target=(190, 315, 850, 840))
        return [
            glass(sun, '#ffd21a', .82, .095, 'outside', .008),
            glass(cloud, '#fff', .84, .100, 'outside', .026),
        ]

    if kind == 'notes':
        card = rounded_rect_mask(214, 190, 596, 648, 116)
        lines = svg_mask('''
          <path d="M320 446 H704 M320 548 H704 M320 650 H610" fill="none" stroke="#fff" stroke-width="22" stroke-linecap="round"/>
          <path d="M590 352 C646 292 704 294 748 328 C701 395 654 436 585 458 Z" fill="#fff"/>
        ''')
        return [glass(card, '#fff4b0', .72, .070, 'inside', .018), glass(lines, '#7c682b', .58, .052, 'outside', .006)]

    if kind in ('calendar', 'google_calendar'):
        body = rounded_rect_mask(206, 162, 612, 700, 126)
        top = svg_mask('<path d="M206 288 V286 Q206 162 332 162 H692 Q818 162 818 288 V326 H206 Z" fill="#fff"/>')
        digits = text_mask('31', 285, 80, False)
        top_color = '#ff5148' if kind == 'calendar' else '#4285f4'
        return [
            glass(body, '#fff', .80, .055, 'inside', .020),
            layer(top, top_color, .92, 0, 'off', 0, 'ink'),
            layer(digits, '#202226', 1, 0, 'off', 0, 'ink'),
        ]

    if kind == 'appstore':
        a1 = stroked_path_mask('M348 716 L506 418', width=60)
        a2 = stroked_path_mask('M520 418 L682 716', width=60)
        cross = stroked_path_mask('M386 642 L650 642', width=58)
        return [glass(a1, '#fff', .86, .095, 'outside', .014), glass(a2, '#fff', .86, .095, 'outside', .014), glass(cross, '#fff', .86, .095, 'outside', .014)]

    if kind == 'revanced':
        # Original semantic mark: a crisp play chevron plus a split vertical rail.
        mark = svg_mask('''
          <path d="M382 300 L746 512 L382 724 Z" fill="#fff"/>
          <rect x="254" y="330" width="52" height="364" rx="26" fill="#fff"/>
          <rect x="320" y="330" width="22" height="150" rx="11" fill="#fff" opacity=".65"/>
        ''')
        return [glass(mark, '#ff5262', .82, .092, 'outside', .018)]

    if kind == 'chrome':
        logo = path_mask(CHROME_D, viewbox=(0, 0, 24, 24), target=(190, 190, 834, 834), fill_rule='evenodd')
        core = circle_mask(512, 512, 113)
        return [glass(logo, '#6d737d', .60, .072, 'outside', .012), glass(core, '#4285f4', .82, .105, 'outside', .010)]

    if kind == 'recorder':
        wave = svg_mask('''
          <g fill="#fff">
            <rect x="270" y="454" width="30" height="116" rx="15"/>
            <rect x="326" y="400" width="30" height="224" rx="15"/>
            <rect x="382" y="336" width="30" height="352" rx="15"/>
            <rect x="438" y="420" width="30" height="184" rx="15"/>
            <rect x="494" y="278" width="30" height="468" rx="15"/>
            <rect x="550" y="358" width="30" height="308" rx="15"/>
            <rect x="606" y="414" width="30" height="196" rx="15"/>
            <rect x="662" y="464" width="30" height="96" rx="15"/>
            <rect x="718" y="490" width="30" height="44" rx="15"/>
          </g>
        ''')
        return [glass(wave, '#ff5b5f', .84, .075, 'outside', .010)]

    if kind == 'soundcloud':
        m = path_mask(SOUNDCLOUD_D, viewbox=(0, 0, 24, 24), target=(165, 280, 859, 744))
        return [glass(m, '#fff', .84, .090, 'outside', .020)]

    if kind == 'kaspi':
        # Clean-room semantic adaptation: person + payment card, authored as SVG.
        person = svg_mask('''
          <circle cx="394" cy="348" r="82" fill="#fff"/>
          <path d="M248 692 C255 535 306 458 394 458 C483 458 534 535 540 692 Q394 764 248 692 Z" fill="#fff"/>
        ''')
        card = svg_mask('''
          <rect x="552" y="438" width="230" height="220" rx="58" fill="#fff"/>
          <path d="M610 514 H724" fill="none" stroke="#fff" stroke-width="26" stroke-linecap="round"/>
          <circle cx="684" cy="590" r="28" fill="#fff"/>
        ''')
        return [glass(person, '#fff', .82, .092, 'outside', .018), glass(card, '#fff', .68, .090, 'outside', .014)]

    if kind == 'twogis':
        outer = svg_mask('<path d="M512 190 L758 332 L758 616 L512 810 L266 616 L266 332 Z" fill="#fff"/>')
        pin = svg_mask('''
          <path fill-rule="evenodd" d="M512 328 C407 328 338 405 338 500 C338 626 512 718 512 718 C512 718 686 626 686 500 C686 405 617 328 512 328 Z M512 430 A76 76 0 1 0 512 582 A76 76 0 1 0 512 430 Z" fill="#fff"/>
        ''')
        return [glass(outer, '#fff', .62, .096, 'outside', .018), layer(pin, '#3fae48', .96, 0, 'off', 0, 'ink')]

    if kind == 'gamehub':
        shell = svg_mask('''
          <path d="M224 356 L352 238 Q380 214 418 214 H708 Q742 214 768 238 L854 336 L742 470 H428 L302 560 L182 438 Z" fill="#fff"/>
          <rect x="294" y="526" width="438" height="226" rx="92" fill="#fff"/>
        ''')
        controls = svg_mask('''
          <path d="M390 638 H520 M455 573 V703" fill="none" stroke="#fff" stroke-width="34" stroke-linecap="round"/>
          <circle cx="620" cy="604" r="24" fill="#fff"/><circle cx="680" cy="664" r="24" fill="#fff"/>
        ''')
        return [glass(shell, '#e9eef2', .72, .094, 'outside', .018), layer(controls, '#22262c', .96, 0, 'off', 0, 'ink')]

    if kind == 'playstore':
        m = path_mask(GOOGLE_PLAY_D, viewbox=(0, 0, 24, 24), target=(220, 220, 804, 804))
        return [glass(m, '#48bfa7', .78, .096, 'outside', .016)]

    if kind == 'google_photos':
        return glyph_vector('photos')

    return None
