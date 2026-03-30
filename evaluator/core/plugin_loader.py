# core/plugin_loader.py

import importlib
import inspect 
import pkgutil
from typing import Any, Dict, List, Union, Tuple, Optional


def _snake_to_camel(s: str) -> str:
    # "demographic_parity" -> "DemographicParity"
    return ''.join(part.capitalize() for part in s.split('_') if part)


def _import_module(module_path: str):
    return importlib.import_module(module_path) #import plugins


def _pick_class_from_module(mod, preferred_name: Optional[str] = None): #class defined by
    #module name
    """
    Select a class from a module:
    - If `preferred_name` is provided, try that first (case-insensitive).
    - If the module defines exactly one class, use that one.
    - Otherwise, raise an explicit error listing available classes.

    Only classes defined in the module itself are considered
    (i.e., classes whose __module__ equals mod.__name__).
    """
    classes = [] #else a list of classes
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        # keep only classes defined in this module (not imported ones)
        if getattr(obj, "__module__", None) == mod.__name__:
            classes.append((name, obj))

    if preferred_name: 
        # case-insensitive match
        for name, obj in classes:
            if name.lower() == preferred_name.lower():
                return obj

    if len(classes) == 1:
        return classes[0][1]

    available = [name for name, _ in classes]
    raise AttributeError(
        f"Unable to determine which class to load in '{mod.__name__}'. "
        f"Specify the class name in the JSON or use the expected name. "
        f"Classes available in the module: {available}"
    )


def _infer_class_name_from_module_path(module_path: str) -> str: #infer it from path 
    # e.g., "plugins.fairness.demographic_parity" -> "DemographicParity"
    last_token = module_path.split('.')[-1]
    return _snake_to_camel(last_token)


def _split_module_and_class(path: str) -> Tuple[str, Optional[str]]: #if module.class
    """
    If the last token contains at least one uppercase letter, treat it as a class name.
    Otherwise, consider the path to be a module-only path.
    """
    tokens = path.split('.')
    if len(tokens) >= 2 and any(c.isupper() for c in tokens[-1]):
        module = '.'.join(tokens[:-1])
        class_name = tokens[-1]
        return module, class_name
    # module-only
    return path, None


def _load_one_plugin(entry: Union[str, Dict[str, Any]], config: Dict[str, Any]): #core
    """
    `entry` can be:
      - string: "plugins.fairness.demographic_parity" (module only)
                "plugins.fairness.demographic_parity.DemographicParity" (module + class)
      - dict:   {"module": "...", "class": "OptionalClassName", "enabled": true/false}
    """
    # 1) normalize input #getting module and class
    enabled = True
    if isinstance(entry, dict):
        enabled = entry.get("enabled", True)
        if not enabled:
            return None  # plugin disabled
        module_path = entry.get("module")
        class_name = entry.get("class")
        if not module_path:
            raise ValueError("Invalid plugin entry: missing 'module' field.")
    elif isinstance(entry, str):
        module_path, class_name = _split_module_and_class(entry)
    else:
        raise TypeError(f"Unsupported plugin entry type: {type(entry)}")

    # 2) import module  #(making use of the path)
    mod = _import_module(module_path)

    # 3) determine class #get class (either inferred or given)
    if not class_name:
        # try to infer from module name
        inferred = _infer_class_name_from_module_path(module_path)
        # try inferred class first; if missing, fall back to auto-discovery
        cls = getattr(mod, inferred, None)
        if cls is None:
            cls = _pick_class_from_module(mod)  # may raise a clear error
    else:
        # module + explicit class name
        try:
            cls = getattr(mod, class_name)
        except AttributeError:
            # fallback: try case-insensitive lookup within the module
            cls = _pick_class_from_module(mod, preferred_name=class_name)

    # 4) instantiate with or without config #instantiate pluging with or without config
    try:
        plugin = cls(config=config)  # privacy metrics usually accept a config
    except TypeError:
        # fairness metrics often have no __init__(config)
        plugin = cls()

    return plugin

#ex. ["plugin.module", "plugin.other.Class"], {"threshold": 0.5}
def load_plugins(entries: List[Union[str, Dict[str, Any]]], config: Optional[Dict[str, Any]] = None):
    """
    Load all plugins listed in `entries` (strings or dicts).
    Pass the config to plugins that accept it. No changes to the JSON format are required.
    """
    config = config or {}
    plugins = []
    for entry in entries: #from list of instantiated plugins 
        # if it's a dict and 'enabled' is False, _load_one_plugin returns None
        plugin = _load_one_plugin(entry, config=config) #load plugins  and eventually configs (imagine config: threshold:0.5, nromalize:True)
        if plugin is not None:
            plugins.append(plugin)
    return plugins


#---------------Dinamycally change UI if a new plugin is created
#discover all available plugins (NOT DEPENDING ON .JSON LISTING)
def discover_all_plugins(base_package: str = "plugins"):
    discovered = []
    package = importlib.import_module(base_package)

    for _, module_name, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        # Exclude package modules like plugins.fairness, plugins.privacy, plugins.new_right_example
        if ispkg:
            continue

        try:
            mod = importlib.import_module(module_name)
        except Exception as e:
            print(f"[discover] failed import {module_name}: {e}")
            continue

        for name, obj in inspect.getmembers(mod, inspect.isclass):
            # only consider classes defined in this module (not imported ones)
            if getattr(obj, "__module__", None) == mod.__name__:
                try:
                    discovered.append(obj())
                except Exception:
                    try:
                        discovered.append(obj(config={}))
                    except Exception as e:
                        print(f"[discover] skip {module_name}.{name}: {e}")

    return discovered



