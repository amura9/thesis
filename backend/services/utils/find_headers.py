#detect prefixes
#find prefixes
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import csv

#Get headers from file in UPLOAD_DIR
def detect_headers(
    uploads_dir: str | Path,
    encoding: str = "utf-8",
    recursive: bool = True,
    delimiters: tuple[str, ...] = (";", ",", "\t"),
) -> Dict[Path, List[str]]:
    uploads_path = Path(uploads_dir)

    if not uploads_path.exists():
        raise FileNotFoundError(f"Uploads directory not found: {uploads_path}")

    pattern = "**/*" if recursive else "*"
    x_test_files = [
        p for p in uploads_path.glob(pattern)
        if p.is_file() and "x_test" in p.name.lower()
    ]

    if not x_test_files:
        raise FileNotFoundError(f"No Main Dataset found: {uploads_path}")

    def read_header(file_path: Path) -> List[str] | None:
        for enc in (encoding, "latin-1"):
            try:
                with file_path.open("r", encoding=enc, newline="") as f:
                    first_line = f.readline()
                    delimiter = max(delimiters, key=first_line.count)

                    f.seek(0)
                    reader = csv.reader(f, delimiter=delimiter)
                    header = next(reader, None)

                if header:
                    return [str(col).strip() for col in header if str(col).strip()]
                return None
            except UnicodeDecodeError:
                continue
        return None

    return {
        file_path: header
        for file_path in x_test_files
        if (header := read_header(file_path)) is not None
    }
