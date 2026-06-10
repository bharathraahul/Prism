"""Push variants to Akamai Cloud (Linode) Object Storage, one bucket per region.

Note: newer-generation Linode Object Storage regions reject the per-object
x-amz-acl header (NotImplemented). For those, we set a bucket-level
public-read policy once and upload without the ACL header.
"""
import json
import os

import boto3
import requests
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()  # must run before REGIONS is built so .env overrides apply

# Bucket names/endpoints can be overridden in .env without touching code,
# e.g. PRISM_EU_BUCKET=prism-eu2
REGIONS = {
    "americas_morning": {
        "bucket": os.getenv("PRISM_US_BUCKET", "prism-us"),
        "endpoint": os.getenv("PRISM_US_ENDPOINT", "https://us-sea-1.linodeobjects.com"),
        "label": "Seattle",
    },
    # EU zone skipped (bucket write issues) — the evening variant is stored in
    # Seattle instead. To re-enable Frankfurt later, set in .env:
    #   PRISM_EU_BUCKET=prism-eu2
    #   PRISM_EU_ENDPOINT=https://de-fra-1.linodeobjects.com
    #   PRISM_EU_LABEL=Frankfurt
    "europe_evening": {
        "bucket": os.getenv("PRISM_EU_BUCKET", "prism-us"),
        "endpoint": os.getenv("PRISM_EU_ENDPOINT", "https://us-sea-1.linodeobjects.com"),
        "label": os.getenv("PRISM_EU_LABEL", "Seattle"),
    },
    "asia_night": {
        "bucket": os.getenv("PRISM_ASIA_BUCKET", "prism-asia"),
        "endpoint": os.getenv("PRISM_ASIA_ENDPOINT", "https://in-maa-1.linodeobjects.com"),
        "label": "Chennai",
    },
}


def _client(endpoint: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("LINODE_S3_ACCESS"),
        aws_secret_access_key=os.getenv("LINODE_S3_SECRET"),
    )


def _make_bucket_public(s3, bucket: str):
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{bucket}/*"],
        }],
    }
    s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))


def put_public_object(s3, bucket: str, key: str, body: bytes, content_type: str):
    """Upload an object that's publicly readable, on both old- and new-gen regions.

    Ladder: per-object ACL -> plain put + bucket-level public-read policy.
    Public readability is verified by the healthcheck either way.
    """
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=body,
                      ACL="public-read", ContentType=content_type)
        return
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("NotImplemented", "AccessDenied"):
            raise
    # New-gen region: no per-object ACLs. Plain upload + public-read bucket policy.
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)
    try:
        _make_bucket_public(s3, bucket)
    except ClientError as e:
        print(f"  [warn] put_bucket_policy on {bucket}: {e}")


def push_to_region(region_key: str, image_url: str, sku_id: str) -> str:
    """Download a generated variant and upload it to the region's bucket. Returns public URL."""
    config = REGIONS[region_key]
    img_bytes = requests.get(image_url, timeout=60).content
    return push_bytes_to_region(region_key, img_bytes, sku_id)


def push_bytes_to_region(region_key: str, img_bytes: bytes, sku_id: str) -> str:
    config = REGIONS[region_key]
    s3 = _client(config["endpoint"])
    key = f"{sku_id}/{region_key}.png"
    put_public_object(s3, config["bucket"], key, img_bytes, "image/png")
    host = config["endpoint"].removeprefix("https://")
    return f"https://{config['bucket']}.{host}/{key}"


def verify_buckets() -> dict:
    """Phase 1 sanity check: confirm each bucket is reachable, writable, publicly readable."""
    results = {}
    for region_key, config in REGIONS.items():
        try:
            s3 = _client(config["endpoint"])
            put_public_object(s3, config["bucket"], "_healthcheck.txt",
                              b"ok", "text/plain")
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
