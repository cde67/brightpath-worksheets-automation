"""
One automation cycle for the Bright Path Worksheets Gumroad store.

Builds the full potential catalog from generate_worksheet.GRADE_CONFIG, checks
which titles already exist on Gumroad (via the API - the product list itself
is the source of truth, so this is safe to re-run from a fresh checkout with
no local state), generates + publishes whatever's missing, and stops
gracefully if Gumroad's daily product-creation cap is hit (resets in 24h,
next scheduled run will pick up where this one left off).

Requires GUMROAD_ACCESS_TOKEN as an environment variable.
"""
import json
import os
import sys
import time
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_worksheet as g
import publish_gumroad as pg

PRICE_CENTS = 399


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
    tags = [
        operation.lower(), grade.lower(), "math worksheets", "homeschool",
        "printable", "math practice", "teacher resource", "instant download",
        "answer key", "elementary math",
    ]
    tags = [t for t in tags if len(t) <= 20]
    return title, description, tags[:10]


def existing_titles():
    if not pg.TOKEN:
        raise RuntimeError("GUMROAD_ACCESS_TOKEN not set")
    req_url = f"{pg.API_BASE}/products?access_token={pg.TOKEN}"
    import urllib.request
    with urllib.request.urlopen(req_url) as resp:
        data = json.loads(resp.read().decode())
    return {p["name"] for p in data.get("products", [])}


def main():
    if not os.environ.get("GUMROAD_ACCESS_TOKEN"):
        print("ERROR: GUMROAD_ACCESS_TOKEN env var not set.")
        sys.exit(1)
    pg.TOKEN = os.environ["GUMROAD_ACCESS_TOKEN"]

    base = os.path.dirname(os.path.abspath(__file__))
    products_dir = os.path.join(base, "products")
    os.makedirs(products_dir, exist_ok=True)

    already = existing_titles()
    print(f"{len(already)} products already live on Gumroad.")

    catalog = []
    to_publish = []
    for grade, ops in g.GRADE_CONFIG.items():
        for operation, (max_n, per_page) in ops.items():
            slug = slugify(f"{grade}_{operation}")
            title, desc, tags = build_meta(grade, operation, 10)
            entry = {
                "slug": slug, "file": f"products/{slug}.pdf", "title": title,
                "description": desc, "tags": tags, "price_cents": PRICE_CENTS,
            }
            catalog.append(entry)
            if title not in already:
                to_publish.append((grade, operation, max_n, per_page, entry))

    print(f"{len(to_publish)} new products to publish this cycle.")

    published = 0
    for grade, operation, max_n, per_page, entry in to_publish:
        out_path = os.path.join(base, entry["file"])
        print(f"Generating {entry['slug']}...")
        g.make_bundle(grade, operation, max_n, per_page, 10, out_path)

        print(f"Publishing {entry['slug']}...")
        try:
            res = pg.create_product(entry["title"], entry["description"], entry["price_cents"], entry["tags"], out_path)
        except urllib.error.HTTPError as e:
            print(f"  upload/create error: {e}")
            break
        if not res.get("success"):
            msg = res.get("message", "")
            print(f"  FAILED: {msg}")
            if "10 products per day" in msg:
                print("  Daily cap hit - stopping here, next scheduled run will continue.")
                break
            continue
        product_id = res["product"]["id"]
        enable_res = pg.enable_product(product_id)
        url = enable_res.get("product", {}).get("short_url", "")
        print(f"  -> {url}")
        published += 1
        time.sleep(2)

    catalog_path = os.path.join(base, "catalog.py")
    with open(catalog_path, "w") as f:
        f.write('"""Auto-generated full catalog (published + pending) of worksheet products."""\n\nCATALOG = [\n')
        for item in catalog:
            f.write(f"    {item!r},\n")
        f.write("]\n")

    print(f"\nCYCLE COMPLETE: {published} new products published this run.")
    remaining = len(to_publish) - published
    if remaining > 0:
        print(f"{remaining} still pending - will publish on the next scheduled run.")


if __name__ == "__main__":
    main()
