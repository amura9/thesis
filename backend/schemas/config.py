from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR ,REGISTRY_DIR
from pydantic import BaseModel, Field
from typing import Optional, Any
from pathlib import Path
import json

#GET ALL METRICS CONFIG FROM PLUGIN_REGISTRY
def load_metric_ids_from_registry(path: Path) -> list[str]:
    try:
        reg = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except Exception:
        return []

    ids: list[str] = []
    for plugin_key, meta in (reg or {}).items():
        metric_id = (meta or {}).get("id") or plugin_key
        ids.append(metric_id)
    return ids

# done once to get the ids
_METRIC_IDS: list[str] = load_metric_ids_from_registry(REGISTRY_DIR / "plugin_registry.json")

#SET FIRST CONFIG .JSON
class DatasetPaths(BaseModel):
    train: Optional[str] = None
    X_test: Optional[str] = None
    y_true: Optional[str] = None
    y_pred: Optional[str] = None


class ModelConfig(BaseModel):
    path: Optional[str] = None


class FeatureConfig(BaseModel):
    sensitive: bool = False


class BinningFeature(BaseModel):  # features
    bins: list[float]
    labels: list[str]


class BinningConfig(BaseModel):
    use_binning: bool = False
    features: dict[str, BinningFeature] = Field(default_factory=dict)


class PostprocessingConfig(BaseModel):
    use_inverse_encoding: bool = False
    inverse_encoding_prefixes: list[str] = Field(default_factory=list)
    binning: BinningConfig = Field(default_factory=BinningConfig)


# set of non discrimination & privacy metrics
class MetricsConfig(BaseModel):
    metrics: dict[str, list[str]] = Field(default_factory=dict)  # keep as you had it


class ConfigIn(BaseModel):
    """
    Initialize metrics at top level
      "fake_right_example": {}
      "demographic_parity": {}
      ...
    """

    class Config:
        extra = "allow"

    datasets: DatasetPaths = Field(default_factory=DatasetPaths)
    model: ModelConfig = Field(default_factory=ModelConfig)

    features: Optional[dict[str, FeatureConfig]] = None
    postprocessing: PostprocessingConfig = Field(default_factory=PostprocessingConfig)

    rights_to_evaluate: list[str] = Field(default_factory=list)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    plugins: list[str] = Field(default_factory=list)

    #for each metric initialize empty dict
    '''
    def __init__(self, **data: Any):
        super().__init__(**data)

        for metric_id in _METRIC_IDS:
            if metric_id not in self.__dict__:
                setattr(self, metric_id, {}) '''