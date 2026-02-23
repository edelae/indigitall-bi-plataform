"""
Test all Indigitall API regional endpoints to find the correct one.

The API is region-specific:
  - am1.api.indigitall.com  (Americas / Latin America)
  - eu1.api.indigitall.com  (Europe pre-2021)
  - eu2.api.indigitall.com  (Europe / worldwide post-2021)
  - eu3.api.indigitall.com  (post-Sept 2024)
  - api.indigitall.com       (legacy/generic)

Auth format: Authorization: ServerKey <UUID>  (NO AppToken header)
"""

import requests
from pathlib import Path
from dotenv import load_dotenv
import os

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

SERVER_KEY = os.getenv("INDIGITALL_SERVER_KEY", "")
APP_TOKEN = os.getenv("INDIGITALL_APP_TOKEN", "")

REGIONS = [
    ("am1", "https://am1.api.indigitall.com"),
    ("eu1", "https://eu1.api.indigitall.com"),
    ("eu2", "https://eu2.api.indigitall.com"),
    ("eu3", "https://eu3.api.indigitall.com"),
    ("generic", "https://api.indigitall.com"),
]

TIMEOUT = 15


def test_region(name: str, base_url: str):
    """Test authentication against a region using ServerKey only."""
    print(f"\n{'='*50}")
    print(f"  Region: {name} — {base_url}")
    print(f"{'='*50}")

    # Test 1: Status (no auth needed)
    try:
        r = requests.get(f"{base_url}/v1/status", timeout=TIMEOUT)
        print(f"  /v1/status: {r.status_code} — {r.text[:100]}")
    except Exception as e:
        print(f"  /v1/status: FAILED — {e}")
        return False

    # Test 2: Application list with ServerKey only (correct format per docs)
    headers_sk = {
        "Authorization": f"ServerKey {SERVER_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        r = requests.get(f"{base_url}/v1/application", headers=headers_sk, timeout=TIMEOUT)
        print(f"  /v1/application (ServerKey only): {r.status_code} — {r.text[:200]}")
        if r.ok:
            print(f"  >>> SUCCESS! Region '{name}' works with ServerKey auth!")
            return True
    except Exception as e:
        print(f"  /v1/application (ServerKey only): FAILED — {e}")

    # Test 3: Try with AppToken as well (in case it's needed for some accounts)
    headers_both = {
        "Authorization": f"ServerKey {SERVER_KEY}",
        "AppToken": APP_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        r = requests.get(f"{base_url}/v1/application", headers=headers_both, timeout=TIMEOUT)
        print(f"  /v1/application (SK + AppToken): {r.status_code} — {r.text[:200]}")
        if r.ok:
            print(f"  >>> SUCCESS! Region '{name}' works with ServerKey + AppToken!")
            return True
    except Exception as e:
        print(f"  /v1/application (SK + AppToken): FAILED — {e}")

    # Test 4: Try AppToken as the ServerKey (maybe credentials are swapped)
    headers_swap = {
        "Authorization": f"ServerKey {APP_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        r = requests.get(f"{base_url}/v1/application", headers=headers_swap, timeout=TIMEOUT)
        print(f"  /v1/application (AppToken as SK): {r.status_code} — {r.text[:200]}")
        if r.ok:
            print(f"  >>> SUCCESS! Region '{name}' works with AppToken as ServerKey!")
            return True
    except Exception as e:
        print(f"  /v1/application (AppToken as SK): FAILED — {e}")

    return False


def main():
    print("=" * 50)
    print("  Indigitall Region Discovery")
    print("=" * 50)
    print(f"  ServerKey: {SERVER_KEY[:8]}...{SERVER_KEY[-4:]}")
    print(f"  AppToken:  {APP_TOKEN[:8]}...{APP_TOKEN[-4:]}")

    found = False
    for name, url in REGIONS:
        if test_region(name, url):
            found = True
            break

    if not found:
        print("\n" + "=" * 50)
        print("  NO REGION MATCHED — All returned 401")
        print("=" * 50)
        print("  Possible causes:")
        print("    1. ServerKey is expired or revoked")
        print("    2. ServerKey was not copied correctly")
        print("    3. Account requires a different auth method")
        print("  Recommendation: verify the ServerKey in the Indigitall Console")
        print("    Settings > Server Keys")
    else:
        print("\n  Region found! Update INDIGITALL_API_BASE_URL in .env")


if __name__ == "__main__":
    main()
