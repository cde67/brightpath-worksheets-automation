"""
Builds a Pinterest Bulk Create Pins CSV for whichever Bright Path Worksheets
products are actually live on Gumroad right now (queried via the API, so this
is always accurate - pending/unpublished products are skipped since there's
nothing to link a pin to yet). Pin images live in the public GitHub repo
(worksheets_automation/pins/*.png, uploaded separately) and are referenced via
raw.githubusercontent.com URLs - Pinterest fetches the image from that URL,
so it must already be public.
"""
import csv
import json
import os
import urllib.request

import catalog as cat

RAW_BASE = "https://raw.githubusercontent.com/cde67/brightpath-worksheets-automation/main/pins"
BOARD = "Homeschool Math Worksheets"


def _old_style_title(grade, operation, num_pages):
    """Duplicated from run_cycle.old_style_title (not imported, to avoid a
    circular import - run_cycle imports this module). A live product created
    before copy_gen existed still has this exact title; matching against it
    too means the CSV isn't blind to already-live products just because
    catalog.py now carries a different (copy_gen-varied) title for the same
    combo."""
    return f"{grade} {operation} Worksheets - {num_pages} Printable Practice Pages + Answer Key - Instant Download"


def load_token():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")) as f:
        for line in f:
            if line.startswith("GUMROAD_ACCESS_TOKEN="):
                return line.strip().split("=", 1)[1]


def live_products_by_title():
    token = load_token()
    result = {}
    url = f"https://api.gumroad.com/v2/products?access_token={token}"
    while url:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
        result.update({p["name"]: p["short_url"] for p in data.get("products", [])})
        next_url = data.get("next_page_url")
        if not next_url:
            break
        full = f"https://api.gumroad.com{next_url}" if next_url.startswith("/") else next_url
        sep = "&" if "?" in full else "?"
        url = f"{full}{sep}access_token={token}"
    return result


def main():
    live = live_products_by_title()
    rows = []
    skipped = []
    for item in cat.CATALOG:
        old_title = _old_style_title(item["grade"], item["operation"], 10)
        link = live.get(item["title"]) or live.get(old_title)
        if not link:
            skipped.append(item["slug"])
            continue
        media_url = f"{RAW_BASE}/{item['slug']}.png"
        rows.append({
            "Title": item["title"][:100],
            "Media URL": media_url,
            "Pinterest board": BOARD,
            "Description": item["description"][:500],
            "Link": link,
        })

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pinterest_bulk_pins.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Title", "Media URL", "Pinterest board", "Description", "Link"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    if skipped:
        print(f"Skipped {len(skipped)} not-yet-published products: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
