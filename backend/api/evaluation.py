from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR #all the dir to be imported
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from backend.services.config_services import latest_config_path
from backend.services.evaluator_services import run_evaluator
import json

router = APIRouter(tags=["results"])

@router.post("/run-evaluation")
def config_to_evaluator():
    config_path = latest_config_path() #get latest config
    evaluator_main = (BASE_DIR.parent / "evaluator" / "main2.py").resolve()
    run_dir = RUN_DIR / config_path.stem

    #save results
    results = run_evaluator(
        evaluator_main=evaluator_main,
        config_path=config_path,
        run_dir=run_dir,
        results_dir=RESULTS_DIR,
    )

    return results


