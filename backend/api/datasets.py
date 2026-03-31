from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR #all the dir to be imported
from backend.services.dataset_services import save_upload
from backend.services.config_services import latest_upload_for_type
from backend.services.utils.csv_tools import read_columns_from_file
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from pathlib import Path
import uuid
import csv

router = APIRouter(tags=["datasets"])

#Save datasets in UPLOADS with following path: {dataset_type}__{dataset_id}__{safe_name}
@router.post("/datasets")
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_type: str = Form(...),     
):
    dataset_id = str(uuid.uuid4())
    safe_name = file.filename.replace("/", "_").replace("\\", "_")

    path = UPLOAD_DIR / f"{dataset_type}__{dataset_id}__{safe_name}"

    save_upload(file, path)

    return {
        "dataset_id": dataset_id,
        "filename": safe_name,
        "dataset_type": dataset_type,
        "path": str(path.resolve()),
    }

#GET: columns to be used for sensitive features selection
@router.get("/datasets/latest/columns")
def latest_columns():
    x_path = latest_upload_for_type(UPLOAD_DIR, "X_test") 
    if not x_path or not Path(x_path).exists():
        raise HTTPException(status_code=404, detail="No X_test uploaded")

    x_path = Path(x_path)

    # read ONLY first line, detect delimiter
    with x_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        first_line = f.readline()

    if not first_line.strip():
        raise HTTPException(status_code=400, detail="Empty file or missing header")

    delimiters = (";", ",", "\t")
    delim = max(delimiters, key=lambda d: first_line.count(d))

    # parse header safely
    header = next(csv.reader([first_line], delimiter=delim), [])
    cols = [c.strip() for c in header if c and c.strip()]

    return {"columns": cols, "delimiter": delim, "path": str(x_path)}









