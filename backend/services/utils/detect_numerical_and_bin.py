import math 
import numpy as np
import pandas as pd
from scipy.stats import shapiro

#remove float for binning
def safe_ceil_int(x):
    if x is None:
        return None
    try:
        x = float(x)
        if math.isnan(x):
            return None
        return int(math.ceil(x))
    except Exception:
        return None


#returns numerical features only if contain more than 3 different values
def detect_numerical_and_bin(
    df: pd.DataFrame,
    bins: int = 10,
    alpha: float = 0.05,
):
    """
    Check each numeric column for normality (QQ-plot proxy via Shapiro-Wilk).
    If normal, suggest Equal-Width Binning.

    Returns a dict keyed by column name.
    """

    results = {}

    for col in df.columns:
        series = df[col]

        # Only numeric columns
        if not pd.api.types.is_numeric_dtype(series):
            continue

        # Drop NaNs
        clean = series.dropna()

        #skip boolean
        u = clean.unique()
        if len(u) <= 3:
            continue


        # Shapiro-Wilk (QQ-plot statistical proxy)
        stat, p_value = shapiro(clean.sample(
            min(len(clean), 5000), random_state=42
        ))

        is_normal = p_value >= alpha

        result = {
            "is_normal": is_normal,
            "shapiro_p_value": float(p_value),
        }

        #pick min and max values
        min_val = clean.min()
        max_val = clean.max()
        result["range"] = [float(min_val), float(max_val)]

        # Suggest Equal-Width Binning if normal
        if is_normal:
            min_val = clean.min()
            max_val = clean.max()
            width = (max_val - min_val) / bins

            bin_edges = np.linspace(min_val, max_val, bins + 1)

            result["binning"] = {
                "type": "equal_width",
                "bins": bins,
                "range": [float(min_val), float(max_val)],
                "bin_width": float(width),
                "edges": bin_edges.tolist(),
            }

        results[col] = result
    return results
