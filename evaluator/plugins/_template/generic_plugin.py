from __future__ import annotations

from typing import Any, Dict, Optional
import pandas as pd

from core.plugin_registry import PluginSpec, ParamSpec
from core.load_config_value import get_config_value


class MyNewMetricPlugin:
    """
    Developer Template Plugin

    Fill in:
    - class name
    - name
    - get_spec() metadata + params
    - evaluate() logic
    """

    # This is what your orchestrator prints: "Running {plugin.name}"
    name = "my_new_metric_plugin"

    # Orchestrator capability flags (set what you need)
    needs_X = True
    needs_y_true = False
    needs_y_pred = False

    # Choose ONE pattern:
    needs_sensitive_feature = False          # evaluate called per sensitive feature
    requires_all_sensitive_features = False  # evaluate called once with list of sensitive features

    # Optional extra pattern
    needs_conditional_variable = False

    @classmethod
    def get_spec(cls) -> PluginSpec:
        return PluginSpec(
            id="my_new_metric_plugin",
            name="My New Metric Plugin",
            right="Fairness",  # or "Privacy", etc.
            description="Explain what this metric does in one sentence.",
            requires=["X_test"],  # add "y_true" / "y_pred" if used
            params=[
                ParamSpec(
                    key="some_param",
                    type="float",
                    required=False,
                    default=0.5,
                    label="Some parameter",
                    help="Explain what this parameter changes.",
                ),
                # ParamSpec(...),
            ],
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # OPTIONAL: read params from config (recommended)
        self.some_param = get_config_value(
            self.config,
            "my_new_metric_plugin",
            "some_param",
            default=0.5,
            required=False,
        )

    def evaluate(
        self,
        y_true: Optional[pd.Series] = None,
        y_pred: Optional[pd.Series] = None,
        X_test: Optional[pd.DataFrame] = None,
        sensitive_feature: Optional[str] = None,
        sensitive_features: Optional[list[str]] = None,
        conditional_variable: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Return a JSON-serializable dict.
        Use:
          - "status": "success" or "error"
          - include "metric": self.get_spec().name for consistency
        """
        try:
            # --- Validate inputs (simple examples) ---
            if self.needs_X and X_test is None:
                return {
                    "metric": self.get_spec().name,
                    "status": "error",
                    "message": "Missing X_test.",
                }

            # If per-sensitive-feature
            if self.needs_sensitive_feature:
                if not sensitive_feature:
                    return {
                        "metric": self.get_spec().name,
                        "status": "error",
                        "message": "Missing sensitive_feature.",
                    }
                if sensitive_feature not in X_test.columns:
                    return {
                        "metric": self.get_spec().name,
                        "status": "error",
                        "message": f"Sensitive column '{sensitive_feature}' not found.",
                        "available_columns": list(X_test.columns),
                    }

            # If all-sensitive-features-at-once
            if self.requires_all_sensitive_features:
                if not sensitive_features:
                    return {
                        "metric": self.get_spec().name,
                        "status": "error",
                        "message": "Missing sensitive_features list.",
                    }
                missing = [c for c in sensitive_features if c not in X_test.columns]
                if missing:
                    return {
                        "metric": self.get_spec().name,
                        "status": "error",
                        "message": f"Missing columns: {', '.join(missing)}",
                    }

            # Optional conditional variable
            if self.needs_conditional_variable and not conditional_variable:
                return {
                    "metric": self.get_spec().name,
                    "status": "error",
                    "message": "Missing conditional_variable.",
                }

            # --- Implement your metric logic here ---
            # Example dummy score:
            score_value = 0.123

            return {
                "metric": self.get_spec().name,
                "status": "success",
                "value": float(score_value),

                # optional metadata:
                "sensitive_feature": sensitive_feature,
                "conditional_variable": conditional_variable,
                "params_used": {
                    "some_param": self.some_param,
                },
            }

        except Exception as e:
            return {
                "metric": self.get_spec().name,
                "status": "error",
                "message": f"Error during computation: {str(e)}",
            }