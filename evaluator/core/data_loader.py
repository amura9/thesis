import pandas as pd
import pickle
from pathlib import Path


def _read_csv_robust(path: str) -> pd.DataFrame:
    """
    Try multiple strategies to load CSV safely.
    """

    # 1) Default comma
    try:
        return pd.read_csv(path)
    except pd.errors.ParserError:
        pass

    # 2) Try semicolon separator (very common in EU exports)
    try:
        return pd.read_csv(path, sep=";")
    except pd.errors.ParserError:
        pass

    # 3) Fallback to python engine (more tolerant)
    try:
        return pd.read_csv(path, engine="python")
    except Exception as e:
        raise RuntimeError(f"Failed to parse CSV file: {path}\n{e}")


def load_dataset(path):
    if path is None:
        return None

    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    # Pickle support
    if path.endswith(('.pkl', '.pickle')):
        return pd.read_pickle(path)

    # Default: CSV (robust)
    return _read_csv_robust(path)

