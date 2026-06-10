"""Magnific Creative Upscaler client: scene-shifting variants that preserve product identity.

Verified against https://docs.magnific.com (June 2026):
- POST https://api.magnific.com/v1/ai/image-upscaler  (JSON, base64 image)
- GET  https://api.magnific.com/v1/ai/image-upscaler/{task_id}  (poll)
- Auth header: x-magnific-api-key
- Status enum: CREATED | IN_PROGRESS | COMPLETED | FAILED
"""
import base64
import io
import os
import time

import requests
from PIL import Image

BASE_URL = "https://api.magnific.com/v1/ai/image-upscaler"
POLL_INTERVAL_S = 3
TIMEOUT_S = 300  # give up after 5 min, demo uses cached assets anyway

# Identity-preserving prefix prepended to every scene prompt
IDENTITY_PREFIX = "Exact same product, unchanged, identical label and details. "


def _headers():
    key = os.getenv("MAGNIFIC_API_KEY") or os.getenv("FREEPIK_API_KEY", "")
    if not key:
        raise RuntimeError("MAGNIFIC_API_KEY (or FREEPIK_API_KEY) not set")
    return {"x-magnific-api-key": key, "Content-Type": "application/json"}


def resize_for_upload(image_bytes: bytes, max_px: int = 1024) -> bytes:
    """Resize to <=1024px on the long edge (Streamlit memory + Magnific speed)."""
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def magnific_variant(image_bytes: bytes, prompt: str,
                     creativity: int = 6, resemblance: int = 3) -> str:
    """Submit one variant job, poll to completion, return the generated image URL.

    creativity: 5-6 shifts the scene; drop to 4 if product identity drifts,
                bump to 7 if the scene shift looks too weak.
    resemblance: positive values pull the result toward the original image —
                 raise it (instead of only lowering creativity) if the product drifts.
    """
    payload = {
        "image": base64.b64encode(image_bytes).decode(),
        "prompt": IDENTITY_PREFIX + prompt,
        "scale_factor": "2x",
        "optimized_for": "standard",
        "creativity": creativity,
        "resemblance": resemblance,
        "hdr": 2,
        "engine": "magnific_sparkle",
    }
    r = requests.post(BASE_URL, json=payload, headers=_headers(), timeout=60)
    r.raise_for_status()
    task_id = r.json()["data"]["task_id"]

    deadline = time.time() + TIMEOUT_S
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_S)
        status = requests.get(f"{BASE_URL}/{task_id}", headers=_headers(), timeout=30).json()
        state = status["data"]["status"]
        if state == "COMPLETED":
            return status["data"]["generated"][0]
        if state == "FAILED":
            raise RuntimeError(f"Magnific task {task_id} failed: {status}")
    raise TimeoutError(f"Magnific task {task_id} did not finish in {TIMEOUT_S}s")
