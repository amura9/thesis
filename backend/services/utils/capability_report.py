from backend.services.config_services import normalize_key
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR,REGISTRY_DIR
from backend.schemas.config import ConfigIn
from pydantic import BaseModel
from typing import Any, List, Dict, Optional
from pathlib import Path
import uuid
import json
import re

router = APIRouter(tags=["rights"])

def capability_report(path: Path, cfg: Dict[str, Any], registry_path: Path) -> Dict[str, Any]: #
    """
    Build capability report comparing:
        - selected rights (cfg["rights_to_evaluate"])
        - uploaded datasets(cfg["datasets"])
        - with plugin_registry (requires)
    """
    if not registry_path.exists():
        raise FileNotFoundError(f"Plugin registry not found: {registry_path}")

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    datasets = cfg.get("datasets", {}) or {}
    available_inputs = {k for k, v in datasets.items() if v}

    selected_rights = set(cfg.get("rights_to_evaluate", []) or [])

    metric_requirements: Dict[str, Any] = {}
    metrics_by_right: Dict[str, List[str]] = {r: [] for r in selected_rights}

    #Define what is computable, if not computable -> report dataset needed
    for plugin_id, spec in registry.items():
        right_raw = spec.get("right")
        right = normalize_key(right_raw) if right_raw else None
        if not right or right not in selected_rights:
            continue

        requires = spec.get("requires", []) or [] 
        missing = [req for req in requires if req not in available_inputs]
        computable = len(missing) == 0

        metric_requirements[plugin_id] = {
            "name": spec.get("name"),
            "right": right,
            "selected_right": right_raw,
            "required_inputs": requires,
            "available_inputs": sorted(list(available_inputs)),
            "missing_inputs": missing,
            "computable": computable, #computable flag
        }

        if right in metrics_by_right:
            metrics_by_right[right].append(plugin_id)

    #Stores requirements per metrics and computability flag
    cfg["metric_requirements"] = metric_requirements
    cfg["metrics_by_right"] = metrics_by_right #used to display the metrics (greyed out) and the missing inputs for its computation

    # write config update
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "config_id": path.stem,
        "path": str(path),
        "selected_rights": sorted(list(selected_rights)),
        "available_inputs": sorted(list(available_inputs)),
        "metrics_by_right": metrics_by_right,
        "metric_requirements": metric_requirements,
    }


