from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR #all the dir to be imported
from backend.services.config_services import latest_config_path, read_config, write_config
from backend.services.utils.prefixes_headers import find_x_test_prefixed_columns, find_x_test_headers
from backend.services.utils.detect_numerical_and_bin import detect_numerical_and_bin
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from backend.services.utils.csv_tools import load_dataframe
from backend.services.dataset_services import latest_main_ds_upload
from pydantic import BaseModel
from typing import List, Dict
import math
import traceback

router = APIRouter(tags=["postprocessing"])

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
    
#Get all headers for binning
@router.get("/inverse-encoding-prefixes")
def get_inverse_encoding_prefixes(recursive: bool = True):
    try:
        headers_map = find_x_test_headers(UPLOAD_DIR, recursive=recursive)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    #file
    groups = {str(path): cols for path, cols in headers_map.items()}

    #headers
    headers = sorted({c for cols in headers_map.values() for c in cols})
    
    return {"groups": groups, "prefixes": headers}

#post the features to recombine in the .json
@router.post("/config/inverse-encoding-prefixes")
def save_inverse_encoding_prefixes(payload: SelectedPrefixesPayload):
    path = latest_config_path(CONFIG_DIR)
    cfg = read_config(path)

    cfg.setdefault("postprocessing", {})
    cfg["postprocessing"].setdefault("binning", {})
    cfg["postprocessing"]["binning"].setdefault("features", {})

    cfg["postprocessing"]["inverse_encoding_prefixes"] = payload.selected_prefixes
    cfg["postprocessing"]["use_inverse_encoding"] = payload.recombine
    cfg["postprocessing"]["binning"]["use_binning"] = payload.binning

    write_config(path, cfg)

    return {"ok": True, "config_id": path.stem, "path": str(path)}

#get what is N distributed and based on this, propose equal width binning
def safe_ceil_int(x):
    if x is None:
        return None
    try:
        x = float(x)
        if math.isnan(x):
            return None
        return int(math.ceil(x))
    except Exception:
        return None

#Determine if feature is n-distributed
@router.get("/n-distrib")
def n_distrib():
    try:
        x_path = latest_main_ds_upload(UPLOAD_DIR)
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

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    
#post the bins in the .json
def edges_to_labels(edges: List[int]) -> List[str]:
    # edges: [16,25,35,45,55,100] -> ["16-25","26-35","36-45","46-55","56+"]
    if not edges or len(edges) < 2:
        return []
    labels = []
    for i in range(len(edges) - 1):
        start = edges[i] if i == 0 else edges[i] + 1
        end = edges[i + 1]
        is_last = i == len(edges) - 2
        labels.append(f"{start}+" if is_last else f"{start}-{end}")
    return labels

@router.post("/config/binning")
def save_binning(payload: BinningPayload):
    path = latest_config_path(CONFIG_DIR)
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





