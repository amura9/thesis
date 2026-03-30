from __future__ import annotations
import inspect
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Type
from core.plugin_registry import PluginSpec, ParamSpec

#Goal: to use this functuon to detect all different plugin structures.
#Based on these structures, a possible structure will be offered to the developer for its plugin
#In this way the UI will be able to automatically display the new metric

def _safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(obj, name, default)
    except Exception:
        return default

#Parameters dictionary
def _param_to_dict(p: Any) -> Dict[str, Any]:
    # Works whether ParamSpec is a dataclass or a plain object
    if hasattr(p, "__dataclass_fields__"):
        return asdict(p)  # type: ignore
    return {
        "key": _safe_getattr(p, "key"),
        "type": _safe_getattr(p, "type"),
        "required": bool(_safe_getattr(p, "required", False)),
        "default": _safe_getattr(p, "default", None),
        "label": _safe_getattr(p, "label", None),
        "help": _safe_getattr(p, "help", None),
    }


def _spec_to_dict(spec: Any) -> Dict[str, Any]:
    # Works whether PluginSpec is a dataclass or a plain object
    if hasattr(spec, "__dataclass_fields__"):
        d = asdict(spec)  # type: ignore
        # ensure params are JSON-friendly
        d["params"] = [_param_to_dict(p) for p in d.get("params", [])]
        return d

    return {
        "id": _safe_getattr(spec, "id"),
        "name": _safe_getattr(spec, "name"),
        "right": _safe_getattr(spec, "right"),
        "description": _safe_getattr(spec, "description"),
        "requires": list(_safe_getattr(spec, "requires", []) or []),
        "params": [_param_to_dict(p) for p in (_safe_getattr(spec, "params", []) or [])],
    }


def _infer_capabilities(plugin_cls: Type[Any]) -> Dict[str, Any]:
    """
    These flags drive your orchestrator decisions. We expose them explicitly in the schema.
    """
    return {
        "needs_X": bool(_safe_getattr(plugin_cls, "needs_X", True)),
        "needs_y_true": bool(_safe_getattr(plugin_cls, "needs_y_true", False)),
        "needs_y_pred": bool(_safe_getattr(plugin_cls, "needs_y_pred", False)),
        "needs_sensitive_feature": bool(_safe_getattr(plugin_cls, "needs_sensitive_feature", False)),
        "needs_sensitive_features": bool(_safe_getattr(plugin_cls, "needs_sensitive_features", False)),
        "needs_conditional_variable": bool(_safe_getattr(plugin_cls, "needs_conditional_variable", False)),
        "requires_all_sensitive_features": bool(_safe_getattr(plugin_cls, "requires_all_sensitive_features", False)),
    }


def _infer_evaluate_signature(plugin_cls: Type[Any]) -> str:
    try:
        sig = inspect.signature(plugin_cls.evaluate)
        return str(sig)
    except Exception:
        return "(unavailable)"


def build_plugin_schema(plugin_classes: List[Type[Any]]) -> Dict[str, Any]:
    """
    Returns a JSON-serializable schema that describes what each plugin is,
    what it requires, and how the UI/orchestrator should treat it.
    """
    plugins_schema: Dict[str, Any] = {}

    for cls in plugin_classes:
        # Must have get_spec()
        if not hasattr(cls, "get_spec") or not callable(getattr(cls, "get_spec")):
            # still include something useful
            plugins_schema[cls.__name__] = {
                "status": "error",
                "message": "Plugin missing get_spec()",
                "class_name": cls.__name__,
            }
            continue

        spec = cls.get_spec()
        spec_dict = _spec_to_dict(spec)

        plugins_schema[spec_dict.get("id") or cls.__name__] = {
            "status": "ok",
            "class_name": cls.__name__,
            "module": cls.__module__,
            "name_attr": _safe_getattr(cls, "name", None),
            "spec": spec_dict,
            "capabilities": _infer_capabilities(cls),
            "evaluate_signature": _infer_evaluate_signature(cls),
            # A developer-facing contract snippet
            "developer_contract": {
                "must_implement": ["get_spec()", "evaluate(...)"],
                "evaluate_must_return": "JSON-serializable dict with at least keys: status ('success'|'error') and optionally metric/name fields.",
                "notes": [
                    "If capabilities.needs_sensitive_feature is true, orchestrator will call evaluate per sensitive feature.",
                    "If capabilities.requires_all_sensitive_features is true, orchestrator will call evaluate once with a list of sensitive features.",
                ],
            },
        }

    return {
        "plugins": plugins_schema,
    }