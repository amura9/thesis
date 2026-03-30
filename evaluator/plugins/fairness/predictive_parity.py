from sklearn.metrics import precision_score
from fairlearn.metrics import MetricFrame
from core.plugin_registry import PluginSpec, ParamSpec


class PredictiveParity:
    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="predictive_parity",
            name="Predictive Parity",
            right="Fairness",
            description="Compares precision across sensitive groups (higher equality means smaller precision gap).",
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
        self.name = "Predictive Parity"
        self.needs_sensitive_feature = True
        self.requires_all_sensitive_features = False

    def evaluate(self, y_true, y_pred, X_test, sensitive_feature_names):
        results = {}

        for feature in sensitive_feature_names:
            if feature not in X_test.columns:
                raise ValueError(f"Feature '{feature}' not found in X_test.")

            sensitive_column = X_test[feature]

            metric_frame = MetricFrame(
                metrics=precision_score,
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sensitive_column,
            )

            #ADDED
            by_group_series = metric_frame.by_group
            precision_by_group = {str(k): float(v) for k, v in by_group_series.to_dict().items()}

            # Fairlearn returns numpy/pandas scalars -> cast to float
            precision_ratio = float(metric_frame.ratio())
            difference = float(metric_frame.difference())

            results[feature] = {
                #Summary metrics
                "metric": self.get_spec().name, #ADDED
                "status": "success",
                "sensitive_feature": feature,

                #Structured Results
                "precision_by_group": precision_by_group,
                "precision_ratio": precision_ratio,
                "difference": difference,
            }

        return results