"""Visitor profile -> regional edge routing, plus live latency measurement."""
import subprocess

VISITOR_PROFILES = {
    "san_francisco_morning": {
        "region_key": "americas_morning",
        "context": "SF, 9am PST, autumn",
        "edge": "Seattle",
    },
    "london_evening": {
        "region_key": "europe_evening",
        "context": "London, 7pm GMT, autumn",
        "edge": "Frankfurt",
    },
    "tokyo_night": {
        "region_key": "asia_night",
        "context": "Tokyo, 11pm JST, autumn",
        "edge": "Singapore",
    },
    "sydney_sunset": {
        "region_key": "asia_night",  # reuse asia variant
        "context": "Sydney, 6pm AEST, spring",
        "edge": "Singapore",
    },
}


def route(visitor_key: str, variant_urls: dict) -> dict:
    profile = VISITOR_PROFILES[visitor_key]
    return {
        "url": variant_urls[profile["region_key"]],
        "edge": profile["edge"],
        "context": profile["context"],
    }


def edge_latency(url: str) -> int:
    """Total request time in ms from this machine to the regional endpoint."""
    try:
        out = subprocess.run(
            ["curl", "-o", "/dev/null", "-s", "-w", "%{time_total}", url],
            capture_output=True, text=True, timeout=15,
        )
        return int(float(out.stdout) * 1000)
    except Exception:
        return -1  # UI shows "n/a" instead of crashing mid-demo
