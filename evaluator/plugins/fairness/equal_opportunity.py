from fairlearn.metrics import (true_positive_rate_difference, true_positive_rate, MetricFrame) 
from core.plugin_registry import PluginSpec, ParamSpec


class EqualOpportunity:
    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="equal_opportunity",
            name="Equal Opportunity",
            right="Fairness",
            description="Measures Equal Opportunity by comparing True Positive Rates across sensitive groups.",
            interpretation="Values close to 0 means equal opportunity is preserved.",
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
            ]
        )
    def __init__(self):
        self.name = "Equal Opportunity"
        self.needs_sensitive_feature = True
        self.requires_all_sensitive_features = False

    def evaluate(self, y_true, y_pred, X_test, sensitive_feature_names):
        results = {}
        
        for feature in sensitive_feature_names:
            if feature not in X_test.columns:
                raise ValueError(f"Feature '{feature}'  not found in X_test.")
            
            sensitive_column = X_test[feature]
            eo_diff = true_positive_rate_difference(
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sensitive_column
            )
            
            metric_frame = MetricFrame(
                metrics={"TPR": true_positive_rate},
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sensitive_column
            )

            normalized_score= 1 - eo_diff
            
            results[feature] = {
                #Summary metrics
                "metric": self.get_spec().name,
                "status": "success",
                "sensitive_feature": feature,

                #Structured Results
                "tpr_by_group": metric_frame.by_group["TPR"].to_dict(),
                "difference": normalized_score.item()
            }
        
        return results