"""
Upload audit reports to IPFS via Pinata v3 API.
"""
import os
import json
import hashlib
import requests

PINATA_V3_URL = "https://uploads.pinata.cloud/v3/files"


def upload_report(report: dict, name: str = "audit-report") -> str:
    """
    Upload a JSON audit report to Pinata IPFS using v3 API.
    Returns the IPFS CID, or a sha256 hash as fallback.
    """
    jwt = os.getenv("PINATA_JWT", "").strip()

    if jwt:
        try:
            content = json.dumps(report, indent=2).encode("utf-8")
            files = {"file": (f"{name}.json", content, "application/json")}
            # network=true tells Pinata to propagate to the public IPFS network
            data  = {"network": "public"}
            headers = {"Authorization": f"Bearer {jwt}"}
            resp = requests.post(PINATA_V3_URL, files=files, data=data,
                                 headers=headers, timeout=30)
            resp.raise_for_status()
            cid = resp.json()["data"]["cid"]
            print(f"[INFO] IPFS upload success: {cid}")
            return cid
        except Exception as e:
            print(f"[WARN] IPFS upload failed, using local hash: {e}")

    # Fallback: SHA256 hash of report content
    report_bytes = json.dumps(report, sort_keys=True).encode("utf-8")
    sha256 = hashlib.sha256(report_bytes).hexdigest()
    return f"sha256:{sha256}"
