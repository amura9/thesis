from backend.services.config_services import attach_uploads_to_config, latest_config_path, read_config, write_config, deep_merge
from backend.services.utils.detect_metric_schema import detect_all_result_schemas
from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR #all the dir to be imported
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from backend.services.result_services import render_report_to_pdf
from fastapi.responses import JSONResponse, FileResponse
from backend.schemas.config import ConfigIn
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime
import logging
import uuid
import json
import os
import re

#logger for debugging
logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["results"])

#DESCRIPTION EXTRACTED FROM PLUGIN_REGISTRY
PLUGIN_REGISTRY_PATH = STORAGE_DIR / "summary/plugin_registry.json"

def load_plugin_registry() -> dict:
    if not PLUGIN_REGISTRY_PATH.exists():
        return {}
    return json.loads(PLUGIN_REGISTRY_PATH.read_text(encoding="utf-8"))

def _as_list(x):
    """Normalize Path|List[Path]|None into List[Path]."""
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    if isinstance(x, Path):
        return [x]
    return []

#METRICS TO BE DISPLAYED DYNAMICALLY IN RESULTS
@router.get("/results/plugins")
def get_plugins():
    cfg_path = latest_config_path()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    return {
        "config_file": cfg_path.name,
        "plugins": cfg.get("plugins", [])
    }

#make it jsonable
def make_jsonable(x):

    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, pd.Series):
        return x.tolist()
    if isinstance(x, pd.DataFrame):
        return x.to_dict(orient="records")
    if isinstance(x, dict):
        return {str(k): make_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [make_jsonable(v) for v in x]
    return x
  

#VALUES FOR METRICS TO BE DISPLAYED
@router.get("/results/values_to_display")
def values_to_display():
    cfgs = _as_list(latest_config_path())
    if not cfgs:
        raise HTTPException(status_code=404, detail="No config files found")

    # try configs from newest to oldest (latest_config_path gives newest first)

    for cfg_path in cfgs:
        run_id = cfg_path.stem

        #extract dataset_name
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

        #get dataset name (Ex. 235h4hxn33__ABC_.csv -> ABC) and evaluation date
        dataset_name = ""
        x_test = (cfg.get("datasets") or {}).get("X_test")
           
        #dataset
        if x_test:
            fname = os.path.basename(str(x_test))
            parts = fname.split("__")
            if len(parts) >= 3:
                dataset_name = parts[-1]
                if dataset_name.lower().endswith(".csv"):
                    dataset_name = dataset_name[:-4]  #no 

        #date
        evaluation_date = datetime.now().strftime("%B %d, %Y")
        logger.info(f"dataset= {dataset_name}")
        
        #results only matching config id
        res_path = RESULTS_DIR / f"{run_id}.json"

        if res_path.exists():
            raw = json.loads(res_path.read_text(encoding="utf-8"))
            cleaned = make_jsonable(raw)
            
            return {
            "run_id": run_id,
            "results": cleaned,
            "evaluation_date": evaluation_date,
            "dataset_name": dataset_name,
        }

    raise HTTPException(status_code=404, detail="No results found matching any config")

#RESULTING SCHEMAS
@router.get("/results/result_schemas")
def get_result_schemas(run_id: str | None = Query(default=None)):
    """
    Returns the schema dictionary saved in backend/storage/results.

    - If run_id is provided: reads RESULTS_DIR/{run_id}_schemas.json
    - If run_id is not provided: uses latest_config_path().stem as run_id
    """
    if run_id is None:
        cfg_path = latest_config_path()
        if not cfg_path:
            raise HTTPException(status_code=404, detail="No config files found")
        run_id = cfg_path.stem

    schemas_path = RESULTS_DIR / f"{run_id}_schemas.json"
    if not schemas_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Schemas file not found for run_id={run_id}. Expected: {schemas_path.name}"
        )

    return json.loads(schemas_path.read_text(encoding="utf-8"))

###############################################################
#Explicit saving
#Save: weights, justification, report content (if save clicked or not)
DEFAULT_WEIGHT = 5

#payload for report
class WeightsSavePayload(BaseModel):
    run_id: str
    group: Optional[str] = None
    metric: str

    #weights provided at metrics level 
    user_weight: Optional[int] = None
    user_justification: Optional[str] = ""
    
    #weights provided at sensitive features level
    weights: Dict[str, int] = Field(default_factory=dict)           # {feature: weight}
    justifications: Dict[str, str] = Field(default_factory=dict)    # {feature: text}

    #save also the schema_type
    schema_type_report: Optional[str] = None

    #context table / summary table
    context_report: Optional[Dict[str, Any]] = None
    summary_report: Optional[Dict[str, Any]] = None

import json
from fastapi import HTTPException

def _clamp_weight(w: int) -> int:
    try:
        w = int(w)
    except Exception:
        w = DEFAULT_WEIGHT
    return max(0, min(10, w))

#WEIGHTS SAVING AND GENERATION OF REPORT DATA
@router.post("/results/save_weights")
def save_weights(payload: WeightsSavePayload):
    run_id = payload.run_id
    group = payload.group
    metric = payload.metric

    #METRIC DESCRIPTION FROM PLUGIN REGISTRY
    plugin_registry = load_plugin_registry()

    metric_meta = plugin_registry.get(metric, {})
    metric_description = metric_meta.get("description") #get description 
    metric_right = metric_meta.get("right")#get right
    source_path = RESULTS_DIR / f"{run_id}.json"
    report_path = RESULTS_DIR / f"{run_id}_report.json"

    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"Results file not found for run_id={run_id}")

    # Build report file starting from original results once, then keep updating report file
    if report_path.exists():
        report_raw = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        report_raw = json.loads(source_path.read_text(encoding="utf-8"))

    report_results = report_raw.get("results") if isinstance(report_raw, dict) and "results" in report_raw else report_raw
    if not isinstance(report_results, dict):
        raise HTTPException(status_code=500, detail="Invalid report structure")

    if metric not in report_results or not isinstance(report_results[metric], dict):
        raise HTTPException(status_code=400, detail=f"Metric '{metric}' not found in results/report")

    metric_obj = report_results[metric]
    # --------------------
    # CASE A: GLOBAL METRIC  - no need of sensitive features / new metric
    '''
    "New Metric": {
        "(global)": {
          "value": 0.82
        }
      }
    '''
    # --------------------
    if payload.user_weight is not None and "(global)" in metric_obj:
        w = _clamp_weight(payload.user_weight)
        just = (payload.user_justification or "").strip()

        if not isinstance(metric_obj["(global)"], dict):
            if isinstance(metric_obj["(global)"], (int, float)):
                metric_obj["(global)"] = {"value": metric_obj["(global)"]}
            else:
                metric_obj["(global)"] = {}

        metric_obj["(global)"]["user_weight_report"] = w

        if group:
            metric_obj["(global)"]["group_report"] = group

        if metric_description:
            metric_obj["(global)"]["metric_description_report"] = metric_description

        if metric_right:
            metric_obj["(global)"]["metric_right_report"] = metric_right

        if w != DEFAULT_WEIGHT:
            metric_obj["(global)"]["user_justification_report"] = just
        else:
            metric_obj["(global)"].pop("user_justification_report", None)

        if payload.context_report is not None:
            metric_obj["(global)"]["context_report"] = payload.context_report

        if payload.schema_type_report is not None:
            metric_obj["(global)"]["schema_type_report"] = payload.schema_type_report

        if payload.summary_report is not None:
            metric_obj["(global)"]["summary_report"] = payload.summary_report

        report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "mode": "global", "run_id": run_id}

    # --------------------
    # CASE B: Metric-level weights, justistifaction and report saving
    '''
    "user_weight_report": 5,
    "metric_description_report": "Evaluates K-Anonymity over quasi-identifiers (each equivalence class must have at least k records).",
    "metric_right_report": "Privacy",
    "context_report": {
      "avg_group_size": 22.94,
      "compliance": false,
      "compliance_percentage": 97.71,
      "k_value": 2,
      "max_group_size": 97,
      "metric": "K-Anonymity",
      "min_group_size": 1,
      "quasi_identifiers": [
        "age_cv",
        "competences_coverage_required"
      ],
      "status": "success",
      "total_groups": 218
    '''
    # --------------------
    if payload.user_weight is not None:
        w = _clamp_weight(payload.user_weight)
        just = (payload.user_justification or "").strip()

        # store at metric level
        metric_obj["user_weight_report"] = w

        #store also the rights
        if group:
            metric_obj["right_report"] = group

        if metric_description:
            metric_obj["metric_description_report"] = metric_description #save description
        
        if metric_right:
            metric_obj["metric_right_report"] = metric_right #save right

        if w != DEFAULT_WEIGHT:
            metric_obj["user_justification_report"] = just
        else:
            metric_obj.pop("user_justification_report", None)
        
        if payload.context_report is not None:
            metric_obj["context_report"] = payload.context_report
        
        if payload.schema_type_report is not None:
                metric_obj["schema_type_report"] = payload.schema_type_report
        
        report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "mode": "metric", "run_id": run_id}

    # --------------------
    # CASE C: Feature-level weights, justistifaction and report saving
    '''
    "user_weight_report": 5,
      "metric_description_report": "Measures disparity in selection rates across sensitive groups conditioned on another variable.",
      "metric_right_report": "Fairness",
      "context_report": {
        "conditional_variable": "age_cv",
        "metric": "Conditional Statistical Parity",
        "sensitive_feature": "competences_coverage_required",  ####FEATURE LEVEL
        "status": "success"
        '''
    
    '''
    "user_weight_report": 5,
      "metric_description_report": "Measures disparity in selection rates across sensitive groups conditioned on another variable.",
      "metric_right_report": "Fairness",
      "context_report": {
        "conditional_variable": "age_cv",
        "metric": "Conditional Statistical Parity",
        "sensitive_feature": "competences_coverage_optional", ####FEATURE LEVEL
        "status": "success"
        '''
    # --------------------
    if payload.weights:
        for feature, w_raw in payload.weights.items():
            w = _clamp_weight(w_raw)
            just = (payload.justifications.get(feature) or "").strip()

            # ensure dict container for feature
            if feature not in metric_obj or not isinstance(metric_obj[feature], dict):
                # if numeric, wrap
                if isinstance(metric_obj.get(feature), (int, float)):
                    metric_obj[feature] = {"value": metric_obj[feature]}
                else:
                    metric_obj[feature] = {}

            metric_obj[feature]["user_weight_report"] = w

            if group:
                metric_obj[feature]["group_report"] = group
            
            if metric_description:
                metric_obj[feature]["metric_description_report"] = metric_description #save description

            if metric_right:
                metric_obj[feature]["metric_right_report"] = metric_right #save right

            if w != DEFAULT_WEIGHT:
                metric_obj[feature]["user_justification_report"] = just
            else:
                metric_obj[feature].pop("user_justification_report", None)

            if payload.schema_type_report is not None:
                metric_obj[feature]["schema_type_report"] = payload.schema_type_report

            #slightly different context report to be used
            if payload.context_report is not None:
                if feature in payload.context_report and isinstance(payload.context_report.get(feature), dict):
                    metric_obj[feature]["context_report"] = payload.context_report[feature]
                else:
                    # fallback: accept flat object too
                    metric_obj[feature]["context_report"] = payload.context_report

            if payload.summary_report is not None:
                if feature in payload.summary_report and isinstance(payload.summary_report.get(feature), dict):
                    metric_obj[feature]["summary_report"] = payload.summary_report[feature]
                else:
                    # fallback: accept flat object too
                    metric_obj[feature]["summary_report"] = payload.summary_report

        report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "mode": "feature", "run_id": run_id}

    raise HTTPException(status_code=400, detail="No weights provided (metric-level or feature-level).")

#USING ABC123_REPORT.json
@router.get("/results/{run_id}_report")
def get_report_json(run_id: str):
    report_path = RESULTS_DIR / f"{run_id}_report.json"

    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Report file not found for run_id={run_id}. Expected: {report_path.name}"
        )

    return json.loads(report_path.read_text(encoding="utf-8"))

#PDF GENERATION
class GeneratePDFRequest(BaseModel):
    run_id: str

@router.post("/results/generate_pdf")
def generate_pdf(req: GeneratePDFRequest):
    run_id = (req.run_id or "").strip()
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id is required")

    frontend_base_url = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5173")

    out_dir = Path("backend/storage/reports")
    out_path = out_dir / f"{run_id}_report.pdf"

    try:
        render_report_to_pdf(
            run_id=run_id,
            frontend_base_url=frontend_base_url,
            out_path=out_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    return FileResponse(
        path=str(out_path),
        media_type="application/pdf",
        filename=f"final_evaluation_report_{run_id}.pdf",
    )