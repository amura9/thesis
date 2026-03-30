from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR #all the dir to be imported
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from backend.services.config_services import latest_config_path
from pathlib import Path
import ast
import json
import re
import subprocess
import sys
import json 

#round the copy evaluator
def round_floats(obj, decimals=3):
    """
    Recursively round all float values inside dict/list structures.
    """
    if isinstance(obj, float):
        return round(obj, decimals)

    if isinstance(obj, dict):
        return {k: round_floats(v, decimals) for k, v in obj.items()}

    if isinstance(obj, list):
        return [round_floats(v, decimals) for v in obj]

    return obj

#MOVE all_results from EVALUATOR TO BACKEND /RESULTS
def copy_evaluator_all_results(evaluator_main: Path, run_id: str) -> Path:
    """
    Reads evaluator/run_results/all_results.json (created by main2.py)
    and copies it into backend RESULTS_DIR with the run_id in the filename.
    """
    src = (evaluator_main.parent / "run_results" / "all_results.json").resolve()
    if not src.exists():
        raise HTTPException(status_code=500, detail=f"Missing evaluator all_results.json at: {src}")

    dest = (RESULTS_DIR / f"{run_id}.json").resolve()

    #round it
    raw_text = src.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    #round to third decimal
    rounded_data = round_floats(data, decimals=3)

    dest.write_text(
        json.dumps(rounded_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    return dest

#MOVE schemas from EVALUATOR TO BACKEND /RESULTS
def copy_evaluator_result_schemas(evaluator_main: Path, run_id: str) -> Path:
    """
    Reads evaluator/run_results/result_schemas.json (created by evaluator)
    and copies it into backend RESULTS_DIR as {run_id}_schemas.json.
    """
    src = (evaluator_main.parent / "run_results" / "result_schemas.json").resolve()
    if not src.exists():
        raise HTTPException(status_code=500, detail=f"Missing evaluator result_schemas.json at: {src}")

    dest = (RESULTS_DIR / f"{run_id}_schemas.json").resolve()
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def save_run_results(run_id: str, results_text: str) -> Path:
    out_path = RESULTS_DIR / f"{run_id}.json" #results

    #stored in vertical structure
    payload = {
        "run_id": run_id,
    }

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path

#RUN EVALUATOR IN BACKEND 
def run_evaluator(evaluator_main, config_path, run_dir, results_dir):  # run evaluator
    
    if not evaluator_main.exists():
        raise HTTPException(status_code=500, detail=f"Evaluator not found: {evaluator_main}")

    run_id = config_path.stem
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [sys.executable, str(evaluator_main), "--config", str(config_path)],
            cwd=str(evaluator_main.parent),
            capture_output=True,
            text=True,
            check=True,
        )

    except subprocess.CalledProcessError as e:
        (run_dir / "stdout.txt").write_text(e.stdout or "", encoding="utf-8")
        (run_dir / "stderr.txt").write_text(e.stderr or "", encoding="utf-8")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Evaluator failed",
                "run_id": run_id,
                "results_content": e.stdout,
                "errors": e.stderr,
            },
        )

    # (?keep or not?)
    (run_dir / "results_content.txt").write_text(result.stdout or "", encoding="utf-8")
    (run_dir / "errors.txt").write_text(result.stderr or "", encoding="utf-8")
    (run_dir / "config_used.json").write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")

    # OLD parsed vertical result (you can keep it if needed)
    saved_path = save_run_results(run_id, result.stdout or "")

    #Copy all_results.json from evaluator to backend with its id
    #do the same for schema
    try:
        all_results_path = copy_evaluator_all_results(evaluator_main, run_id)
        schemas_path = copy_evaluator_result_schemas(evaluator_main, run_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to copy evaluator outputs: {e}")

    return {
        "status": "completed",
        "run_id": run_id,
        "config_file": config_path.name,
        "results_file": str(saved_path),                  # parsed version
        "all_results_file": str(all_results_path),        # full structured version
    }
