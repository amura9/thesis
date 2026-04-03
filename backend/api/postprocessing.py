from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR #all the dir to be imported
from backend.services.config_services import latest_config_path, read_config, write_config
from backend.services.utils.find_headers import detect_headers
from backend.services.utils.detect_numerical_and_bin import detect_numerical_and_bin, safe_ceil_int, edges_to_labels
from backend.services.utils.get_file_columns import get_file_columns
from fastapi import APIRouter, HTTPException
from backend.services.utils.csv_tools import load_dataframe
from backend.services.dataset_services import latest_upload_for_type
from pydantic import BaseModel
from typing import List, Dict
import traceback

router = APIRouter(tags=["postprocessing"])

#Postprocessing payload
class RunIn(BaseModel):
    dataset_id: str
    config_id: str

class SelectedPrefixesPayload(BaseModel):
    selected_prefixes: List[str]
    recombine: bool
    binning: bool

class BinningPayload(BaseModel):
    use_binning: bool = True
    bins: Dict[str, List[int]]  # feature -> edges
    
#GET headers for postprocessing
@router.get("/postprocessing/headers")
def latest_columns():
    result = get_file_columns()

    return {"columns": result["columns"]} 

#GET n-distributed numerical features
@router.get("/n-distrib")
def n_distrib():
    try:
        x_path = latest_upload_for_type(UPLOAD_DIR, "X_test")
        print("X_test used:", x_path)

        df = load_dataframe(x_path)
        results = detect_numerical_and_bin(df=df)

        extracted = {}
        for col, info in results.items():
            r = info.get("range")
            min_v = r[0] if isinstance(r, (list, tuple)) and len(r) >= 2 else None
            max_v = r[1] if isinstance(r, (list, tuple)) and len(r) >= 2 else None

            if info.get("is_normal") and isinstance(info.get("binning"), dict):
                edges = info["binning"].get("edges") or []
                extracted[col] = [v for v in (safe_ceil_int(e) for e in edges) if v is not None]
            else:
                a = safe_ceil_int(min_v)
                b = safe_ceil_int(max_v)
                extracted[col] = [v for v in (a, b) if v is not None]

        return extracted

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

#################################

#POST: inverse encoding + binning
@router.post("/config/inverse-encoding-prefixes")
def save_inverse_encoding_prefixes(payload: SelectedPrefixesPayload):
    path = latest_config_path()
    cfg = read_config(path)

    cfg.setdefault("postprocessing", {})
    cfg["postprocessing"].setdefault("binning", {})
    cfg["postprocessing"]["binning"].setdefault("features", {})

    cfg["postprocessing"]["inverse_encoding_prefixes"] = payload.selected_prefixes
    cfg["postprocessing"]["use_inverse_encoding"] = payload.recombine
    cfg["postprocessing"]["binning"]["use_binning"] = payload.binning

    write_config(path, cfg)

    return {"ok": True, "config_id": path.stem, "path": str(path)}

#POST: defined bins
@router.post("/config/binning")
def save_binning(payload: BinningPayload):
    path = latest_config_path()
    cfg = read_config(path)

    cfg.setdefault("postprocessing", {})
    cfg["postprocessing"].setdefault("binning", {})
    cfg["postprocessing"]["binning"]["use_binning"] = bool(payload.use_binning)

    features_out: Dict[str, dict] = {}

    for feat, edges in (payload.bins or {}).items():
        if not edges:
            continue
        try:
            arr = sorted({int(e) for e in edges})
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid edges for feature '{feat}'")

        if len(arr) < 2:
            continue

        features_out[feat] = {
            "bins": arr,
            "labels": edges_to_labels(arr),
        }

    cfg["postprocessing"]["binning"]["features"] = features_out

    write_config(path, cfg)
    return {"ok": True, "config_id": path.stem, "path": str(path)}





