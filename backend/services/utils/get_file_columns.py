from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR #all the dir to be imported
from backend.services.dataset_services import save_upload
from backend.services.config_services import latest_upload_for_type, get_config_id
from backend.services.utils.csv_tools import read_columns_from_file
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from pathlib import Path
import json
import uuid
import csv

#Get columns from the X_test
def get_file_columns():
    cfg_id = get_config_id()

    cfg_path = CONFIG_DIR / f"{cfg_id}.json"
    with cfg_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    x_test_path = config.get("datasets", {}).get("X_test")
    if not x_test_path:
        raise HTTPException(status_code=404, detail="X_test not found in config")

    filename = Path(x_test_path).name
    x_path = UPLOAD_DIR / filename

    #Read first line and return columns
    with x_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        first_line = f.readline()

    if not first_line.strip():
        raise HTTPException(status_code=400, detail="Empty file or missing header")

    delimiters = (";", ",", "\t")
    delim = max(delimiters, key=lambda d: first_line.count(d))

    # parse header safely
    header = next(csv.reader([first_line], delimiter=delim), [])
    cols = [c.strip() for c in header if c and c.strip()]

    return {"columns": cols, "path": str(x_path)}