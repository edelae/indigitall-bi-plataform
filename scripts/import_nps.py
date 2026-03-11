"""Import NPS survey data from CSV files into the nps_surveys table.

Reads CSV files from NPS/ folder, parses JSON content, determines
conversation type (Bot/Agente/Mixta), and inserts into database.

Usage: python -m scripts.import_nps
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import engine, Base
from app.models.schemas import NpsSurvey

BASE_DIR = Path(__file__).resolve().parent.parent / "NPS"

SATISFACTION_SCORES = {
    "😊 Muy satisfecho": 5,
    "🙂 Satisfecho": 4,
    "😐 Neutral": 3,
    "😞 Insatisfecho": 2,
    "😡 Muy insatisfecho": 1,
}

YES_NO_SCORES = {
    "⏱️ Sí ": 1, "⏱️ Sí": 1, "✅ Sí": 1, "👍 Sí": 1,
    "🕓 No": 0, "❌ No ": 0, "❌ No": 0, "👎 No": 0,
    "Sí": 1, "No": 0,
}

MONTH_MAP = {
    "1_JUL": "2025-07", "2_AGO": "2025-08", "3_SEP": "2025-09",
    "4_OCT": "2025-10", "5_NOV": "2025-11", "6_DIC": "2025-12",
    "7_ENE": "2026-01", "8_FEB": "2026-02", "9_MAR": "2026-03",
}

QUESTION_MAP = {
    "¿Cómo calificarías la atención que recibiste?": "calificacion_atencion",
    "¿La atención fue rápida?": "atencion_rapida",
    "¿Pudiste resolver tu duda o problema?": "problema_resuelto",
    "¿Volverías a utilizar este canal para ser atendido?": "volveria_a_usar",
    "¿Cómo calificarías el trato que recibiste por parte del asesor?": "calificacion_asesor",
    "¿Quieres dejar un comentario o sugerencia? ✍️": "comentario",
}


def parse_flow_response(content_str: str) -> dict | None:
    """Parse JSON content and extract survey flow response."""
    if not content_str:
        return None
    try:
        data = json.loads(content_str)
        flow = data.get("eventParameters", {}).get("flowResponse", {})
        if flow.get("type") != "encuesta":
            return None
        return flow
    except (json.JSONDecodeError, TypeError):
        return None


def compute_nps_categoria(score_atencion, score_asesor):
    """Compute NPS category from satisfaction scores."""
    scores = [s for s in [score_atencion, score_asesor] if s is not None]
    if not scores:
        return None
    avg = sum(scores) / len(scores)
    if avg >= 4.5:
        return "Promotor"
    elif avg >= 3.0:
        return "Pasivo"
    return "Detractor"


def get_conversation_types(tenant_id: str) -> dict:
    """Query messages table to classify conversations as Bot/Agente/Mixta."""
    query = text("""
        SELECT conversation_id,
            bool_or(is_bot) AS has_bot,
            bool_or(is_human) AS has_human
        FROM messages
        WHERE tenant_id = :tenant
          AND conversation_id IS NOT NULL
        GROUP BY conversation_id
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"tenant": tenant_id}).fetchall()

    result = {}
    for row in rows:
        conv_id = row[0]
        has_bot = row[1]
        has_human = row[2]
        if has_bot and has_human:
            result[conv_id] = "Mixta"
        elif has_human:
            result[conv_id] = "Agente"
        elif has_bot:
            result[conv_id] = "Bot"
        else:
            result[conv_id] = "Desconocido"
    return result


def process_csvs(tenant_id: str = "visionamos"):
    """Parse all NPS CSVs and return list of row dicts for DB insertion."""
    conv_types = get_conversation_types(tenant_id)
    print(f"Loaded {len(conv_types)} conversation type classifications")

    rows = []
    csv_files = sorted(BASE_DIR.glob("*.csv"))

    for csv_file in csv_files:
        stem = csv_file.stem
        month_label = MONTH_MAP.get(stem, stem)

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                flow = parse_flow_response(row.get("content", ""))
                if not flow:
                    continue

                # Extract survey answers
                answers = {}
                for full_q, short_name in QUESTION_MAP.items():
                    val = flow.get(full_q, "")
                    answers[short_name] = val.strip() if val else ""

                entity = flow.get("entity", "").strip()

                # Compute scores
                score_atencion = SATISFACTION_SCORES.get(answers["calificacion_atencion"])
                score_asesor = SATISFACTION_SCORES.get(answers["calificacion_asesor"])
                rapida = YES_NO_SCORES.get(answers["atencion_rapida"])
                resuelto = YES_NO_SCORES.get(answers["problema_resuelto"])
                volveria = YES_NO_SCORES.get(answers["volveria_a_usar"])
                nps_cat = compute_nps_categoria(score_atencion, score_asesor)

                # Parse date
                msg_date = row.get("messageDate", "")
                try:
                    dt = datetime.fromisoformat(msg_date)
                    date_val = dt.date()
                    hour_val = dt.strftime("%H:%M")
                    weekday = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"][dt.weekday()]
                except Exception:
                    date_val = None
                    hour_val = None
                    weekday = None
                    dt = None

                if not date_val:
                    continue

                conv_id = row.get("agentConversationId", "")
                canal_tipo = conv_types.get(conv_id, "Agente")

                rows.append({
                    "tenant_id": tenant_id,
                    "message_date": dt,
                    "date": date_val,
                    "hour": hour_val,
                    "day_of_week": weekday,
                    "month_label": month_label,
                    "contact_name": row.get("profileName", ""),
                    "contact_id": row.get("contactId", ""),
                    "entity": entity,
                    "score_atencion": score_atencion,
                    "score_asesor": score_asesor,
                    "rapida": rapida,
                    "resuelto": resuelto,
                    "volveria": volveria,
                    "nps_categoria": nps_cat,
                    "comentario": answers.get("comentario", ""),
                    "agent_id": row.get("agentId", ""),
                    "conversation_id": conv_id,
                    "close_reason": row.get("agentCloseReason", ""),
                    "canal_tipo": canal_tipo,
                })

    return rows


def import_to_db(rows: list):
    """Insert NPS survey rows into the database."""
    # Ensure table exists
    Base.metadata.create_all(bind=engine, tables=[NpsSurvey.__table__])

    with engine.begin() as conn:
        # Clear existing data
        conn.execute(text("DELETE FROM nps_surveys"))

        if not rows:
            print("No rows to import")
            return

        # Bulk insert
        conn.execute(NpsSurvey.__table__.insert(), rows)

    print(f"Imported {len(rows)} NPS survey records")


def main():
    print("=" * 50)
    print("NPS Survey Import")
    print("=" * 50)

    if not BASE_DIR.exists():
        print(f"NPS folder not found: {BASE_DIR}")
        return

    csv_count = len(list(BASE_DIR.glob("*.csv")))
    print(f"Found {csv_count} CSV files in {BASE_DIR}")

    rows = process_csvs()
    print(f"Parsed {len(rows)} survey responses")

    if rows:
        # Summary
        from collections import Counter
        cats = Counter(r["nps_categoria"] for r in rows if r["nps_categoria"])
        canals = Counter(r["canal_tipo"] for r in rows)
        total = len(rows)
        prom = cats.get("Promotor", 0)
        det = cats.get("Detractor", 0)
        nps = round((prom - det) / total * 100, 1) if total > 0 else 0

        print(f"\nNPS Score: {nps}")
        print(f"  Promotores:  {prom} ({prom/total*100:.1f}%)")
        print(f"  Pasivos:     {cats.get('Pasivo', 0)} ({cats.get('Pasivo', 0)/total*100:.1f}%)")
        print(f"  Detractores: {det} ({det/total*100:.1f}%)")
        print(f"\nCanal tipo: {dict(canals)}")

        import_to_db(rows)
    else:
        print("No survey data found!")


if __name__ == "__main__":
    main()
