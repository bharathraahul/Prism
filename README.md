# Prism 🔷

**Personalized product imagery at the edge.** Same product, different visitor, different hero image — served from the Akamai Cloud region nearest them.

One phone photo in → Claude generates a context matrix → Magnific Creative Upscaler produces identity-preserving scene variants → variants distributed across 3 Akamai Cloud Object Storage regions (Seattle, Frankfurt, Singapore) → each visitor gets their variant from their nearest edge.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in keys
python storage.py      # verify all 3 regional buckets (Phase 1 check)

# Pre-generate variants per demo product (run ONCE before demo)
python generate.py candle-01 photos/candle.jpg "Amber glass candle with cream label"
python generate.py sneaker-01 photos/sneaker.jpg "White leather sneaker with red logo"

# Demo
streamlit run app.py --server.port 8501
```

## Structure

```
app.py             Streamlit demo UI (reads cached variants only)
generate.py        One-shot pipeline: photo → variants → regional buckets
claude_prompts.py  OpenAI context matrix (with hardcoded fallback prompts)
magnific.py        Freepik/Magnific Creative Upscaler client
storage.py         Regional bucket uploads + healthcheck
routing.py         Visitor profile → edge routing + latency
demo_assets/       variants.json with pre-generated URLs
```

## Demo flow

Pick a product, click through visitor profiles (SF / London / Tokyo / Sydney), watch the hero image, edge region, and live latency change. Toggle "Static hero vs Prism" for the side-by-side.
