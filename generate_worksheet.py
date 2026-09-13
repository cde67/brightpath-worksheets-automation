"""
Generates math practice worksheet bundles (PDF) for a given grade + operation.
Each bundle = N worksheet pages + 1 answer key page, guaranteed-correct content
(problems and answers are computed programmatically, not guessed).
"""
import os
import random
from PIL import Image, ImageDraw, ImageFont

PAGE_W, PAGE_H = 1700, 2200  # ~8.5x11in at 200dpi
MARGIN = 120

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_TITLE = os.path.join(SCRIPT_DIR, "ArchivoBlack-Regular.ttf")
FONT_BODY = os.path.join(SCRIPT_DIR, "Oswald-Variable.ttf")

INK = (40, 40, 45, 255)
ACCENT = (216, 90, 80, 255)

# grade -> (operation -> (num_range, problems_per_page))
# For "Skip Counting", num_range is repurposed as the counting step size.
GRADE_CONFIG = {
    "Kindergarten": {"Addition": (5, 20), "Subtraction": (5, 20), "Skip Counting": (2, 10)},
    "1st Grade": {"Addition": (10, 20), "Subtraction": (10, 20), "Skip Counting": (5, 10)},
    "2nd Grade": {"Addition": (20, 20), "Subtraction": (20, 20), "Multiplication": (5, 20), "Skip Counting": (10, 10)},
    "3rd Grade": {"Multiplication": (12, 20), "Division": (12, 20), "Addition": (100, 20)},
    "4th Grade": {"Multiplication": (12, 20), "Division": (12, 20), "Subtraction": (1000, 20)},
    "5th Grade": {"Multiplication": (12, 20), "Division": (12, 20)},
}


def load_font(path, size):
    font = ImageFont.truetype(path, size)
    if path == FONT_BODY:
        font.set_variation_by_axes([600])
    return font


def gen_problem(operation, max_n):
    if operation == "Addition":
        a, b = random.randint(0, max_n), random.randint(0, max_n)
        return f"{a} + {b} =", a + b
    if operation == "Subtraction":
        a = random.randint(0, max_n)
        b = random.randint(0, a)
        return f"{a} - {b} =", a - b
    if operation == "Multiplication":
        a, b = random.randint(0, max_n), random.randint(0, max_n)
        return f"{a} x {b} =", a * b
    if operation == "Division":
        b = random.randint(1, max_n)
        answer = random.randint(0, max_n)
        a = b * answer
        return f"{a} / {b} =", answer
    if operation == "Skip Counting":
        step = max_n  # max_n repurposed as the step size for this operation
        start = random.randint(0, 5) * step
        terms = [start + i * step for i in range(5)]
        blank_idx = random.randint(1, 3)
        answer = terms[blank_idx]
        shown = [str(t) if i != blank_idx else "__" for i, t in enumerate(terms)]
        return f"Count by {step}s: " + ", ".join(shown), answer
    raise ValueError(operation)


def draw_header(draw, title, subtitle, page_num=None):
    font1 = load_font(FONT_TITLE, 70)
    draw.text((MARGIN, 80), title, font=font1, fill=INK)
    font2 = load_font(FONT_BODY, 40)
    draw.text((MARGIN, 165), subtitle, font=font2, fill=ACCENT)
    draw.line([(MARGIN, 230), (PAGE_W - MARGIN, 230)], fill=INK, width=4)
    if page_num is not None:
        font3 = load_font(FONT_BODY, 32)
        draw.text((PAGE_W - MARGIN - 120, 80), f"Page {page_num}", font=font3, fill=INK)


def make_worksheet_page(grade, operation, max_n, problems_per_page, page_num, show_answers=False):
    img = Image.new("RGB", (PAGE_W, PAGE_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    title = f"{grade} {operation} Practice"
    subtitle = "Answer Key" if show_answers else "Name: _______________________   Date: ____________"
    draw_header(draw, title, subtitle, page_num)

    if operation == "Skip Counting":
        font_problem = load_font(FONT_BODY, 44)
        cols, rows = 1, 10
    else:
        font_problem = load_font(FONT_BODY, 46)
        cols, rows = 2, 10
    col_w = (PAGE_W - 2 * MARGIN) // cols
    row_h = (PAGE_H - 320 - MARGIN) // rows

    random.seed(f"{grade}-{operation}-{page_num}")
    for i in range(problems_per_page):
        col = i // rows
        row = i % rows
        x = MARGIN + col * col_w
        y = 300 + row * row_h
        problem, answer = gen_problem(operation, max_n)
        text = f"{i+1}. {problem}" + (f" {answer}" if show_answers else "")
        draw.text((x, y), text, font=font_problem, fill=INK)

    return img


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
