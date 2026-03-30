from typing import Dict, Any
import pandas as pd
from core.load_config_value import get_config_value
from core.plugin_registry import PluginSpec, ParamSpec
from utilities.privacy_metric_base import PrivacyMetricBase

class LDiversity(PrivacyMetricBase):
    name = "L-Diversity"
    needs_sensitive_feature = False
    requires_all_sensitive_features = True

    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="l_diversity",
            name="L-Diversity",
            right="Privacy",
            description="Computes L-Diversity by grouping on quasi-identifiers and counting distinct values of a sensitive attribute.",
            requires=["X_test"], #datasets

            #parameters specification   
            params=[
                ParamSpec(
                    key="quasi_identifiers",
                    type="list[string]",
                    required=True,
                    default=[],
                    label="Quasi-identifiers",
                    help="Columns used to form groups. If empty, falls back to selected sensitive_features."
                ),
                ParamSpec(
                    key="sensitive_attribute",
                    type="string",
                    required=False, #if not provided -> fallback -> uses sensitive features
                    default=None,
                    label="Sensitive attribute",
                    help="Column name whose diversity within each group is measured."
                ),
            ],
        )

    def __init__(self, max_combinations_to_display: int = 10, config=None):
        super().__init__(config)
        self.max_display = max_combinations_to_display #added for displayable purposes
        self.quasi_identifiers = get_config_value(
            self.config, "l_diversity", "quasi_identifiers", default=[], required=False
        )
        self.sensitive_attribute = get_config_value(
            self.config, "l_diversity", "sensitive_attribute", default=None, required=False
        )

    def evaluate(
        self, y_true, y_pred, X_test: pd.DataFrame, sensitive_features: list
    ) -> Dict[str, Any]:
        try:
            # Fallback to QI from caller if not in config
            qi = self.quasi_identifiers or (sensitive_features or [])
            if not qi:
                return {
                    "status": "error",
                    "message": "No quasi_identifiers provided (config l_diversity.quasi_identifiers is empty and the caller list is empty)."
                }

            if not self.sensitive_attribute:
                return {
                    "status": "error",
                    "message": "l_diversity.sensitive_attribute missing in config."
                }

            needed = qi + [self.sensitive_attribute]
            missing = [c for c in needed if c not in X_test.columns]
            if missing:
                return {
                    "status": "error",
                    "message": f"Missing columns: {missing}",
                    "available_columns": list(X_test.columns),
                    "requested_columns": needed
                }

            # Compute L-diversity:
            # group by QIs, then count distinct values of the sensitive attribute
            l_series = (
                X_test.groupby(qi, dropna=False)[self.sensitive_attribute]
                .nunique()
                .astype(int)
            )

            if l_series.empty:
                return {
                    "status": "error",
                    "message": "No valid groups found for L-Diversity calculation."
                }

            l_min = int(l_series.min())
            l_avg = float(l_series.mean())
            total_groups = int(l_series.shape[0])

            # Serialize groups as strings for output
            l_by_group = {}
            for idx, val in l_series.items():
                if not isinstance(idx, tuple):
                    idx = (idx,)
                key = str(tuple(zip(qi, idx)))
                l_by_group[key] = int(val)

            #limit to 10
            l_series_limited = (
                l_series.sort_values(ascending=True)
                .head(self.max_display)
            )

            l_by_group_structured = []
            for idx, val in l_series_limited.items():
                if not isinstance(idx, tuple):
                    idx = (idx,)

                obj = {col: v for col, v in zip(qi, idx)}
                obj["l"] = int(val)  # the l-diversity value for that group
                l_by_group_structured.append(obj)
                        
            full_results = []
            for idx, val in l_series.items():
                if not isinstance(idx, tuple):
                    idx = (idx,)

                obj = {col: v for col, v in zip(qi, idx)}
                obj["l"] = int(val)  # the l-diversity value for that group
                full_results.append(obj)

            return {
                #Summary statistics
                "metric": self.get_spec().name,
                "status": "success",
                "l_min": l_min,
                "l_avg": l_avg, 
                "total_groups": total_groups,
                "quasi_identifiers": qi,
                "sensitive_attribute": self.sensitive_attribute,

                #Representation subset of interest
                "example_groups": l_by_group_structured, 

                #All -> for audit trailing
                "full_results": full_results,

                #Old
                #"l_by_group": l_by_group

            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
