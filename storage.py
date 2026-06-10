"""Push variants to Akamai Cloud (Linode) Object Storage, one bucket per region."""
import os

import boto3
import requests

REGIONS = {
    "americas_morning": {
        "bucket": "prism-us",
        "endpoint": "https://us-sea-1.linodeobjects.com",
        "label": "Seattle",
    },
    "europe_evening": {
        "bucket": "prism-eu",
        "endpoint": "https://de-fra-1.linodeobjects.com",
        "label": "Frankfurt",
    },
    "asia_night": {
        "bucket": "prism-asia",
        "endpoint": "https://sg-sin-1.linodeobjects.com",
        "label": "Singapore",
    },
}


def _client(endpoint: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("LINODE_S3_ACCESS"),
        aws_secret_access_key=os.getenv("LINODE_S3_SECRET"),
    )


def push_to_region(region_key: str, image_url: str, sku_id: str) -> str:
    """Download a generated variant and upload it to the region's bucket. Returns public URL."""
    config = REGIONS[region_key]
    img_bytes = requests.get(image_url, timeout=60).content
    s3 = _client(config["endpoint"])
    key = f"{sku_id}/{region_key}.png"
    s3.put_object(
        Bucket=config["bucket"],
        Key=key,
        Body=img_bytes,
        ACL="public-read",
        ContentType="image/png",
    )
    host = config["endpoint"].removeprefix("https://")
    return f"https://{config['bucket']}.{host}/{key}"


def verify_buckets() -> dict:
    """Phase 1 sanity check: confirm each bucket is reachable and writable."""
    results = {}
    for region_key, config in REGIONS.items():
        try:
            s3 = _client(config["endpoint"])
            s3.put_object(
                Bucket=config["bucket"], Key="_healthcheck.txt",
                Body=b"ok", ACL="public-read", ContentType="text/plain",
            )
            host = config["endpoint"].removeprefix("https://")
            url = f"https://{config['bucket']}.{host}/_healthcheck.txt"
            ok = requests.get(url, timeout=10).status_code == 200
            results[region_key] = "OK" if ok else "upload ok, public read FAILED"
        except Exception as e:
            results[region_key] = f"FAILED: {e}"
    return results


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    for region, status in verify_buckets().items():
        print(f"{region}: {status}")
