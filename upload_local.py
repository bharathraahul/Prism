"""Fallback pipeline: upload locally-generated variants (e.g. from the Magnific
web app) to the regional buckets and write demo_assets/variants.json.

Usage:
    python upload_local.py <sku_id> <original> <americas_img> <europe_img> <asia_img>

Example:
    python upload_local.py candle-01 photos/candle.jpg \
        variants/candle_morning.png variants/candle_evening.png variants/candle_night.png

Output is identical to generate.py — app.py can't tell the difference.
"""
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

from storage import REGIONS, push_bytes_to_region  # noqa: E402

VARIANTS_FILE = Path("demo_assets/variants.json")
REGION_ORDER = ["americas_morning", "europe_evening", "asia_night"]


def push_local_file(region_key: str, file_path: str, sku_id: str) -> str:
    url = push_bytes_to_region(region_key, Path(file_path).read_bytes(), sku_id)
    # Verify public read immediately — fail loud now, not mid-demo
    if requests.get(url, timeout=15).status_code != 200:
        raise RuntimeError(f"Uploaded but public read failed: {url}")
    return url


def main():
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    sku_id, original = sys.argv[1], sys.argv[2]
    variant_paths = sys.argv[3:6]

    for p in [original, *variant_paths]:
        if not Path(p).exists():
            sys.exit(f"File not found: {p}")

    regional_urls = {}
    for region_key, path in zip(REGION_ORDER, variant_paths):
        url = push_local_file(region_key, path, sku_id)
        print(f"  {region_key} ({REGIONS[region_key]['label']}): {url}")
        regional_urls[region_key] = url

    VARIANTS_FILE.parent.mkdir(exist_ok=True)
    existing = json.loads(VARIANTS_FILE.read_text()) if VARIANTS_FILE.exists() else {}
    existing[sku_id] = {**regional_urls, "original": original}
    VARIANTS_FILE.write_text(json.dumps(existing, indent=2))
    print(f"Saved to {VARIANTS_FILE}")


if __name__ == "__main__":
    main()
