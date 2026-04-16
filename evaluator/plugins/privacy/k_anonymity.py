import pandas as pd
from typing import Dict, Any
from utilities.privacy_metric_base import PrivacyMetricBase
from core.plugin_registry import PluginSpec, ParamSpec
from core.load_config_value import get_config_value

class KAnonymity(PrivacyMetricBase):
    name = "K-Anonymity"
    requires_all_sensitive_features = True

    @classmethod #added
    def get_spec(cls):
        return PluginSpec(
            id="k_anonymity",
            name="K-Anonymity",
            right="Privacy",
            description="Evaluates K-Anonymity over quasi-identifiers (each equivalence class must have at least k records).",
            requires=["X_test"], #datasets

            #parameters specification
            params=[
                ParamSpec(
                    key="k_value",
                    type="int",
                    required=True,
                    default=2,
                    label="k value",
                    help="Minimum group size for k-anonymity compliance."
                ),
                ParamSpec(
                    key="quasi_identifiers",
                    type="list[string]",
                    required=False, #if not provided -> fallback -> uses sensitive features
                    default=None,
                    label="Quasi-identifiers",
                    help="Columns used to form equivalence classes. If empty, falls back to the selected sensitive_features."
                ),  
            ],
        )

    #Max combination to display, set to 10
    def __init__(self, max_combinations_to_display: int = 10, config=None):
        super().__init__(config)
        # Read parameters from config if present; otherwise fall back inside evaluate()
        self.max_display = max_combinations_to_display #added for displayable purposes
        self.quasi_identifiers = get_config_value(
            self.config, "k_anonymity", "quasi_identifiers", default=[], required=False
        )
        self.k_value = get_config_value(
            self.config, "k_anonymity", "k_value", default=2, required=False
        )
        self.group_counts = None

    def evaluate(
        self,
        y_true: pd.Series,
        y_pred: pd.Series,
        X_test: pd.DataFrame,
        sensitive_features: list
    ) -> Dict[str, Any]:
        """
        Evaluate K-Anonymity on the preprocessed dataset.
        Uses quasi_identifiers from config; if empty, falls back to those passed from the caller.
        """
        #same structure for all the group_metric:map
        #results: Dict [str, Any] = {}
        try:
            # Fallback: if config provides no QI, use those received from the caller
            quasi_identifiers = self.quasi_identifiers or (sensitive_features or [])
            if not quasi_identifiers:
                return self._error_result(
                    "No quasi-identifiers provided (config k_anonymity.quasi_identifiers is empty and the caller list is empty).",
                    quasi_identifiers
                )

            # Column existence check
            missing = [c for c in quasi_identifiers if c not in X_test.columns]
            if missing:
                return self._error_result(f"Missing features: {', '.join(missing)}", quasi_identifiers)

            # Group sizes
            groups = X_test[quasi_identifiers]
            self.group_counts = groups.groupby(quasi_identifiers).size()

            compliance_series = (self.group_counts >= self.k_value)
            comp_pct = round(float(compliance_series.mean()) * 100.0, 2) if len(compliance_series) else None

            #score definition
            group_scores = self.group_counts.apply(lambda g: min(float(g) / float(self.k_value), 1.0)) #group_score = min(1, group_size (how many groups contain certain
            #quasi identifiers) / k) 
            normalized_score = round(float(group_scores.mean()), 3) if len(group_scores) else None #avg. anonimyty quality
            final_score = round(10 * normalized_score, 3) if normalized_score is not None else None
            

            non_compliant = self.group_counts[self.group_counts < self.k_value]
            non_compliant_limited = non_compliant.sort_values(ascending=True).head(self.max_display)

            # Format output for csv
            formatted_groups = []
            for group, count in self.group_counts.items():
                if not isinstance(group, tuple):
                    group = (group,)
                group_str = "\n".join([f"{' '*10}{col}: {val}" for col, val in zip(quasi_identifiers, group)])
                formatted_groups.append({
                    "group": group_str,
                    "count": int(count),
                    "compliant": bool(count >= self.k_value)
                })

            #full result for audit 
            full_results = []

            for group_key, count in self.group_counts.items():
                if not isinstance(group_key, tuple):
                    group_key = (group_key,)

                obj = {col: val for col, val in zip(quasi_identifiers, group_key)}
                obj["count"] = int(count)
                obj["compliant"] = bool(count >= self.k_value)

                full_results.append(obj)
    
            #limit to 10
            non_compliant = self.group_counts[self.group_counts < self.k_value]
            non_compliant_limited = non_compliant.sort_values(ascending=True).head(self.max_display)

            return {
                #Summary statistics
                "metric": self.get_spec().name,
                "status": "success",
                "k_value": self.k_value,
                "total_groups": int(len(self.group_counts)),
                "min_group_size": int(self.group_counts.min()) if len(self.group_counts) else None,
                "max_group_size": int(self.group_counts.max()) if len(self.group_counts) else None,
                "avg_group_size": round(float(self.group_counts.mean()), 2) if len(self.group_counts) else None,
                "compliance": bool(compliance_series.all()) if len(compliance_series) else None,
                "compliance_percentage": comp_pct,
                "quasi_identifiers": quasi_identifiers,
                "final_score": final_score,

            
                #All -> for audit trailing
                "full_results": full_results, #full result

                #old
                #"non_compliant_groups": {   str(k): int(v)   for k, v in self.group_counts[self.group_counts < self.k_value].to_dict().items()}, #full list of non_compliant_groups
                #"formatted_groups": formatted_groups #this is a full formatted result ->to be used for csv
            }
    

        except Exception as e:

            # On exception, try to report the QIs used (config or caller)
            quasi_identifiers = self.quasi_identifiers or (sensitive_features or [])
            return self._error_result(f"Error during computation: {str(e)}", quasi_identifiers)

    def _error_result(self, message: str, qi_snapshot) -> Dict[str, Any]:
        return {
            "status": "error",
            "message": message,
            "k_value": getattr(self, "k_value", None),
            "sensitive_features": qi_snapshot
        }

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "KAnonymity":
        # Keep the signature for compatibility, but the instance now reads config in __init__
        return cls(config=config)
