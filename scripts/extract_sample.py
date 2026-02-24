"""
Extract a small sample (5-10 records) from each Indigitall data source
to inspect the data model. No Docker required.

Usage:
    python scripts/extract_sample.py
"""

import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

BASE_URL = os.getenv("INDIGITALL_API_BASE_URL", "https://am1.api.indigitall.com").rstrip("/")
SERVER_KEY = os.getenv("INDIGITALL_SERVER_KEY", "")

HEADERS = {
    "Authorization": f"ServerKey {SERVER_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

TIMEOUT = 30
APP_ID = 100274
SAMPLE_DIR = Path(__file__).resolve().parent / "data_sample"

date_to = date.today().isoformat()
date_7d = (date.today() - timedelta(days=7)).isoformat()
date_30d = (date.today() - timedelta(days=30)).isoformat()


def api_get(endpoint: str, params: dict | None = None) -> dict | None:
    url = f"{BASE_URL}{endpoint}"
    time.sleep(0.3)
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        if r.ok:
            return r.json()
        print(f"    [{r.status_code}] {endpoint}: {r.text[:150]}")
    except Exception as e:
        print(f"    [ERROR] {endpoint}: {e}")
    return None


def save(name: str, data):
    SAMPLE_DIR.mkdir(exist_ok=True)
    path = SAMPLE_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    return path


def show_schema(name: str, data):
    """Print the schema of the data for quick inspection."""
    print(f"\n{'-'*60}")
    print(f"  {name}")
    print(f"{'-'*60}")

    if isinstance(data, dict):
        payload = data.get("data", data)
    else:
        payload = data

    if isinstance(payload, list):
        print(f"  Tipo: Array [{len(payload)} registros]")
        if payload and isinstance(payload[0], dict):
            print(f"  Campos:")
            for key, val in payload[0].items():
                vtype = type(val).__name__
                sample = str(val)[:60] if val is not None else "null"
                print(f"    {key:30s}  {vtype:8s}  {sample}")
    elif isinstance(payload, dict):
        print(f"  Tipo: Objeto")
        print(f"  Campos:")
        for key, val in payload.items():
            vtype = type(val).__name__
            if isinstance(val, dict):
                sample = f"{{...}} ({len(val)} keys)"
            elif isinstance(val, list):
                sample = f"[...] ({len(val)} items)"
            else:
                sample = str(val)[:60] if val is not None else "null"
            print(f"    {key:30s}  {vtype:8s}  {sample}")
    else:
        print(f"  Tipo: {type(payload).__name__}")


def main():
    print("=" * 60)
    print("  Extracción de Muestra — Modelo de Datos Visionamos")
    print("=" * 60)

    samples = {}

    # -- 1. Aplicación --
    print("\n[1/8] Aplicación...")
    data = api_get("/v1/application", {"limit": 5, "page": 0})
    if data:
        samples["01_aplicacion"] = data
        show_schema("APLICACIÓN", data)

    # -- 2. Estadísticas de cuenta --
    print("\n[2/8] Estadísticas de cuenta...")
    data = api_get("/v1/application/stats", {"applicationId": APP_ID, "limit": 5, "page": 0})
    if data:
        samples["02_estadisticas_cuenta"] = data
        show_schema("ESTADÍSTICAS DE CUENTA", data)

    # -- 3. Estadísticas diarias (push) --
    print("\n[3/8] Estadísticas diarias (push)...")
    data = api_get(f"/v1/application/{APP_ID}/dateStats",
                   {"dateFrom": date_7d, "dateTo": date_to, "periodicity": "daily"})
    if data:
        # Solo 6 registros (2 días × 3 plataformas)
        if isinstance(data.get("data"), list):
            data["data"] = data["data"][:6]
        samples["03_stats_diarios_push"] = data
        show_schema("ESTADÍSTICAS DIARIAS (PUSH)", data)

    # -- 4. Heatmap de engagement --
    print("\n[4/8] Heatmap de engagement...")
    data = api_get(f"/v1/application/{APP_ID}/pushHeatmap",
                   {"dateFrom": date_7d, "dateTo": date_to})
    if data:
        samples["04_heatmap_engagement"] = data
        show_schema("HEATMAP DE ENGAGEMENT", data)

    # -- 5. Estadísticas de dispositivos --
    print("\n[5/8] Estadísticas de dispositivos...")
    data = api_get(f"/v1/application/{APP_ID}/stats/device",
                   {"dateFrom": date_7d, "dateTo": date_to})
    if data:
        samples["05_stats_dispositivos"] = data
        show_schema("ESTADÍSTICAS DE DISPOSITIVOS", data)

    # -- 6. Contactos de chat (WhatsApp) — 10 registros --
    print("\n[6/8] Contactos de chat (WhatsApp)...")
    data = api_get("/v1/chat/contacts",
                   {"applicationId": APP_ID, "limit": 10, "offset": 0})
    if data:
        samples["06_contactos_chat"] = data
        show_schema("CONTACTOS DE CHAT (WHATSAPP)", data)

    # -- 7. Estado de agentes --
    print("\n[7/8] Estado de agentes de chat...")
    data = api_get("/v1/chat/agent/status", {"applicationId": APP_ID})
    if data:
        samples["07_agentes_chat"] = data
        show_schema("ESTADO DE AGENTES", data)

    # -- 8. Campañas --
    print("\n[8/8] Campañas...")
    data = api_get("/v1/campaign",
                   {"applicationId": APP_ID, "limit": 10, "page": 0})
    if data:
        samples["08_campanas"] = data
        show_schema("CAMPAÑAS", data)

    # -- Guardar todo --
    print(f"\n\n{'='*60}")
    print(f"  Guardando muestras en: scripts/data_sample/")
    print(f"{'='*60}")
    for name, sdata in samples.items():
        path = save(name, sdata)
        records = len(sdata.get("data", [])) if isinstance(sdata, dict) and isinstance(sdata.get("data"), (list,)) else 1
        print(f"  {path.name:40s}  {records} registro(s)")

    # -- Resumen del modelo de datos --
    print(f"\n\n{'='*60}")
    print(f"  RESUMEN DEL MODELO DE DATOS")
    print(f"{'='*60}")
    print(f"""
  La cuenta Visionamos (app 100274) tiene estos conjuntos de datos:

  FUENTE                    REGISTROS   DESCRIPCIÓN
  -------------------------------------------------------------
  Aplicación                1           Metadatos de la app
  Stats de cuenta           1           Resumen: campaigns, devices, impacts
  Stats diarios (push)      3/día       Por plataforma: android, ios, web
  Heatmap engagement        1           Tasas de interacción por hora/día
  Stats dispositivos        0           Sin dispositivos registrados
  Contactos WhatsApp        20+         Paginado, con metadata de contacto
  Agentes de chat           4 activos   Conteo de agentes activos
  Campañas                  0           Sin campañas activas

  CANAL PRINCIPAL: Chat / WhatsApp (canal "cloudapi")
  CANALES INACTIVOS: Push, SMS, Email, InApp
""")


if __name__ == "__main__":
    main()
