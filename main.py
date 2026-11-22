#!/usr/bin/env python3
"""The picture that tastes of one ingredient.

A single-ingredient close-up: golden honey dripping from a wooden dipper
into a thick, glossy pool. Rendered procedurally with PIL only -- no
network, no external assets, no copied images. Everything (background
glow, bokeh, honey gradients, specular highlights, grain) is drawn from
code so the picture reads as rich, warm and delicious at full size and
at ~300 px.

Writes /output/entry.png (1024x1024, <= 1 MiB).
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

W = H = 1024
OUT = "/output/entry.png"
MAX_BYTES = 1_048_576
SEED = 20261123

# ---------------------------------------------------------------- palette
DARK_BG = (26, 14, 6)        # deep warm brown, frame edges
GLOW_BG = (122, 62, 14)      # warm amber glow behind the honey
GOLD_BRIGHT = (255, 201, 60)  # honey highlight
GOLD_MID = (247, 168, 35)     # honey body
GOLD_DEEP = (214, 122, 8)     # honey shadow
GOLD_DARK = (138, 74, 0)      # honey rim
WOOD = (138, 90, 43)          # dipper wood
WOOD_DARK = (94, 58, 24)
WOOD_LIGHT = (186, 130, 66)


def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def radial_gradient(size, stops):
    """Small radial gradient image; stops = [(pos 0..1, rgb), ...]."""
    img = Image.new("RGB", size)
    px = img.load()
    cx, cy = size[0] / 2.0, size[1] / 2.0
    maxr = math.hypot(cx, cy)
    for y in range(size[1]):
        for x in range(size[0]):
            r = math.hypot(x - cx, y - cy) / maxr
            if r <= stops[0][0]:
                px[x, y] = stops[0][1]
                continue
            if r >= stops[-1][0]:
                px[x, y] = stops[-1][1]
                continue
            for i in range(len(stops) - 1):
                p0, c0 = stops[i]
                p1, c1 = stops[i + 1]
                if p0 <= r <= p1:
                    t = (r - p0) / (p1 - p0) if p1 > p0 else 0.0
                    px[x, y] = lerp(c0, c1, t)
                    break
    return img


def vertical_gradient(size, top, bottom):
    img = Image.new("RGB", size)
    px = img.load()
    h = size[1]
    for y in range(h):
        c = lerp(top, bottom, y / max(h - 1, 1))
        for x in range(size[0]):
            px[x, y] = c
    return img


def ellipse_mask(size, box):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.ellipse(box, fill=255)
    return m


def soft_blob(size, box, color, alpha, blur):
    """A blurred ellipse of colour on a transparent layer."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse(box, fill=color + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def main():
    rng = random.Random(SEED)

    # ---------------------------------------------------------- background
    bg = radial_gradient(
        (512, 512),
        [(0.0, GLOW_BG), (0.45, (74, 36, 10)), (1.0, DARK_BG)],
    ).resize((W, H), Image.BICUBIC)
    img = bg.convert("RGBA")

    # warm light spilling in from the upper left
    img.alpha_composite(soft_blob((W, H), (-260, -320, 620, 300),
                                 (255, 190, 90), 70, 120))
    # soft bokeh discs, out of focus, behind the honey
    bokeh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bokeh)
    for _ in range(34):
        x = rng.randint(0, W)
        y = rng.randint(0, 620)
        r = rng.randint(14, 64)
        warm = rng.choice([(255, 180, 80), (255, 210, 120), (220, 140, 40)])
        a = rng.randint(14, 46)
        bd.ellipse([x - r, y - r, x + r, y + r], fill=warm + (a,))
    img.alpha_composite(bokeh.filter(ImageFilter.GaussianBlur(14)))

    # ------------------------------------------------- honey dipper (top)
    # Drawn upright on its own layer, then tilted, so the grooves stay even.
    dip = Image.new("RGBA", (360, 560), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dip)
    # handle -- shorter and thicker, warm wood
    dd.rounded_rectangle([150, 0, 210, 300], radius=26, fill=WOOD + (255,))
    dd.rounded_rectangle([158, 0, 172, 300], radius=7, fill=WOOD_LIGHT + (210,))
    dd.rounded_rectangle([192, 0, 202, 300], radius=5, fill=WOOD_DARK + (170,))
    # grooved bulb head: few thick rounded bars, wider in the middle
    widths = [118, 146, 160, 152, 130, 104]
    y = 296
    for i, wdt in enumerate(widths):
        x0 = 180 - wdt // 2
        x1 = 180 + wdt // 2
        col = lerp(WOOD_LIGHT, WOOD_DARK, i / max(len(widths) - 1, 1))
        dd.rounded_rectangle([x0, y, x1, y + 38], radius=18, fill=col + (255,))
        # groove shadow between bars
        if i < len(widths) - 1:
            dd.ellipse([x0 + 4, y + 30, x1 - 4, y + 44], fill=(60, 34, 12, 170))
        y += 34
    # bulb bottom tip
    dd.ellipse([128, y - 8, 232, y + 36], fill=WOOD_DARK + (255,))
    # honey coating the lower bulb: golden glaze so it reads as honey
    dd.ellipse([124, y - 60, 236, y + 40], fill=(247, 168, 35, 110))
    dip = dip.rotate(-25, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(dip, (400, -110))

    # ------------------------------------------- honey stream from dipper
    # A thick wavy ribbon falling from the dipper tip into the pool.
    top_x, top_y = 575, 370
    bot_x, bot_y = 525, 640
    left, right = [], []
    steps = 24
    for i in range(steps + 1):
        t = i / steps
        y = top_y + (bot_y - top_y) * t
        cx = top_x + (bot_x - top_x) * t + math.sin(t * 9.0) * 10 * (1 - t * 0.4)
        half = 26 + 16 * math.sin(t * math.pi) + 10 * t
        left.append((cx - half, y))
        right.append((cx + half, y))
    stream_mask = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(stream_mask)
    sd.polygon(left + right[::-1], fill=255)
    stream_mask = stream_mask.filter(ImageFilter.GaussianBlur(3))
    grad = vertical_gradient((160, bot_y - top_y + 40),
                             GOLD_BRIGHT, GOLD_DEEP)
    stream = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    stream.paste(grad, (top_x - 80, top_y - 10),
                 stream_mask.crop((top_x - 80, top_y - 10,
                                   top_x + 80, bot_y + 30)))
    img.alpha_composite(stream)
    # bright highlight stripe down the stream's left side
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hl_pts = []
    for i in range(steps + 1):
        t = i / steps
        y = top_y + (bot_y - top_y) * t
        cx = top_x + (bot_x - top_x) * t + math.sin(t * 9.0) * 10 * (1 - t * 0.4)
        half = 26 + 16 * math.sin(t * math.pi) + 10 * t
        hl_pts.append((cx - half + 8, y))
    hd.line(hl_pts, fill=(255, 240, 190, 170), width=9)
    img.alpha_composite(hl.filter(ImageFilter.GaussianBlur(4)))

    # ------------------------------------------------------ honey pool
    # Big glossy mound filling the lower centre: ~70% of the frame wide.
    pool_box = (150, 470, 890, 940)
    pool_grad = radial_gradient(
        (420, 420),
        [(0.0, GOLD_BRIGHT), (0.35, GOLD_MID), (0.7, GOLD_DEEP),
         (1.0, GOLD_DARK)],
    )
    pool_mask = ellipse_mask((W, H), pool_box).filter(
        ImageFilter.GaussianBlur(2))
    pool = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pool.paste(pool_grad.resize((740, 470), Image.BICUBIC),
               (150, 470), pool_mask.crop((150, 470, 890, 940)))
    img.alpha_composite(pool)

    # swirl folds inside the pool: thin darker amber arcs low in the pool,
    # plus one bright glossy fold band across its upper middle
    swirls = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    swd = ImageDraw.Draw(swirls)
    for (bx0, by0, bx1, by1, a0, a1) in [
            (300, 700, 720, 900, 200, 340),
            (360, 740, 680, 920, 160, 20),
            (260, 660, 780, 860, 300, 60)]:
        swd.arc([bx0, by0, bx1, by1], a0, a1,
                fill=(160, 84, 4, 110), width=10)
    img.alpha_composite(swirls.filter(ImageFilter.GaussianBlur(5)))
    fold = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fold)
    fd.arc([300, 600, 760, 780], 195, 345, fill=(255, 205, 90, 95),
           width=20)
    img.alpha_composite(fold.filter(ImageFilter.GaussianBlur(8)))

    # specular highlights: a soft sheen high on the pool only
    img.alpha_composite(soft_blob((W, H), (330, 545, 500, 640),
                                  (255, 236, 170), 80, 30))
    # glint on the stream
    img.alpha_composite(soft_blob((W, H), (530, 430, 570, 500),
                                  (255, 244, 200), 170, 8))
    # fat droplet where the stream meets the pool -- the drip moment
    drop = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dpd = ImageDraw.Draw(drop)
    dpd.ellipse([505, 455, 575, 545], fill=GOLD_MID + (255,))
    dpd.polygon([(520, 470), (560, 470), (540, 425)], fill=GOLD_MID + (255,))
    dpd.ellipse([522, 470, 542, 505], fill=(255, 244, 200, 230))
    img.alpha_composite(drop.filter(ImageFilter.GaussianBlur(2)))

    # honey dripping over the pool's front edge
    edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ed = ImageDraw.Draw(edge)
    for (ex, ey, er) in [(400, 905, 22), (620, 915, 26), (510, 925, 18)]:
        ed.ellipse([ex - er, ey - er, ex + er, ey + er * 1.6],
                   fill=GOLD_DEEP + (235,))
        ed.ellipse([ex - er * 0.4, ey - er * 0.5, ex - er * 0.05,
                    ey - er * 0.1], fill=(255, 240, 190, 220))
    img.alpha_composite(edge.filter(ImageFilter.GaussianBlur(1.5)))

    # -------------------------------------------- droplets around the pool
    drops = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    drd = ImageDraw.Draw(drops)
    for (dx, dy, dr) in [(250, 880, 26), (790, 860, 30), (700, 930, 20),
                         (330, 950, 18), (860, 760, 16), (180, 780, 15)]:
        drd.ellipse([dx - dr, dy - dr * 0.8, dx + dr, dy + dr * 0.8],
                    fill=GOLD_MID + (235,))
        drd.ellipse([dx - dr * 0.45, dy - dr * 0.55, dx - dr * 0.05,
                     dy - dr * 0.15], fill=(255, 244, 200, 230))
    img.alpha_composite(drops.filter(ImageFilter.GaussianBlur(1.5)))

    # faint honeycomb hint, bottom-left corner, low contrast
    comb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(comb)
    for row in range(3):
        for col in range(3):
            cx = 60 + col * 62 + (row % 2) * 31
            cy = 900 + row * 52
            pts = []
            for k in range(6):
                ang = math.pi / 3 * k + math.pi / 6
                pts.append((cx + 30 * math.cos(ang), cy + 30 * math.sin(ang)))
            cd.polygon(pts, outline=(255, 190, 90, 90), width=4)
    img.alpha_composite(comb.filter(ImageFilter.GaussianBlur(1)))

    # ------------------------------------------------------------- finish
    # gentle vignette to pull the eye to the centre
    vig_mask = radial_gradient(
        (512, 512),
        [(0.0, (0, 0, 0)), (0.62, (0, 0, 0)), (1.0, (255, 255, 255))],
    ).resize((W, H), Image.BICUBIC).convert("L")
    dark = Image.new("RGB", (W, H), (10, 5, 2))
    base = img.convert("RGB")
    base = Image.composite(Image.blend(base, dark, 0.6), base, vig_mask)

    # fine grain over the whole frame -- this is what keeps the PNG rich
    # (flat vector fills compress to tens of KB and lose to rich renders).
    noise = Image.effect_noise((W, H), 18).convert("RGB")
    base = Image.blend(base, noise, 0.038)

    import io

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    buf = io.BytesIO()
    base.save(buf, format="PNG")
    if buf.tell() <= MAX_BYTES:
        base.save(OUT, format="PNG")
    else:
        quality = 92
        while quality >= 70:
            base.save(OUT, format="JPEG", quality=quality)
            if os.path.getsize(OUT) <= MAX_BYTES:
                break
            quality -= 6
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
