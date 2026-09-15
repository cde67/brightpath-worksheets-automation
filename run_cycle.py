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
import subprocess
import sys
import time
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import copy_gen as cg
import generate_worksheet as g
import publish_gumroad as pg
import build_pin_images as bpi
import build_pinterest_csv as bpc

PRICE_CENTS = 399
GITHUB_REPO = "cde67/brightpath-worksheets-automation"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"


def slugify(text):
    return text.lower().replace(" ", "_").replace("'", "")


def old_style_title(grade, operation, num_pages):
    """The rigid pre-copy_gen title pattern every currently-live product
    still has. Needed so the 'already published' check below doesn't
    mistake already-live products for new ones just because copy_gen now
    generates different (varied) titles - see existing_titles()."""
    return f"{grade} {operation} Worksheets - {num_pages} Printable Practice Pages + Answer Key - Instant Download"


def build_meta(grade, operation, num_pages):
    return cg.build_meta(grade, operation, num_pages)


def existing_titles():
    if not pg.TOKEN:
        raise RuntimeError("GUMROAD_ACCESS_TOKEN not set")
    import urllib.request
    titles = set()
    url = f"{pg.API_BASE}/products?access_token={pg.TOKEN}"
    while url:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
        titles.update(p["name"] for p in data.get("products", []))
        next_url = data.get("next_page_url")
        if not next_url:
            break
        full = f"https://api.gumroad.com{next_url}" if next_url.startswith("/") else next_url
        sep = "&" if "?" in full else "?"
        url = f"{full}{sep}access_token={pg.TOKEN}"
    return titles


def main():
    if not os.environ.get("GUMROAD_ACCESS_TOKEN"):
        print("ERROR: GUMROAD_ACCESS_TOKEN env var not set.")
        sys.exit(1)
    pg.TOKEN = os.environ["GUMROAD_ACCESS_TOKEN"]

    base = os.path.dirname(os.path.abspath(__file__))
    products_dir = os.path.join(base, "products")
    pins_dir = os.path.join(base, "pins")
    thumbs_dir = os.path.join(base, "thumbs")
    os.makedirs(products_dir, exist_ok=True)
    os.makedirs(pins_dir, exist_ok=True)
    os.makedirs(thumbs_dir, exist_ok=True)

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
                "grade": grade, "operation": operation,
            }
            catalog.append(entry)
            old_title = old_style_title(grade, operation, 10)
            if title not in already and old_title not in already:
                to_publish.append((grade, operation, max_n, per_page, entry))

    print(f"{len(to_publish)} new products to publish this cycle.")

    # Generate the PDF + pin + thumbnail images for everything we're about to
    # publish BEFORE creating any Gumroad products, then push once so the
    # image URLs are live on GitHub before we ask Gumroad to fetch them.
    for grade, operation, max_n, per_page, entry in to_publish:
        out_path = os.path.join(base, entry["file"])
        print(f"Generating {entry['slug']}...")
        g.make_bundle(grade, operation, max_n, per_page, 10, out_path)
        pin_path = os.path.join(pins_dir, f"{entry['slug']}.png")
        thumb_path = os.path.join(thumbs_dir, f"{entry['slug']}.png")
        bpi.make_pin(grade, operation, 10, max_n, per_page, pin_path)
        bpi.make_thumbnail(grade, operation, 10, max_n, per_page, thumb_path)

    if to_publish:
        sync_to_github(base, extra_paths=["pins", "thumbs"])

    published = 0
    for grade, operation, max_n, per_page, entry in to_publish:
        out_path = os.path.join(base, entry["file"])
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

        pin_url = f"{RAW_BASE}/pins/{entry['slug']}.png"
        thumb_url = f"{RAW_BASE}/thumbs/{entry['slug']}.png"
        try:
            pg.set_cover(product_id, pin_url)
            pg.set_thumbnail(product_id, thumb_url)
            print(f"  cover + thumbnail set from {pin_url}")
        except urllib.error.HTTPError as e:
            print(f"  cover/thumbnail set failed (non-fatal): {e}")

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

    if published > 0:
        print("\nRebuilding Pinterest CSV from live Gumroad listings...")
        bpc.main()
        sync_to_github(base)


def sync_to_github(base, extra_paths=None):
    """Push updated catalog.py, pins/, thumbs/, and pinterest_bulk_pins.csv to
    the public GitHub repo so images are reachable at raw.githubusercontent.com
    URLs (Gumroad's cover/thumbnail endpoints fetch from a public URL, so this
    must run before those API calls, not just at the end of the cycle).
    Skips gracefully (does not fail the cycle) if no GITHUB_TOKEN is configured."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set - skipping GitHub sync. Pin images/CSV are up to date locally only.")
        return

    remote = f"https://x-access-token:{token}@github.com/cde67/brightpath-worksheets-automation.git"

    def run(cmd, **kw):
        return subprocess.run(cmd, cwd=base, capture_output=True, text=True, **kw)

    if not os.path.isdir(os.path.join(base, ".git")):
        run(["git", "init"])
        run(["git", "config", "user.name", "Bright Path Automation"])
        run(["git", "config", "user.email", "automation@brightpathworksheets.local"])
        run(["git", "remote", "add", "origin", remote])
        fetch = run(["git", "fetch", "origin", "main"])
        if fetch.returncode == 0:
            run(["git", "checkout", "-B", "main", "origin/main"])
        else:
            run(["git", "checkout", "-B", "main"])
    else:
        run(["git", "remote", "set-url", "origin", remote])
        run(["git", "fetch", "origin", "main"])
        run(["git", "merge", "origin/main", "--no-edit"])

    add_paths = ["catalog.py", "pins", "pinterest_bulk_pins.csv"]
    for p in (extra_paths or []):
        if p not in add_paths:
            add_paths.append(p)
    run(["git", "add"] + add_paths)
    commit = run(["git", "commit", "-m", "Automated cycle: new pin/thumbnail images + Pinterest CSV"])
    if commit.returncode != 0:
        print("Nothing new to commit for GitHub sync.")
        return
    push = run(["git", "push", "origin", "main"])
    if push.returncode == 0:
        print("Pushed updated pins/CSV to GitHub.")
    else:
        print(f"GitHub push failed:\n{push.stderr}")


if __name__ == "__main__":
    main()
