"""
Round 2: Deeper exploration of working endpoints + chat-focused discovery.

Findings from Round 1:
  - Region: am1
  - App: VISIONAMOS PROD (id=100274, chatEnabled=true)
  - Working: /v1/application, /v1/chat/contacts, /v1/chat/agent/status, pushHeatmap
  - Pagination uses: limit + page (not offset) for most endpoints
"""

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

BASE_URL = os.getenv("INDIGITALL_API_BASE_URL", "https://am1.api.indigitall.com").rstrip("/")
SERVER_KEY = os.getenv("INDIGITALL_SERVER_KEY", "")

TIMEOUT = 30
APP_ID = 100274
CONTACT_ID = "573054821614"  # "Gise" — active contact with recent messages

date_to = date.today().isoformat()
date_7d = (date.today() - timedelta(days=7)).isoformat()
date_30d = (date.today() - timedelta(days=30)).isoformat()


def req(method: str, endpoint: str, params: dict | None = None,
        payload: dict | None = None) -> dict | None:
    url = f"{BASE_URL}{endpoint}"
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
    except Exception as exc:
        print(f"  [ERROR] {exc}")
        return None

    ms = int((time.time() - start) * 1000)
    print(f"  Status: {resp.status_code} ({ms}ms)")

    if not resp.ok:
        print(f"  [ERROR] {resp.text[:300]}")
        return None

    try:
        data = resp.json()
    except ValueError:
        print(f"  [ERROR] Non-JSON: {resp.text[:200]}")
        return None

    if isinstance(data, dict):
        print(f"  Keys: {list(data.keys())}")
        for k in ("data", "items", "results"):
            if k in data and isinstance(data[k], list):
                print(f"  data['{k}']: {len(data[k])} items")
                if data[k] and isinstance(data[k][0], dict):
                    print(f"    First keys: {list(data[k][0].keys())}")
            elif k in data and isinstance(data[k], dict):
                print(f"  data['{k}']: dict with keys {list(data[k].keys())[:10]}")
    elif isinstance(data, list):
        print(f"  List with {len(data)} items")

    return data


def save(name: str, data):
    out_dir = Path(__file__).resolve().parent / "api_responses"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved: {path.name}")


def main():
    print("=" * 60)
    print("  Round 2 — Chat + Stats Deep Exploration")
    print("=" * 60)

    # --- Chat Messages for a specific contact ---
    print("\n\n### Chat Messages ###")
    msgs = req("GET", "/v1/chat/message",
               params={"applicationId": APP_ID, "contactId": CONTACT_ID,
                        "limit": 20, "offset": 0})
    if msgs:
        save("20_chat_messages", msgs)

    # --- Chat Messages (page-based) ---
    msgs2 = req("GET", "/v1/chat/message",
                params={"applicationId": APP_ID, "contactId": CONTACT_ID,
                         "limit": 20, "page": 0})
    if msgs2:
        save("20b_chat_messages_page", msgs2)

    # --- Chat instances ---
    print("\n\n### Chat Instances ###")
    instances = req("GET", "/v1/chat/instance",
                    params={"applicationId": APP_ID, "limit": 20, "page": 0})
    if instances:
        save("21_chat_instances", instances)

    instances2 = req("GET", "/v1/chat/instance",
                     params={"applicationId": APP_ID, "limit": 20, "offset": 0})
    if instances2:
        save("21b_chat_instances_offset", instances2)

    # --- Chat agents list ---
    print("\n\n### Chat Agents ###")
    agents = req("GET", "/v1/chat/agent",
                 params={"applicationId": APP_ID, "limit": 50, "page": 0})
    if agents:
        save("22_chat_agents", agents)

    agents2 = req("GET", "/v1/chat/agent",
                  params={"applicationId": APP_ID, "limit": 50, "offset": 0})
    if agents2:
        save("22b_chat_agents_offset", agents2)

    # --- Chat stats ---
    print("\n\n### Chat Stats ###")
    chat_stats = req("GET", "/v1/chat/stats",
                     params={"applicationId": APP_ID,
                             "dateFrom": date_7d, "dateTo": date_to})
    if chat_stats:
        save("23_chat_stats", chat_stats)

    # --- Date stats (daily periodicity) ---
    print("\n\n### Date Stats (daily) ###")
    ds = req("GET", f"/v1/application/{APP_ID}/dateStats",
             params={"dateFrom": date_7d, "dateTo": date_to, "periodicity": "daily"})
    if ds:
        save("04_date_stats", ds)

    # --- Device stats (7-day range to avoid 403) ---
    print("\n\n### Device Stats (7 days) ###")
    dev = req("GET", f"/v1/application/{APP_ID}/stats/device",
              params={"dateFrom": date_7d, "dateTo": date_to})
    if dev:
        save("13_device_stats", dev)

    # --- Campaign stats with page ---
    print("\n\n### Campaign Stats ###")
    cs = req("GET", "/v1/campaign/stats",
             params={"applicationId": APP_ID,
                     "dateFrom": date_30d, "dateTo": date_to,
                     "limit": 20, "page": 0})
    if cs:
        save("08_campaign_stats", cs)

    # --- Application stats with applicationId ---
    print("\n\n### Application Stats (with appId) ###")
    astats = req("GET", "/v1/application/stats",
                 params={"applicationId": APP_ID, "limit": 50, "page": 0})
    if astats:
        save("15_account_stats", astats)

    # --- Chat contact details ---
    print("\n\n### Chat Contact Detail ###")
    cd = req("GET", f"/v1/chat/contacts/{CONTACT_ID}",
             params={"applicationId": APP_ID})
    if cd:
        save("24_chat_contact_detail", cd)

    # --- Chat WhatsApp templates ---
    print("\n\n### Chat Templates (WhatsApp) ###")
    tpl = req("GET", "/v1/chat/whatsapp/template",
              params={"applicationId": APP_ID, "limit": 20, "page": 0})
    if tpl:
        save("25_whatsapp_templates", tpl)

    tpl2 = req("GET", f"/v1/chat/{APP_ID}/template",
               params={"limit": 20, "page": 0})
    if tpl2:
        save("25b_chat_templates", tpl2)

    # --- Chat tags ---
    print("\n\n### Chat Tags ###")
    tags = req("GET", "/v1/chat/tag",
               params={"applicationId": APP_ID, "limit": 50, "page": 0})
    if tags:
        save("26_chat_tags", tags)

    tags2 = req("GET", "/v1/chat/tag",
                params={"applicationId": APP_ID, "limit": 50, "offset": 0})
    if tags2:
        save("26b_chat_tags_offset", tags2)

    # --- InApp with shorter date range ---
    print("\n\n### InApp Stats (7 days) ###")
    ia = req("GET", "/v1/inApp/stats",
             params={"applicationId": APP_ID,
                     "dateFrom": date_7d, "dateTo": date_to})
    if ia:
        save("12_inapp_stats", ia)

    # --- Dashboard stats (try v2) ---
    print("\n\n### Dashboard Stats v2 ###")
    d2 = req("GET", f"/v2/application/{APP_ID}/stats/dashboard")
    if d2:
        save("05b_dashboard_v2", d2)

    # --- Chat groups ---
    print("\n\n### Chat Groups ###")
    grp = req("GET", "/v1/chat/group",
              params={"applicationId": APP_ID, "limit": 20, "page": 0})
    if grp:
        save("27_chat_groups", grp)

    grp2 = req("GET", "/v1/chat/group",
               params={"applicationId": APP_ID, "limit": 20, "offset": 0})
    if grp2:
        save("27b_chat_groups_offset", grp2)

    print("\n\n" + "=" * 60)
    print("  Round 2 Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
