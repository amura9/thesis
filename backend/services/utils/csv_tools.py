from pathlib import Path
import csv
import pandas as pd
from fastapi import HTTPException

#get sensitive features
def read_columns_from_file(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".csv": #either csv
        df = pd.read_csv(path, nrows=0) #or excel 
    elif suffix in (".xlsx", ".xls", ".xlsm", ".xlsb"):
        df = pd.read_excel(path, nrows=0)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
    return [str(c) for c in df.columns.tolist()]

def load_dataframe(path: str | Path, *, encoding: str = "utf-8"):
    path = Path(path)

    # Try a couple encodings if needed
    for enc in (encoding, "latin-1"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                sample = f.read(4096)
                f.seek(0)

                # Detect delimiter from sample
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
                    sep = dialect.delimiter
                except Exception:
                    # Fallback: choose delimiter with most occurrences in first line
                    first_line = sample.splitlines()[0] if sample else ""
                    sep = max([";", ",", "\t"], key=lambda d: first_line.count(d))

            # Now read with detected delimiter
            return pd.read_csv(path, sep=sep, encoding=enc)
        except UnicodeDecodeError:
            continue

    # If we get here, encoding is the problem
    raise ValueError(f"Could not decode CSV file: {path}")
