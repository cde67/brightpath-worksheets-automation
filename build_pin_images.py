"""
Generates branded Pinterest-ready pin images (1000x1500, 2:3 ratio - Pinterest's
recommended aspect ratio) for each live Bright Path Worksheets product. These
double as Gumroad cover images. Pure local rendering, no network calls.
"""
import os
from PIL import Image, ImageDraw, ImageFont

import catalog as cat

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_TITLE = os.path.join(SCRIPT_DIR, "ArchivoBlack-Regular.ttf")
FONT_BODY = os.path.join(SCRIPT_DIR, "Oswald-Variable.ttf")

PIN_W, PIN_H = 1000, 1500
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


def make_pin(grade, operation, num_pages, out_path):
    img = Image.new("RGB", (PIN_W, PIN_H), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, PIN_W, 26], fill=ACCENT)

    eyebrow_font = load_font(FONT_BODY, 34, 600)
    draw.text((MARGIN, 90), "PRINTABLE MATH WORKSHEETS", font=eyebrow_font, fill=ACCENT)

    title_font = load_font(FONT_TITLE, 78)
    lines = wrap_text(draw, f"{grade} {operation}", title_font, PIN_W - 2 * MARGIN)
    y = 160
    for line in lines:
        draw.text((MARGIN, y), line, font=title_font, fill=INK)
        y += 92

    card_top = y + 40
    card_bottom = card_top + 560
    draw.rounded_rectangle([MARGIN, card_top, PIN_W - MARGIN, card_bottom], radius=24, fill=CARD, outline=INK, width=3)

    big_font = load_font(FONT_TITLE, 130)
    draw.text((PIN_W // 2, card_top + 130), f"{num_pages}", font=big_font, fill=ACCENT, anchor="mm")
    sub_font = load_font(FONT_BODY, 40, 500)
    draw.text((PIN_W // 2, card_top + 210), "practice pages", font=sub_font, fill=INK, anchor="mm")

    draw.line([(MARGIN + 60, card_top + 260), (PIN_W - MARGIN - 60, card_top + 260)], fill=(220, 220, 220), width=2)

    feat_font = load_font(FONT_BODY, 36, 500)
    feats = ["+ Matching Answer Key", "Instant PDF Download", "Homeschool & Classroom Ready"]
    fy = card_top + 300
    for feat in feats:
        draw.ellipse([MARGIN + 60, fy + 8, MARGIN + 76, fy + 24], fill=ACCENT)
        draw.text((MARGIN + 96, fy), feat, font=feat_font, fill=INK)
        fy += 60

    price_font = load_font(FONT_TITLE, 60)
    draw.text((PIN_W // 2, card_bottom + 70), "$3.99", font=price_font, fill=INK, anchor="mm")

    brand_font = load_font(FONT_BODY, 38, 600)
    draw.text((PIN_W // 2, PIN_H - 70), "Bright Path Worksheets", font=brand_font, fill=ACCENT, anchor="mm")

    img.save(out_path, "PNG")


OPERATIONS = ["Skip Counting", "Addition", "Subtraction", "Multiplication", "Division"]


def parse_grade_operation(title):
    prefix = title.split(" Worksheets -")[0].strip()
    for op in OPERATIONS:
        if prefix.endswith(op):
            return prefix[: -len(op)].strip(), op
    raise ValueError(f"Could not parse grade/operation from title: {title!r}")


def main():
    out_dir = os.path.join(SCRIPT_DIR, "pins")
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for item in cat.CATALOG:
        grade, operation = parse_grade_operation(item["title"])
        out_path = os.path.join(out_dir, f"{item['slug']}.png")
        make_pin(grade, operation, 10, out_path)
        made.append(out_path)
        print(f"Made {out_path}")
    print(f"\n{len(made)} pin images generated in {out_dir}/")


if __name__ == "__main__":
    main()
