from backend.services.dataset_services import latest_upload_for_type, latest_upload_matching
from backend.services.metrics_services import compute_metrics, metrics_to_plugins
from backend.core.settings import CONFIG_DIR
from pathlib import Path
from fastapi import HTTPException
import json

#SAVES UPLOADED FILES IN CONFIG WITH ABSOLUTE PATH
def attach_uploads_to_config(cfg_path: Path, upload_dir: Path) -> None:

    #get latest uploaded files from UPLOADS
    x_test = latest_upload_for_type(upload_dir, "X_test")
    y_true = latest_upload_for_type(upload_dir, "y_true")
    y_pred = latest_upload_for_type(upload_dir, "y_pred")
    train = latest_upload_for_type(upload_dir, "train")
    model = latest_upload_for_type(upload_dir, "model")

    #minimum attachable files
    if x_test is None:
        raise HTTPException(
            status_code=400,
            detail="Missing required upload: Main Dataset",
        )

    cfg = read_config(cfg_path)
    cfg.setdefault("datasets", {})
    cfg.setdefault("model", {})

    #store absolute path (minimum dataset)
    cfg["datasets"]["X_test"] = str(x_test.resolve())


    #save absolute paths -> OPTIONAL
    if y_true is not None:
        cfg["datasets"]["y_true"] = str(y_true.resolve())

    if y_pred is not None:
        cfg["datasets"]["y_pred"] = str(y_pred.resolve())

    if train is not None:
        cfg["datasets"]["train"] = str(train.resolve())

    if model is not None:
        cfg["model"]["path"] = str(model.resolve())

    write_config(cfg_path, cfg)

#Load lastest config file
def latest_config_path():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_files = list(CONFIG_DIR.glob("*.json"))
    if not config_files:
        raise HTTPException(status_code=404, detail="No configs found")
    return max(config_files, key=lambda p: p.stat().st_mtime)








    


def read_config(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {e}")
    
#WRITE CONFIG
def write_config(path: Path, cfg: dict) -> None:
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

