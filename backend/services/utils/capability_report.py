from backend.services.config_services import attach_uploads_to_config, latest_config_path, read_config, write_config, deep_merge
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

def capability_report(path: Path, cfg: Dict[str, Any], registry_path: Path) -> Dict[str, Any]:
    """
    Build a capability report by reading plugin_registry.json and checking:
      - selected rights (cfg["rights_to_evaluate"])
      - uploaded datasets (cfg["datasets"])
      - each plugin's "requires" list
    """

    # 1) Load plugin registry
    if not registry_path.exists():
        raise FileNotFoundError(f"Plugin registry not found: {registry_path}")

    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    # 2) Load datasets
    datasets = cfg.get("datasets", {}) or {}
    available_inputs = {k for k, v in datasets.items() if v}

    # 3) Filter plugins by selected rights
    selected_rights = set(cfg.get("rights_to_evaluate", []) or [])

    metric_requirements: Dict[str, Any] = {}
    metrics_by_right: Dict[str, List[str]] = {r: [] for r in selected_rights}

    # 4) Compute computability flag
    for plugin_id, spec in registry.items():
        right_raw = spec.get("right")
        right = normalize_right(right_raw) if right_raw else None
        if not right or right not in selected_rights:
            continue

        requires = spec.get("requires", []) or [] #get required datasets

        #if not in datasets, then not computable
        missing = [req for req in requires if req not in available_inputs]

        computable = len(missing) == 0

        metric_requirements[plugin_id] = {
            "name": spec.get("name"),
            "right": right,
            "selected_right": right_raw,
            "required_inputs": requires,
            "available_inputs": sorted(list(available_inputs)),
            "missing_inputs": missing,
            "computable": computable,
        }

        if right in metrics_by_right:
            metrics_by_right[right].append(plugin_id)

    # 5) Store in config (optional but useful)
    cfg["metric_requirements"] = metric_requirements
    cfg["metrics_by_right"] = metrics_by_right

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

#Little helper
def normalize_right(value: str) -> str:
    """
    Convert right label to machine format:
    - lowercase
    - spaces -> underscore
    - collapse multiple underscores
    - remove leading/trailing underscores
    """
    s = (value or "").strip().lower()
    s = re.sub(r"\s+", "_", s)          # spaces -> underscore
    s = re.sub(r"_+", "_", s)           # collapse multiple _
    s = re.sub(r"[^a-z0-9_]", "", s)    # remove other chars (optional but safe)
    return s.strip("_")
