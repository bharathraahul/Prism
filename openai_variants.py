"""Last-resort variant generation via OpenAI's image-edits API (gpt-image-1).

Use only if Magnific access is unavailable. Produces morning.png / evening.png /
night.png in the current directory, ready for upload_local.py.

Usage:
    python openai_variants.py photos/Watch.jpg "silver analog wristwatch ... worn on a wrist"
    python upload_local.py watch-01 photos/Watch.jpg morning.png evening.png night.png
"""
import base64
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

from claude_prompts import get_context_matrix  # noqa: E402
from magnific import IDENTITY_PREFIX, resize_for_upload  # noqa: E402

EDIT_URL = "https://api.openai.com/v1/images/edits"
OUTFILES = {
    "americas_morning": "morning.png",
    "europe_evening": "evening.png",
    "asia_night": "night.png",
}


def openai_variant(image_bytes: bytes, prompt: str) -> bytes:
    r = requests.post(
        EDIT_URL,
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        files={"image": ("source.png", image_bytes, "image/png")},
        data={
            "model": "gpt-image-1",
            "prompt": IDENTITY_PREFIX + prompt,
            "size": "1024x1024",
            "quality": "medium",
        },
        timeout=300,
    )
    r.raise_for_status()
    return base64.b64decode(r.json()["data"][0]["b64_json"])


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    image_path, product_desc = sys.argv[1], sys.argv[2]
    image_bytes = resize_for_upload(Path(image_path).read_bytes())

    prompts = get_context_matrix(product_desc)
    for region, outfile in OUTFILES.items():
        print(f"Generating {region} -> {outfile} ...")
        Path(outfile).write_bytes(openai_variant(image_bytes, prompts[region]))
    print("Done. Next:")
    print(f"  python upload_local.py <sku_id> {image_path} morning.png evening.png night.png")


if __name__ == "__main__":
    main()
