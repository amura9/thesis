from fairlearn.metrics import demographic_parity_difference
from core.plugin_registry import PluginSpec, ParamSpec

class DemographicParity:
    @classmethod #added
    def get_spec(cls):
        return PluginSpec(
            id="demographic_parity",
            name="Demographic Parity",
            right="Non_Discrimination",
            description="Measures demographic parity by computing selection rate differences across sensitive groups.",
            interpretation="Values close to 1 indicate better demographic parity (less disparity) between groups.",
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
        self.name = "Demographic Parity"
        self.needs_sensitive_feature = True
        self.requires_all_sensitive_features = False

    def evaluate(self, y_true, y_pred, X_test, sensitive_feature_names):
        results = {}
        for feature in sensitive_feature_names:
            if feature not in X_test.columns:
                raise ValueError(f"Feature '{feature}' not found in X_test.")

            sensitive_column = X_test[feature]
            dp_diff = demographic_parity_difference(
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sensitive_column
            )
            results[feature] = 1 - dp_diff.item()
        return results
