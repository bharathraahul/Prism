"""One-shot pipeline: source photo -> Claude context matrix -> Magnific variants
-> regional buckets -> demo_assets/variants.json.

Run this ONCE per demo product BEFORE the demo. The Streamlit app only reads
the resulting JSON, never re-generates.

Usage:
    python generate.py <sku_id> <image_path> "<product description>"
    python generate.py candle-01 photos/candle.jpg "Amber glass candle with cream label reading 'Fireside No. 4'"
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from claude_prompts import get_context_matrix  # noqa: E402
from magnific import magnific_variant, resize_for_upload  # noqa: E402
from storage import push_to_region  # noqa: E402

VARIANTS_FILE = Path("demo_assets/variants.json")


def generate_all_variants(image_bytes: bytes, product_desc: str) -> dict:
    """Claude -> 3 prompts -> 3 parallel Magnific jobs. Returns {region: generated_url}."""
    prompts = get_context_matrix(product_desc)
    print("Context matrix:")
    for k, v in prompts.items():
        print(f"  {k}: {v[:80]}...")
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {region: ex.submit(magnific_variant, image_bytes, p)
                   for region, p in prompts.items()}
        return {region: f.result() for region, f in futures.items()}


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    sku_id, image_path, product_desc = sys.argv[1], sys.argv[2], sys.argv[3]

    image_bytes = resize_for_upload(Path(image_path).read_bytes())
    print(f"Generating variants for {sku_id}...")
    generated = generate_all_variants(image_bytes, product_desc)

    print("Pushing to regional buckets...")
    regional_urls = {region: push_to_region(region, url, sku_id)
                     for region, url in generated.items()}
    for region, url in regional_urls.items():
        print(f"  {region}: {url}")

    # Merge into variants.json, keep "original" for the static-vs-Prism toggle
    VARIANTS_FILE.parent.mkdir(exist_ok=True)
    existing = json.loads(VARIANTS_FILE.read_text()) if VARIANTS_FILE.exists() else {}
    existing[sku_id] = {**regional_urls, "original": image_path}
    VARIANTS_FILE.write_text(json.dumps(existing, indent=2))
    print(f"Saved to {VARIANTS_FILE}")


if __name__ == "__main__":
    main()
