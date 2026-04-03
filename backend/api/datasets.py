from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR #all the dir to be imported
from backend.services.dataset_services import save_upload, delete_existing_uploads
from backend.services.config_services import latest_upload_for_type, get_config_id
from backend.services.utils.get_file_columns import get_file_columns
from backend.services.utils.csv_tools import read_columns_from_file
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from pathlib import Path
import json
import uuid
import csv

router = APIRouter(tags=["datasets"])

#Save datasets in UPLOADS with following path: {dataset_type}__{cfg_id}__{safe_name}
@router.post("/datasets")
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_type: str = Form(...),):
    cfg_id = get_config_id() 
    safe_name = file.filename.replace("/", "_").replace("\\", "_")

    # keep only one file for each dataset_type
    delete_existing_uploads(dataset_type)

    path = UPLOAD_DIR / f"{dataset_type}__{cfg_id}__{safe_name}"

    save_upload(file, path)

    return {
        "filename": safe_name,
        "dataset_type": dataset_type,
        "path": str(path.resolve()),
    }

#GET: if files already uploaded, keep them (when go Back), else if upload new ones, overwrite them
@router.get("/datasets/latest-status")
def latest_status():
    cfg = get_config_id()

    dataset_types = ["X_test", "y_true", "y_pred", "train", "model"]
    result = {}

    for ds_type in dataset_types:
        files = sorted(
            UPLOAD_DIR.glob(f"{ds_type}__{cfg}__*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if files:
            file_name = files[0].name.split("__")[-1]

            if ds_type == "X_test":
                result[ds_type] = {
                    "ok": True,
                    "filename": file_name,
                }
            else:
                result[ds_type] = {
                    "filename": file_name,
                }

        else:
            if ds_type == "X_test":
                result[ds_type] = {
                    "ok": False,
                    "filename": "",
                }
            else:
                result[ds_type] = {
                    "filename": "",
                }

    return result

#GET: headers for sensitive features
@router.get("/headers")
def latest_columns():
    result = get_file_columns()

    return {"columns": result["columns"]}










