from fairlearn.metrics import (selection_rate, MetricFrame) 
from core.plugin_registry import PluginSpec, ParamSpec
import numpy as np
import pandas as pd


class DisparateImpact:
    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="disparate_impact",
            name="Disparate Impact",
            right="Fairness",
            description="Disparate Impact based on selection rates across sensitive groups (min SR / max SR).",
            interpretation="Values near 1 indicates fairness, while values below 0.8 often signal potential discrimination.",
            requires=["X_test", "y_true", "y_pred"], #datasets
            
            #parameters specification
            params=[
                ParamSpec(
                    key="sensitive_features",
                    type="list[string]",
                    required=True,
                    default=None,
                    label="Sensitive features",
                    help="Select one or more sensitive feature columns (e.g., sex, age)."
                ),
            ],
        )

    def __init__(self):
        self.name = "Disparate Impact"
        self.needs_sensitive_feature = True
        self.requires_all_sensitive_features = False

    def evaluate(self, y_true, y_pred, X_test, sensitive_feature_names):
        results = {}
        
        for feature in sensitive_feature_names:
            if feature not in X_test.columns:
                raise ValueError(f"Feature '{feature}'  not found in X_test.")
            
            sensitive_column = X_test[feature]
            metric_frame = MetricFrame(
                metrics=selection_rate,
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sensitive_column
            )
            
            sr = metric_frame.by_group
            min_sr = sr.min()
            max_sr = sr.max()
            di =  min_sr / max_sr if max_sr != 0 else np.nan
            normalized_score = 1 - di
            
            results[feature] = {
                #Summary metrics
                "metric": self.get_spec().name,
                "status": "success",
                "sensitive_feature": feature,

                #Structured Results
                "selection_rates": sr.to_dict(),
                "disparate_impact": normalized_score .item()
            }
        
        return results