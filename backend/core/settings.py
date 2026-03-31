from pathlib import Path

#DIR where to save stuff 

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
CONFIG_DIR = STORAGE_DIR / "configs"
RESULTS_DIR = STORAGE_DIR / "results"
RUN_DIR = STORAGE_DIR / "runs"
REGISTRY_DIR = STORAGE_DIR / "summary"

def ensure_dirs() -> None:
    for d in (UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR, REGISTRY_DIR):
        d.mkdir(parents=True, exist_ok=True)

