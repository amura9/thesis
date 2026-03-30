from core.plugin_registry import PluginSpec, ParamSpec
from typing import Dict, Any, List
import pandas as pd

class AnonymitySetSize:
    name = "Anonymity Set Size"
    needs_sensitive_feature = True
    requires_all_sensitive_features = True

    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="anonymity_set_size",
            name="Anonymity Set Size",
            right="Privacy",
            description="Computes anonymity set sizes for combinations of sensitive features (quasi-identifiers).",
            requires=["X_test"], #datasets

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

    #Max combination to display, set to 10
    def __init__(self, max_combinations_to_display: int = 10, config=None): 
        # no config required; keep a uniform signature
        self.max_display = int(max_combinations_to_display)


    ###NORMALIZATION SCORE###
    @staticmethod
    def normalized_score(value: float) -> float:
        
        if value <= 1:
            return 0.0
        return float(1 * (1.0 - (1.0 / value)))

    def evaluate(
        self,
        y_true,
        y_pred,
        X_test: pd.DataFrame,
        sensitive_features: List[str]
    ) -> Dict[str, Any]:
        try:
            if not sensitive_features:
                return {
                    "status": "error",
                    "message": "No quasi_identifiers/sensitive_features list was provided by the caller."
                }

            missing = [c for c in sensitive_features if c not in X_test.columns]
            if missing:
                return {
                    "status": "error",
                    "message": f"Missing columns: {missing}",
                    "available_columns": list(X_test.columns),
                    "requested_features": sensitive_features
                }

            # Group sizes for each combination of sensitive features
            group_sizes = (
                X_test[sensitive_features]
                .value_counts(dropna=False)
                .reset_index()
            )
            group_sizes.columns = sensitive_features + ["count"]

            if group_sizes.empty:
                return {
                    "status": "error",
                    "message": "No valid combinations found to compute Anonymity Set Size."
                }

            # Distribution: how many groups have size = k
            size_counts = group_sizes["count"].value_counts().sort_index()

            # Bucketize >=10 as "10+"
            histogram: Dict[str, int] = {}
            for size, cnt in size_counts.items():
                size = int(size)
                if size >= 10:
                    histogram["10+"] = histogram.get("10+", 0) + int(cnt)
                else:
                    histogram[str(size)] = int(cnt)

            # Summary stats
            average = float(group_sizes["count"].mean())
            min_size = int(group_sizes["count"].min())
            max_size = int(group_sizes["count"].max())
            total_records = int(len(X_test))
            unique_combinations = int(len(group_sizes))

            ###NORMALIZATION SCORE###
            normalized_average = self.normalized_score(average)

            # Examples
            example_groups = []
            for _, row in group_sizes.head(self.max_display).iterrows():
                item = {col: row[col] for col in sensitive_features}
                item["count"] = int(row["count"])
                example_groups.append(item)

            #make it json
            return {
                #Summary statistics
                "metric": self.get_spec().name,
                "status": "success",
                "average": average,
                "min": min_size,
                "max": max_size,
                "unique_combinations": unique_combinations,
                "total_records": total_records,
                "sensitive_features": sensitive_features,
                "score": normalized_average,

                #Representation subset of interest
                "example_groups": example_groups, 
                #"distribution": histogram,

                #All -> for audit trailing
                "full_results": group_sizes.to_dict(orient="records")    

                #Old
                       
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
