"""Create n8n workflow for automated incremental data pipeline.

Usage:
    python scripts/create_n8n_workflow.py

Requires N8N_API_TOKEN env var or pass as argument.
"""

import json
import sys
import urllib.request
import urllib.error

N8N_BASE = "http://localhost:5678"
N8N_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJiNTRkMWIzNS03ZjBjLTQwOWMtODhkMi01ZjFkMjlhNGQ3MWIi"
    "LCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzcyOTM0ODcyfQ."
    "hAjiikJgWD_DHgHvap0PWL3_xttDerDiuxq3JQwNjZU"
)

PIPELINE_URL = "http://app:8050/api/pipeline/run"
STATUS_URL = "http://app:8050/api/pipeline/status"

WORKFLOW = {
    "name": "Indigitall Data Pipeline — Incremental Sync (10 min)",
    "nodes": [
        {
            "parameters": {
                "rule": {
                    "interval": [{"field": "minutes", "minutesInterval": 10}]
                }
            },
            "id": "cron-trigger",
            "name": "Cron: Every 10 Minutes",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [0, 0],
        },
        {
            "parameters": {
                "method": "POST",
                "url": PIPELINE_URL,
                "options": {"timeout": 600000},
            },
            "id": "trigger-pipeline",
            "name": "POST /api/pipeline/run",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [300, 0],
        },
        {
            "parameters": {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                    },
                    "conditions": [
                        {
                            "id": "check-accepted",
                            "leftValue": "={{ $json.status }}",
                            "rightValue": "accepted",
                            "operator": {
                                "type": "string",
                                "operation": "equals",
                            },
                        }
                    ],
                    "combinator": "and",
                }
            },
            "id": "check-started",
            "name": "Pipeline Started?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [600, 0],
        },
        {
            "parameters": {"amount": 120, "unit": "seconds"},
            "id": "wait-120s",
            "name": "Wait 2 min",
            "type": "n8n-nodes-base.wait",
            "typeVersion": 1.1,
            "position": [900, -100],
        },
        {
            "parameters": {
                "method": "GET",
                "url": STATUS_URL,
                "options": {},
            },
            "id": "check-status",
            "name": "GET Pipeline Status",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1200, -100],
        },
        {
            "parameters": {},
            "id": "skip-already-running",
            "name": "Already Running — Skip",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [900, 100],
        },
    ],
    "connections": {
        "Cron: Every 10 Minutes": {
            "main": [
                [
                    {
                        "node": "POST /api/pipeline/run",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
        "POST /api/pipeline/run": {
            "main": [
                [
                    {
                        "node": "Pipeline Started?",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
        "Pipeline Started?": {
            "main": [
                [{"node": "Wait 2 min", "type": "main", "index": 0}],
                [{"node": "Already Running — Skip", "type": "main", "index": 0}],
            ]
        },
        "Wait 2 min": {
            "main": [
                [
                    {
                        "node": "GET Pipeline Status",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
    },
    "settings": {
        "executionOrder": "v1",
        "timezone": "America/Bogota",
    },
}


def main():
    print("=" * 60)
    print("  Creating n8n Workflow")
    print("=" * 60)

    # Step 1: Create workflow
    print("\n  [1/2] Creating workflow...")
    body = json.dumps(WORKFLOW).encode("utf-8")
    req = urllib.request.Request(
        f"{N8N_BASE}/api/v1/workflows",
        data=body,
        headers={
            "Authorization": "Basic " + __import__("base64").b64encode(b"admin:JBkRgJwzCuZorQm59njCpQ").decode(),
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            workflow_id = result.get("id")
            print(f"  Created: {result.get('name')} (ID: {workflow_id})")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  [ERROR] {e.code}: {error_body}")
        return 1

    # Step 2: Activate workflow
    print("\n  [2/2] Activating workflow...")
    activate_req = urllib.request.Request(
        f"{N8N_BASE}/api/v1/workflows/{workflow_id}/activate",
        headers={
            "Authorization": "Basic " + __import__("base64").b64encode(b"admin:JBkRgJwzCuZorQm59njCpQ").decode(),
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(activate_req) as resp:
            result = json.loads(resp.read())
            print(f"  Active: {result.get('active')}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  [ERROR] Activation failed: {e.code}: {error_body}")
        return 1

    print(f"\n{'=' * 60}")
    print(f"  Workflow '{WORKFLOW['name']}' created and activated!")
    print(f"  It will run every 10 minutes and execute:")
    print(f"    1. API extraction (incremental — only new data)")
    print(f"    2. Transform bridge (raw → public tables)")
    print(f"    3. dbt run (staging → marts + analytics)")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
