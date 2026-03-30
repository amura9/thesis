from backend.services.config_services import attach_uploads_to_config, latest_config_path, read_config, write_config, deep_merge
from backend.services.utils.capability_report import capability_report, normalize_right
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

#SAVE FIRST PLUGIN REGISTRY
@configs_router.get("/plugin-registry")
def get_plugin_registry():
    plugins = discover_all_plugins("evaluator.plugins")

    reg = build_registry_from_plugins(plugins)

    try:
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

        out_path = REGISTRY_DIR / "plugin_registry.json"
        out_path.write_text(json.dumps(reg, indent=2), encoding="utf-8")

        logger.info("Plugin registry saved to: %s", out_path)
    except Exception as e:
        logger.exception("Failed to save plugin registry to REGISTRY_DIR: %s", e)

    return reg

#SAVE FIRST CONFIG FILE & UPLOADED DATASETS
@configs_router.post("/config")
def save_config(cfg: ConfigIn):
    config_id = str(uuid.uuid4())
    path = CONFIG_DIR / f"{config_id}.json"

    payload = cfg.model_dump()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    attach_uploads_to_config(path, UPLOAD_DIR)

    return {"config_id": config_id}

#GET MOST RECENT CONFIG FILE
@configs_router.get("/configs/latest")
def get_latest_config():
    latest_path = latest_config_path()
    try:
        cfg = json.loads(latest_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read latest config: {e}")

    return {"config_id": latest_path.stem, "config": cfg}

#PUT SENSITIVE FEATURES into config file
class SensitiveFeaturesUpdate(BaseModel):
    features: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

@configs_router.put("/configs/sensitive_features")
def update_sensitive_features(payload: SensitiveFeaturesUpdate):
    configs = sorted(
        CONFIG_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if not configs:
        raise HTTPException(status_code=404, detail="No config found")

    path = configs[0]

    # read config
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {e}")

    features = current.get("features")
    if not isinstance(features, dict):
        # If it's missing, null, list, string, etc. -> replace with empty object
        features = {}
        current["features"] = features

    # Merge incoming features into config using your desired shape
    for feat_name, feat_obj in payload.features.items():
        sensitive_value = True
        if isinstance(feat_obj, dict) and "sensitive" in feat_obj:
            sensitive_value = bool(feat_obj["sensitive"])

        features[feat_name] = {"sensitive": sensitive_value}

    # write back
    try:
        path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write config: {e}")

    return {"config_id": path.stem, "features": current["features"]}

#Put latest metrics selected in .json
class Update(BaseModel):
    metrics: Dict[str, List[str]]
    plugins: List[str]


#save metrics to be computed in .json
@configs_router.put("/configs/metrics_to_compute")
def update_latest_metrics(payload: Update):
    # get latest config file path
    latest = latest_config_path()  # ← pass CONFIG_DIR

    # read current config from file
    try:
        cfg = json.loads(latest.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read latest config: {e}")

    # update metrics
    cfg["metrics"] = payload.metrics
    cfg["plugins"] = payload.plugins

    # write back to same file
    try:
        latest.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write latest config: {e}")

    return {"config_id": latest.stem, "config": cfg}

#Save parameters for metrics to be computed in .json
'''
class metricABC(BaseModel):
    enabled: bool = True
    quasi_identifiers: List[str]
    k_value: int
'''

class ParametersPayload(RootModel[Dict[str, Dict[str, Any]]]):
    pass

def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)      # spaces/dashes -> underscore
    s = re.sub(r"[^a-z0-9_]", "", s)    # drop punctuation
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"


def _load_plugin_registry() -> Dict[str, Dict[str, Any]]:
    reg_path = REGISTRY_DIR / "plugin_registry.json"
    try:
        return json.loads(reg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _is_fairness_metric(metric_id: str, registry: Dict[str, Dict[str, Any]]) -> bool:
    meta = registry.get(metric_id) or {}
    return (meta.get("right") or "").strip().lower() == "fairness"


def _fairness_section_key(metric_id: str, registry: Dict[str, Dict[str, Any]]) -> str:
    """
    For fairness metrics, derive the section key from the param label shown in UI.
    label 'Conditional variable' -> 'conditional_variable'
    Fallback order:
      1) label of param with key == 'conditional_variable'
      2) the param key itself ('conditional_variable')
      3) metric_id (last resort)
    """
    meta = registry.get(metric_id) or {}
    params = meta.get("params") or []

    # try to find the conditional_variable param
    for p in params:
        if (p or {}).get("key") == "conditional_variable":
            label = (p or {}).get("label") or "conditional_variable"
            return _slugify(label)

    # fallback: if registry missing param spec
    return "conditional_variable"


@configs_router.put("/configs/parameters")
def update_latest_metrics(payload: ParametersPayload):
    latest = latest_config_path()

    try:
        cfg = json.loads(latest.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read latest config: {e}")

    registry = _load_plugin_registry()
    incoming = payload.root or {}

    for metric_id, params in incoming.items():
        if not isinstance(params, dict):
            continue

        # fairness rights params will be flagged like this
        if _is_fairness_metric(metric_id, registry):
            section_key = _fairness_section_key(metric_id, registry)  # e.g. "conditional_variable"
        else:
            section_key = metric_id

        #else the section key takes metric as key and params as content
        if not isinstance(cfg.get(section_key), dict):
            cfg[section_key] = {}

        cfg[section_key].update(params)

        # optional: if you still want enabled for sections that get params
        cfg[section_key]["enabled"] = True

    try:
        latest.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write latest config: {e}")

    return {"config_id": latest.stem, "config": cfg}


#RIGHTS ROUTER - SAVE RIGHTS INTO CONFIG
class RightsPayload(BaseModel):
    rights_to_evaluate: List[str]

@rights_router.post("/rights/configs")
def save_rights(payload: RightsPayload):
    try:
        path = latest_config_path() #ADDED!!! (CONFIG_DIR)
        cfg = read_config(path)
    except FileNotFoundError:
        # create new config if none exists
        config_id = str(uuid.uuid4())
        path = CONFIG_DIR / f"{config_id}.json"
        cfg = {}

    cfg.setdefault("datasets", {})   #Generate first available 
    cfg.setdefault("metrics", {})
    cfg.setdefault("plugins", [])

    normalized_rights = [normalize_right(r) for r in payload.rights_to_evaluate] 
    cfg["rights_to_evaluate"] = normalized_rights


    write_config(path, cfg)
    registry_path = REGISTRY_DIR / "plugin_registry.json"

    result = capability_report(path, cfg, registry_path) #COMPARE PLUGIN REGISTRY WITH UPLOADED 
    return  result #all passed

