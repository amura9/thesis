from sklearn.metrics import precision_score
from fairlearn.metrics import MetricFrame
from core.plugin_registry import PluginSpec, ParamSpec

class GDPRRightExample:
    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="gdpr_right_example",
            name="GDPR Right Example",
            right="GDPR Right",
            description="Analysis of the right for GDPR",
            requires=["X_test", "y_true", "y_pred", "other_dataset"], #datasets

            #parameters specification
            params=[
                ParamSpec(
                    key="explainable_parameter",
                    type="list[string]",
                    required=True,
                    default=None,
                    label="Explainable parameter",
                    help="Select one or more explainable parameters"
                ),
            ],
        )
    
    def __init__(self):
        self.name = "Predictive Parity"
        self.needs_sensitive_feature = True

    def evaluate(self, y_true, y_pred, X_test, sensitive_feature_names):
        results = {}

        # For each sensitive feature, compute the metric
        for feature in sensitive_feature_names:
            if feature not in X_test.columns:
                raise ValueError(f"Feature '{feature}' not found in X_test.")

            sensitive_column = X_test[feature]
            metric_frame = MetricFrame(
                metrics=precision_score,
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sensitive_column
            )

            precision_ratio = metric_frame.ratio()
            difference = metric_frame.difference()

            # Save results for each group
            results[feature] = {
                "precision_by_group": metric_frame.by_group,
                "precision_ratio": precision_ratio,
                "difference": difference
            }

            # Also save the precision for each category of the feature
            for index, value in metric_frame.by_group.items():
                key = f"{feature}_{index}"
                results[key] = value

        return results
