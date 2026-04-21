from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR ,REGISTRY_DIR
from pydantic import BaseModel, Field
from typing import Optional, Any
from pathlib import Path
import json

#Get all metrics from plugin registry
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

_METRIC_IDS: list[str] = load_metric_ids_from_registry(REGISTRY_DIR / "plugin_registry.json")

#Set first config for .json file
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


#Save metrics belonging for each right:
'''
"metrics": {
    "new_right": [
      "metric_example"
    ],
    "privacy": [
      "anonymity_set_size",
      "k_anonymity"]}'''

class MetricsConfig(BaseModel):
    metrics: dict[str, list[str]] = Field(default_factory=dict)  # keep as you had it

#Initializes full config strcture
class ConfigIn(BaseModel):

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

    # FRIA contextual information
    description_of_processes: str = ""
    period_and_frequency_of_use: str = ""
    affected_persons_and_groups: str = ""

