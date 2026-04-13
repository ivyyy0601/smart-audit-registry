"""
Fetch verified Solidity source code from Etherscan API.
"""
import os
import json
import requests

ETHERSCAN_API = "https://api.etherscan.io/v2/api"


def fetch_source_code(contract_address: str, api_key: str = None) -> str:
    """
    Fetch the Solidity source code of a verified contract by its address.
    Raises ValueError if the contract is not verified or the request fails.
    """
    key = api_key or os.getenv("ETHERSCAN_API_KEY")
    if not key:
        raise ValueError("ETHERSCAN_API_KEY not set")

    params = {
        "chainid": "11155111",  # Sepolia
        "module": "contract",
        "action": "getsourcecode",
        "address": contract_address,
        "apikey": key,
    }
    resp = requests.get(ETHERSCAN_API, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "1" or not data.get("result"):
        raise ValueError(f"Etherscan error: {data.get('message', 'Unknown error')}")

    result = data["result"][0]
    source = result.get("SourceCode", "").strip()

    if not source:
        raise ValueError("Contract source code not verified on Etherscan")

    # Handle multi-file contracts (source is a JSON string wrapped in extra braces)
    if source.startswith("{{"):
        source = source[1:-1]
        try:
            files = json.loads(source).get("sources", {})
            source = "\n\n".join(v.get("content", "") for v in files.values())
        except Exception:
            pass

    return source
