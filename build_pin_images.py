"""
Generates branded product imagery for Bright Path Worksheets:
- Pinterest pins (1000x1500, 2:3 ratio) -> pins/
- Gumroad covers (same 1000x1500 image) -> covers/
- Gumroad square thumbnails (800x800, >=600x600 required) -> thumbs/

All three show an actual mockup of a real generated worksheet page (not just
text/numbers) so the listing shows people what they're actually buying,
styled as a slightly-tilted paper sheet with a drop shadow and a "10 pages +
answer key" corner badge. Pure local rendering, no network calls.
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


def draw_badge(base, cx, cy, lines):
    r = 62
    draw = ImageDraw.Draw(base)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT, outline=(255, 255, 255), width=4)
    f1 = load_font(FONT_TITLE, 30)
    f2 = load_font(FONT_BODY, 20, 600)
    draw.text((cx, cy - 14), lines[0], font=f1, fill=(255, 255, 255), anchor="mm")
    draw.text((cx, cy + 16), lines[1], font=f2, fill=(255, 255, 255), anchor="mm")


def make_pin(grade, operation, num_pages, max_n, per_page, out_path):
    img = Image.new("RGB", (PIN_W, PIN_H), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, PIN_W, 26], fill=ACCENT)

    eyebrow_font = load_font(FONT_BODY, 34, 600)
    draw.text((MARGIN, 60), "PRINTABLE MATH WORKSHEETS", font=eyebrow_font, fill=ACCENT)

    title_font = load_font(FONT_TITLE, 70)
    lines = wrap_text(draw, f"{grade} {operation}", title_font, PIN_W - 2 * MARGIN)
    y = 120
    for line in lines:
        draw.text((MARGIN, y), line, font=title_font, fill=INK)
        y += 82

    card_top = y + 30
    card_bottom = PIN_H - 130
    draw.rounded_rectangle([MARGIN - 20, card_top, PIN_W - MARGIN + 20, card_bottom], radius=24, fill=CARD, outline=(230, 224, 214), width=2)

    paper = worksheet_mockup(grade, operation, max_n, per_page, target_w=560, rotation=-3)
    px = (PIN_W - paper.width) // 2
    py = card_top + 40
    paste_with_shadow(img, paper, px, py)
    draw = ImageDraw.Draw(img)
    draw_badge(img, PIN_W - MARGIN - 30, py + 40, [f"{num_pages}", "PAGES"])

    feat_font = load_font(FONT_BODY, 32, 500)
    fy = py + paper.height + 30
    feats = ["+ Matching Answer Key", "Instant PDF Download"]
    for feat in feats:
        # Bullet dot and text share one vertical center (bullet_cy) instead of
        # each being placed from its own top-left origin - the dot's fixed
        # geometry lined up with the text's font-ascender line, not its
        # visual glyph center, so it rode ~16px too high relative to the
        # actual letters (found while auditing cover/pin image quality).
        bullet_cy = fy + 13
        draw.ellipse([MARGIN + 40, bullet_cy - 7, MARGIN + 54, bullet_cy + 7], fill=ACCENT)
        draw.text((MARGIN + 72, bullet_cy), feat, font=feat_font, fill=INK, anchor="lm")
        fy += 46

    price_font = load_font(FONT_TITLE, 52)
    draw.text((PIN_W - MARGIN - 40, card_bottom - 60, ), "$3.99", font=price_font, fill=INK, anchor="rm")

    brand_font = load_font(FONT_BODY, 38, 600)
    draw.text((PIN_W // 2, PIN_H - 60), "Bright Path Worksheets", font=brand_font, fill=ACCENT, anchor="mm")

    img.save(out_path, "PNG")


def make_thumbnail(grade, operation, num_pages, max_n, per_page, out_path):
    """Square (800x800) version for Gumroad's thumbnail slot - same real
    worksheet mockup, tighter crop so it reads well small."""
    img = Image.new("RGB", (THUMB_SIZE, THUMB_SIZE), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, THUMB_SIZE, 16], fill=ACCENT)

    paper = worksheet_mockup(grade, operation, max_n, per_page, target_w=430, rotation=-4)
    px = (THUMB_SIZE - paper.width) // 2 + 20
    py = 150
    paste_with_shadow(img, paper, px, py)
    draw = ImageDraw.Draw(img)
    draw_badge(img, THUMB_SIZE - 90, 110, [f"{num_pages}", "PAGES"])

    title_font = load_font(FONT_TITLE, 44)
    lines = wrap_text(draw, f"{grade} {operation}", title_font, THUMB_SIZE - 2 * MARGIN)
    ty = 40
    for line in lines[:2]:
        draw.text((THUMB_SIZE // 2, ty), line, font=title_font, fill=INK, anchor="mm")
        ty += 50

    brand_font = load_font(FONT_BODY, 26, 600)
    draw.text((THUMB_SIZE // 2, THUMB_SIZE - 30), "Bright Path Worksheets", font=brand_font, fill=ACCENT, anchor="mm")

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
