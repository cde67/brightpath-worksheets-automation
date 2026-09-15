"""
Generates branded product imagery for Bright Path Worksheets:
- Pinterest pins (1000x1500, 2:3 ratio) -> pins/
- Gumroad covers (same 1000x1500 image) -> covers/
- Gumroad square thumbnails (800x800, >=600x600 required) -> thumbs/

v2 layout - redesigned after surveying real competitor pins on Pinterest for
"printable math worksheets" / "addition worksheets printable pdf". The
previous version (thin accent hairline, one flat page, small plain circle
badge, all on a near-white background) reads as flat/quiet next to what's
actually winning attention in that feed: a full color-blocked header band, a
diagonal "value" ribbon instead of a small badge, a FANNED STACK of pages
(not one flat sheet) to signal volume at a glance, and the brand's own
mascot (the owl from generate_worksheet.py) enlarged and used as a character,
not just a tiny in-corner icon. Still pure local rendering, no network calls,
and still shows an actual real generated worksheet page (not placeholder
text) so the pin/cover doesn't oversell what's inside.

v3 - narrowed the research specifically to what teacher-buyers respond to,
not just "Pinterest pins" generally: real bestseller thumbnails on
Teachers Pay Teachers (The Moffatt Girls, A Teachable Teacher, Shelly Sitz -
all with thousands of reviews). The one element every top seller had that
this design was missing: an explicit "NO PREP" callout. It's the single most
repeated phrase across that whole category, because it's the actual thing a
teacher is paying to avoid - and it's honestly true of a print-and-go PDF, so
it's a real claim, not just decoration. Added as a bold pill badge. The page
count badge on real bestsellers is more often a plain circle than a diagonal
ribbon, but the ribbon reads fine here and isn't worth re-churning.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import catalog as cat
import generate_worksheet as gw

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_TITLE = os.path.join(SCRIPT_DIR, "ArchivoBlack-Regular.ttf")
FONT_BODY = os.path.join(SCRIPT_DIR, "Oswald-Variable.ttf")

PIN_W, PIN_H = 1000, 1500
THUMB_SIZE = 800
MARGIN = 70

INK = (40, 40, 45, 255)
ACCENT = (216, 90, 80, 255)
BG = (255, 250, 240, 255)
CARD = (255, 255, 255, 255)
CREAM = (250, 246, 238, 255)


def load_font(path, size, weight=None):
    font = ImageFont.truetype(path, size)
    if path == FONT_BODY and weight:
        font.set_variation_by_axes([weight])
    return font


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def worksheet_mockup(grade, operation, max_n, per_page, target_w, rotation=0):
    """Renders an actual worksheet page (real problems, not placeholder text)
    scaled down and framed like a paper sheet, ready to paste with a shadow."""
    page = gw.make_worksheet_page(grade, operation, max_n, per_page, page_num=1)
    ratio = target_w / page.width
    page = page.resize((target_w, int(page.height * ratio)), Image.LANCZOS)

    border = 10
    framed = Image.new("RGB", (page.width + border * 2, page.height + border * 2), (255, 255, 255))
    framed.paste(page, (border, border))
    draw = ImageDraw.Draw(framed)
    draw.rectangle([0, 0, framed.width - 1, framed.height - 1], outline=(225, 220, 210), width=2)

    if rotation:
        framed = framed.rotate(rotation, expand=True, fillcolor=(255, 250, 240), resample=Image.BICUBIC)
    return framed


def paste_with_shadow(base, paper, x, y, blur=14, offset=10, opacity=70):
    shadow = Image.new("RGBA", (paper.width + offset * 2 + blur * 2, paper.height + offset * 2 + blur * 2), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sx, sy = blur + offset, blur + offset
    sd.rectangle([sx, sy, sx + paper.width, sy + paper.height], fill=(30, 25, 20, opacity))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    base.paste(shadow, (x - blur, y - blur), shadow)
    base.paste(paper, (x, y))


def paste_with_alpha_shadow(base, tile, x, y, blur=18, offset=12, opacity=60):
    """Like paste_with_shadow, but the shadow silhouette is traced from the
    tile's own alpha channel instead of a plain rectangle - needed for the
    fanned page stack below, whose outline is several overlapping rotated
    rectangles, not one flat one."""
    alpha = tile.split()[-1]
    pad = offset + blur
    shadow = Image.new("RGBA", (tile.width + pad * 2, tile.height + pad * 2), (0, 0, 0, 0))
    solid = Image.new("RGBA", tile.size, (30, 25, 20, opacity))
    shadow.paste(solid, (pad, pad), alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    base.paste(shadow, (x - pad, y - pad), shadow)
    base.paste(tile, (x, y), tile)


def fanned_stack(grade, operation, max_n, per_page, target_w):
    """Three real worksheet pages fanned like a hand of cards instead of one
    flat sheet - the single biggest gap found versus competitor pins on
    Pinterest, which almost always show a spread/stack to signal volume at
    a glance rather than a single page."""
    pages = [
        worksheet_mockup(grade, operation, max_n, per_page, target_w, rotation=-7),
        worksheet_mockup(grade, operation, max_n, per_page, target_w, rotation=4),
        worksheet_mockup(grade, operation, max_n, per_page, target_w, rotation=0),
    ]
    offsets = [(14, 22), (34, 14), (24, 0)]  # back-to-front draw order, tight cascade
    max_w = max(p.width + ox for p, (ox, oy) in zip(pages, offsets))
    max_h = max(p.height + oy for p, (ox, oy) in zip(pages, offsets))
    canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
    for p, (ox, oy) in zip(pages, offsets):
        canvas.alpha_composite(p.convert("RGBA"), (ox, oy))
    return canvas


def draw_star(draw, cx, cy, r, color):
    """4-point sparkle accent - matches the small doodle stars/suns/clouds
    seen scattered on real competitor kids-worksheet pins."""
    draw.polygon([
        (cx, cy - r), (cx + r * 0.24, cy - r * 0.24),
        (cx + r, cy), (cx + r * 0.24, cy + r * 0.24),
        (cx, cy + r), (cx - r * 0.24, cy + r * 0.24),
        (cx - r, cy), (cx - r * 0.24, cy - r * 0.24),
    ], fill=color)


def pill_badge(draw, x, y, text, fg, bg, font_size=24):
    """A small rounded 'NO PREP' style pill, left-anchored at (x, y) - the
    one element every real TPT bestseller thumbnail had that this design
    was missing (see module docstring). Returns the pill's right edge x, so
    callers can lay out more elements after it."""
    font = load_font(FONT_BODY, font_size, 700)
    pad_x, pad_y = 18, 10
    text_w = draw.textlength(text, font=font)
    x1, y1 = x + text_w + pad_x * 2, y + font_size + pad_y * 2
    draw.rounded_rectangle([x, y, x1, y1], radius=(y1 - y) / 2, fill=bg)
    draw.text((x + pad_x, (y + y1) / 2 + 1), text, font=font, fill=fg, anchor="lm")
    return x1


def build_ribbon(text, accent, angle=-30, font_size=30, pad=70, height=66):
    """Builds the rotated diagonal ribbon banner as its own image, without
    pasting it anywhere - split out from ribbon_badge() so a caller that
    needs to lay out OTHER elements around it (e.g. title text that must
    not run under it) can measure its exact rendered footprint first via
    PIL's own rotation, rather than hand-deriving the rotated bounding box
    with trig and risking it drifting out of sync with the real pixels."""
    font = load_font(FONT_TITLE, font_size)
    tmp_draw = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    text_w = tmp_draw.textlength(text, font=font)
    width = int(text_w) + pad
    ribbon = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ribbon)
    rd.rectangle([0, 0, width, height], fill=accent)
    rd.text((width / 2, height / 2 + 1), text, font=font, fill=(255, 255, 255, 255), anchor="mm")
    return ribbon.rotate(angle, expand=True, resample=Image.BICUBIC)


def ribbon_badge(base, cx, cy, text, accent, angle=-30, font_size=30, pad=70, height=66):
    """A diagonal corner 'value' ribbon (e.g. '10 PAGES + KEY') instead of a
    small plain circle - this exact device (a bold diagonal banner over the
    corner) is what every strong-performing competitor pin in the Pinterest
    audit used to call out page count / bundle size.

    font_size/pad/height default to the pin's original fixed values, but are
    parameters because the 800x800 thumbnail needs a visibly smaller ribbon
    than the 1000x1500 pin - at the pin's fixed size, the ribbon's footprint
    ran directly into the title text for several real product titles (e.g.
    "3rd Grade Multiplication"), found by actually measuring rendered text
    width, not by eyeballing one example."""
    ribbon = build_ribbon(text, accent, angle, font_size, pad, height)
    base.paste(ribbon, (int(cx - ribbon.width / 2), int(cy - ribbon.height / 2)), ribbon)


def make_pin(grade, operation, num_pages, max_n, per_page, out_path):
    accent = gw.accent_for(grade)
    img = Image.new("RGB", (PIN_W, PIN_H), BG)
    draw = ImageDraw.Draw(img)

    # Full color-blocked header band (was a 26px hairline) - the header is
    # the first thing a thumb-scrolling feed sees, and a flat cream page
    # with a thin accent line reads as quiet next to a colored block.
    header_h = 300
    draw.rectangle([0, 0, PIN_W, header_h], fill=accent)

    # A couple of small sparkle accents in the header for a playful,
    # kids-worksheet feel (matches the cloud/sun/star doodles competitor
    # pins use, instead of a bare color block).
    draw_star(draw, 60, 250, 14, CREAM)
    draw_star(draw, 96, 210, 8, CREAM)

    eyebrow_font = load_font(FONT_BODY, 30, 600)
    draw.text((MARGIN, 44), "PRINTABLE MATH WORKSHEETS", font=eyebrow_font, fill=CREAM)

    # "NO PREP" pill, right after the eyebrow text - the single most
    # repeated trust phrase across real bestselling teacher-facing worksheet
    # listings (The Moffatt Girls, A Teachable Teacher, Shelly Sitz all use
    # it prominently). It's also honestly true of a print-and-go PDF, so
    # it's a real claim, not just decoration. Width is measured rather than
    # hardcoded so this stays correctly placed if the eyebrow text changes.
    eyebrow_w = draw.textlength("PRINTABLE MATH WORKSHEETS", font=eyebrow_font)
    pill_badge(draw, MARGIN + eyebrow_w + 20, 34, "NO PREP", INK, CREAM, font_size=22)

    title_font = load_font(FONT_TITLE, 62)
    lines = wrap_text(draw, f"{grade} {operation}", title_font, PIN_W - 2 * MARGIN - 130)
    y = 92
    for line in lines[:3]:
        draw.text((MARGIN, y), line, font=title_font, fill=CREAM)
        y += 72

    # The brand mascot, enlarged into an actual character in the header
    # instead of a tiny corner icon on the worksheet page itself - gives the
    # pin a recognizable face the way competitor mascots do.
    gw.draw_mascot_owl(draw, PIN_W - 130, 205, 78, accent)

    card_top = header_h + 34
    card_bottom = PIN_H - 130
    draw.rounded_rectangle([MARGIN - 20, card_top, PIN_W - MARGIN + 20, card_bottom], radius=24, fill=CARD, outline=(230, 224, 214), width=2)

    stack = fanned_stack(grade, operation, max_n, per_page, target_w=530)
    px = (PIN_W - stack.width) // 2
    py = card_top + 30
    paste_with_alpha_shadow(img, stack, px, py)
    draw = ImageDraw.Draw(img)

    # Diagonal ribbon over the header/card seam, top-right - the "value
    # callout" device every strong competitor pin used, replacing the old
    # small plain circle badge.
    ribbon_badge(img, PIN_W - 150, header_h - 6, f"{num_pages} PAGES + KEY", INK)
    draw = ImageDraw.Draw(img)

    feat_font = load_font(FONT_BODY, 32, 500)
    fy = py + stack.height + 20
    feats = ["+ Matching Answer Key", "Instant PDF Download"]
    for feat in feats:
        # Bullet dot and text share one vertical center (bullet_cy) instead of
        # each being placed from its own top-left origin - the dot's fixed
        # geometry lined up with the text's font-ascender line, not its
        # visual glyph center, so it rode ~16px too high relative to the
        # actual letters (found while auditing cover/pin image quality).
        bullet_cy = fy + 13
        draw.ellipse([MARGIN + 40, bullet_cy - 7, MARGIN + 54, bullet_cy + 7], fill=accent)
        draw.text((MARGIN + 72, bullet_cy), feat, font=feat_font, fill=INK, anchor="lm")
        fy += 46

    price_font = load_font(FONT_TITLE, 52)
    draw.text((PIN_W - MARGIN - 40, card_bottom - 60, ), "$3.99", font=price_font, fill=INK, anchor="rm")

    draw_star(draw, MARGIN + 18, PIN_H - 60, 10, accent)
    brand_font = load_font(FONT_BODY, 38, 600)
    draw.text((PIN_W // 2, PIN_H - 60), "Bright Path Worksheets", font=brand_font, fill=accent, anchor="mm")
    draw_star(draw, PIN_W - MARGIN - 18, PIN_H - 60, 10, accent)

    img.save(out_path, "PNG")


def make_thumbnail(grade, operation, num_pages, max_n, per_page, out_path):
    """Square (800x800) version for Gumroad's thumbnail slot - same fanned
    real-page mockup and mascot treatment as the pin, tighter crop so it
    reads well small."""
    accent = gw.accent_for(grade)
    img = Image.new("RGB", (THUMB_SIZE, THUMB_SIZE), BG)
    draw = ImageDraw.Draw(img)

    header_h = 190
    draw.rectangle([0, 0, THUMB_SIZE, header_h], fill=accent)

    mascot_cx, mascot_cy, mascot_r = 92, 95, 52
    gw.draw_mascot_owl(draw, mascot_cx, mascot_cy, mascot_r, accent)

    # "NO PREP" pill horizontally centered directly under the owl's face
    # (not just left-anchored near it) - measured against the pill's own
    # rendered width via the same font/padding pill_badge uses internally,
    # so it stays centered if the text or font size ever changes.
    _pill_font = load_font(FONT_BODY, 18, 700)
    _pill_w = draw.textlength("NO PREP", font=_pill_font) + 18 * 2  # + pill_badge's pad_x*2
    pill_x = mascot_cx - _pill_w / 2
    pill_y = mascot_cy + mascot_r + 6
    pill_badge(draw, pill_x, pill_y, "NO PREP", INK, CREAM, font_size=18)

    # Build the page-count ribbon FIRST (smaller than the pin's - the pin's
    # fixed 30pt ribbon, measured, ran directly into the title text for
    # several real product titles like "3rd Grade Multiplication" on this
    # more cramped 800x800 canvas) so its true post-rotation size - not an
    # estimate - can define how much width is actually safe for the title.
    ribbon_cx, ribbon_cy = THUMB_SIZE - 90, 40
    ribbon_font_size = 20
    ribbon_img = build_ribbon(f"{num_pages} PAGES", INK, angle=-30,
                               font_size=ribbon_font_size, pad=50,
                               height=int(ribbon_font_size * 1.6))
    ribbon_left_edge = ribbon_cx - ribbon_img.width / 2

    title_start_x = 170
    title_safety_gap = 15
    title_max_w = ribbon_left_edge - title_start_x - title_safety_gap

    title_font = load_font(FONT_TITLE, 40)
    lines = wrap_text(draw, f"{grade} {operation}", title_font, title_max_w)
    ty = header_h / 2 - (len(lines[:2]) * 46) / 2 + 23
    for line in lines[:2]:
        draw.text((title_start_x, ty), line, font=title_font, fill=CREAM, anchor="lm")
        ty += 46

    stack = fanned_stack(grade, operation, max_n, per_page, target_w=335)
    px = (THUMB_SIZE - stack.width) // 2 + 15
    py = header_h + 26
    paste_with_alpha_shadow(img, stack, px, py)
    draw = ImageDraw.Draw(img)

    img.paste(ribbon_img, (int(ribbon_cx - ribbon_img.width / 2), int(ribbon_cy - ribbon_img.height / 2)), ribbon_img)
    draw = ImageDraw.Draw(img)

    brand_font = load_font(FONT_BODY, 26, 600)
    draw.text((THUMB_SIZE // 2, THUMB_SIZE - 30), "Bright Path Worksheets", font=brand_font, fill=accent, anchor="mm")

    img.save(out_path, "PNG")


def config_for(grade, operation):
    return gw.GRADE_CONFIG[grade][operation]


def main():
    pins_dir = os.path.join(SCRIPT_DIR, "pins")
    thumbs_dir = os.path.join(SCRIPT_DIR, "thumbs")
    os.makedirs(pins_dir, exist_ok=True)
    os.makedirs(thumbs_dir, exist_ok=True)
    made = []
    for item in cat.CATALOG:
        grade, operation = item["grade"], item["operation"]
        max_n, per_page = config_for(grade, operation)
        pin_path = os.path.join(pins_dir, f"{item['slug']}.png")
        thumb_path = os.path.join(thumbs_dir, f"{item['slug']}.png")
        make_pin(grade, operation, 10, max_n, per_page, pin_path)
        make_thumbnail(grade, operation, 10, max_n, per_page, thumb_path)
        made.append(pin_path)
        print(f"Made {pin_path} + {thumb_path}")
    print(f"\n{len(made)} pin/thumbnail image pairs generated.")


if __name__ == "__main__":
    main()
