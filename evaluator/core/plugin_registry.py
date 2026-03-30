from __future__ import annotations

import re
import inspect
from pathlib import Path
from dataclasses import dataclass, asdict, field, is_dataclass
from typing import Any, Dict, List, Optional


# Automatically identify new rights, plugins and parameters needed for calculation.
# These will be then provided in the .json config

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
    requires: List[str] = field(default_factory=list)

    #Additional fiels needed for evaluator run
    plugin_path: Optional[str] = None
    params: List[ParamSpec] = field(default_factory=list)


def _infer_right_from_module(module_name: str, base_package: str = "plugins") -> str:
    parts = module_name.split(".")
    if len(parts) >= 2 and parts[0] == base_package:
        return parts[1]
    return "unknown"


def _safe_get_name(plugin) -> str:
    # keep the plugin's own name if present
    return getattr(plugin, "name", plugin.__class__.__name__)


def _make_id(name: str) -> str:
    """
    Convert display name -> machine id.
    - lowercase
    - spaces/dashes -> underscore
    - remove non-alphanumeric/underscore
    - collapse multiple underscores
    """
    s = (name or "").strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)          # spaces and dashes to underscore
    s = re.sub(r"[^a-z0-9_]", "", s)        # drop other punctuation
    s = re.sub(r"_+", "_", s).strip("_")    # collapse underscores
    return s or "unknown_plugin"


def _as_plain_dict(obj: Any) -> Any:
    """
    Convert dataclasses (PluginSpec/ParamSpec) into plain dicts recursively.
    Leaves already-plain dict/list/primitive values unchanged.
    """
    if is_dataclass(obj):
        return {k: _as_plain_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _as_plain_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_as_plain_dict(v) for v in obj]
    return obj

#get the plugin path
def _plugin_path_from_file(plugin_instance: Any, base_pkg: str = "plugins") -> str:
    """
    Return import path like: plugins.fake_right.new_metric
    based on the real .py file location.

    Works even if the class was imported under some other prefix, as long as the
    file sits under a folder named `plugins` that is a Python package.
    """
    try:
        file_path = Path(inspect.getfile(plugin_instance.__class__)).resolve()
    except Exception:
        # fallback: use python's module name if inspection fails
        return plugin_instance.__class__.__module__

    parts = list(file_path.parts)

    # Find ".../plugins/..." in the path and build dotted module from there
    if base_pkg in parts:
        i = parts.index(base_pkg)
        rel = parts[i:]  # ["plugins", "fake_right", "new_metric.py"]
        rel[-1] = Path(rel[-1]).stem  # "new_metric"
        return ".".join(rel)

    # fallback: if we can't locate the base folder, use __module__
    return plugin_instance.__class__.__module__


def _normalize_spec_dict(spec_dict: Dict[str, Any], plugin_instance: Any) -> Dict[str, Any]:
    """
    Normalize/repair a spec dict so frontend always receives consistent fields.
    Also bridges naming mismatches (needs_sensitive_feature vs need_sensitive_feature).
    """
    display_name = spec_dict.get("name") or _safe_get_name(plugin_instance)

    spec_dict["plugin_path"] = spec_dict.get("plugin_path") or _plugin_path_from_file(plugin_instance, base_pkg="plugins")

    # ID needed to display the metrics
    plugin_id = (
        spec_dict.get("id")
        or getattr(plugin_instance, "plugin_id", None)
        or getattr(plugin_instance, "id", None)
        or _make_id(display_name)
    )
    spec_dict["id"] = str(plugin_id)
    spec_dict["name"] = display_name

    # Handle flag naming mismatch:
    # some plugins/specs might use "needs_sensitive_feature" (plural) by mistake.
    if "need_sensitive_feature" not in spec_dict and "needs_sensitive_feature" in spec_dict:
        spec_dict["need_sensitive_feature"] = bool(spec_dict.pop("needs_sensitive_feature"))

    # Ensure flags exist (fallback to instance attrs)
    if "need_sensitive_feature" not in spec_dict:
        spec_dict["need_sensitive_feature"] = bool(getattr(plugin_instance, "needs_sensitive_feature", False))

    if "needs_all_sensitive_features" not in spec_dict:
        spec_dict["needs_all_sensitive_features"] = bool(
            getattr(plugin_instance, "requires_all_sensitive_features", False)
        )

    if "needs_conditional_variable" not in spec_dict:
        spec_dict["needs_conditional_variable"] = bool(getattr(plugin_instance, "needs_conditional_variable", False))

    # Requires: if missing, infer
    if not spec_dict.get("requires"):
        requires = ["X_test"]
        # if metric uses sensitive features (either per-feature or all-together), UI should ask for them
        if spec_dict["need_sensitive_feature"] or spec_dict["needs_all_sensitive_features"]:
            requires.append("sensitive_features")
        spec_dict["requires"] = requires

    # Params: ensure list of dicts
    params = spec_dict.get("params", [])
    if params is None:
        params = []

    # Convert ParamSpec dataclasses (or mixed) to dicts
    spec_dict["params"] = [_as_plain_dict(p) for p in params]

    # Fill optional fields
    spec_dict.setdefault("description", "")
    spec_dict.setdefault("version", "1.0")

    return spec_dict


def build_registry_from_plugins(plugins: List[Any]) -> Dict[str, Dict[str, Any]]:
    """
    plugins: coming from discovery (instances)
    returns: {plugin_id: spec_dict}
    """
    registry: Dict[str, Dict[str, Any]] = {}

    for p in plugins:
        if getattr(p, "hidden", False):
            continue

        display_name = _safe_get_name(p)

        # 1) If plugin provides explicit spec, trust it (but normalize)
        if hasattr(p, "get_spec") and callable(getattr(p, "get_spec")):
            spec = p.get_spec()

            # Convert dataclass/dict to plain dict
            spec_dict = _as_plain_dict(spec)

            # Normalize + fill missing fields (also sets plugin_path)
            spec_dict = _normalize_spec_dict(spec_dict, p)

            registry[spec_dict["id"]] = spec_dict
            continue

        # 2) Otherwise infer minimal spec from attributes (legacy plugins)
        module_name = p.__class__.__module__
        right = _infer_right_from_module(module_name)

        needs_sensitive = bool(getattr(p, "needs_sensitive_feature", False))
        needs_all = bool(getattr(p, "requires_all_sensitive_features", False))
        needs_cond = bool(getattr(p, "needs_conditional_variable", False))

        requires = ["X_test"]
        if needs_sensitive or needs_all:
            requires.append("sensitive_features")

        legacy_spec = PluginSpec(
            id=getattr(p, "plugin_id", None) or _make_id(display_name),
            name=display_name,
            right=right,
            description="",
            version=getattr(p, "version", "1.0"),
            requires=requires,

            # ✅ NEW (optional here, but explicit): set plugin_path for legacy inferred plugins
            plugin_path=p.__class__.__module__,

            need_sensitive_feature=bool(needs_sensitive and not needs_all),
            needs_all_sensitive_features=needs_all,
            needs_conditional_variable=needs_cond,
            params=[],
        )

        spec_dict = _normalize_spec_dict(_as_plain_dict(legacy_spec), p)
        registry[spec_dict["id"]] = spec_dict

    return registry

# generate empty metrics dict for each plugin id, to be filled by the user in the UI before evaluation
