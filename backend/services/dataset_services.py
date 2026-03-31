from pathlib import Path
from fastapi import UploadFile, HTTPException

#DS SAVE IN UPLOAD
def save_upload(upload_file: UploadFile, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with dest_path.open("wb") as f:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

#LATEST DS UPLOAD -> (UPLOAD_DIR, X_TEST)
def latest_upload_for_type(upload_dir: Path, dataset_type: str) -> Path | None:
    files = [p for p in upload_dir.glob(f"{dataset_type}__*") if p.is_file()]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None

def latest_upload_matching(upload_dir: Path, predicate) -> Path:
    files = [p for p in upload_dir.glob("*__*") if p.is_file() and predicate(p.name.lower())]
    if not files:
        raise HTTPException(status_code=404, detail="Required dataset upload not found")
    return max(files, key=lambda p: p.stat().st_mtime)












