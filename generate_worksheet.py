"""
Generates math practice worksheet bundles (PDF) for a given grade + operation.
Each bundle = N worksheet pages + 1 answer key page, guaranteed-correct content
(problems and answers are computed programmatically, not guessed).

v2 layout - redesigned after studying real bestselling worksheet listings on
Teachers Pay Teachers (the actual dominant marketplace for this niche): the
previous version was plain floating text on a blank page with zero visual
design, which reads as obviously generated rather than something a real
teacher/seller made. Real bestsellers consistently have: a bordered box per
problem (not floating inline text), a worked example at the top, a simple
friendly mascot icon, a brand/copyright footer on every page, and a bold
color accent in the header. This version adds all of those while keeping
the actual math generation (still the important part) untouched.
"""
import os
import random

from PIL import Image, ImageDraw, ImageFont

PAGE_W, PAGE_H = 1700, 2200  # ~8.5x11in at 200dpi
MARGIN = 110

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_TITLE = os.path.join(SCRIPT_DIR, "ArchivoBlack-Regular.ttf")
FONT_BODY = os.path.join(SCRIPT_DIR, "Oswald-Variable.ttf")

INK = (45, 40, 50, 255)
PAPER = (255, 255, 255, 255)

# Each grade gets its own accent color so the catalog reads as a real,
# varied product line rather than one template recolored identically.
GRADE_ACCENTS = {
    "Kindergarten": (233, 122, 68, 255),   # warm orange
    "1st Grade": (86, 150, 214, 255),      # sky blue
    "2nd Grade": (95, 168, 105, 255),      # leaf green
    "3rd Grade": (200, 100, 170, 255),     # berry pink
    "4th Grade": (110, 120, 200, 255),     # indigo
    "5th Grade": (60, 150, 150, 255),      # teal
}

# grade -> (operation -> (num_range, problems_per_page))
# For "Skip Counting", num_range is repurposed as the counting step size.
#
# Multiplication/Division ranges step up by grade (10 -> 12 -> 25) so a 5th
# grade bundle is genuinely harder than a 3rd grade one, not just a recolor
# of the same 0-12 times-table facts - a real content gap found when
# spot-checking rendered pages against what the listing promises.
GRADE_CONFIG = {
    "Kindergarten": {"Addition": (5, 20), "Subtraction": (5, 20), "Skip Counting": (2, 10)},
    "1st Grade": {"Addition": (10, 20), "Subtraction": (10, 20), "Skip Counting": (5, 10)},
    "2nd Grade": {"Addition": (20, 20), "Subtraction": (20, 20), "Multiplication": (5, 20), "Skip Counting": (10, 10)},
    "3rd Grade": {"Multiplication": (10, 20), "Division": (10, 20), "Addition": (100, 20)},
    "4th Grade": {"Multiplication": (12, 20), "Division": (12, 20), "Subtraction": (1000, 20)},
    "5th Grade": {"Multiplication": (25, 20), "Division": (25, 20)},
}


def load_font(path, size):
    font = ImageFont.truetype(path, size)
    if path == FONT_BODY:
        font.set_variation_by_axes([600])
    return font


def accent_for(grade):
    return GRADE_ACCENTS.get(grade, (216, 90, 80, 255))


def gen_problem(operation, max_n, rng=random):
    if operation == "Addition":
        a, b = rng.randint(0, max_n), rng.randint(0, max_n)
        return f"{a} + {b}", a + b
    if operation == "Subtraction":
        a = rng.randint(0, max_n)
        b = rng.randint(0, a)
        return f"{a} - {b}", a - b
    if operation == "Multiplication":
        a, b = rng.randint(0, max_n), rng.randint(0, max_n)
        return f"{a} x {b}", a * b
    if operation == "Division":
        b = rng.randint(1, max_n)
        answer = rng.randint(0, max_n)
        a = b * answer
        return f"{a} / {b}", answer
    if operation == "Skip Counting":
        step = max_n  # max_n repurposed as the step size for this operation
        start = rng.randint(0, 5) * step
        terms = [start + i * step for i in range(5)]
        blank_idx = rng.randint(1, 3)
        answer = terms[blank_idx]
        shown = [str(t) if i != blank_idx else "__" for i, t in enumerate(terms)]
        return "Count by " + f"{step}s: " + ", ".join(shown), answer
    raise ValueError(operation)


def gen_unique_problems(operation, max_n, count, rng):
    """Draws `count` problems with no repeated problem text on the page -
    plain repeated random.randint() draws visibly duplicated problems on the
    same page for narrow ranges (e.g. Kindergarten's 0-5 addition, or Skip
    Counting's ~18-combination space), which reads as a low-effort/low-value
    product. Retries on the same rng so worksheet pages and their answer-key
    pages (generated from an identical seed - see make_worksheet_page) still
    draw the exact same sequence and stay in sync.

    Falls back to allowing repeats past a generous attempt budget, so a
    grade/operation config with fewer unique combinations than `count` still
    terminates instead of looping forever."""
    problems = []
    seen = set()
    attempts = 0
    max_attempts = count * 200 + 500
    while len(problems) < count and attempts < max_attempts:
        problem, answer = gen_problem(operation, max_n, rng)
        attempts += 1
        if problem in seen:
            continue
        seen.add(problem)
        problems.append((problem, answer))
    while len(problems) < count:
        problems.append(gen_problem(operation, max_n, rng))
    return problems


def draw_mascot_owl(draw, cx, cy, r, accent):
    """A simple, friendly owl face - built entirely from primitive shapes,
    used as a small recurring brand character (matches the real-competitor
    pattern of a cute mascot icon on every page, not a bare text header)."""
    body = (250, 240, 225, 255)
    # ear tufts
    draw.polygon([(cx - r * 0.75, cy - r * 0.55), (cx - r * 0.25, cy - r * 0.55), (cx - r * 0.55, cy - r * 1.15)], fill=accent)
    draw.polygon([(cx + r * 0.75, cy - r * 0.55), (cx + r * 0.25, cy - r * 0.55), (cx + r * 0.55, cy - r * 1.15)], fill=accent)
    # head
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=body, outline=accent, width=max(3, int(r * 0.06)))
    # eyes
    eye_r = r * 0.34
    for dx in (-0.42, 0.42):
        ex = cx + dx * r
        draw.ellipse([ex - eye_r, cy - eye_r * 0.6, ex + eye_r, cy + eye_r * 1.2], fill=(255, 255, 255, 255), outline=accent, width=max(2, int(r * 0.04)))
        pr = eye_r * 0.42
        draw.ellipse([ex - pr, cy - pr * 0.2, ex + pr, cy + pr * 1.4], fill=(50, 45, 40, 255))
    # beak
    draw.polygon([(cx - r * 0.14, cy + r * 0.22), (cx + r * 0.14, cy + r * 0.22), (cx, cy + r * 0.5)], fill=accent)


def draw_footer(draw, accent, page_num=None):
    font = load_font(FONT_BODY, 26)
    draw.line([(MARGIN, PAGE_H - 90), (PAGE_W - MARGIN, PAGE_H - 90)], fill=(225, 220, 215, 255), width=2)
    draw.text((MARGIN, PAGE_H - 68), "Bright Path Worksheets  © 2026", font=font, fill=accent)
    if page_num is not None:
        w = draw.textlength(f"Page {page_num}", font=font)
        draw.text((PAGE_W - MARGIN - w, PAGE_H - 68), f"Page {page_num}", font=font, fill=INK)


def draw_header(draw, title, subtitle, accent, page_num=None, show_mascot=True):
    if show_mascot:
        draw_mascot_owl(draw, MARGIN + 55, 130, 55, accent)
        text_x = MARGIN + 140
    else:
        text_x = MARGIN

    font1 = load_font(FONT_TITLE, 66)
    draw.text((text_x, 78), title, font=font1, fill=INK)
    font2 = load_font(FONT_BODY, 36)
    draw.text((text_x, 155), subtitle, font=font2, fill=accent)
    draw.rectangle([MARGIN, 218, PAGE_W - MARGIN, 224], fill=accent)


def draw_example_box(draw, operation, max_n, accent, rng):
    """A worked, already-solved example at the top of the page - the same
    'here's how it works' box seen on real bestselling worksheets, and a
    genuinely useful teaching aid, not just decoration."""
    problem, answer = gen_problem(operation, max_n, rng)
    box_top, box_h = 244, 92
    draw.rounded_rectangle([MARGIN, box_top, PAGE_W - MARGIN, box_top + box_h], radius=14,
                            fill=(250, 246, 238, 255), outline=accent, width=3)
    label_font = load_font(FONT_BODY, 28)
    draw.text((MARGIN + 24, box_top + 14), "EXAMPLE", font=label_font, fill=accent)
    ex_font = load_font(FONT_TITLE, 40)
    draw.text((MARGIN + 24, box_top + 44), f"{problem} = {answer}", font=ex_font, fill=INK)
    return box_top + box_h + 30


def draw_problem_grid(draw, operation, max_n, problems_per_page, accent, content_top, show_answers, rng):
    """Each problem sits in its own bordered box (2-column grid) instead of
    floating as bare inline text - the single biggest visual-polish gap
    versus real competitor listings found during research."""
    if operation == "Skip Counting":
        cols, rows = 1, 10
    else:
        cols, rows = 2, 10

    gutter = 24
    col_w = (PAGE_W - 2 * MARGIN - gutter * (cols - 1)) // cols
    avail_h = (PAGE_H - 110) - content_top
    row_h = (avail_h - gutter * (rows - 1)) // rows

    font_problem = load_font(FONT_BODY, 40 if operation != "Skip Counting" else 34)
    num_font = load_font(FONT_BODY, 26)

    count = min(problems_per_page, cols * rows)
    problems = gen_unique_problems(operation, max_n, count, rng)

    for i in range(count):
        col = i // rows
        row = i % rows
        x0 = MARGIN + col * (col_w + gutter)
        y0 = content_top + row * (row_h + gutter)
        x1, y1 = x0 + col_w, y0 + row_h

        draw.rounded_rectangle([x0, y0, x1, y1], radius=10, outline=(210, 205, 198, 255), width=2)
        draw.text((x0 + 14, y0 + 8), str(i + 1), font=num_font, fill=accent)

        problem, answer = problems[i]
        text = f"{problem} =" + (f" {answer}" if show_answers else "")
        ty = y0 + (row_h - 44) / 2 + 6
        draw.text((x0 + 20, ty), text, font=font_problem, fill=INK)
        if not show_answers:
            blank_w, blank_h = 78, 4
            blank_y = ty + 40
            draw.rectangle([x1 - blank_w - 20, blank_y, x1 - 20, blank_y + blank_h], fill=(190, 185, 178, 255))


def make_worksheet_page(grade, operation, max_n, problems_per_page, page_num, show_answers=False, seed_extra=""):
    accent = accent_for(grade)
    img = Image.new("RGBA", (PAGE_W, PAGE_H), PAPER)
    draw = ImageDraw.Draw(img)

    title = f"{grade} {operation} Practice"
    subtitle = "Answer Key" if show_answers else "Name: _______________________   Date: ____________"
    draw_header(draw, title, subtitle, accent, page_num, show_mascot=not show_answers)

    rng = random.Random(f"{grade}-{operation}-{page_num}-{seed_extra}")
    content_top = 244
    if page_num == 1 and not show_answers:
        content_top = draw_example_box(draw, operation, max_n, accent, random.Random(f"{grade}-{operation}-example"))

    draw_problem_grid(draw, operation, max_n, problems_per_page, accent, content_top, show_answers, rng)
    draw_footer(draw, accent, page_num)

    return img.convert("RGB")


def make_bundle(grade, operation, max_n, problems_per_page, num_pages, out_path):
    pages = []
    for p in range(1, num_pages + 1):
        pages.append(make_worksheet_page(grade, operation, max_n, problems_per_page, p))
    # answer key as final page(s), regenerated with same seeds so they match
    for p in range(1, num_pages + 1):
        pages.append(make_worksheet_page(grade, operation, max_n, problems_per_page, p, show_answers=True))

    pages[0].save(out_path, "PDF", save_all=True, append_images=pages[1:], resolution=200.0)
    print(f"Saved {out_path} ({num_pages} worksheets + {num_pages} answer key pages)")


if __name__ == "__main__":
    os.makedirs(os.path.join(SCRIPT_DIR, "products"), exist_ok=True)
    make_bundle("2nd Grade", "Addition", 20, 20, 10,
                os.path.join(SCRIPT_DIR, "products", "test_2nd_grade_addition.pdf"))
