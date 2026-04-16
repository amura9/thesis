from backend.services.config_services import attach_uploads_to_config, latest_config_path, read_config, write_config
from backend.services.utils.detect_metric_schema import detect_all_result_schemas
from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR, REGISTRY_DIR #all the dir to be imported
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from backend.services.result_services import render_report_to_pdf, load_plugin_registry, compute_total_score
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


logger = logging.getLogger("uvicorn.error")
router = APIRouter(tags=["results"])

#GET: metrics to be displayed in dashboard
@router.get("/results/plugins")
def get_plugins():
    path = latest_config_path()
    cfg = json.loads(path.read_text(encoding="utf-8"))
    return {
        "config_file": path.name,
        "plugins": cfg.get("plugins", [])
    }

#GET: values to be displayed for the dashboard + metadata for report generation -> datset used, evaluation date
@router.get("/results/values_to_display")
def values_to_display():
    cfg = latest_config_path()
    if not cfg:
        raise HTTPException(status_code=404, detail="No config files found")

    run_id = cfg.stem    
    cfg = json.loads(cfg.read_text(encoding="utf-8"))

    dataset_name = ""
    x_test = (cfg.get("datasets") or {}).get("X_test")
        
    #dataset used to display in final report
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
        results = json.loads(res_path.read_text(encoding="utf-8"))  
        
        return {
        "run_id": run_id, 
        "results": results, #to be displayed
        "evaluation_date": evaluation_date, #needed for the report generation
        "dataset_name": dataset_name, #needed for the report generation
    }

    raise HTTPException(status_code=404, detail="No results found matching any config")

#GET: returns the schema identified for each metric in the results
@router.get("/results/result_schemas")
def get_result_schemas(run_id: str | None = Query(default=None)):
    if run_id is None:
        cfg = latest_config_path()
        if not cfg:
            raise HTTPException(status_code=404, detail="No config files found")
        run_id = cfg.stem

    schemas_path = RESULTS_DIR / f"{run_id}_schemas.json"
    if not schemas_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Schemas file not found for run_id={run_id}. Expected: {schemas_path.name}"
        )

    return json.loads(schemas_path.read_text(encoding="utf-8"))

#payload for report
class WeightsSavePayload(BaseModel):
    run_id: str #id
    group: Optional[str] = None #right
    metric: str #metric

    #metric description will instead be taken from the plugin_registry

    #weights / justification at metric level
    user_weight: Optional[float] = None
    user_justification: Optional[str] = ""
    
    #weights / justification at sensitive features level
    weights: Dict[str, float] = Field(default_factory=dict)           
    justifications: Dict[str, str] = Field(default_factory=dict)    

    #schema 
    schema_type_report: Optional[str] = None

    #context and summary
    context_report: Optional[Dict[str, Any]] = None
    summary_report: Optional[Dict[str, Any]] = None

#POST: save weights, justification and report content (context + summary)
@router.post("/results/save_weights")
def save_weights(payload: WeightsSavePayload):
    run_id = payload.run_id
    group = payload.group
    metric = payload.metric

    #Metric deascription, right taken from plugin registry
    plugin_registry = load_plugin_registry(REGISTRY_DIR)

    metric_meta = plugin_registry.get(metric, {})
    metric_description = metric_meta.get("description") #get description 
    metric_right = metric_meta.get("right")#get right

    #create {id}_report.json path
    source_path = RESULTS_DIR / f"{run_id}.json"
    report_path = RESULTS_DIR / f"{run_id}_report.json"

    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"Results file not found for run_id={run_id}")

    if report_path.exists():
        report_raw = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        report_raw = json.loads(source_path.read_text(encoding="utf-8"))

    report_results = report_raw.get("results") if isinstance(report_raw, dict) and "results" in report_raw else report_raw

    if metric not in report_results or not isinstance(report_results[metric], dict):
        raise HTTPException(status_code=400, detail=f"Metric '{metric}' not found in results/report")

    metric_obj = report_results[metric] #select results per metric
    # --------------------
    # CASE A: GLOBAL METRIC  - Case: a new metric
    '''
    "New Metric": {
        "(global)": {
          "value": 0.82
        }
      }
    '''
    # --------------------
    if payload.user_weight is not None and "(global)" in metric_obj:
        w = payload.user_weight
        just = (payload.user_justification).strip()

        if not isinstance(metric_obj["(global)"], dict):
            if isinstance(metric_obj["(global)"], (int, float)):
                metric_obj["(global)"] = {"value": metric_obj["(global)"]}
            else:
                metric_obj["(global)"] = {}

        metric_value = (payload.context_report or {}).get("final_score")

        final_score = compute_total_score(metric_value, w)
        if final_score is not None:
            metric_obj["(global)"]["total_score_report"] = final_score

        #in report: weight, right, metric description, justification, context
        if w: 
            metric_obj["(global)"]["user_weight_report"] = w

        if group:
            metric_obj["(global)"]["group_report"] = group

        if metric_description:
            metric_obj["(global)"]["metric_description_report"] = metric_description

        if metric_right:
                metric_obj["(global)"]["metric_right_report"] = metric_right #save right

        if just:
            metric_obj["(global)"]["user_justification_report"] = just

        if payload.schema_type_report is not None:
            metric_obj["(global)"]["schema_type_report"] = payload.schema_type_report

        if payload.context_report is not None:
            metric_obj["(global)"]["context_report"] = payload.context_report

        report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "mode": "global", "run_id": run_id}

    # --------------------
    # CASE B, Store at metric-level: weights, justistifaction and report saving
    '''
    "user_weight_report": 5,
    "user_justification_report": ""
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
        w = payload.user_weight
        just = (payload.user_justification or "").strip()

        metric_value = (payload.context_report or {}).get("final_score")

        final_score = compute_total_score(metric_value, w)
        if final_score is not None:
            metric_obj["total_score_report"] = final_score

        ##in report: weight, right, metric description, justification, context
        if w: 
            metric_obj["user_weight_report"] = w

        if group:
            metric_obj["right_report"] = group

        if metric_description:
            metric_obj["metric_description_report"] = metric_description #save description
        
        if metric_right:
            metric_obj["metric_right_report"] = metric_right #save right

        if just:
            metric_obj["user_justification_report"] = just

        if payload.schema_type_report is not None:
                metric_obj["schema_type_report"] = payload.schema_type_report
        
        if payload.context_report is not None:
            metric_obj["context_report"] = payload.context_report
        
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
            w = w_raw
            just = (payload.justifications.get(feature) or "").strip()

            # feature to be a dict
            if feature not in metric_obj or not isinstance(metric_obj[feature], dict):
                if isinstance(metric_obj.get(feature), (int, float)):
                    metric_obj[feature] = {"value": metric_obj[feature]}
            else:
                metric_obj[feature] = {}

            metric_value = ((payload.summary_report or {}).get(feature, {}).get("Final Score")
                            or (payload.context_report or {}).get(feature, {}).get("Final Score")
                            or ((payload.context_report or {}).get(feature, {}).get("value")*10)
            )

            final_score = compute_total_score(metric_value, w)
            if final_score is not None:
                metric_obj[feature]["total_score_report"] = final_score

            ##in report: weight, right, metric description, justification, context report, summary report
            metric_obj[feature]["user_weight_report"] = w

            if group:
                metric_obj[feature]["group_report"] = group
            
            if metric_description:
                metric_obj[feature]["metric_description_report"] = metric_description #save description

            if metric_right:
                metric_obj[feature]["metric_right_report"] = metric_right #save right

            if just:
                metric_obj[feature]["user_justification_report"] = just
        
            if payload.schema_type_report is not None:
                metric_obj[feature]["schema_type_report"] = payload.schema_type_report
            
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


#GET: take the _report.json to generate the final PDF
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

    frontend_base_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

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