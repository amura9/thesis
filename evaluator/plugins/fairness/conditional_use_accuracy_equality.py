from core.plugin_registry import PluginSpec, ParamSpec
from sklearn.metrics import accuracy_score
from fairlearn.metrics import MetricFrame
import pandas as pd


class ConditionalUseAccuracyEquality:
    @classmethod
    def get_spec(cls):
        return PluginSpec( #Plugin specs
            id="conditional_use_accuracy_equality",
            name="Conditional Use Accuracy Equality",
            right="Fairness",
            description="Accuracy parity across sensitive groups, computed only on samples with positive predictions (ŷ=1).",
            requires=["X_test", "y_true", "y_pred"],  
            params=[
                ParamSpec( #Parameters specs
                    key="sensitive_features",
                    type="list[string]",
                    required=True,
                    default=None,
                    label="Sensitive features",
                    help="Select one or more sensitive feature columns (e.g., sex, age).",
                ),
            ],
        )

    def __init__(self):
        self.name = "Conditional Use Accuracy Equality"
        self.needs_sensitive_feature = True
        self.needs_conditional_variable = False
        self.requires_all_sensitive_features = False

    def evaluate(self, y_true, y_pred, X_test, sensitive_features):
        results = {}

        # Convert to Series and align indices
        y_true = pd.Series(y_true).reset_index(drop=True)
        y_pred = pd.Series(y_pred).reset_index(drop=True)
        X_test = X_test.reset_index(drop=True)

        # Keep only positive predictions (ŷ = 1)
        positive_mask = y_pred == 1
        y_true_pos = y_true[positive_mask]
        y_pred_pos = y_pred[positive_mask]
        X_pos = X_test.loc[positive_mask]

        for feature in sensitive_features:
            try:
                if feature not in X_pos.columns:
                    raise ValueError(f"Feature '{feature}' not found in the dataset after filtering positives.")

                metric_frame = MetricFrame(
                    metrics=accuracy_score,
                    y_true=y_true_pos,
                    y_pred=y_pred_pos,
                    sensitive_features=X_pos[feature],
                )

                by_group = metric_frame.by_group  # pandas Series
                by_group_dict = {str(k): float(v) for k, v in by_group.to_dict().items()}

                diff = float(by_group.max() - by_group.min()) if len(by_group) else 0.0
                normalized_score = float(1.0 - diff)

                results[feature] = {
                    #Summary Metrics
                    "metric": self.get_spec().name,
                    "status": "success",
                    "sensitive_feature": feature,

                    #Structured Results
                    "accuracy_by_group": by_group_dict,
                    "difference": diff,
                    "normalized_score": normalized_score,
                }

            except Exception as e:
                results[feature] = {
                    "metric": self.get_spec().name,
                    "status": "error",
                    "sensitive_feature": feature,
                    "message": str(e),
                }

        return results