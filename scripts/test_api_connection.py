"""
Quick connectivity test for the Indigitall API using ServerKey auth.

Usage:
    python scripts/test_api_connection.py

No Docker or database required — runs standalone.
"""

import json
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

BASE_URL = os.getenv("INDIGITALL_API_BASE_URL", "https://am1.api.indigitall.com").rstrip("/")
SERVER_KEY = os.getenv("INDIGITALL_SERVER_KEY", "")
APP_TOKEN = os.getenv("INDIGITALL_APP_TOKEN", "")

TIMEOUT = 30


def make_request(method: str, endpoint: str, params: dict | None = None,
                 payload: dict | None = None, base_url: str | None = None) -> dict | None:
    """Make an authenticated request and print the result."""
    url = f"{base_url or BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"ServerKey {SERVER_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    print(f"\n{'='*60}")
    print(f"  {method} {endpoint}")
    if params:
        print(f"  Params: {params}")
    print(f"{'='*60}")

    start = time.time()
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
        else:
            resp = requests.post(url, headers=headers, json=payload, params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        print(f"  [ERROR] Request failed: {exc}")
        return None

    duration_ms = int((time.time() - start) * 1000)

    print(f"  Status: {resp.status_code} ({duration_ms}ms)")
    print(f"  Content-Type: {resp.headers.get('content-type', 'unknown')}")

    if not resp.ok:
        print(f"  [ERROR] Response: {resp.text[:500]}")
        return None

    try:
        data = resp.json()
    except ValueError:
        print(f"  [ERROR] Non-JSON response: {resp.text[:300]}")
        return None

    # Print structure summary
    if isinstance(data, list):
        print(f"  Response: list with {len(data)} items")
        if data:
            print(f"  First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else type(data[0])}")
    elif isinstance(data, dict):
        print(f"  Response keys: {list(data.keys())}")
        # Check for nested data arrays
        for key in ("data", "items", "results", "applications", "campaigns"):
            if key in data and isinstance(data[key], list):
                print(f"  data['{key}']: list with {len(data[key])} items")
                if data[key] and isinstance(data[key][0], dict):
                    print(f"  First item keys: {list(data[key][0].keys())}")
    else:
        print(f"  Response type: {type(data)}")

    return data


def save_response(name: str, data):
    """Save raw response to a JSON file for inspection."""
    out_dir = Path(__file__).resolve().parent / "api_responses"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved to: {out_path}")


def main():
    print("=" * 60)
    print("  Indigitall API Connection Test")
    print("=" * 60)

    if not SERVER_KEY or not APP_TOKEN:
        print("\n[ERROR] INDIGITALL_SERVER_KEY and INDIGITALL_APP_TOKEN must be set in .env")
        sys.exit(1)

    print(f"\n  Base URL:   {BASE_URL}")
    print(f"  ServerKey:  {SERVER_KEY[:8]}...{SERVER_KEY[-4:]}")
    print(f"  AppToken:   {APP_TOKEN[:8]}...{APP_TOKEN[-4:]}")

    # ---- Test 1: Server Status ----
    print("\n\n### TEST 1: Server Status ###")
    status = make_request("GET", "/v1/status")
    if status:
        save_response("01_status", status)

    # ---- Test 2: List Applications ----
    print("\n\n### TEST 2: List Applications ###")
    apps = make_request("GET", "/v1/application", params={"limit": 50, "page": 0})
    if apps:
        save_response("02_applications", apps)

        # Extract app IDs for further testing
        app_list = apps if isinstance(apps, list) else apps.get("data", apps.get("applications", []))
        if isinstance(app_list, dict):
            app_list = [app_list]

        if app_list:
            first_app = app_list[0]
            app_id = first_app.get("appKey") or first_app.get("id") or first_app.get("applicationId")
            app_name = first_app.get("name", "unknown")
            print(f"\n  Using first app for tests: {app_name} (id={app_id})")

            if app_id:
                from datetime import date, timedelta
                date_to = date.today().isoformat()
                date_from = (date.today() - timedelta(days=30)).isoformat()

                # ---- Test 3: App Stats ----
                print("\n\n### TEST 3: Application Stats ###")
                stats = make_request("GET", f"/v1/application/{app_id}/stats")
                if stats:
                    save_response("03_app_stats", stats)

                # ---- Test 4: App Date Stats ----
                print("\n\n### TEST 4: Application Date Stats ###")
                date_stats = make_request("GET", f"/v1/application/{app_id}/dateStats",
                                          params={"dateFrom": date_from, "dateTo": date_to,
                                                  "periodicity": "day"})
                if date_stats:
                    save_response("04_date_stats", date_stats)

                # ---- Test 5: Dashboard Stats ----
                print("\n\n### TEST 5: Dashboard Stats ###")
                dash_stats = make_request("GET", f"/v1/application/{app_id}/stats/dashboard")
                if dash_stats:
                    save_response("05_dashboard_stats", dash_stats)

                # ---- Test 6: Push Heatmap ----
                print("\n\n### TEST 6: Push Heatmap ###")
                heatmap = make_request("GET", f"/v1/application/{app_id}/pushHeatmap",
                                       params={"dateFrom": date_from, "dateTo": date_to})
                if heatmap:
                    save_response("06_push_heatmap", heatmap)

                # ---- Test 7: Campaigns ----
                print("\n\n### TEST 7: Campaigns ###")
                campaigns = make_request("GET", "/v1/campaign",
                                         params={"applicationId": app_id, "limit": 20, "page": 0})
                if campaigns:
                    save_response("07_campaigns", campaigns)

                # ---- Test 8: Campaign Stats ----
                print("\n\n### TEST 8: Campaign Stats ###")
                camp_stats = make_request("GET", "/v1/campaign/stats",
                                          params={"applicationId": app_id,
                                                  "dateFrom": date_from, "dateTo": date_to,
                                                  "limit": 20})
                if camp_stats:
                    save_response("08_campaign_stats", camp_stats)

                # ---- Test 9: Chat Contacts ----
                print("\n\n### TEST 9: Chat Contacts ###")
                contacts = make_request("GET", "/v1/chat/contacts",
                                        params={"applicationId": app_id, "limit": 20, "offset": 0})
                if contacts:
                    save_response("09_chat_contacts", contacts)

                # ---- Test 10: SMS Stats ----
                print("\n\n### TEST 10: SMS Stats ###")
                sms = make_request("GET", f"/v2/sms/stats/{app_id}",
                                   params={"dateFrom": date_from, "dateTo": date_to})
                if sms:
                    save_response("10_sms_stats", sms)

                # ---- Test 11: Email Stats ----
                print("\n\n### TEST 11: Email Stats ###")
                email = make_request("GET", f"/v2/email/stats/{app_id}",
                                     params={"dateFrom": date_from, "dateTo": date_to})
                if email:
                    save_response("11_email_stats", email)

                # ---- Test 12: InApp Stats ----
                print("\n\n### TEST 12: InApp Stats ###")
                inapp = make_request("GET", "/v1/inApp/stats",
                                     params={"applicationId": app_id,
                                             "dateFrom": date_from, "dateTo": date_to})
                if inapp:
                    save_response("12_inapp_stats", inapp)

                # ---- Test 13: Device Stats ----
                print("\n\n### TEST 13: Device Stats ###")
                devices = make_request("GET", f"/v1/application/{app_id}/stats/device",
                                       params={"dateFrom": date_from, "dateTo": date_to})
                if devices:
                    save_response("13_device_stats", devices)

                # ---- Test 14: Chat Agent Status ----
                print("\n\n### TEST 14: Chat Agent Status ###")
                agents = make_request("GET", "/v1/chat/agent/status",
                                      params={"applicationId": app_id})
                if agents:
                    save_response("14_chat_agent_status", agents)

                # ---- Test 15: Account Stats ----
                print("\n\n### TEST 15: Account-level Stats ###")
                account_stats = make_request("GET", "/v1/application/stats",
                                             params={"limit": 50, "page": 0})
                if account_stats:
                    save_response("15_account_stats", account_stats)

                # ---- Test 16: Chat conversations ----
                print("\n\n### TEST 16: Chat Conversations ###")
                convos = make_request("GET", "/v1/chat/conversations",
                                      params={"applicationId": app_id, "limit": 20, "offset": 0})
                if convos:
                    save_response("16_chat_conversations", convos)

                # ---- Test 17: Push campaigns ----
                print("\n\n### TEST 17: Push Campaigns ###")
                push_camp = make_request("GET", f"/v1/push/{app_id}/campaign",
                                         params={"limit": 20, "page": 0})
                if push_camp:
                    save_response("17_push_campaigns", push_camp)

                # ---- Test 18: Device browser stats ----
                print("\n\n### TEST 18: Device Browser Stats ###")
                browsers = make_request("GET", f"/v1/application/{app_id}/stats/browser",
                                        params={"dateFrom": date_from, "dateTo": date_to})
                if browsers:
                    save_response("18_browser_stats", browsers)

                # ---- Test 19: WhatsApp templates ----
                print("\n\n### TEST 19: WhatsApp Templates ###")
                wa_templates = make_request("GET", "/v1/chat/template",
                                            params={"applicationId": app_id, "limit": 20, "page": 0})
                if wa_templates:
                    save_response("19_whatsapp_templates", wa_templates)

    # ---- Summary ----
    print("\n\n" + "=" * 60)
    print("  Test Complete")
    print("=" * 60)
    print(f"  Responses saved to: scripts/api_responses/")
    print(f"  Review the JSON files to understand the API structure.")
    print("=" * 60)


if __name__ == "__main__":
    main()
