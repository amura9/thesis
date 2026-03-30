from fairlearn.metrics import MetricFrame, selection_rate
from core.load_config_value import get_config_value
from core.plugin_registry import PluginSpec, ParamSpec #added
import numpy as np
import pandas as pd

class ConditionalStatisticalParity:
    @classmethod
    def get_spec(cls):
        #plugin specifications
        return PluginSpec( 
            id="conditional_statistical_parity",
            name="Conditional Statistical Parity",
            right="Fairness",
            description="Measures disparity in selection rates across sensitive groups conditioned on another variable.",
            requires=["X_test", "y_pred"], #datasets

            #parameters specification
            params=[
                ParamSpec(
                    key="sensitive_features",
                    type="list[string]",
                    required=True,
                    default=None,
                    label="Sensitive features",
                    help="Select one or more sensitive feature columns (e.g., sex, age).",
                ),
                ParamSpec(
                    key="conditional_variable",
                    type="string",
                    required=True,
                    default=None,
                    label="Conditional variable",
                    help="Column name used to condition the fairness comparison.",
                ),
            ],
        )
    
    name = "conditional_statistical_parity"
    needs_sensitive_feature = True 
    needs_conditional_variable = True

    def __init__(self, config=None):
        self.config = config or {}

    def _to_1d_series(self, arr_like) -> pd.Series:
        """Ensure 1D alignment and reset the index."""
        s = pd.Series(arr_like)
        return s.reset_index(drop=True)

    def _binarize(self, s: pd.Series, threshold: float = 0.5) -> pd.Series:
        """Convert probabilities/continuous values to 0/1; if already binary, return as-is."""
        uniq = pd.unique(s.dropna())
        if set(uniq).issubset({0, 1}) or set(uniq).issubset({0.0, 1.0}):
            return s.astype(int)
        return (pd.to_numeric(s, errors="coerce").fillna(0.0) >= threshold).astype(int)

    def evaluate(self, y_true, y_pred, X_test, sensitive_feature, conditional_variable=None, **kwargs): #
        # 1) get conditional variable 
        conditional_variable = conditional_variable or get_config_value(
            self.config, "conditional_fairness", "conditional_variable", required=False
        )
        if not conditional_variable:
            return {
                "metric": self.get_spec().name,
                "status": "error",
                "sensitive_feature": sensitive_feature,
                "message": "Missing 'conditional_variable' in config.",
                "requested_columns": ["conditional_fairness.conditional_variable"]
                }

        # 2) column checks
        if sensitive_feature not in X_test.columns:
            return {
                "metric": self.get_spec().name,
                "status": "error",
                "sensitive_feature": sensitive_feature,
                "conditional_variable": conditional_variable,
                "requested_columns": [sensitive_feature],
                "available_columns": list(X_test.columns)
                }
    
        if conditional_variable not in X_test.columns:
            return {
                "metric": self.get_spec().name,
                "status": "error",
                "sensitive_feature": sensitive_feature,
                "conditional_variable": conditional_variable,
                "message": f"Conditional column '{conditional_variable}' not found.",
                "available_columns": list(X_test.columns),
                "requested_columns": [conditional_variable]
       }

        # 3) prepare data
        yp = self._to_1d_series(y_pred)
        yp_bin = self._binarize(yp, threshold=0.5)

        df = X_test[[sensitive_feature, conditional_variable]].copy().reset_index(drop=True)
        if df[sensitive_feature].dtypes == "object":
            df[sensitive_feature] = df[sensitive_feature].astype("string").str.strip()
        if df[conditional_variable].dtype == "object":
            df[conditional_variable] = df[conditional_variable].astype("string").str.strip()
        df[sensitive_feature] = df[sensitive_feature].fillna("__MISSING__")
        df[conditional_variable] = df[conditional_variable].fillna("__MISSING__")

        # 4) iterate Z = z
        out = {
            #Summary statistics
            "metric": self.get_spec().name,
            "status": "success",
            "conditional_variable": conditional_variable,
            "sensitive_feature": sensitive_feature,
            "conditions": {}, #double nesting
            "disparity_summary": {} #double nesting
        }

        total_n = len(df)
        raw_diffs, norm_scores, weights = [], [], []

        df["y_pred_bin"] = yp_bin

        for cond, cond_df in df.groupby(conditional_variable, dropna=False):
            n = len(cond_df)
            if n == 0:
                continue

            # IMPORTANT: pass predictions as both y_true and y_pred so selection_rate always works
            mf = MetricFrame(
                metrics=selection_rate,
                y_true=cond_df["y_pred_bin"],
                y_pred=cond_df["y_pred_bin"],
                sensitive_features=cond_df[sensitive_feature]
            )

            sr = mf.by_group  # group -> selection rate (0..1)
            if sr.empty:
                continue

            rates = sr.to_numpy(dtype=float)
            raw = float(np.max(rates) - np.min(rates))   # 0..1 gap (0 = perfect parity)
            norm = float(max(0.0, 1.0 - raw))            # 0..1 score (1 = perfect parity)
            w = n / total_n if total_n > 0 else 0.0

            raw_diffs.append(raw)
            norm_scores.append(norm)
            weights.append(w)

            selection_rates_dict = {str(k): float(v) for k, v in sr.to_dict().items()}

            out["conditions"][str(cond)] = {
                **selection_rates_dict,
                "raw_difference": raw,
                "normalized_score": norm,
                "weight": w,
                "total_samples": int(n)
            }

        # 5) summary
        if raw_diffs:
            out["disparity_summary"] = {
                # raw difference summary (flattened)
                "raw_average": float(np.average(raw_diffs, weights=weights)),
                "raw_max": float(np.max(raw_diffs)),
                "raw_min": float(np.min(raw_diffs)),

                # normalized score summary (flattened)
                "normalized_average": float(np.average(norm_scores, weights=weights)),
                "normalized_max": float(np.max(norm_scores)),
                "normalized_min": float(np.min(norm_scores)),

                # meta
                "processed_conditions": int(len(raw_diffs)),
                "total_samples": int(total_n),
            }
        else:
            out["message"] = "No valid conditions/groups to evaluate."
        
        # orchestrator contract
        return  out 
    