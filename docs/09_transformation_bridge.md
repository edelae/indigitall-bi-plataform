# Transformation Bridge — raw.* JSONB → public.* Structured Tables

## Overview

The transformation bridge converts raw JSONB API responses stored in `raw.*` tables into typed, structured rows in `public.*` tables that power the Dash frontend and dbt analytics marts.

```
Indigitall API
     │
     ▼
┌──────────────────────┐
│  scripts/extractors/  │  ← Phase 7–9 (existing)
│  orchestrator.py      │
└──────────┬───────────┘
           │ JSONB blobs
           ▼
┌──────────────────────┐
│  raw.* tables         │  raw_contacts_api, raw_push_stats,
│  (PostgreSQL)         │  raw_chat_stats, raw_campaigns_api, ...
└──────────┬───────────┘
           │ transform_bridge.py
           ▼
┌──────────────────────┐
│  public.* tables      │  contacts, toques_daily, toques_heatmap,
│  (PostgreSQL)         │  campaigns, daily_stats
└──────────┬───────────┘
           │ dbt run
           ▼
┌──────────────────────┐
│  staging.* views      │  stg_contacts, stg_toques_daily, ...
│  marts.* tables       │  fct_daily_stats, dim_contacts, ...
└──────────┬───────────┘
           │
           ▼
       Dash App
```

## Data Mapping

### contacts

| Raw Field (JSONB) | Public Column | Type | Notes |
|---|---|---|---|
| `contactId` | `contact_id` | VARCHAR(100) | Natural key |
| `profileName` | `contact_name` | VARCHAR(255) | |
| `createdAt` | `first_contact` | DATE | Cast from ISO 8601 |
| `updatedAt` | `last_contact` | DATE | Cast from ISO 8601 |
| — | `total_messages` | INTEGER | Set to 0 (needs JWT) |
| — | `total_conversations` | INTEGER | Set to 0 (needs JWT) |

**Source**: `raw.raw_contacts_api` → endpoint `/v1/chat/contacts`

### toques_daily

| Raw Field (JSONB) | Public Column | Type | Notes |
|---|---|---|---|
| `platformGroup` | `canal` | VARCHAR(30) | android, ios, web |
| `statsDate` | `date` | DATE | |
| `numDevicesSent` | `enviados` | INTEGER | |
| `numDevicesSuccess` | `entregados` | INTEGER | |
| `numDevicesReceived` | `abiertos` | INTEGER | |
| `numDevicesClicked` | `clicks` | INTEGER | |
| — | `ctr` | NUMERIC(6,2) | Calculated: clicks/enviados*100 |
| — | `tasa_entrega` | NUMERIC(6,2) | Calculated: entregados/enviados*100 |
| — | `open_rate` | NUMERIC(6,2) | Calculated: abiertos/entregados*100 |

**Source**: `raw.raw_push_stats` → endpoint `/v1/application/{id}/dateStats`

### toques_heatmap

| Raw Field (JSONB) | Public Column | Type | Notes |
|---|---|---|---|
| `weekday-hour.{weekday}.{hour}` | `dia_semana` + `hora` | VARCHAR(12) + SMALLINT | Cross-join flatten |
| engagement rate value | `ctr` | NUMERIC(6,2) | Multiplied by 100 |
| weekday name | `dia_orden` | SMALLINT | Monday=1 .. Sunday=7 |

**Source**: `raw.raw_push_stats` → endpoint `/v1/application/{id}/pushHeatmap`

### campaigns

| Raw Field (JSONB) | Public Column | Type | Notes |
|---|---|---|---|
| `id` / `campaignId` | `campana_id` | VARCHAR(100) | |
| `name` / `title` | `campana_nombre` | VARCHAR(255) | |
| `channel` / `type` | `canal` | VARCHAR(30) | |
| `sent` | `total_enviados` | INTEGER | |
| `delivered` | `total_entregados` | INTEGER | |
| `clicked` | `total_clicks` | INTEGER | |
| `startDate` | `fecha_inicio` | DATE | |
| `endDate` | `fecha_fin` | DATE | |

**Source**: `raw.raw_campaigns_api` → endpoint `/v1/campaign`
**Note**: Currently 0 campaigns. Pipeline is ready for when they appear.

### daily_stats

Derived by aggregating `public.toques_daily` per day across all platforms.

| Column | Source | Notes |
|---|---|---|
| `total_messages` | `SUM(enviados)` | From toques_daily |
| `unique_contacts` | 0 | Needs message-level data (JWT) |
| `conversations` | 0 | Needs conversation data (JWT) |
| `fallback_count` | 0 | Needs message-level data (JWT) |

## Data Availability Limitations

| Public Table | Status | Blocker |
|---|---|---|
| `contacts` | **Partial** | `total_messages`, `total_conversations` = 0 (needs JWT) |
| `toques_daily` | **Full** | — |
| `toques_heatmap` | **Full** | Only engagement rates, no absolute counts |
| `campaigns` | **Ready** | 0 campaigns currently exist |
| `daily_stats` | **Partial** | `unique_contacts`, `conversations` = 0 (needs JWT) |
| `agents` | **Blocked** | Only `activeAgents` count — no individual agent data |
| `messages` | **Blocked** | `/v1/chat/message` returns 404 with ServerKey auth |
| `toques_usuario` | **Blocked** | No per-user endpoint available |

## Running the Pipeline

### Full pipeline (extract + transform + dbt)

```bash
docker compose exec app python scripts/run_pipeline.py
```

### Transform only (skip API extraction)

```bash
docker compose exec app python scripts/run_pipeline.py --skip-extract
```

### Transform without dbt

```bash
docker compose exec app python scripts/run_pipeline.py --transform-only
```

### Individual steps

```bash
# Audit raw data
python scripts/audit_raw_data.py

# Analyze JSONB quality
python scripts/analyze_raw_quality.py

# Run transform bridge only
python scripts/transform_bridge.py

# Run dbt
cd dbt && dbt run && dbt test
```

## Adding New Extractors / Transforms

1. **Create extractor** in `scripts/extractors/` (extend `BaseExtractor`)
2. **Add raw table** in `scripts/create_raw_schema.py`
3. **Create dbt staging model** in `dbt/models/staging/stg_raw_*.sql`
4. **Add transform function** in `scripts/transform_bridge.py`:
   - Write the SQL to flatten JSONB
   - Write the UPSERT SQL matching `app/models/schemas.py`
   - Add to `TRANSFORMS` list
5. **Add tests** in `dbt/tests/` and `dbt/models/staging/schema.yml`
6. **Register** in `scripts/extractors/orchestrator.py`

## Files

| File | Purpose |
|---|---|
| `scripts/audit_raw_data.py` | Row counts, JSONB keys, date ranges |
| `scripts/analyze_raw_quality.py` | Field mapping, fill rates, duplicates |
| `scripts/transform_bridge.py` | UPSERT from raw.* → public.* |
| `scripts/run_pipeline.py` | End-to-end orchestrator |
| `dbt/models/sources_raw.yml` | dbt source for raw schema |
| `dbt/models/staging/stg_raw_*.sql` | JSONB flattening views |
| `dbt/tests/assert_*.sql` | Data quality tests |
