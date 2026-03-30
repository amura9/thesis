#detect prefixes
#find prefixes
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import csv

def find_x_test_prefixed_columns(
    uploads_dir: str | Path,
    *,
    delimiter: str = "_",
    encoding: str = "utf-8",
    min_group_size: int = 2,
    recursive: bool = True,
) -> Dict[str, List[str]]:
    """
    Look in `uploads_dir` for a dataset file whose name contains 'X_test'.
    Read its header (column names). Group columns by prefix (before `delimiter`).
    Return only groups with at least `min_group_size` columns.

    Assumptions:
      - File is CSV-like (comma separated) with header in the first row.
      - Prefix rule: prefix = column_name.split(delimiter)[0]
        (e.g. race_Asian -> race)

    Returns:
      dict like {"race": ["race_Asian", "race_Black"], "sex": ["sex_F","sex_M"]}

    Raises:
      FileNotFoundError if no file with 'X_test' is found.
      ValueError if header cannot be read.
    """
    uploads_path = Path(uploads_dir)

    if not uploads_path.exists():
        raise FileNotFoundError(f"Uploads directory not found: {uploads_path}")

    # Find candidate files containing "X_test" (case-insensitive)
    pattern = "**/*" if recursive else "*"
    candidates = [
        p for p in uploads_path.glob(pattern)
        if p.is_file() and "x_test" in p.name.lower()
    ]

    if not candidates:
        raise FileNotFoundError(f"No file containing 'X_test' found in: {uploads_path}")

    # IF there is a .csv, it picks that one
    def score(p: Path) -> Tuple[int, int]:
        ext = p.suffix.lower()
        ext_score = 2 if ext in {".csv"} else 1 if ext in {".txt", ".tsv"} else 0
        # smaller file name length tie-breaker (often more canonical)
        return (ext_score, -len(p.name))

    best = sorted(candidates, key=score, reverse=True)[0]

    #Reads only the header
    try:
        with best.open("r", encoding=encoding, newline="") as f:
            reader = csv.reader(f,delimiter=";")
            header = next(reader, None)
            print(header)
    except UnicodeDecodeError:
        # Fallback to latin-1 if encoding mismatch
        with best.open("r", encoding="latin-1", newline="") as f:
            reader = csv.reader(f,delimiter=";")
            header = next(reader, None)

    if not header:
        raise ValueError(f"Could not read header row from file: {best}")

    # Normalize header cells
    columns = [str(c).strip() for c in header if str(c).strip() != ""]

    # Group by prefix
    groups: Dict[str, List[str]] = {}
    for col in columns:
        if delimiter not in col:
            continue
        prefix = col.split(delimiter, 1)[0].strip()
        if not prefix:
            continue
        groups.setdefault(prefix, []).append(col)

    # Filter by min_group_size
    groups = {p: cols for p, cols in groups.items() if len(cols) >= max(2, min_group_size)}

    return groups

def find_x_test_headers(
    uploads_dir: str | Path,
    encoding: str = "utf-8",
    recursive: bool = True,
    delimiters: tuple[str, ...] = (";", ",", "\t"),
) -> Dict[Path, List[str]]:
    """
    Look in `uploads_dir` for all dataset files whose name contains 'X_test'.
    Read only their header rows.

    Returns:
      dict mapping file paths to header lists, e.g.
      {
          Path("X_test.csv"): ["age", "sex_M", "sex_F"],
          Path("nested/X_test_v2.csv"): ["race_Asian", "race_Black"]
      }

    Raises:
      FileNotFoundError if no file with 'X_test' is found.
    """
    uploads_path = Path(uploads_dir)

    if not uploads_path.exists():
        raise FileNotFoundError(f"Uploads directory not found: {uploads_path}")

    pattern = "**/*" if recursive else "*"
    x_test_files = [
        p for p in uploads_path.glob(pattern)
        if p.is_file() and "x_test" in p.name.lower()
    ]

    if not x_test_files:
        raise FileNotFoundError(f"No file containing 'X_test' found in: {uploads_path}")

    headers: Dict[Path, List[str]] = {}

    for file_path in x_test_files:
        header = None

        for enc in (encoding, "latin-1"):
            try:
                with file_path.open("r", encoding=enc, newline="") as f:
                    first_line = f.readline()

                    # pick delimiter with most hits
                    delimiter = max(delimiters, key=lambda d: first_line.count(d))

                    f.seek(0)
                    reader = csv.reader(f, delimiter=delimiter)
                    header = next(reader, None)
                break
            except UnicodeDecodeError:
                continue

        if not header:
            continue

        headers[file_path] = [
            str(c).strip()
            for c in header
            if str(c).strip() != ""
        ]

    return headers

