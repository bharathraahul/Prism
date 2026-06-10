"""OpenAI generates the context matrix: 3 scene prompts, one per visitor profile."""
import json
import os

import requests

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
# gpt-5.5 = current flagship; gpt-5.4-mini is the cheap/fast option for this simple JSON task
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")

CONTEXT_MATRIX_SYSTEM = """You are an e-commerce imagery strategist.
Given a product, output JSON with exactly 3 context-shifted scene prompts
for Magnific Creative Upscaler. Each scene targets a different visitor profile.

Rules:
- Preserve product identity: the prompt must reinforce that the EXACT product
  in the source image remains the subject, unchanged
- Shift the scene, lighting, mood, time of day around the product
- 40-60 words per prompt

Profiles to cover:
1. americas_morning: bright, optimistic, west-coast morning vibe
2. europe_evening: warm, considered, golden-hour interior
3. asia_night: cozy, neon-adjacent, evening urban setting

Return ONLY valid JSON:
{"americas_morning": "...", "europe_evening": "...", "asia_night": "..."}"""

# Fallback prompts if the API returns invalid JSON (see failure modes table)
FALLBACK_PROMPTS = {
    "americas_morning": (
        "The exact same product, completely unchanged, placed on a sunlit "
        "white oak table by a large window. Bright Pacific-coast morning "
        "light, soft shadows, a hint of fog burning off outside, optimistic "
        "and clean atmosphere, minimal styling, fresh greenery blurred in "
        "the background."
    ),
    "europe_evening": (
        "The exact same product, completely unchanged, resting on a warm "
        "walnut sideboard in a considered European interior. Golden-hour "
        "light streaming low through linen curtains, amber tones, soft "
        "candle glow nearby, quiet and refined evening mood, gentle film-like "
        "warmth."
    ),
    "asia_night": (
        "The exact same product, completely unchanged, on a dark tabletop in "
        "a cozy late-night urban apartment. Soft neon glow from city signage "
        "outside the window, cool blue and magenta accents, warm desk lamp "
        "counterlight, intimate nighttime atmosphere, rain-flecked glass in "
        "the background."
    ),
}

REQUIRED_KEYS = set(FALLBACK_PROMPTS)


def get_context_matrix(product_desc: str) -> dict:
    """Return {profile: scene_prompt}. Falls back to hardcoded prompts on any failure."""
    try:
        api_key = os.environ["OPENAI_API_KEY"]
        resp = requests.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "max_completion_tokens": 1200,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": CONTEXT_MATRIX_SYSTEM},
                    {"role": "user", "content": f"Product: {product_desc}"},
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        matrix = json.loads(text)
        if not REQUIRED_KEYS.issubset(matrix):
            raise ValueError(f"missing keys: {REQUIRED_KEYS - set(matrix)}")
        return {k: matrix[k] for k in REQUIRED_KEYS}
    except Exception as e:
        print(f"[claude_prompts] falling back to hardcoded prompts: {e}")
        return dict(FALLBACK_PROMPTS)
