"""
Orchestrator — main entry point for the Indigitall extraction pipeline.

Usage:
    docker compose exec app python -m scripts.extractors.orchestrator
"""

import sys
import time
from pathlib import Path

# Ensure project root is on sys.path so `app.*` and `scripts.*` resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.models.database import engine
from scripts.extractors.config import extraction_settings as cfg
from scripts.extractors.api_client import IndigitallAPIClient
from scripts.extractors.discovery import discover_applications, get_visionamos_apps
from scripts.extractors.push_extractor import PushExtractor
from scripts.extractors.chat_extractor import ChatExtractor
from scripts.extractors.sms_extractor import SMSExtractor
from scripts.extractors.email_extractor import EmailExtractor
from scripts.extractors.inapp_extractor import InAppExtractor
from scripts.extractors.campaigns_extractor import CampaignsExtractor
from scripts.extractors.contacts_extractor import ContactsExtractor

MAX_FALLBACK_APPS = 3


def main():
    print("=" * 60)
    print("  Indigitall API Extraction Pipeline")
    print("=" * 60)

    # ----- Validate credentials -----
    has_server_key = bool(cfg.INDIGITALL_SERVER_KEY)
    has_jwt_creds = cfg.INDIGITALL_EMAIL and cfg.INDIGITALL_PASSWORD
    if not has_server_key and not has_jwt_creds:
        print("\n[ERROR] Set INDIGITALL_SERVER_KEY (ServerKey auth)")
        print("        or INDIGITALL_EMAIL + INDIGITALL_PASSWORD (JWT auth)")
        print("        in .env")
        sys.exit(1)

    start_time = time.time()

    # ----- Authenticate -----
    print("\n[1/4] Authenticating...")
    client = IndigitallAPIClient(engine)
    try:
        client.authenticate()
        print("  Authentication successful")
    except Exception as exc:
        print(f"  [FATAL] Authentication failed: {exc}")
        sys.exit(1)

    # ----- Discover applications -----
    print("\n[2/4] Discovering applications...")
    all_apps = discover_applications(client, engine)

    if not all_apps:
        print("  [FATAL] No applications found. Check credentials and permissions.")
        sys.exit(1)

    # ----- Filter Visionamos -----
    target_apps = get_visionamos_apps(all_apps)

    if not target_apps:
        fallback = all_apps[:MAX_FALLBACK_APPS]
        names = [a.get("name", "?") for a in fallback]
        print(f"  Using fallback: first {len(fallback)} app(s): {names}")
        target_apps = fallback

    # ----- Run extractors -----
    print(f"\n[3/4] Extracting data for {len(target_apps)} app(s)...")
    print(f"  Date range: {cfg.EXTRACTION_DAYS_BACK} days back")

    extractors = [
        PushExtractor(client, engine),
        ChatExtractor(client, engine),
        SMSExtractor(client, engine),
        EmailExtractor(client, engine),
        InAppExtractor(client, engine),
        CampaignsExtractor(client, engine),
        ContactsExtractor(client, engine),
    ]

    results = {}
    for extractor in extractors:
        print(f"\n  --- {extractor.CHANNEL_NAME.upper()} ---")
        count = extractor.extract(target_apps)
        results[extractor.CHANNEL_NAME] = count

    # ----- Summary -----
    elapsed = time.time() - start_time
    total = sum(results.values())

    print("\n" + "=" * 60)
    print(f"[4/4] Extraction Summary")
    print("=" * 60)
    print(f"  Apps processed:  {len(target_apps)}")
    print(f"  Total records:   {total}")
    print(f"  Elapsed time:    {elapsed:.1f}s")
    print()
    for channel, count in results.items():
        status = "OK" if count > 0 else "EMPTY"
        print(f"    {channel:12s}  {count:4d} records  [{status}]")
    print()

    if total == 0:
        print("  [WARN] No data was extracted. Possible issues:")
        print("    - API endpoints may have changed")
        print("    - Applications may not have data for the date range")
        print("    - Check raw.extraction_log for error details")
    else:
        print("  Extraction complete. Inspect raw.* tables for results.")

    print("=" * 60)


if __name__ == "__main__":
    main()
