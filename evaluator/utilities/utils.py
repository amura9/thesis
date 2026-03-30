#core/utils.py

import importlib
import numpy as np
import pandas as pd

def import_from_path(path):
    module_path, class_name = path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)

def to_series_1d(y: object) -> pd.Series: #convert the y_pred, y_test if provided 
    """Convert any input (DataFrame, Series, ndarray, list) into a 1D pandas Series."""
    if isinstance(y, pd.DataFrame):
        if y.shape[1] != 1:
            raise ValueError(f"Expected 1 column for y, found {y.shape[1]}")
        y = y.iloc[:, 0] #into array
        return y.reset_index(drop=True)

    if isinstance(y, pd.Series):
        return y.reset_index(drop=True)

    if isinstance(y, np.ndarray):
        return pd.Series(np.ravel(y)).reset_index(drop=True)

    return pd.Series(y).reset_index(drop=True)

def sanitize_sensitive_col(s: pd.Series) -> pd.Series:
    """Normalize sensitive columns (strings/NaN/interval) for use with fairlearn."""
    if pd.api.types.is_interval_dtype(s):
        s = s.astype(str)

    if s.dtype == "object" or pd.api.types.is_categorical_dtype(s) or pd.api.types.is_string_dtype(s):
        return s.astype("string").fillna("__MISSING__")

    if pd.api.types.is_numeric_dtype(s):
        return s.fillna(-1)  # or keep NaN if you want to distinguish them

    return s.astype("string").fillna("__MISSING__")

#export all results to json
def export_all_results_to_json(all_results: dict, out_json: str = "run_results/all_results.json") -> str:
    out_path = Path(out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(out_path)
