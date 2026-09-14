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
from build_pin_images import parse_grade_operation

RAW_BASE = "https://raw.githubusercontent.com/cde67/brightpath-worksheets-automation/main/pins"
BOARD = "Homeschool Math Worksheets"


def load_token():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")) as f:
        for line in f:
            if line.startswith("GUMROAD_ACCESS_TOKEN="):
                return line.strip().split("=", 1)[1]


def live_products_by_title():
    token = load_token()
    url = f"https://api.gumroad.com/v2/products?access_token={token}"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read().decode())
    return {p["name"]: p["short_url"] for p in data.get("products", [])}


def main():
    live = live_products_by_title()
    rows = []
    skipped = []
    for item in cat.CATALOG:
        link = live.get(item["title"])
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
