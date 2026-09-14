"""
Publishes worksheet bundle PDFs (from catalog.py) to Gumroad via their API:
presign -> upload to S3 -> complete -> create product with the file attached.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.gumroad.com/v2"


def load_token():
    env_token = os.environ.get("GUMROAD_ACCESS_TOKEN")
    if env_token:
        return env_token
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("GUMROAD_ACCESS_TOKEN="):
                    return line.strip().split("=", 1)[1]
    return None


TOKEN = load_token()


def post_form(path, fields):
    body = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(f"{API_BASE}{path}", data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print("ERROR body:", e.read().decode())
        raise


def upload_file(file_path):
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    presign = post_form("/files/presign", {
        "access_token": TOKEN,
        "filename": filename,
        "file_size": file_size,
    })
    if not presign.get("success"):
        raise RuntimeError(f"presign failed: {presign}")

    upload_id = presign["upload_id"]
    key = presign["key"]
    file_url = presign["file_url"]
    parts = presign["parts"]  # list of {part_number, url}

    with open(file_path, "rb") as f:
        data = f.read()

    etags = []
    chunk_size = (len(data) + len(parts) - 1) // len(parts) if len(parts) > 1 else len(data)
    for part in parts:
        pn = part["part_number"]
        start = (pn - 1) * chunk_size
        end = min(start + chunk_size, len(data))
        chunk = data[start:end]
        put_req = urllib.request.Request(part["presigned_url"], data=chunk, method="PUT")
        with urllib.request.urlopen(put_req) as resp:
            etag = resp.headers.get("ETag", "").strip('"')
        etags.append({"part_number": pn, "etag": etag})

    complete_fields = [("access_token", TOKEN), ("upload_id", upload_id), ("key", key)]
    for e in etags:
        complete_fields.append(("parts[][part_number]", str(e["part_number"])))
        complete_fields.append(("parts[][etag]", e["etag"]))
    complete = post_form("/files/complete", complete_fields)
    if not complete.get("success"):
        raise RuntimeError(f"complete failed: {complete}")

    return complete.get("file_url", file_url)


def create_product(title, description, price_cents, tags, file_path):
    file_url = upload_file(file_path)
    fields = [
        ("access_token", TOKEN),
        ("name", title),
        ("price", str(price_cents)),
        ("price_currency_type", "usd"),
        ("description", description),
        ("native_type", "digital"),
        ("files[][url]", file_url),
    ]
    for t in tags:
        fields.append(("tags[]", t))
    result = post_form("/products", fields)
    return result


def enable_product(product_id):
    req = urllib.request.Request(
        f"{API_BASE}/products/{urllib.parse.quote(product_id)}/enable",
        data=urllib.parse.urlencode({"access_token": TOKEN}).encode(),
        method="PUT",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    import catalog as cat
    results = []
    for item in cat.CATALOG:
        path = os.path.join(os.path.dirname(__file__), item["file"])
        print(f"Publishing {item['slug']}...")
        res = create_product(item["title"], item["description"], item["price_cents"], item["tags"], path)
        if not res.get("success"):
            print(f"  FAILED: {res}")
            continue
        product_id = res["product"]["id"]
        enable_res = enable_product(product_id)
        url = enable_res.get("product", {}).get("short_url", "")
        print(f"  -> {url}")
        results.append({"slug": item["slug"], "id": product_id, "url": url})

    print(f"\nDONE: {len(results)}/{len(cat.CATALOG)} published")
    for r in results:
        print(r)


if __name__ == "__main__":
    main()
