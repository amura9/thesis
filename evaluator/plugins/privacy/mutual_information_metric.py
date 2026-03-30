from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from core.load_config_value import get_config_value
from core.plugin_registry import PluginSpec, ParamSpec
from sklearn.feature_selection import mutual_info_classif
from utilities.privacy_metric_base import PrivacyMetricBase

class MutualInformationMetric(PrivacyMetricBase):
    """
    Computes the Mutual Information between each feature in X_test
    (after excluding some columns) and the sensitive attribute defined in the config.
    Behavior is identical to the original implementation, but config is provided
    through PrivacyMetricBase.
    """
    name = "Mutual Information"
    needs_sensitive_feature = False
    requires_all_sensitive_features = True

    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="mutual_information",
            name="Mutual Information",
            right="Privacy",
            description="Computes Mutual Information between each feature and a selected sensitive attribute.",
            requires=["X_test"], #datasets

            #parameters specification
            params=[
                ParamSpec(
                    key="sensitive_attribute",
                    type="string",
                    required=True,
                    default=None,
                    label="Sensitive Attribute",
                    help="Column used as target variable for Mutual Information computation."
                ),
                ParamSpec(
                    key="columns_to_exclude",
                    type="list[string]",
                    required=False, #if not provided -> fallback -> uses sensitive features
                    default=[],
                    label="Columns to Exclude",
                    help="Columns excluded from MI computation (besides the sensitive attribute)."
                ),
            ],
        )

    def __init__(self, max_combinations_to_display: int = 10,config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Parameters from config
        self.sensitive_attribute: Optional[str] = get_config_value(
            self.config, "mutual_information", "sensitive_attribute", default=None
        )
        self.columns_to_exclude = get_config_value(
            self.config, "mutual_information", "columns_to_exclude", default=[]
        )

        self.max_display = max_combinations_to_display # #to display

        # Optional debug
        #print(f"Loaded sensitive attribute: {self.sensitive_attribute}")
        #print(f"Columns to exclude: {self.columns_to_exclude}")

    def _encode_features_and_build_mask(self, X: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Convert all columns of X into numeric form:
          - numeric: coerced to float/int, NaN filled with 0
          - categorical: converted to category codes
        Returns (X_encoded, discrete_mask) where discrete_mask=True for categorical columns.
        """
        X_enc = X.copy()
        discrete_mask = []

        for col in X_enc.columns:
            if pd.api.types.is_numeric_dtype(X_enc[col]):
                X_enc[col] = pd.to_numeric(X_enc[col], errors="coerce").fillna(0)
                discrete_mask.append(False)
            else:
                X_enc[col] = (
                    X_enc[col]
                    .astype("string")
                    .fillna("__MISSING__")
                    .astype("category")
                    .cat.codes
                )
                discrete_mask.append(True)

        return X_enc, np.array(discrete_mask, dtype=bool)

    def _encode_target(self, y: pd.Series) -> np.ndarray:
        """Convert the target into numeric codes if not already numeric."""
        if not pd.api.types.is_numeric_dtype(y):
            y_enc = (
                y.astype("string")
                 .fillna("__MISSING__")
                 .astype("category")
                 .cat.codes
                 .to_numpy()
            )
        else:
            y_enc = pd.to_numeric(y, errors="coerce").fillna(0).astype(int).to_numpy()
        return y_enc

    def evaluate(
        self,
        y_true: pd.Series,
        y_pred: pd.Series,
        X_test: pd.DataFrame,
        sensitive_features: list
    ) -> Dict[str, Any]:
        try:
            # 1) Check parameters
            if not self.sensitive_attribute:
                return {
                    "status": "error",
                    "message": "The sensitive attribute was not loaded correctly from the config."
                }

            if X_test is None or not isinstance(X_test, pd.DataFrame):
                return {"status": "error", "message": "X_test is missing or invalid."}

            if self.sensitive_attribute not in X_test.columns:
                return {
                    "status": "error",
                    "message": f"The sensitive attribute '{self.sensitive_attribute}' is not present in the dataset.",
                    "available_columns": list(X_test.columns)
                }

            # 2) Prepare X and y
            X_original = X_test.copy()
            y = X_original[self.sensitive_attribute]

            # 3) Drop excluded columns (including the sensitive attribute)
            columns_to_remove = [self.sensitive_attribute] + list(self.columns_to_exclude or [])
            X_filtered = X_original.drop(columns=columns_to_remove, errors="ignore")

            if X_filtered.shape[1] == 0:
                return {
                    "status": "error",
                    "message": "After dropping columns, no features remain for Mutual Information calculation."
                }

            # 4) Encode features and target
            X_enc, discrete_mask = self._encode_features_and_build_mask(X_filtered)
            y_enc = self._encode_target(y)

            # 5) Ensure target variability
            if len(np.unique(y_enc)) < 2:
                return {
                    "status": "error",
                    "message": f"The sensitive attribute '{self.sensitive_attribute}' has only one class after encoding: Mutual Information cannot be computed."
                }

            # 6) Compute Mutual Information
            mi = mutual_info_classif(
                X_enc.to_numpy(),
                y_enc,
                discrete_features=discrete_mask,
                random_state=42
            )

            # 7) Results
            mi_df = pd.DataFrame({
                "Feature": X_enc.columns,
                "Mutual_Information": mi
            }).sort_values(by="Mutual_Information", ascending=False, ignore_index=True)

            #ADDED (not use)
            full_results = [
                {row["Feature"]: float(row["Mutual_Information"])}
                for _, row in mi_df.iterrows()
            ]

            #ADDED
            pairs = list(zip(X_enc.columns, mi))[: self.max_display]
            mi_map = {str(f): float(v) for f, v in zip(X_enc.columns, mi)}

            #limit to 10 for display

            mi_map_example = {str(f): float(v) for f, v in pairs}

            return {
                #Summary statistics
                "metric": self.get_spec().name,
                "status": "success",
                "total_mi": float(np.sum(mi)),
                "sensitive_attribute": self.sensitive_attribute,
                "used_features": list(X_enc.columns),

                ##Representation subset of interest
                "example_groups": mi_map_example, 

                ##All -> for audit trailing
                "full_results": mi_map,
                
                #Old
                "discrete_mask": discrete_mask.tolist(), 
                #"full_results": full_results
                
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
