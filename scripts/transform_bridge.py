"""
Phase 2c — Transform Bridge: raw.* JSONB → public.* structured tables.

Reads flattened data from staging SQL (same logic as dbt stg_raw_* models)
and UPSERTs into public.* tables matching app/models/schemas.py definitions.

Usage:
    docker compose exec app python scripts/transform_bridge.py
    python scripts/transform_bridge.py          # local (requires .env)

Rules:
    - tenant_id = 'visionamos' for all records
    - All timestamps stored as TIMESTAMPTZ (UTC)
    - NEVER deletes from raw.* tables
    - Idempotent — safe to re-run
"""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import engine

TENANT_ID = "visionamos"
APP_ID = "100274"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def update_sync_state(conn, entity: str, records: int, status: str = "success"):
    """UPSERT sync_state for the given entity."""
    conn.execute(text("""
        INSERT INTO public.sync_state (tenant_id, entity, last_sync_at, records_synced, status)
        VALUES (:tid, :entity, :ts, :records, :status)
        ON CONFLICT (tenant_id, entity) DO UPDATE SET
            last_sync_at   = EXCLUDED.last_sync_at,
            records_synced = EXCLUDED.records_synced,
            status         = EXCLUDED.status
    """), {
        "tid": TENANT_ID,
        "entity": entity,
        "ts": datetime.now(timezone.utc),
        "records": records,
        "status": status,
    })


# ---------------------------------------------------------------------------
# Transform: contacts
# ---------------------------------------------------------------------------

CONTACTS_SQL = """
WITH raw_rows AS (
    SELECT
        source_data,
        coalesce(tenant_id, :tid) AS tenant_id,
        loaded_at
    FROM raw.raw_contacts_api
    WHERE source_data->'data' IS NOT NULL
      AND jsonb_typeof(source_data->'data') = 'array'
),
flattened AS (
    SELECT
        r.tenant_id,
        elem->>'contactId'                       AS contact_id,
        elem->>'profileName'                      AS contact_name,
        (elem->>'createdAt')::timestamptz::date   AS first_contact,
        (elem->>'updatedAt')::timestamptz::date   AS last_contact,
        r.loaded_at
    FROM raw_rows r,
         jsonb_array_elements(r.source_data->'data') AS elem
    WHERE elem->>'contactId' IS NOT NULL
),
deduplicated AS (
    SELECT *,
        row_number() OVER (
            PARTITION BY tenant_id, contact_id
            ORDER BY last_contact DESC NULLS LAST, loaded_at DESC
        ) AS _rn
    FROM flattened
)
SELECT tenant_id, contact_id, contact_name, first_contact, last_contact
FROM deduplicated WHERE _rn = 1
"""

CONTACTS_UPSERT = """
INSERT INTO public.contacts
    (tenant_id, contact_id, contact_name, total_messages, first_contact, last_contact, total_conversations)
VALUES
    (:tenant_id, :contact_id, :contact_name, 0, :first_contact, :last_contact, 0)
ON CONFLICT (tenant_id, contact_id) DO UPDATE SET
    contact_name  = EXCLUDED.contact_name,
    first_contact = LEAST(contacts.first_contact, EXCLUDED.first_contact),
    last_contact  = GREATEST(contacts.last_contact, EXCLUDED.last_contact)
"""


def transform_contacts(conn) -> int:
    rows = conn.execute(text(CONTACTS_SQL), {"tid": TENANT_ID}).fetchall()
    count = 0
    for r in rows:
        conn.execute(text(CONTACTS_UPSERT), {
            "tenant_id": r[0],
            "contact_id": r[1],
            "contact_name": r[2],
            "first_contact": r[3],
            "last_contact": r[4],
        })
        count += 1
    return count


# ---------------------------------------------------------------------------
# Transform: toques_daily
# ---------------------------------------------------------------------------

TOQUES_DAILY_SQL = """
WITH raw_rows AS (
    SELECT
        source_data,
        coalesce(tenant_id, :tid) AS tenant_id,
        coalesce(application_id, :app_id) AS application_id,
        loaded_at
    FROM raw.raw_push_stats
    WHERE endpoint LIKE '%%/dateStats%%'
      AND source_data->'data' IS NOT NULL
      AND jsonb_typeof(source_data->'data') = 'array'
),
flattened AS (
    SELECT
        r.tenant_id,
        r.application_id                               AS proyecto_cuenta,
        elem->>'platformGroup'                          AS canal,
        (elem->>'statsDate')::date                      AS date,
        coalesce((elem->>'numDevicesSent')::int, 0)     AS enviados,
        coalesce((elem->>'numDevicesSuccess')::int, 0)  AS entregados,
        coalesce((elem->>'numDevicesReceived')::int, 0) AS abiertos,
        coalesce((elem->>'numDevicesClicked')::int, 0)  AS clicks,
        r.loaded_at
    FROM raw_rows r,
         jsonb_array_elements(r.source_data->'data') AS elem
    WHERE elem->>'platformGroup' IS NOT NULL
      AND elem->>'statsDate' IS NOT NULL
),
deduplicated AS (
    SELECT *,
        row_number() OVER (
            PARTITION BY tenant_id, date, canal, proyecto_cuenta
            ORDER BY loaded_at DESC
        ) AS _rn
    FROM flattened
)
SELECT tenant_id, date, canal, proyecto_cuenta, enviados, entregados, abiertos, clicks
FROM deduplicated WHERE _rn = 1
"""

TOQUES_DAILY_UPSERT = """
INSERT INTO public.toques_daily
    (tenant_id, date, canal, proyecto_cuenta,
     enviados, entregados, clicks, chunks, usuarios_unicos,
     abiertos, rebotes, bloqueados, spam, desuscritos, conversiones,
     ctr, tasa_entrega, open_rate, conversion_rate)
VALUES
    (:tenant_id, :date, :canal, :proyecto_cuenta,
     :enviados, :entregados, :clicks, 0, 0,
     :abiertos, 0, 0, 0, 0, 0,
     :ctr, :tasa_entrega, :open_rate, 0)
ON CONFLICT (tenant_id, date, canal, proyecto_cuenta) DO UPDATE SET
    enviados     = EXCLUDED.enviados,
    entregados   = EXCLUDED.entregados,
    clicks       = EXCLUDED.clicks,
    abiertos     = EXCLUDED.abiertos,
    ctr          = EXCLUDED.ctr,
    tasa_entrega = EXCLUDED.tasa_entrega,
    open_rate    = EXCLUDED.open_rate
"""


def transform_toques_daily(conn) -> int:
    rows = conn.execute(text(TOQUES_DAILY_SQL), {"tid": TENANT_ID, "app_id": APP_ID}).fetchall()
    count = 0
    for r in rows:
        enviados = r[4]
        entregados = r[5]
        abiertos = r[6]
        clicks = r[7]
        ctr = round(clicks / enviados * 100, 2) if enviados > 0 else 0
        tasa_entrega = round(entregados / enviados * 100, 2) if enviados > 0 else 0
        open_rate = round(abiertos / entregados * 100, 2) if entregados > 0 else 0

        conn.execute(text(TOQUES_DAILY_UPSERT), {
            "tenant_id": r[0],
            "date": r[1],
            "canal": r[2],
            "proyecto_cuenta": r[3],
            "enviados": enviados,
            "entregados": entregados,
            "clicks": clicks,
            "abiertos": abiertos,
            "ctr": ctr,
            "tasa_entrega": tasa_entrega,
            "open_rate": open_rate,
        })
        count += 1
    return count


# ---------------------------------------------------------------------------
# Transform: toques_heatmap
# ---------------------------------------------------------------------------

HEATMAP_SQL = """
WITH raw_rows AS (
    SELECT
        source_data,
        coalesce(tenant_id, :tid) AS tenant_id,
        loaded_at
    FROM raw.raw_push_stats
    WHERE endpoint LIKE '%%/pushHeatmap%%'
      AND source_data->'data' IS NOT NULL
      AND jsonb_typeof(source_data->'data') = 'object'
),
latest AS (
    SELECT *,
        row_number() OVER (PARTITION BY tenant_id ORDER BY loaded_at DESC) AS _rn
    FROM raw_rows
),
weekday_entries AS (
    SELECT
        l.tenant_id,
        weekday_key,
        weekday_val
    FROM latest l,
         jsonb_each(l.source_data->'data'->'weekday-hour') AS wd(weekday_key, weekday_val)
    WHERE l._rn = 1
      AND jsonb_typeof(weekday_val) = 'object'
),
flattened AS (
    SELECT
        w.tenant_id,
        'push' AS canal,
        w.weekday_key AS dia_semana,
        hour_key::smallint AS hora,
        round((hour_val::text)::numeric * 100, 2) AS ctr,
        CASE w.weekday_key
            WHEN 'monday'    THEN 1
            WHEN 'tuesday'   THEN 2
            WHEN 'wednesday' THEN 3
            WHEN 'thursday'  THEN 4
            WHEN 'friday'    THEN 5
            WHEN 'saturday'  THEN 6
            WHEN 'sunday'    THEN 7
            ELSE 0
        END AS dia_orden
    FROM weekday_entries w,
         jsonb_each(w.weekday_val) AS h(hour_key, hour_val)
)
SELECT tenant_id, canal, dia_semana, hora, ctr, dia_orden
FROM flattened
"""

HEATMAP_UPSERT = """
INSERT INTO public.toques_heatmap
    (tenant_id, canal, dia_semana, hora, enviados, clicks, abiertos, conversiones, ctr, dia_orden)
VALUES
    (:tenant_id, :canal, :dia_semana, :hora, 0, 0, 0, 0, :ctr, :dia_orden)
ON CONFLICT (tenant_id, canal, dia_semana, hora) DO UPDATE SET
    ctr       = EXCLUDED.ctr,
    dia_orden = EXCLUDED.dia_orden
"""


def transform_heatmap(conn) -> int:
    rows = conn.execute(text(HEATMAP_SQL), {"tid": TENANT_ID}).fetchall()
    count = 0
    for r in rows:
        conn.execute(text(HEATMAP_UPSERT), {
            "tenant_id": r[0],
            "canal": r[1],
            "dia_semana": r[2],
            "hora": int(r[3]),
            "ctr": float(r[4]),
            "dia_orden": int(r[5]),
        })
        count += 1
    return count


# ---------------------------------------------------------------------------
# Transform: campaigns
# ---------------------------------------------------------------------------

CAMPAIGNS_SQL = """
WITH raw_rows AS (
    SELECT
        source_data,
        coalesce(tenant_id, :tid) AS tenant_id,
        loaded_at
    FROM raw.raw_campaigns_api
    WHERE source_data->'data' IS NOT NULL
      AND jsonb_typeof(source_data->'data') = 'array'
),
flattened AS (
    SELECT
        r.tenant_id,
        coalesce(elem->>'id', elem->>'campaignId')             AS campana_id,
        coalesce(elem->>'name', elem->>'title', 'Sin nombre')  AS campana_nombre,
        coalesce(elem->>'channel', elem->>'type', 'push')      AS canal,
        coalesce(elem->>'applicationId', :app_id)               AS proyecto_cuenta,
        elem->>'status'                                         AS tipo_campana,
        coalesce((elem->>'sent')::int, 0)                       AS total_enviados,
        coalesce((elem->>'delivered')::int, 0)                  AS total_entregados,
        coalesce((elem->>'clicked')::int, 0)                    AS total_clicks,
        (elem->>'startDate')::date                              AS fecha_inicio,
        (elem->>'endDate')::date                                AS fecha_fin,
        coalesce((elem->>'opened')::int, 0)                     AS total_abiertos,
        coalesce((elem->>'bounced')::int, 0)                    AS total_rebotes,
        coalesce((elem->>'blocked')::int, 0)                    AS total_bloqueados,
        coalesce((elem->>'spam')::int, 0)                       AS total_spam,
        coalesce((elem->>'unsubscribed')::int, 0)               AS total_desuscritos,
        coalesce((elem->>'converted')::int, 0)                  AS total_conversiones,
        r.loaded_at
    FROM raw_rows r,
         jsonb_array_elements(r.source_data->'data') AS elem
),
deduplicated AS (
    SELECT *,
        row_number() OVER (
            PARTITION BY tenant_id, campana_id
            ORDER BY loaded_at DESC
        ) AS _rn
    FROM flattened
    WHERE campana_id IS NOT NULL
)
SELECT tenant_id, campana_id, campana_nombre, canal, proyecto_cuenta, tipo_campana,
       total_enviados, total_entregados, total_clicks, fecha_inicio, fecha_fin,
       total_abiertos, total_rebotes, total_bloqueados, total_spam,
       total_desuscritos, total_conversiones
FROM deduplicated WHERE _rn = 1
"""

CAMPAIGNS_UPSERT = """
INSERT INTO public.campaigns
    (tenant_id, campana_id, campana_nombre, canal, proyecto_cuenta, tipo_campana,
     total_enviados, total_entregados, total_clicks, total_chunks,
     fecha_inicio, fecha_fin,
     total_abiertos, total_rebotes, total_bloqueados, total_spam,
     total_desuscritos, total_conversiones,
     ctr, tasa_entrega, open_rate, conversion_rate)
VALUES
    (:tenant_id, :campana_id, :campana_nombre, :canal, :proyecto_cuenta, :tipo_campana,
     :total_enviados, :total_entregados, :total_clicks, 0,
     :fecha_inicio, :fecha_fin,
     :total_abiertos, :total_rebotes, :total_bloqueados, :total_spam,
     :total_desuscritos, :total_conversiones,
     :ctr, :tasa_entrega, :open_rate, :conversion_rate)
ON CONFLICT (tenant_id, campana_id) DO UPDATE SET
    campana_nombre    = EXCLUDED.campana_nombre,
    canal             = EXCLUDED.canal,
    proyecto_cuenta   = EXCLUDED.proyecto_cuenta,
    tipo_campana      = EXCLUDED.tipo_campana,
    total_enviados    = EXCLUDED.total_enviados,
    total_entregados  = EXCLUDED.total_entregados,
    total_clicks      = EXCLUDED.total_clicks,
    fecha_inicio      = EXCLUDED.fecha_inicio,
    fecha_fin         = EXCLUDED.fecha_fin,
    total_abiertos    = EXCLUDED.total_abiertos,
    total_rebotes     = EXCLUDED.total_rebotes,
    total_bloqueados  = EXCLUDED.total_bloqueados,
    total_spam        = EXCLUDED.total_spam,
    total_desuscritos = EXCLUDED.total_desuscritos,
    total_conversiones = EXCLUDED.total_conversiones,
    ctr               = EXCLUDED.ctr,
    tasa_entrega      = EXCLUDED.tasa_entrega,
    open_rate         = EXCLUDED.open_rate,
    conversion_rate   = EXCLUDED.conversion_rate
"""


def transform_campaigns(conn) -> int:
    rows = conn.execute(text(CAMPAIGNS_SQL), {"tid": TENANT_ID, "app_id": APP_ID}).fetchall()
    count = 0
    for r in rows:
        enviados = r[6]
        entregados = r[7]
        clicks = r[8]
        abiertos = r[11]
        conversiones = r[16]

        ctr = round(clicks / enviados * 100, 2) if enviados > 0 else 0
        tasa_entrega = round(entregados / enviados * 100, 2) if enviados > 0 else 0
        open_rate = round(abiertos / entregados * 100, 2) if entregados > 0 else 0
        conversion_rate = round(conversiones / clicks * 100, 2) if clicks > 0 else 0

        conn.execute(text(CAMPAIGNS_UPSERT), {
            "tenant_id": r[0],
            "campana_id": r[1],
            "campana_nombre": r[2],
            "canal": r[3],
            "proyecto_cuenta": r[4],
            "tipo_campana": r[5],
            "total_enviados": enviados,
            "total_entregados": entregados,
            "total_clicks": clicks,
            "fecha_inicio": r[9],
            "fecha_fin": r[10],
            "total_abiertos": abiertos,
            "total_rebotes": r[12],
            "total_bloqueados": r[13],
            "total_spam": r[14],
            "total_desuscritos": r[15],
            "total_conversiones": conversiones,
            "ctr": ctr,
            "tasa_entrega": tasa_entrega,
            "open_rate": open_rate,
            "conversion_rate": conversion_rate,
        })
        count += 1
    return count


# ---------------------------------------------------------------------------
# Transform: daily_stats (aggregated from toques_daily)
# ---------------------------------------------------------------------------

DAILY_STATS_SQL = """
SELECT
    tenant_id,
    date,
    coalesce(sum(enviados), 0)   AS total_messages,
    0                            AS unique_contacts,
    0                            AS conversations,
    0                            AS fallback_count
FROM public.toques_daily
WHERE tenant_id = :tid
GROUP BY tenant_id, date
"""

DAILY_STATS_UPSERT = """
INSERT INTO public.daily_stats
    (tenant_id, date, total_messages, unique_contacts, conversations, fallback_count)
VALUES
    (:tenant_id, :date, :total_messages, :unique_contacts, :conversations, :fallback_count)
ON CONFLICT (tenant_id, date) DO UPDATE SET
    total_messages  = EXCLUDED.total_messages,
    unique_contacts = EXCLUDED.unique_contacts,
    conversations   = EXCLUDED.conversations,
    fallback_count  = EXCLUDED.fallback_count
"""


def transform_daily_stats(conn) -> int:
    rows = conn.execute(text(DAILY_STATS_SQL), {"tid": TENANT_ID}).fetchall()
    count = 0
    for r in rows:
        conn.execute(text(DAILY_STATS_UPSERT), {
            "tenant_id": r[0],
            "date": r[1],
            "total_messages": r[2],
            "unique_contacts": r[3],
            "conversations": r[4],
            "fallback_count": r[5],
        })
        count += 1
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TRANSFORMS = [
    ("contacts",       transform_contacts),
    ("toques_daily",   transform_toques_daily),
    ("toques_heatmap", transform_heatmap),
    ("campaigns",      transform_campaigns),
    ("daily_stats",    transform_daily_stats),
]


def main():
    print("=" * 60)
    print("  Transform Bridge — raw.* JSONB → public.* tables")
    print("=" * 60)

    start = time.time()
    results = {}

    for entity, transform_fn in TRANSFORMS:
        print(f"\n  [{entity}] Transforming...")
        try:
            with engine.begin() as conn:
                count = transform_fn(conn)
                update_sync_state(conn, entity, count, "success")
            results[entity] = count
            print(f"    {count} rows upserted")
        except Exception as exc:
            results[entity] = -1
            print(f"    [ERROR] {exc}")
            try:
                with engine.begin() as conn:
                    update_sync_state(conn, entity, 0, f"error: {str(exc)[:200]}")
            except Exception:
                pass

    elapsed = time.time() - start

    print(f"\n{'=' * 60}")
    print(f"  Transform Summary")
    print(f"{'=' * 60}")
    print(f"  Elapsed: {elapsed:.1f}s\n")
    for entity, count in results.items():
        status = "OK" if count >= 0 else "ERROR"
        count_str = str(count) if count >= 0 else "FAILED"
        print(f"    {entity:<20s}  {count_str:>6s} rows  [{status}]")

    total_ok = sum(v for v in results.values() if v >= 0)
    total_err = sum(1 for v in results.values() if v < 0)
    print(f"\n  Total: {total_ok} rows upserted, {total_err} errors")
    print(f"{'=' * 60}")

    return 0 if total_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
