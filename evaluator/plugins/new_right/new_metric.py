from typing import Any, Dict, Optional

import pandas as pd
import numpy as np

from core.plugin_registry import PluginSpec, ParamSpec

class FakeRightExample:

    
    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="new_metric",
            name="New Metric",
            right="New Right",
            description="New metric used to test parameters: uses first numeric column in Test Dataset",
            requires=["X_test"],  #datasets

            #parameters specification
            params=[
                ParamSpec(
                    key="threshold",
                    type="float",
                    required=True,
                    default=None,
                    label="Threshold",
                    help="If computed value > threshold, return threshold; otherwise return computed value.",
                    enum=None,
                ),
            ],
        )
    
    needs_sensitive_feature = False
    requires_all_sensitive_features = False

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.name = "New Metric Example"

    def evaluate(self, y_true=None, y_pred=None, X_test=None, sensitive_feature_names=None) -> Dict[str, Any]:
        # X_test to be provided
        if X_test is None:
            return {"status": "error", "message": "Test Dataset is required but was not provided."}
        if not isinstance(X_test, pd.DataFrame):
            return {"status": "error", "message": "Test Dataset must be a pandas DataFrame."}
        if X_test.empty:
            return {"status": "error", "message": "Test Dataset is empty."}

        # check threshold from config (stored under the plugin id section)
        threshold = None
        if isinstance(self.config, dict):
            plugin_id = self.get_spec().id
            section = self.config.get(plugin_id)  

            if isinstance(section, dict):
                threshold = section.get("threshold")

            # optional fallback (if you ever support flat config {"threshold": ...})
            if threshold is None:
                threshold = self.config.get("threshold")


        if threshold is None:
            return {"status": "error", "message": "Missing required parameter: threshold"}
        try:
            threshold = float(threshold)
        except Exception:
            return {"status": "error", "message": f"Invalid threshold (must be numeric): {threshold!r}"}

        # Pick the first numeric column
        numeric_cols = list(X_test.select_dtypes(include=[np.number]).columns)
        if not numeric_cols:
            return {"status": "error", "message": "No numeric columns found in X_test."}

        col = numeric_cols[0]
        series = pd.to_numeric(X_test[col], errors="coerce").dropna()
        if series.empty:
            return {"status": "error", "message": f"Numeric column '{col}' has no valid numeric values."}

        mean_val = float(series.mean())
        median_val = float(series.median())

        # Compute value: if mean > median => mean/median else median/mean (safe division)
        eps = 1e-12
        if mean_val > median_val:
            computed = mean_val / (median_val if abs(median_val) > eps else eps)
            rule = "mean/median"
        else:
            computed = median_val / (mean_val if abs(mean_val) > eps else eps)
            rule = "median/mean"

        # Apply threshold rule: if computed > threshold => return threshold else return computed
        final_value = computed if computed <= threshold else threshold

        return {
            "status": "success",
            "metric": "New Metric",
            "used_column": col,
            "mean": mean_val,
            "median": median_val,
            "ratio_rule": rule,
            "computed": computed,
            "threshold": threshold,
            "result": final_value,
            "final_score": (10*final_value),
        }
