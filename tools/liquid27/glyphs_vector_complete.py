from __future__ import annotations

from .material import layer
from .vector import circle_mask, path_mask, rounded_rect_mask, stroked_path_mask, svg_mask

# Every catalog kind not already handled by the reference/home/curated modules.
# This file exists to make `legacy` an invalid state for a release build.
COMPLETE_VECTOR_KINDS = {
    'facetime', 'music', 'wallet', 'files', 'calculator', 'health', 'compass',
    'slack', 'netflix', 'amazon', 'uber', 'paypal', 'venmo', 'robinhood',
    'strava', 'zoom', 'shazam', 'keep', 'meet', 'drive', 'docs', 'sheets',
    'slides', 'translate', 'search', 'classroom', 'one',
}

# Open-source brand silhouettes. The source geometry is only the semantic mark;
# sizing, layering and Liquid27 material treatment are authored here.
SLACK_D = 'M6 15A2 2 0 0 1 4 17A2 2 0 0 1 2 15A2 2 0 0 1 4 13H6V15M7 15A2 2 0 0 1 9 13A2 2 0 0 1 11 15V20A2 2 0 0 1 9 22A2 2 0 0 1 7 20V15M9 7A2 2 0 0 1 7 5A2 2 0 0 1 9 3A2 2 0 0 1 11 5V7H9M9 8A2 2 0 0 1 11 10A2 2 0 0 1 9 12H4A2 2 0 0 1 2 10A2 2 0 0 1 4 8H9M17 10A2 2 0 0 1 19 8A2 2 0 0 1 21 10A2 2 0 0 1 19 12H17V10M16 10A2 2 0 0 1 14 12A2 2 0 0 1 12 10V5A2 2 0 0 1 14 3A2 2 0 0 1 16 5V10M14 18A2 2 0 0 1 16 20A2 2 0 0 1 14 22A2 2 0 0 1 12 20V18H14M14 17A2 2 0 0 1 12 15A2 2 0 0 1 14 13H19A2 2 0 0 1 21 15A2 2 0 0 1 19 17H14Z'
NETFLIX_D = 'M6.5 2H10.5L13.44 10.83L13.5 2H17.5V22C16.25 21.78 14.87 21.64 13.41 21.58L10.5 13L10.43 21.59C9.03 21.65 7.7 21.79 6.5 22V2Z'
AMAZON_D = 'M257.7 162.7c-48.7 1.8-169.5 15.5-169.5 117.5 0 109.5 138.3 114 183.5 43.2 6.5 10.2 35.4 37.5 45.3 46.8l56.8-56s-32.3-25.3-32.3-52.8V114.3C341.5 89 317 32 229.2 32 141.2 32 94.5 87 94.5 136.3l73.5 6.8c16.3-49.5 54.2-49.5 54.2-49.5 40.7-.1 35.5 29.8 35.5 69.1zm0 86.8c0 80-84.2 68-84.2 17.2 0-47.2 50.5-56.7 84.2-57.8v40.6zM393.7 413c-7.7 10-70 67-174.5 67S34.7 408.5 10.2 379c-6.8-7.7 1-11.3 5.5-8.3 73.3 44.5 187.8 117.8 372.5 30.3 7.5-3.7 13.3 2 5.5 12zm39.8 2.2c-6.5 15.8-16 26.8-21.2 31-5.5 4.5-9.5 2.7-6.5-3.8s19.3-46.5 12.7-55c-6.5-8.3-37-4.3-48-3.2-10.8 1-13 2-14-.3-2.3-5.7 21.7-15.5 37.5-17.5 15.7-1.8 41-.8 46 5.7 3.7 5.1 0 27.1-6.5 43.1z'
UBER_D = 'M414.1 32H33.9C15.2 32 0 47.2 0 65.9V446c0 18.8 15.2 34 33.9 34H414c18.7 0 33.9-15.2 33.9-33.9V65.9C448 47.2 432.8 32 414.1 32zM237.6 391.1C163 398.6 96.4 344.2 88.9 269.6h94.4V290c0 3.7 3 6.8 6.8 6.8H258c3.7 0 6.8-3 6.8-6.8v-67.9c0-3.7-3-6.8-6.8-6.8h-67.9c-3.7 0-6.8 3-6.8 6.8v20.4H88.9c7-69.4 65.4-122.2 135.1-122.2s128.1 52.8 135.1 122.2c7.5 74.5-46.9 141.1-121.5 148.6z'
PAYPAL_D = 'M111.9 295.9c-3.5 19.2-17.4 108.7-21.5 134-.3 1.8-1 2.5-3 2.5H12.8c-7.6 0-13.1-6.6-12.1-13.9L59.3 46.6c1.5-9.6 10.1-16.9 20-16.9 152.3 0 165.1-3.7 204 11.4 60.1 23.3 65.6 79.5 44 140.3-21.5 62.6-72.5 89.5-140.1 90.3-43.4.7-69.5-7-75.3 24.2zM357.6 152c-1.8-1.3-2.5-1.8-3 1.3-2 11.4-5.1 22.5-8.8 33.6-39.9 113.8-150.5 103.9-204.5 103.9-6.1 0-10.1 3.3-10.9 9.4-22.6 140.4-27.1 169.7-27.1 169.7-1 7.1 3.5 12.9 10.6 12.9h63.5c8.6 0 15.7-6.3 17.4-14.9.7-5.4-1.1 6.1 14.4-91.3 4.6-22 14.3-19.7 29.3-19.7 71 0 126.4-28.8 142.9-112.3 6.5-34.8 4.6-71.4-23.8-92.6z'
STRAVA_D = 'M158.4 0L7 292H96.2L158.4 175.9L220.1 292H308.6L158.4 0zM308.6 292L264.7 380.2 220.1 292H152.5L264.7 512 376.2 292H308.6z'


def glass(mask, fill='#fff', opacity=.84, refraction=.085, specular='outside', shadow=.012):
    return layer(mask, fill, opacity, refraction, specular, shadow, 'glass', 'normal', (0, -2), 0, 1.3, 3.5)


def ink(mask, fill='#fff', opacity=1.0):
    return layer(mask, fill, opacity, 0, 'off', 0, 'ink', 'normal', (0, 0), 0, 0, 0)


def _facetime():
    body = rounded_rect_mask(220, 310, 410, 390, 92)
    lens = svg_mask('<path d="M632 390 L810 300 Q838 286 838 326 V698 Q838 738 810 724 L632 634 Z" fill="#fff"/>')
    return [glass(body, '#fff', .88, .088), glass(lens, '#fff', .88, .088)]


def _music():
    note = svg_mask('''
      <path d="M430 250 L738 188 V590 C738 674 670 734 590 728 C527 723 489 683 492 635 C495 586 542 548 604 548 C630 548 651 553 666 562 V334 L500 367 V653 C500 737 431 797 351 791 C288 786 251 746 254 698 C257 649 303 611 365 611 C390 611 414 617 430 626 Z" fill="#fff"/>
    ''')
    return [glass(note, '#fff', .90, .092)]


def _wallet():
    back = rounded_rect_mask(228, 244, 568, 508, 122)
    strips = [
        rounded_rect_mask(280, 306, 464, 94, 34),
        rounded_rect_mask(280, 406, 464, 94, 34),
        rounded_rect_mask(280, 506, 464, 94, 34),
    ]
    return [
        glass(back, '#25272c', .70, .070, 'inside'),
        glass(strips[0], '#ff5f57', .86, .085),
        glass(strips[1], '#ffd60a', .86, .085),
        glass(strips[2], '#34c759', .86, .085),
    ]


def _files():
    back = svg_mask('<path d="M202 344 Q202 250 296 250 H454 L510 306 H728 Q822 306 822 400 V720 Q822 798 744 798 H280 Q202 798 202 720 Z" fill="#fff"/>')
    front = svg_mask('<path d="M180 410 Q180 334 256 334 H768 Q844 334 844 410 V726 Q844 806 764 806 H260 Q180 806 180 726 Z" fill="#fff"/>')
    return [glass(back, '#83c9ff', .70, .075), glass(front, '#39a7ff', .78, .092)]


def _calculator():
    body = rounded_rect_mask(230, 196, 564, 632, 112)
    screen = rounded_rect_mask(304, 266, 416, 112, 28)
    layers = [glass(body, '#282a2f', .76, .068, 'inside'), glass(screen, '#9ca4af', .60, .050, 'inside')]
    for r in range(3):
        for c in range(3):
            layers.append(glass(circle_mask(352 + c*126, 474 + r*112, 32), '#d3d7dd', .74, .060, 'inside', .004))
    layers.append(glass(rounded_rect_mask(668, 438, 58, 250, 26), '#ff9f0a', .90, .070, 'inside', .004))
    return layers


def _health():
    heart = svg_mask('<path d="M512 786 C460 730 244 592 244 414 C244 308 318 246 407 246 C458 246 493 274 512 308 C531 274 566 246 617 246 C706 246 780 308 780 414 C780 592 564 730 512 786 Z" fill="#fff"/>')
    return [glass(heart, '#ff375f', .88, .092)]


def _compass():
    ring = svg_mask('<path fill-rule="evenodd" d="M512 188 A324 324 0 1 1 512 836 A324 324 0 1 1 512 188 Z M512 258 A254 254 0 1 0 512 766 A254 254 0 1 0 512 258 Z" fill="#fff"/>')
    north = svg_mask('<path d="M512 294 L620 560 L512 518 L404 560 Z" fill="#fff"/>')
    south = svg_mask('<path d="M512 730 L404 464 L512 506 L620 464 Z" fill="#fff"/>')
    return [glass(ring, '#c9ced5', .64, .070), glass(north, '#ff453a', .88, .090), glass(south, '#d3d7dd', .72, .076)]


def _zoom():
    body = rounded_rect_mask(236, 330, 390, 360, 94)
    cam = svg_mask('<path d="M624 414 L802 324 Q832 310 832 348 V674 Q832 712 802 698 L624 608 Z" fill="#fff"/>')
    return [glass(body, '#fff', .88, .090), glass(cam, '#fff', .88, .090)]


def _shazam():
    p1 = stroked_path_mask('M326 430 C366 344 448 316 526 368 L616 428 C658 456 658 516 614 544 L512 612', width=66)
    p2 = stroked_path_mask('M698 594 C658 680 576 708 498 656 L408 596 C366 568 366 508 410 480 L512 412', width=66)
    return [glass(p1, '#fff', .90, .095), glass(p2, '#fff', .90, .095)]


def _robinhood():
    feather = svg_mask('''
      <path d="M292 720 C386 594 432 456 714 244 C665 390 608 493 520 570 C600 538 660 493 720 432 C665 560 573 654 454 710 L384 786 Z" fill="#fff"/>
      <path d="M320 722 L692 282" fill="none" stroke="#fff" stroke-width="34" stroke-linecap="round"/>
    ''')
    return [glass(feather, '#15211a', .88, .082)]


def _keep():
    bulb = svg_mask('''
      <path d="M512 222 C360 222 278 338 278 454 C278 548 330 594 382 638 C408 660 420 690 420 724 H604 C604 690 616 660 642 638 C694 594 746 548 746 454 C746 338 664 222 512 222 Z" fill="#fff"/>
      <rect x="424" y="738" width="176" height="54" rx="27" fill="#fff"/>
      <rect x="452" y="806" width="120" height="38" rx="19" fill="#fff"/>
    ''')
    return [glass(bulb, '#fff', .88, .085)]


def _meet():
    body = rounded_rect_mask(216, 324, 408, 356, 74)
    wing = svg_mask('<path d="M624 412 L804 318 Q836 302 836 346 V666 Q836 710 804 694 L624 600 Z" fill="#fff"/>')
    return [glass(body, '#fff', .84, .088), glass(wing, '#fff', .84, .088)]


def _drive():
    green = svg_mask('<path d="M410 232 H560 L806 658 H656 Z" fill="#fff"/>')
    yellow = svg_mask('<path d="M410 232 L164 658 L240 790 L486 364 Z" fill="#fff"/>')
    blue = svg_mask('<path d="M240 790 L164 658 H656 L806 658 L730 790 Z" fill="#fff"/>')
    return [glass(green, '#34a853', .88, .078), glass(yellow, '#fbbc04', .88, .078), glass(blue, '#4285f4', .88, .078)]


def _document(kind):
    paper = svg_mask('<path d="M298 190 H606 L730 314 V822 H298 Q246 822 246 770 V242 Q246 190 298 190 Z" fill="#fff"/>')
    fold = svg_mask('<path d="M606 190 V314 H730 Z" fill="#fff"/>')
    color = {'docs':'#4285f4', 'sheets':'#34a853', 'slides':'#fbbc04'}[kind]
    layers = [glass(paper, '#fff', .80, .066, 'inside'), glass(fold, color, .78, .070)]
    if kind == 'docs':
        for y in (430, 510, 590, 670):
            layers.append(glass(rounded_rect_mask(360, y, 250, 24, 12), color, .78, .055, 'inside', .003))
    elif kind == 'sheets':
        frame = svg_mask('<rect x="350" y="420" width="286" height="258" rx="18" fill="none" stroke="#fff" stroke-width="24"/><path d="M350 506 H636 M350 592 H636 M445 420 V678 M540 420 V678" fill="none" stroke="#fff" stroke-width="20"/>')
        layers.append(glass(frame, color, .78, .060, 'inside', .003))
    else:
        frame = rounded_rect_mask(356, 430, 280, 202, 20)
        inner = rounded_rect_mask(392, 466, 208, 130, 12)
        layers.extend([glass(frame, color, .76, .060), glass(inner, '#fff', .50, .050, 'inside', .002)])
    return layers


def _translate():
    left = rounded_rect_mask(196, 258, 374, 410, 74)
    right = rounded_rect_mask(454, 356, 374, 410, 74)
    glyph = svg_mask('''
      <path d="M292 350 H472 M382 324 V354 M310 386 C338 462 402 510 476 526 M454 386 C430 462 374 512 306 536" fill="none" stroke="#fff" stroke-width="26" stroke-linecap="round"/>
      <path d="M558 660 L638 462 L718 660 M584 596 H692" fill="none" stroke="#fff" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>
    ''')
    return [glass(left, '#4285f4', .68, .070), glass(right, '#7aa7f8', .60, .070), glass(glyph, '#fff', .88, .060)]


def _search():
    ring = svg_mask('<circle cx="454" cy="448" r="186" fill="none" stroke="#fff" stroke-width="64"/>')
    handle = stroked_path_mask('M590 584 L750 744', width=68)
    return [glass(ring, '#fff', .88, .095), glass(handle, '#fff', .88, .095)]


def _classroom():
    board = rounded_rect_mask(216, 274, 592, 452, 82)
    teacher = circle_mask(512, 434, 76)
    people = svg_mask('<path d="M312 654 C326 566 384 530 448 540 C488 546 512 570 528 598 C544 570 568 546 608 540 C672 530 730 566 744 654 Z" fill="#fff"/>')
    return [glass(board, '#fff', .64, .070, 'inside'), glass(teacher, '#34a853', .86, .080), glass(people, '#34a853', .82, .076)]


def _one():
    # Google One's ribbon-like 1, represented as separate chromatic glass faces.
    blue = svg_mask('<path d="M360 298 L520 206 L520 690 L430 742 L430 362 L360 402 Z" fill="#fff"/>')
    green = svg_mask('<path d="M520 206 L664 290 L664 596 L584 642 L584 338 L520 302 Z" fill="#fff"/>')
    yellow = svg_mask('<path d="M584 642 L664 596 L724 702 L642 750 Z" fill="#fff"/>')
    red = svg_mask('<path d="M430 742 L520 690 L584 642 L642 750 L514 824 Z" fill="#fff"/>')
    return [glass(blue, '#4285f4', .86, .078), glass(green, '#34a853', .86, .078), glass(yellow, '#fbbc04', .86, .078), glass(red, '#ea4335', .86, .078)]


def glyph_vector_complete(kind):
    if kind not in COMPLETE_VECTOR_KINDS:
        return None

    if kind == 'facetime': return _facetime()
    if kind == 'music': return _music()
    if kind == 'wallet': return _wallet()
    if kind == 'files': return _files()
    if kind == 'calculator': return _calculator()
    if kind == 'health': return _health()
    if kind == 'compass': return _compass()
    if kind == 'zoom': return _zoom()
    if kind == 'shazam': return _shazam()
    if kind == 'robinhood': return _robinhood()
    if kind == 'keep': return _keep()
    if kind == 'meet': return _meet()
    if kind == 'drive': return _drive()
    if kind in ('docs', 'sheets', 'slides'): return _document(kind)
    if kind == 'translate': return _translate()
    if kind == 'search': return _search()
    if kind == 'classroom': return _classroom()
    if kind == 'one': return _one()

    brand = {
        'slack': (SLACK_D, (176, 176, 848, 848), (0, 0, 24, 24), '#ffffff'),
        'netflix': (NETFLIX_D, (274, 178, 750, 846), (0, 0, 24, 24), '#e50914'),
        'amazon': (AMAZON_D, (174, 188, 850, 836), (0, 0, 448, 512), '#17191c'),
        'uber': (UBER_D, (194, 194, 830, 830), (0, 0, 448, 512), '#ffffff'),
        'paypal': (PAYPAL_D, (252, 158, 772, 854), (0, 0, 384, 512), '#ffffff'),
        'strava': (STRAVA_D, (270, 154, 754, 854), (0, 0, 384, 512), '#ffffff'),
    }
    if kind in brand:
        d, target, viewbox, fill = brand[kind]
        return [glass(path_mask(d, viewbox=viewbox, target=target, fill_rule='evenodd'), fill, .90, .088)]

    if kind == 'venmo':
        # App-scale Venmo V rather than the long wordmark.
        v = svg_mask('<path d="M322 286 L442 270 L492 626 C574 514 624 400 602 300 L724 280 C754 444 676 642 548 760 H392 Z" fill="#fff"/>')
        return [glass(v, '#ffffff', .90, .088)]

    raise RuntimeError(f'Unhandled complete vector kind: {kind}')
