# metrics/privacy/t_closeness.py

# metrics/privacy/t_closeness.py

from typing import Optional, List
import pandas as pd
from scipy.stats import wasserstein_distance
from core.load_config_value import get_config_value
from core.plugin_registry import PluginSpec, ParamSpec
from utilities.privacy_metric_base import PrivacyMetricBase

class TCloseness(PrivacyMetricBase):
    """
    Version that exactly replicates your snippet’s computation:
    - groupby over quasi_identifiers **and** the sensitive attribute
    - EMD (Wasserstein) computed between the FREQUENCY DISTRIBUTIONS (normalized value_counts)
      of the global sensitive attribute and the group-specific one
    - Returns a formatted STRING listing all values and the t_optimal

    Note: this is not the “classic” t-closeness, but matches your reference code 1:1.
    """

    name = "T-Closeness"
    needs_sensitive_feature = False
    # We set this so the orchestrator runs it once,
    # passing current_X and storing the result under "__combined__"
    requires_all_sensitive_features = True

    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="t_closeness",
            name="T-Closeness",
            right="Privacy", 
            description="Computes Wasserstein distance between global and group distributions of a sensitive attribute, grouped by quasi-identifiers.",
            requires=["X_test"], #datasets  

            #parameters specification
            params=[
                ParamSpec(
                    key="quasi_identifiers",
                    type="list[string]",
                    required=True,
                    default=None,
                    label="Quasi-identifiers",
                    help="Columns used to form groups. If empty, falls back to selected sensitive_features."
                ),
                ParamSpec(
                    key="sensitive_attribute",
                    type="string",
                    required=False, #if not provided -> fallback -> uses sensitive features
                    default=None,
                    label="Sensitive attribute",
                    help="Column whose distribution is compared globally vs within each group."
                ),
            ],
        )

    def __init__(self, max_combinations_to_display: int = 10,config: Optional[dict] = None):
        # Use PrivacyMetricBase to obtain self.config
        super().__init__(config)
        self.max_display = max_combinations_to_display #added for displayable purposes

        # Read parameters from config via get_config_value
        # (We do NOT load the file here: the caller/orchestrator already does that)
        self.quasi_identifiers: List[str] = get_config_value(
            self.config, "t_closeness", "quasi_identifiers", []
        )
        self.sensitive_attribute: Optional[str] = get_config_value(
            self.config, "t_closeness", "sensitive_attribute", None
        )

    def evaluate(self, y_true, y_pred, X_test: pd.DataFrame, sensitive_features=None):
        try:
            # Required parameters check
            if not self.quasi_identifiers or not self.sensitive_attribute:
                raise ValueError("Missing configuration for quasi_identifiers or sensitive_attribute.")

            if X_test is None or not isinstance(X_test, pd.DataFrame):
                return {"status": "error", "message": "X_test is missing or invalid."}

            # Check columns presence
            missing = [col for col in self.quasi_identifiers + [self.sensitive_attribute] if col not in X_test.columns]
            if missing:
                return {
                    "status": "error",
                    "message": f"Missing columns: {missing}",
                    "available_columns": list(X_test.columns)
                }

            # Global distribution of the sensitive attribute (normalized frequencies)
            global_distribution = (
                X_test[self.sensitive_attribute]
                .value_counts(normalize=True)
                .sort_index()
            )

            # Local function to compute “t-closeness” as EMD between frequency distributions
            def t_closeness(group: pd.DataFrame, global_distribution: pd.Series) -> float:
                group_distribution = (
                    group[self.sensitive_attribute]
                    .value_counts(normalize=True)
                    .sort_index()
                )
                # Align on the same index (categories)
                global_dist_aligned = global_distribution.reindex(global_distribution.index, fill_value=0)
                group_dist_aligned = group_distribution.reindex(global_distribution.index, fill_value=0)
                # EMD between probability vectors (as in your snippet)
                return float(wasserstein_distance(global_dist_aligned, group_dist_aligned))

            # Compute for each group defined by QIs + sensitive attribute (as in your snippet)
            t_closeness_values = X_test.groupby(self.quasi_identifiers + [self.sensitive_attribute]).apply(
                t_closeness, global_distribution
            )

            # Maximum observed value
            t_optimal = float(t_closeness_values.max()) if len(t_closeness_values) else 0.0

            group_cols = self.quasi_identifiers + [self.sensitive_attribute]

            ## t_closeness_values json friendly
            t_closeness_values_serialized = {}
            for idx, val in t_closeness_values.items():
                if not isinstance(idx, tuple):
                    idx = (idx,)
                key = str(tuple(zip(group_cols, idx)))
                t_closeness_values_serialized[key] = float(val)

            t_limited = t_closeness_values.sort_values(ascending=False).head(self.max_display)

            #example groups
            example_groups = []
            for idx, val in t_limited.items():
                if not isinstance(idx, tuple):
                    idx = (idx,)
                obj = {col: v for col, v in zip(group_cols, idx)}
                obj["t"] = float(val)
                example_groups.append(obj)

            #full_results -> for auditing
            full_results = []
            for idx, val in t_closeness_values.items():
                if not isinstance(idx, tuple):
                    idx = (idx,)
                obj = {col: v for col, v in zip(group_cols, idx)}
                obj["t"] = float(val)
                full_results.append(obj)

            # Text output (same format as your code)
            result = (
                "T-Closeness for each group (composed of quasi_identifiers and sensitive_attribute):\n"
                f"{t_closeness_values}\n\n"
                f"Optimal t value (maximum distance): {t_optimal}\n"
            )
            return {
                #Summary statistics
                "metric": self.get_spec().name,
                "status": "success",
                "quasi_identifiers": list(self.quasi_identifiers),
                "sensitive_attribute": self.sensitive_attribute,
                "t_optimal": float(t_optimal),

                #Representation subset of interest
                "example_groups": example_groups,

                #All -> for audit trailing
                "full_results": full_results,

                #Old
                #"result": result
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
