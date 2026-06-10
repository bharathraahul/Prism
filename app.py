"""Prism demo UI. Reads pre-generated variants only — never calls Magnific live."""
import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from routing import VISITOR_PROFILES, edge_latency, route

load_dotenv()

st.set_page_config(page_title="Prism", page_icon="🔷", layout="wide")

VARIANTS_FILE = Path("demo_assets/variants.json")


@st.cache_data
def load_products() -> dict:
    if not VARIANTS_FILE.exists():
        return {}
    return json.loads(VARIANTS_FILE.read_text())


@st.cache_data(ttl=60)
def cached_latency(url: str) -> int:
    return edge_latency(url)


DEMO_PRODUCTS = load_products()

st.title("Prism")
st.caption("Personalized product imagery at the edge. Same product. Every visitor. Their light.")

if not DEMO_PRODUCTS:
    st.warning(
        "No demo products found. Run the pipeline first:\n\n"
        "`python generate.py <sku_id> <image_path> \"<product description>\"`"
    )
    st.stop()

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("Pick a demo product")
    sku = st.radio("Product", list(DEMO_PRODUCTS.keys()),
                   format_func=lambda k: k.replace("-", " ").title())

    st.subheader("View as visitor from")
    visitor = st.radio("Visitor profile", list(VISITOR_PROFILES.keys()),
                       format_func=lambda k: k.replace("_", " ").title())

    compare = st.toggle("Static hero vs Prism", value=False,
                        help="Left: what every visitor sees today. Right: what Prism serves.")

with col_right:
    variants = DEMO_PRODUCTS[sku]
    routed = route(visitor, variants)

    if compare and variants.get("original"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Static hero (today)**")
            st.image(variants["original"], use_container_width=True)
        with c2:
            st.markdown("**Prism (this visitor)**")
            st.image(routed["url"], use_container_width=True)
    else:
        st.image(routed["url"], use_container_width=True)

    latency = cached_latency(routed["url"])
    latency_str = f"{latency}ms" if latency >= 0 else "n/a"

    m1, m2, m3 = st.columns(3)
    m1.metric("Visitor context", routed["context"])
    m2.metric("Served from", f"Akamai edge · {routed['edge']}")
    m3.metric("Latency", latency_str)

st.divider()

with st.expander("Why this matters"):
    st.write("""
    A/B testing product imagery is a proven 20-40% conversion lever.
    Today, no e-commerce platform does it at the asset layer because variant
    generation and per-visitor delivery are both manual.

    Prism makes both automatic:
    - Magnific Creative Upscaler with reference image mode generates context
      variants that preserve exact product identity
    - Akamai Cloud Object Storage regions serve the right variant from the
      edge nearest each visitor
    """)
