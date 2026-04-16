from fairlearn.metrics import equalized_odds_difference
from core.plugin_registry import PluginSpec, ParamSpec


class EqualizedOddsDifference:
    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="equalized_odds_difference",
            name="Equalized Odds Difference",
            right="Non_Discrimination",
            description="Measures Equalized Odds difference across sensitive groups (lower is better).",
            interpretation="Values near 0 indicate prediction errors are evenly distributed.",
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
        self.name = "Equalized Odds Difference"
        self.needs_sensitive_feature = True

    def evaluate(self, y_true, y_pred, X_test, sensitive_features):
        results = {}

        for feature in sensitive_features:
            sensitive_column = X_test[feature]
            eod_diff = equalized_odds_difference(
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sensitive_column
            )
            results[feature] = 1 - eod_diff  
        return results
