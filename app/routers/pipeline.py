"""Pipeline trigger and status."""
import threading
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter()

_pipeline_state = {
    "running": False,
    "last_run": None,
    "last_status": None,
    "last_duration_s": None,
    "last_results": None,
}
_pipeline_lock = threading.Lock()


def _run_pipeline_background(skip_extract=False, skip_dbt=False):
    import time
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    start = time.time()
    results = {}
    errors = []

    try:
        if not skip_extract:
            try:
                from scripts.extractors.orchestrator import main as extraction_main
                extraction_main()
                results["extract"] = "ok"
            except Exception as exc:
                results["extract"] = f"error: {str(exc)[:200]}"
                errors.append(f"extract: {exc}")

        try:
            from scripts.transform_bridge import main as transform_main
            rc = transform_main()
            results["transform"] = "ok" if rc == 0 else "error"
        except Exception as exc:
            results["transform"] = f"error: {str(exc)[:200]}"
            errors.append(f"transform: {exc}")

        if not skip_dbt:
            import subprocess
            project_root = Path(__file__).resolve().parent.parent.parent
            dbt_dir = project_root / "dbt"
            try:
                r = subprocess.run(
                    ["dbt", "run"], cwd=str(dbt_dir),
                    capture_output=True, text=True, timeout=120,
                )
                results["dbt_run"] = "ok" if r.returncode == 0 else "error"
            except Exception as exc:
                results["dbt_run"] = f"error: {str(exc)[:100]}"

        elapsed = time.time() - start
        status = "success" if not errors else "partial_error"

    except Exception as exc:
        elapsed = time.time() - start
        status = "error"
        results["fatal"] = str(exc)[:300]

    with _pipeline_lock:
        _pipeline_state["running"] = False
        _pipeline_state["last_run"] = datetime.now(timezone.utc).isoformat()
        _pipeline_state["last_status"] = status
        _pipeline_state["last_duration_s"] = round(elapsed, 1)
        _pipeline_state["last_results"] = results


@router.post("/run")
async def run_pipeline(
    skip_extract: bool = Query(False),
    skip_dbt: bool = Query(False),
):
    with _pipeline_lock:
        if _pipeline_state["running"]:
            return {"status": "already_running", "message": "Pipeline is already running."}
        _pipeline_state["running"] = True

    thread = threading.Thread(
        target=_run_pipeline_background,
        args=(skip_extract, skip_dbt),
        daemon=True,
    )
    thread.start()

    return {"status": "accepted", "message": "Pipeline started in background."}


@router.get("/status")
async def pipeline_status():
    with _pipeline_lock:
        return dict(_pipeline_state)
