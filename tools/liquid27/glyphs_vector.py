from __future__ import annotations

import math

from .material import layer
from .vector import (
    circle_mask,
    ellipse_mask,
    path_mask,
    paths_mask,
    stroked_path_mask,
    svg_mask,
)

# These are the reference glyphs used to judge the visual system.  Every mask
# here comes from continuous SVG geometry rasterized at 2048 px.  No Pillow
# polygon approximations, no bitmap rotation, no sampled 'Bezier as a line'.
VECTOR_KINDS = {
    'phone', 'messages', 'camera', 'photos', 'settings', 'mail',
    'telegram', 'discord', 'youtube', 'spotify', 'instagram', 'chatgpt',
}

# Bootstrap Icons (MIT), used as clean semantic vector bases for system glyphs.
PHONE_D = 'M1.885.511a1.745 1.745 0 0 1 2.61.163L6.29 2.98c.329.423.445.974.315 1.494l-.547 2.19a.68.68 0 0 0 .178.643l2.457 2.457a.68.68 0 0 0 .644.178l2.189-.547a1.75 1.75 0 0 1 1.494.315l2.306 1.794c.829.645.905 1.87.163 2.611l-1.034 1.034c-.74.74-1.846 1.065-2.877.702a18.6 18.6 0 0 1-7.01-4.42 18.6 18.6 0 0 1-4.42-7.009c-.362-1.03-.037-2.137.703-2.877z'
MESSAGES_D = 'M8 15c4.418 0 8-3.134 8-7s-3.582-7-8-7-8 3.134-8 7c0 1.76.743 3.37 1.97 4.6-.097 1.016-.417 2.13-.771 2.966-.079.186.074.394.273.362 2.256-.37 3.597-.938 4.18-1.234A9 9 0 0 0 8 15'
CAMERA_BODY_D = 'M2 4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-1.172a2 2 0 0 1-1.414-.586l-.828-.828A2 2 0 0 0 9.172 2H6.828a2 2 0 0 0-1.414.586l-.828.828A2 2 0 0 1 3.172 4zm.5 2a.5.5 0 1 1 0-1 .5.5 0 0 1 0 1m9 2.5a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0'
GEAR_D = 'M9.405 1.05c-.413-1.4-2.397-1.4-2.81 0l-.1.34a1.464 1.464 0 0 1-2.105.872l-.31-.17c-1.283-.698-2.686.705-1.987 1.987l.169.311c.446.82.023 1.841-.872 2.105l-.34.1c-1.4.413-1.4 2.397 0 2.81l.34.1a1.464 1.464 0 0 1 .872 2.105l-.17.31c-.698 1.283.705 2.686 1.987 1.987l.311-.169a1.464 1.464 0 0 1 2.105.872l.1.34c.413 1.4 2.397 1.4 2.81 0l.1-.34a1.464 1.464 0 0 1 2.105-.872l.31.17c1.283.698 2.686-.705 1.987-1.987l-.169-.311a1.464 1.464 0 0 1 .872-2.105l.34-.1c1.4-.413 1.4-2.397 0-2.81l-.34-.1a1.464 1.464 0 0 1-.872-2.105l.17-.31c.698-1.283-.705-2.686-1.987-1.987l-.311.169a1.464 1.464 0 0 1-2.105-.872zM8 10.93a2.929 2.929 0 1 1 0-5.86 2.929 2.929 0 0 1 0 5.858z'
MAIL_D = 'M.05 3.555A2 2 0 0 1 2 2h12a2 2 0 0 1 1.95 1.555L8 8.414zM0 4.697v7.104l5.803-3.558zM6.761 8.83l-6.57 4.027A2 2 0 0 0 2 14h12a2 2 0 0 0 1.808-1.144l-6.57-4.027L8 9.586zm3.436-.586L16 11.801V4.697z'

# SuperTinyIcons (MIT) / clean brand geometry.  The material/color treatment is
# ours; only the continuous semantic silhouette is used.
TELEGRAM_PLANE_D = 'M291 220q6-4 8-1t-3 8c-31 32-54 50-67 65q-9 10 5 20l62 42c25 17 33 3 36-14q17-91 24-151c2-15-3-23-22-17q-27 8-194 81c-21 8-17 17-5 21s21 7 33 10 20 4 34-5'
DISCORD_HALF_D = 'M196 304a34 37 0 10-1 0m63 58q-46 0-95-21l-7 5q7 6 31 16-8 16-20 32-52-16-93-47-13-109 54-211 38-18 77-24l10 20q16-3 42-3Z'
YOUTUBE_D = 'M313 256l-93-53V309Zm114-87c9 37 9 138 0 174-4 15-17 27-32 31-37 10-242 10-278 0-15-4-28-16-32-31-10-39-9-136 0-174 4-15 17-27 32-31 39-10 244-9 278 0 15 4 28 16 32 31Z'
CHATGPT_ARM_D = 'm243.3 208.7 88.9 51.3c.3.1.5.4.5.7V361c5.8-.3 11.5-.7 17-.9a79.8 79.8 0 0053.3-38.7c17.6-30.3 13.6-68.5-9.9-94.5-6-5-12-10-17.8-14.8-.5-.3-1.3-.8-1.9-1.1l-61.8-35.7a10.4 10.4 0 00-10.5 0l-57.7 33.5zm105.1 43.7-77.8-44.9 26.9-15.5c.3-.2.6-.2.9-.1l64.4 37.2c28.7 16.6 38.5 53.3 21.9 81.9a59.9 59.9 0 01-31.2 26.3v-75.8c0-3.7-2-7.2-5.2-9.1z'

# Simple Icons (CC0) outline geometry for Instagram.
INSTAGRAM_D = 'M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077'


def _glass(mask, fill='#fff', opacity=.82, refraction=.078, specular='outside', shadow=.024,
           material='glass', blend='normal', offset=(0, -2)):
    return layer(mask, fill, opacity, refraction, specular, shadow, material, blend, offset, 0, 2.0, 5.0)


def glyph_vector(kind):
    if kind not in VECTOR_KINDS:
        return None

    if kind == 'phone':
        return [_glass(path_mask(PHONE_D, viewbox=(0, 0, 16, 16), target=(205, 170, 819, 850)), refraction=.090)]

    if kind == 'messages':
        return [_glass(path_mask(MESSAGES_D, viewbox=(0, 0, 16, 16), target=(166, 205, 858, 820)), opacity=.84, refraction=.086)]

    if kind == 'camera':
        body = path_mask(CAMERA_BODY_D, viewbox=(0, 0, 16, 16), target=(140, 220, 884, 804))
        lens_outer = circle_mask(512, 516, 178)
        lens_mid = circle_mask(512, 516, 126)
        lens_inner = circle_mask(486, 487, 62)
        return [
            _glass(body, '#f5f7fa', .76, .060, 'inside', .020),
            _glass(lens_outer, '#2f3742', .70, .082, 'outside', .024),
            _glass(lens_mid, '#1878e8', .70, .112, 'outside', .010),
            _glass(lens_inner, '#a8e1ff', .33, .128, 'inside', .003),
        ]

    if kind == 'photos':
        colors = ['#ff5260','#ff8800','#ffd000','#75d400','#00c982','#08aee8','#4677e7','#a23faa']
        layers = []
        for i, color in enumerate(colors):
            a = math.radians(i * 45 - 90)
            cx = 512 + 164 * math.cos(a)
            cy = 512 + 164 * math.sin(a)
            mask = ellipse_mask(cx, cy, 114, 204, rotate=i * 45)
            layers.append(_glass(mask, color, .75, .100, 'outside', .008, offset=(0, -3)))
        layers.append(_glass(circle_mask(512, 512, 83), '#fff', .33, .074, 'inside', .002, offset=(0, -1)))
        return layers

    if kind == 'settings':
        gear = path_mask(GEAR_D, viewbox=(0, 0, 16, 16), target=(190, 190, 834, 834), fill_rule='evenodd')
        return [_glass(gear, '#f4f6f8', .75, .080, 'outside', .024)]

    if kind == 'mail':
        env = path_mask(MAIL_D, viewbox=(0, 0, 16, 16), target=(150, 275, 874, 755), fill_rule='evenodd')
        return [_glass(env, '#fff', .80, .092, 'outside', .022)]

    if kind == 'telegram':
        plane = path_mask(TELEGRAM_PLANE_D, viewbox=(0, 0, 512, 512), target=(145, 150, 875, 860))
        return [_glass(plane, '#fff', .82, .102, 'outside', .020)]

    if kind == 'discord':
        logo = paths_mask(
            [(DISCORD_HALF_D, None), (DISCORD_HALF_D, 'matrix(-1 0 0 1 512 0)')],
            viewbox=(0, 0, 512, 512), target=(145, 180, 879, 842),
        )
        return [_glass(logo, '#fff', .80, .090, 'outside', .020)]

    if kind == 'youtube':
        logo = path_mask(YOUTUBE_D, viewbox=(0, 0, 512, 512), target=(130, 210, 894, 814), fill_rule='evenodd')
        return [_glass(logo, '#fff', .80, .090, 'outside', .022)]

    if kind == 'spotify':
        # Smooth cubic curves instead of the previous polyline approximation.
        p1 = stroked_path_mask('M270 390 C390 340 565 350 748 410', width=43)
        p2 = stroked_path_mask('M300 505 C415 465 565 475 710 525', width=38)
        p3 = stroked_path_mask('M340 615 C440 585 555 592 672 632', width=34)
        return [
            layer(p1, '#101214', .96, 0, 'off', 0, 'ink'),
            layer(p2, '#101214', .96, 0, 'off', 0, 'ink'),
            layer(p3, '#101214', .96, 0, 'off', 0, 'ink'),
        ]

    if kind == 'instagram':
        logo = path_mask(INSTAGRAM_D, viewbox=(0, 0, 24, 24), target=(210, 210, 814, 814), fill_rule='evenodd')
        return [_glass(logo, '#fff', .82, .090, 'outside', .018)]

    if kind == 'chatgpt':
        fragment = '<defs><path id="arm" d="%s" fill="#fff"/></defs>' % CHATGPT_ARM_D
        fragment += '<use href="#arm"/>'
        for deg in (60, 120, 180, 240, 300):
            fragment += f'<use href="#arm" transform="rotate({deg} 256 256)"/>'
        logo = svg_mask(fragment, viewbox=(0, 0, 512, 512), target=(155, 155, 869, 869))
        return [_glass(logo, '#eef8f4', .67, .108, 'outside', .010, blend='plus_lighter')]

    return None
