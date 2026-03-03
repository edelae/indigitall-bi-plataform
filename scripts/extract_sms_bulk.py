"""Bulk SMS extraction — fetches sendings + contacts from Indigitall API v2.

Writes directly to public.sms_envios (sendings) and public.sms_contacts (contacts).
Target: 4M+ records.

Usage:
    python scripts/extract_sms_bulk.py                   # extract both
    python scripts/extract_sms_bulk.py --sendings-only   # only sendings
    python scripts/extract_sms_bulk.py --contacts-only   # only contacts
    python scripts/extract_sms_bulk.py --limit 4000000   # cap at 4M sendings
"""
import sys
import time
import json

import psycopg2
import psycopg2.extras
import requests
from dotenv import dotenv_values

# ── Config ──
env = dotenv_values(".env")
SERVER_KEY = env.get("INDIGITALL_SERVER_KEY", "")
API_BASE = env.get("INDIGITALL_API_BASE_URL", "https://am1.api.indigitall.com")
DB_PASS = env.get("POSTGRES_PASSWORD", "")
DB_HOST = env.get("DB_HOST", "localhost")
TENANT_ID = "visionamos"
APP_ID = "100274"

# ── CLI args ──
SENDINGS_ONLY = "--sendings-only" in sys.argv
CONTACTS_ONLY = "--contacts-only" in sys.argv
MAX_SENDINGS = 4_500_000  # default target
for i, arg in enumerate(sys.argv):
    if arg == "--limit" and i + 1 < len(sys.argv):
        MAX_SENDINGS = int(sys.argv[i + 1])

# ── API session ──
session = requests.Session()
session.headers.update({
    "Authorization": f"ServerKey {SERVER_KEY}",
    "Accept": "application/json",
})


def get_db():
    conn = psycopg2.connect(
        host=DB_HOST, port=5432, dbname="postgres",
        user="postgres", password=DB_PASS,
    )
    return conn


def ensure_tables(conn):
    """Create tables if not exist."""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.sms_envios (
            id serial PRIMARY KEY,
            tenant_id text NOT NULL DEFAULT 'visionamos',
            sending_id varchar NOT NULL,
            application_id varchar,
            campaign_id varchar,
            total_chunks integer DEFAULT 1,
            sending_type varchar,
            is_flash boolean DEFAULT false,
            sent_at timestamptz,
            UNIQUE(tenant_id, sending_id)
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_sms_envios_sent_at
        ON public.sms_envios (sent_at)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.sms_contacts (
            id serial PRIMARY KEY,
            tenant_id text NOT NULL DEFAULT 'visionamos',
            contact_id varchar NOT NULL,
            phone varchar NOT NULL,
            country_code varchar,
            external_code varchar,
            enabled boolean DEFAULT true,
            created_at timestamptz,
            updated_at timestamptz,
            unsubscription_url varchar,
            UNIQUE(tenant_id, contact_id)
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_sms_contacts_phone
        ON public.sms_contacts (tenant_id, phone)
    """)

    conn.commit()
    cur.close()


def extract_sendings(conn):
    """Extract SMS sendings from /v2/sms/send — paginated, batch upsert."""
    cur = conn.cursor()

    # Get current count to resume
    cur.execute("SELECT count(*) FROM public.sms_envios WHERE tenant_id = %s", (TENANT_ID,))
    existing = cur.fetchone()[0]
    print(f"\n{'='*60}")
    print(f"  EXTRACCION SMS SENDINGS")
    print(f"  Existentes en BD: {existing:,}")
    print(f"  Objetivo: {MAX_SENDINGS:,}")
    print(f"{'='*60}\n")

    page_size = 500
    page = 1
    total_fetched = 0
    api_total = None
    start_time = time.time()
    errors = 0

    while True:
        if total_fetched >= MAX_SENDINGS:
            print(f"\n  Objetivo alcanzado: {total_fetched:,}")
            break

        try:
            resp = session.get(
                f"{API_BASE}/v2/sms/send",
                params={"applicationId": APP_ID, "limit": page_size, "page": page},
                timeout=60,
            )
        except requests.RequestException as exc:
            errors += 1
            print(f"  [ERROR] Page {page}: {exc}")
            if errors >= 10:
                print("  10 errores, deteniendo.")
                break
            time.sleep(2 ** min(errors, 5))
            continue

        if resp.status_code == 429:
            print(f"  [RATE LIMITED] Page {page}, esperando 15s...")
            time.sleep(15)
            continue

        if not resp.ok:
            errors += 1
            print(f"  [HTTP {resp.status_code}] Page {page}")
            if errors >= 10:
                break
            time.sleep(2)
            continue

        errors = 0
        resp.encoding = "utf-8"
        data = resp.json()

        if api_total is None:
            api_total = data.get("count", 0)
            print(f"  API total: {api_total:,} sendings\n")

        sendings = data.get("data", {}).get("sendings", [])
        if not sendings:
            print(f"\n  Fin: pagina {page} vacia")
            break

        # Batch upsert
        rows = []
        for s in sendings:
            sid = s.get("id")
            if not sid:
                continue
            rows.append((
                TENANT_ID,
                str(sid),
                str(s.get("applicationId", APP_ID)),
                str(s.get("campaignId", "")) if s.get("campaignId") else None,
                s.get("estimatedChunks") or 1,
                f"{s.get('type', '')}_{s.get('mode', '')}".strip("_") or None,
                s.get("flash", False),
                s.get("sentAt"),
            ))

        if rows:
            insert_sql = """
                INSERT INTO public.sms_envios (
                    tenant_id, sending_id, application_id, campaign_id,
                    total_chunks, sending_type, is_flash, sent_at
                ) VALUES %s
                ON CONFLICT (tenant_id, sending_id) DO NOTHING
            """
            psycopg2.extras.execute_values(cur, insert_sql, rows, page_size=500)
            conn.commit()

        total_fetched += len(sendings)
        elapsed = time.time() - start_time
        rate = total_fetched / elapsed if elapsed > 0 else 0
        pct = (total_fetched / api_total * 100) if api_total else 0

        if page % 50 == 0 or page <= 3:
            eta_min = ((api_total - total_fetched) / rate / 60) if rate > 0 and api_total else 0
            print(
                f"  Page {page:,} | {total_fetched:,}/{min(api_total or 0, MAX_SENDINGS):,} "
                f"({pct:.1f}%) | {rate:.0f} rec/s | ETA: {eta_min:.0f}min"
            )

        page += 1
        if len(sendings) < page_size:
            print(f"\n  Fin: ultima pagina con {len(sendings)} rows")
            break
        time.sleep(0.2)

    elapsed = time.time() - start_time
    cur.execute("SELECT count(*) FROM public.sms_envios WHERE tenant_id = %s", (TENANT_ID,))
    final_count = cur.fetchone()[0]
    print(f"\n  Sendings: {total_fetched:,} fetched | {final_count:,} en BD | {elapsed/60:.1f}min")
    cur.close()
    return total_fetched


def extract_contacts(conn):
    """Extract SMS contacts from /v2/sms/contact — paginated, batch upsert."""
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM public.sms_contacts WHERE tenant_id = %s", (TENANT_ID,))
    existing = cur.fetchone()[0]
    print(f"\n{'='*60}")
    print(f"  EXTRACCION SMS CONTACTS")
    print(f"  Existentes en BD: {existing:,}")
    print(f"{'='*60}\n")

    page_size = 500
    page = 1
    total_fetched = 0
    api_total = None
    start_time = time.time()
    errors = 0

    while True:
        try:
            resp = session.get(
                f"{API_BASE}/v2/sms/contact",
                params={"applicationId": APP_ID, "limit": page_size, "page": page},
                timeout=60,
            )
        except requests.RequestException as exc:
            errors += 1
            print(f"  [ERROR] Page {page}: {exc}")
            if errors >= 10:
                break
            time.sleep(2 ** min(errors, 5))
            continue

        if resp.status_code == 429:
            print(f"  [RATE LIMITED] Page {page}, esperando 15s...")
            time.sleep(15)
            continue

        if not resp.ok:
            errors += 1
            if errors >= 10:
                break
            time.sleep(2)
            continue

        errors = 0
        resp.encoding = "utf-8"
        data = resp.json()

        if api_total is None:
            api_total = data.get("count", 0)
            print(f"  API total: {api_total:,} contacts\n")

        contacts = data.get("data", {}).get("contacts", [])
        if not contacts:
            print(f"\n  Fin: pagina {page} vacia")
            break

        rows = []
        for c in contacts:
            cid = c.get("id")
            if not cid:
                continue
            rows.append((
                TENANT_ID,
                str(cid),
                c.get("phone", ""),
                c.get("countryCode"),
                c.get("externalCode"),
                c.get("enabled", True),
                c.get("createdAt"),
                c.get("updatedAt"),
                c.get("unsubscriptionUrl"),
            ))

        if rows:
            insert_sql = """
                INSERT INTO public.sms_contacts (
                    tenant_id, contact_id, phone, country_code, external_code,
                    enabled, created_at, updated_at, unsubscription_url
                ) VALUES %s
                ON CONFLICT (tenant_id, contact_id) DO UPDATE SET
                    updated_at = EXCLUDED.updated_at,
                    enabled = EXCLUDED.enabled
            """
            psycopg2.extras.execute_values(cur, insert_sql, rows, page_size=500)
            conn.commit()

        total_fetched += len(contacts)
        elapsed = time.time() - start_time
        rate = total_fetched / elapsed if elapsed > 0 else 0

        if page % 100 == 0 or page <= 3:
            pct = (total_fetched / api_total * 100) if api_total else 0
            print(f"  Page {page:,} | {total_fetched:,}/{api_total:,} ({pct:.1f}%) | {rate:.0f} rec/s")

        page += 1
        if len(contacts) < page_size:
            break
        time.sleep(0.2)

    elapsed = time.time() - start_time
    cur.execute("SELECT count(*) FROM public.sms_contacts WHERE tenant_id = %s", (TENANT_ID,))
    final = cur.fetchone()[0]
    print(f"\n  Contacts: {total_fetched:,} fetched | {final:,} en BD | {elapsed/60:.1f}min")
    cur.close()
    return total_fetched


def main():
    conn = get_db()
    conn.autocommit = False
    ensure_tables(conn)

    total = 0
    if not CONTACTS_ONLY:
        total += extract_sendings(conn)
    if not SENDINGS_ONLY:
        total += extract_contacts(conn)

    print(f"\n{'='*60}")
    print(f"  TOTAL EXTRAIDO: {total:,} registros")
    print(f"{'='*60}")
    conn.close()


if __name__ == "__main__":
    main()
