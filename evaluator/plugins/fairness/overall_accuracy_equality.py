from sklearn.metrics import accuracy_score
from fairlearn.metrics import MetricFrame
from core.plugin_registry import PluginSpec, ParamSpec


class OverallAccuracyEquality:
    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="overall_accuracy_equality",
            name="Overall Accuracy Equality",
            right="Fairness",
            description="Compares accuracy across sensitive groups and reports difference/ratio (higher equality_score is better).",
            interpretation="Values close to 0 indicate uniform predictive performance.",
            requires=["X_test", "y_true", "y_pred"],  # datasets
            params=[
                ParamSpec(
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
        self.name = "Overall Accuracy Equality"
        self.needs_sensitive_feature = True
        self.requires_all_sensitive_features = False

    def evaluate(self, y_true, y_pred, X_test, sensitive_feature_names):
        results = {}

        for feature in sensitive_feature_names:
            if feature not in X_test.columns:
                raise ValueError(f"Feature '{feature}' not found in X_test.")

            metric_frame = MetricFrame(
                metrics=accuracy_score,
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=X_test[feature],
            )

            #ADDED
            by_group_series = metric_frame.by_group
            accuracy_by_group = {str(k): float(v) for k, v in by_group_series.to_dict().items()}

            #ADDED
            accuracy_ratio = float(metric_frame.ratio())
            difference = float(metric_frame.difference())
            equality_score = float(1.0 - difference)

            results[feature] = {
                #Summary Metrics
                "metric": self.get_spec().name,
                "status": "success",
                "sensitive_feature": feature,

                #Structured Results
                "accuracy_by_group": accuracy_by_group,
                "accuracy_ratio": accuracy_ratio,
                "difference": difference,
                "equality_score": equality_score,
            }

        return results