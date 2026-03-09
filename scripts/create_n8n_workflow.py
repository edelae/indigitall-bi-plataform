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
N8N_API_KEY = "n8n_api_indigitall_pipeline_2026"

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


def _api_call(method: str, path: str, body: dict | None = None) -> dict | None:
    """Make an authenticated n8n API call. Returns parsed JSON or None on error."""
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        f"{N8N_BASE}{path}",
        data=data,
        headers={
            "X-N8N-API-KEY": N8N_API_KEY,
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  [ERROR] {e.code}: {error_body}")
        return None


def main(activate: bool = False):
    print("=" * 60)
    print("  Creating n8n Workflow")
    print("=" * 60)

    # Step 1: Create workflow (always inactive by default)
    print("\n  [1/2] Creating workflow...")
    result = _api_call("POST", "/api/v1/workflows", WORKFLOW)
    if result is None:
        return 1

    workflow_id = result.get("id")
    print(f"  Created: {result.get('name')} (ID: {workflow_id})")

    # Step 2: Activate only if explicitly requested
    if activate:
        print("\n  [2/2] Activating workflow...")
        act_result = _api_call("POST", f"/api/v1/workflows/{workflow_id}/activate")
        if act_result is None:
            print("  [WARN] Workflow created but activation failed")
            return 1
        print(f"  Active: {act_result.get('active')}")
    else:
        print("\n  [2/2] Skipping activation (workflow created INACTIVE)")
        print("        To activate later, run:")
        print(f"        python scripts/create_n8n_workflow.py --activate {workflow_id}")

    print(f"\n{'=' * 60}")
    status = "created and ACTIVATED" if activate else "created (INACTIVE)"
    print(f"  Workflow '{WORKFLOW['name']}' {status}!")
    print(f"  When active, it will run every 10 minutes and execute:")
    print(f"    1. API extraction (incremental — only new data)")
    print(f"    2. Transform bridge (raw → public tables)")
    print(f"    3. dbt run (staging → marts + analytics)")
    print(f"{'=' * 60}")

    return 0


def activate_workflow(workflow_id: str):
    """Activate an existing workflow by ID."""
    print(f"  Activating workflow {workflow_id}...")
    result = _api_call("POST", f"/api/v1/workflows/{workflow_id}/activate")
    if result is None:
        return 1
    print(f"  Active: {result.get('active')}")
    print(f"  Workflow is now running every 10 minutes!")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--activate":
        sys.exit(activate_workflow(sys.argv[2]))
    elif "--activate" in sys.argv:
        print("  Usage: python scripts/create_n8n_workflow.py --activate <workflow_id>")
        sys.exit(1)
    else:
        sys.exit(main(activate="--active" in sys.argv))
