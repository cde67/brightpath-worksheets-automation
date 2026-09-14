"""
Generates the full starting catalog of math worksheet bundle PDFs, one per
(grade, operation) combo defined in generate_worksheet.GRADE_CONFIG.
Also writes a catalog.py with product metadata (title, description, tags,
price) for the publish step.
"""
import os
import generate_worksheet as g

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_DIR = os.path.join(SCRIPT_DIR, "products")

PRICE_CENTS = 399  # $3.99 - impulse-buy price point for a single-topic bundle


def slugify(text):
    return text.lower().replace(" ", "_").replace("'", "")


def build_meta(grade, operation, num_pages):
    title = f"{grade} {operation} Worksheets - {num_pages} Printable Practice Pages + Answer Key - Instant Download"
    description = (
        f"Help your {grade.lower()} student master {operation.lower()} with this printable "
        f"worksheet bundle. Includes {num_pages} practice pages plus a matching answer key, "
        f"ready to print at home or in the classroom. Instant digital download - no waiting, "
        f"no shipping.\n\nPerfect for homeschool, classroom practice, or extra review at home."
    )
    # Gumroad caps tags at 20 characters each
    tags = [
        operation.lower(),
        grade.lower(),
        "math worksheets",
        "homeschool",
        "printable",
        "math practice",
        "teacher resource",
        "instant download",
        "answer key",
        "elementary math",
    ]
    tags = [t for t in tags if len(t) <= 20]
    return title, description, tags[:10]


def main():
    os.makedirs(PRODUCTS_DIR, exist_ok=True)
    catalog = []
    for grade, ops in g.GRADE_CONFIG.items():
        for operation, (max_n, per_page) in ops.items():
            slug = slugify(f"{grade}_{operation}")
            out_path = os.path.join(PRODUCTS_DIR, f"{slug}.pdf")
            num_pages = 10
            print(f"Building {slug}...")
            g.make_bundle(grade, operation, max_n, per_page, num_pages, out_path)
            title, desc, tags = build_meta(grade, operation, num_pages)
            catalog.append({
                "slug": slug,
                "file": f"products/{slug}.pdf",
                "title": title,
                "description": desc,
                "tags": tags,
                "price_cents": PRICE_CENTS,
            })

    catalog_path = os.path.join(SCRIPT_DIR, "catalog.py")
    with open(catalog_path, "w") as f:
        f.write('"""Auto-generated catalog of worksheet bundle products."""\n\nCATALOG = [\n')
        for item in catalog:
            f.write(f"    {item!r},\n")
        f.write("]\n")

    print(f"\nBuilt {len(catalog)} products. Catalog written to {catalog_path}")


if __name__ == "__main__":
    main()
