from backend.services.config_services import attach_uploads_to_config, latest_config_path, read_config, write_config, get_config_id, normalize_key
from backend.services.utils.capability_report import capability_report, normalize_key
from evaluator.core.plugin_loader import discover_all_plugins #cancel
from evaluator.core.plugin_registry import build_registry_from_plugins
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR , REGISTRY_DIR
from backend.schemas.config import ConfigIn
from pydantic import BaseModel, Field, RootModel
from typing import Optional, Dict, List, Any
from pathlib import Path
import importlib
import logging
import uuid
import json
import sys
import re

#logger
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# import all from evaluator.core, evaluator.utilities
sys.modules.setdefault("core", importlib.import_module("evaluator.core"))
sys.modules.setdefault("utilities", importlib.import_module("evaluator.utilities"))

#routing
configs_router = APIRouter(tags=["configs"])
rights_router = APIRouter(tags=["rights"])

####################################

#POST: Create first config
@configs_router.post("/first_config")
def save_config(cfg_path: ConfigIn):
    cfg_path_id = str(uuid.uuid4())
    path = CONFIG_DIR / f"{cfg_path_id}.json"

    payload = cfg_path.model_dump()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {"config_id": cfg_path_id}

#POST: save datasets with {cfg_path_id}_X_test
@configs_router.post("/config")
def save_config(cfg_path: ConfigIn):
    cfg_path_id = get_config_id() 
    path = CONFIG_DIR / f"{cfg_path_id}.json"

    payload = cfg_path.model_dump()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    attach_uploads_to_config(path, UPLOAD_DIR) #save files from uploads to config.json

    return {"config_id": cfg_path_id}

#GET: Build Plugin registry: maps all the metrics and rights existing in the system
@configs_router.get("/plugin-registry")
def get_plugin_registry():
    plugins = discover_all_plugins("evaluator.plugins") #returns: evaluator.plugins.fairness.demographic_parity.DemographicParity
    
    reg = build_registry_from_plugins(plugins)  #store registry

    try:
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

        out_path = REGISTRY_DIR / "plugin_registry.json"
        out_path.write_text(json.dumps(reg, indent=2), encoding="utf-8")

        logger.info("Plugin registry saved to: %s", out_path)
    except Exception as e:
        logger.exception("Failed to save plugin registry to REGISTRY_DIR: %s", e)

    return reg

#POST: rights selected into config + capability report based on right and requires
class RightsPayload(BaseModel):
    rights_to_evaluate: List[str]

@rights_router.post("/rights/configs")
def save_rights(payload: RightsPayload):
    path = latest_config_path() 
    cfg_path = read_config(path)

    normalized_rights = [normalize_key
(r) for r in payload.rights_to_evaluate] 
    cfg_path["rights_to_evaluate"] = normalized_rights

    write_config(path, cfg_path)
    
    registry_path = REGISTRY_DIR / "plugin_registry.json"

    result = capability_report(path, cfg_path, registry_path) 
    return result

#PUT: Add SensitiveFeatures in the config file
class SensitiveFeaturesUpdate(BaseModel):
    features: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

@configs_router.put("/configs/sensitive_features")
def update_sensitive_features(payload: SensitiveFeaturesUpdate):
    path = latest_config_path() 

    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {e}")

    features = current.get("features")
    if not isinstance(features, dict): #if none selected -> empty dict
        features = {}
        current["features"] = features

    # Into config file
    for feat_name, feat_obj in payload.features.items():
        sensitive_value = True
        if isinstance(feat_obj, dict) and "sensitive" in feat_obj:
            sensitive_value = bool(feat_obj["sensitive"])

        features[feat_name] = {"sensitive": sensitive_value}

    try:
        path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write config: {e}")

    return {"config_id": path.stem, "features": current["features"]}

#GET: last config file
@configs_router.get("/configs/latest")
def get_latest_config():
    path = latest_config_path()
    try:
        cfg_path = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find config: {e}")

    return {"config_id": path.stem, "config": cfg_path}

#PUT: metrics to be computed + plugin paths
class Update(BaseModel):
    metrics: Dict[str, List[str]]
    plugins: List[str]

@configs_router.put("/configs/metrics_to_compute")
def update_latest_metrics(payload: Update):
    path = latest_config_path() 

    try:
        cfg_path = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read latest config: {e}")

    cfg_path["metrics"] = payload.metrics
    cfg_path["plugins"] = payload.plugins

    try:
        path.write_text(
            json.dumps(cfg_path, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write latest config: {e}")

    return {"config_id": path.stem, "config": cfg_path}

#Update FRIA CONTEXT:
class FRIAContextPayload(BaseModel):
    description_of_processes: str = ""
    period_and_frequency_of_use: str = ""
    affected_persons_and_groups: str = ""

@configs_router.put("/configs/update_fria_context")
def update_fria_context(payload: FRIAContextPayload):
    latest_cfg = latest_config_path()  # use your existing helper
    if not latest_cfg.exists():
        raise HTTPException(status_code=404, detail="No config file found")

    cfg = json.loads(latest_cfg.read_text(encoding="utf-8"))

    cfg["description_of_processes"] = payload.description_of_processes
    cfg["period_and_frequency_of_use"] = payload.period_and_frequency_of_use
    cfg["affected_persons_and_groups"] = payload.affected_persons_and_groups

    latest_cfg.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"ok": True}



#Save parameters selected for metrics.json
class ParametersPayload(RootModel[Dict[str, Dict[str, Any]]]): 
    pass

'''{
  "statistical_parity_difference": {
    "threshold": 0.2
  },
'''
@configs_router.put("/configs/parameters")
def update_latest_metrics(payload: ParametersPayload):
    cfg_id = get_config_id()
    cfg_path = CONFIG_DIR / f"{cfg_id}.json"

    #loads config file
    with cfg_path.open("r", encoding="utf-8") as f:
        config_file = json.load(f) 
       
    incoming = payload.root or {} #metrics from frontend + params -> {"statistical_parity_difference": {"threshold": 0.2}}

    for metric_id, params in incoming.items():
        section_key = metric_id

        #Create dictionary with selected params in config file
        if not isinstance(config_file.get(section_key), dict):
            config_file[section_key] = {}

        config_file[section_key].update(params)

    try:
        cfg_path.write_text(json.dumps(config_file, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write latest config: {e}")

    return {"config_id": cfg_path.stem, "config": config_file}




