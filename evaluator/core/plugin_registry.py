from __future__ import annotations

import re
import inspect
from pathlib import Path
from dataclasses import dataclass, asdict, field, is_dataclass
from typing import Any, Dict, List, Optional

#Identify: rights, metrics, PluginSpec, ParamSpec

@dataclass
class ParamSpec:
    key: str
    type: str = "string"
    required: bool = False  # sensitive features are a param spec
    default: Any = None
    label: Optional[str] = None
    help: str = ""
    enum: Optional[List[str]] = None

@dataclass
class PluginSpec:
    id: str
    name: str
    right: str
    description: str = ""
    interpretation: str = ""
    requires: List[str] = field(default_factory=list)

    #Additional fiels needed for evaluator run
    plugin_path: Optional[str] = None
    params: List[ParamSpec] = field(default_factory=list)


def _safe_get_name(plugin) -> str:
    return getattr(plugin, "name", plugin.__class__.__name__)

def _make_id(name: str) -> str: #this_is_a_plugin
    s = (name or "").strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)          
    s = re.sub(r"[^a-z0-9_]", "", s)        
    s = re.sub(r"_+", "_", s).strip("_")    
    return s or "unknown_plugin"

def _as_plain_dict(obj: Any) -> Any: #converts dataclasses into dict -> 
    '''{
    "id": "conditional_statistical_parity",
    "params": [
        {
            "key": "sensitive_features",
            "type": "list[string]"
        }
    ]
    }'''
    if is_dataclass(obj):
        return {k: _as_plain_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _as_plain_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_as_plain_dict(v) for v in obj]
    return obj

#get the plugin path
def _plugin_path_from_file(plugin_instance: Any, base_pkg: str = "plugins") -> str: #returns: plugins.fairness.conditional_statistical_parity
    try:
        file_path = Path(inspect.getfile(plugin_instance.__class__)).resolve()
    except Exception:
        return plugin_instance.__class__.__module__

    parts = list(file_path.parts)

    if base_pkg in parts:
        i = parts.index(base_pkg)
        rel = parts[i:]  
        rel[-1] = Path(rel[-1]).stem
        return ".".join(rel)

    return plugin_instance.__class__.__module__

def _normalize_spec_dict(spec_dict: Dict[str, Any], plugin_instance: Any) -> Dict[str, Any]: #Normalizes SpectDict
    display_name = spec_dict.get("name") or _safe_get_name(plugin_instance)
    spec_dict["plugin_path"] = spec_dict.get("plugin_path") or _plugin_path_from_file(plugin_instance, base_pkg="plugins")

    # ID: this_is_a_plugin
    plugin_id = (
        spec_dict.get("id")
        or getattr(plugin_instance, "plugin_id", None)
        or getattr(plugin_instance, "id", None)
        or _make_id(display_name)
    )
    spec_dict["id"] = str(plugin_id)
    spec_dict["name"] = display_name

    #If not: need_sensitive_feature, needs_all_sensitive_features, needs_conditional_variable -> False
    if "need_sensitive_feature" not in spec_dict:
        spec_dict["need_sensitive_feature"] = bool(getattr(plugin_instance, "needs_sensitive_feature", False))

    if "needs_all_sensitive_features" not in spec_dict:
        spec_dict["needs_all_sensitive_features"] = bool(
            getattr(plugin_instance, "requires_all_sensitive_features", False))

    if "needs_conditional_variable" not in spec_dict:
        spec_dict["needs_conditional_variable"] = bool(getattr(plugin_instance, "needs_conditional_variable", False))

    # Requires from plugins always needed
    if "requires" not in spec_dict or not spec_dict["requires"]:
        print(f"[PLUGIN ERROR] '{spec_dict['name']}'requires' has always to be provided")

    #Params: dict
    params = spec_dict.get("params", [])
    if params is None:
        params = []

    #ParamSpec -> dict
    spec_dict["params"] = [_as_plain_dict(p) for p in params]

    return spec_dict

#Builds the registry
def build_registry_from_plugins(plugins: List[Any]) -> Dict[str, Dict[str, Any]]:
    registry = {}

    for p in plugins:
        if getattr(p, "hidden", False):
            continue

        if not hasattr(p, "get_spec") or not callable(getattr(p, "get_spec")):
            raise ValueError(
                f"Plugin '{p.__class__.__name__}' must implement get_spec()."
            )

        spec = p.get_spec()
        spec_dict = _normalize_spec_dict(_as_plain_dict(spec), p)
        registry[spec_dict["id"]] = spec_dict

    return registry