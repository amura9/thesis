from __future__ import annotations
from typing import Any, Dict, Literal
import numbers

SchemaKind = Literal["scalar_map", "group_metric_map", "conditional_nested", "record_with_table", "card_map", "unknown"]

'''
types:

-- scalar_map
{
  "age_cv": 0.12,
  "gender_cv": 0.08,
  "nationality_cv": 0.15
}

-- group_metric_map
{
  "age_cv": {
    "metric": "Disparate Impact",
    "status": "success",
    "selection_rates": {
      "18": 0.65,
      "19": 0.57,
      "20": 0.50
    },
    "disparate_impact": 1.0
  }
}

-- conditional_nested
{
  "age_cv": {
    "conditional_variable": "education",
    "conditions": {
      "Bachelor": {
        "18": 0.60,
        "19": 0.55
      },
      "Master": {
        "18": 0.70,
        "19": 0.65
      }
    }
  }
}

-- record_with_table
{
  "k_value": 5,
  "metric": "K-Anonymity",
  "status": "success",
  "avg_group_size": 200.0,
  "compliance": true,
  "full_results": [
    {"group": "A", "count": 12},
    {"group": "B", "count": 8}
  ]
}

-- card_map
{
  "(global)": {
    "status": "success",
    "metric": "Fake Right Example",
    "mean": 35.34,
    "median": 32.0,
    "computed": 1.10
  }
}
'''
#if list of dicts .> record_with_table
def _is_list_of_dicts(v: Any) -> bool:
    return isinstance(v, list) and len(v) > 0 and all(isinstance(x, dict) for x in v)

def _contains_list_of_dicts(obj: Any) -> bool: #the other element has a dict, list, dict
    """
    True if anywhere inside obj there is a list-of-dicts.
    Traverses dicts and lists recursively.
    """
    if isinstance(obj, dict):
        return any(_contains_list_of_dicts(v) for v in obj.values()) #{"a": 1, "b": [{"x": 1}]} true
    if isinstance(obj, list):
        if _is_list_of_dicts(obj):
            return True
        return any(_contains_list_of_dicts(x) for x in obj) #[{"x": 1}, {"x": 2}] true
    return False

def _leaf_category(v: Any) -> str:
    """Coarse type buckets for leaf values."""
    if v is None:
        return "none"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, numbers.Number):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, (list, tuple, set)):
        return "sequence"
    return "other"

def _is_map_like_dict(d: dict) -> bool:
    """
    Dynamic (no hardcoded keys):
    - If values mix dict and non-dict => record-like wrapper => NOT map-like.
    - If values are all dicts => likely a map to submaps => map-like.
    - If values are all non-dicts:
        * If leaf categories are homogeneous and numeric/bool-heavy => map-like
        * If leaf categories are heterogeneous (e.g., string+number) => record-like
    """
    if not d:
        return False

    vals = list(d.values())
    has_dict = any(isinstance(v, dict) for v in vals)
    has_non_dict = any(not isinstance(v, dict) for v in vals)

    # Mixed => record-like wrapper
    if has_dict and has_non_dict:
        return False

    # All dicts => map to subdicts
    if has_dict and not has_non_dict:
        return True

    # All non-dicts: decide by value-type homogeneity
    cats = {_leaf_category(v) for v in vals}

    # Homogeneous numeric/bool leaves => map-like (groups -> scalar)
    if cats.issubset({"number", "bool", "none"}) and len(cats) <= 2:
        return True

    # Otherwise treat as record-like (cards/metadata)
    return False

def _map_depth(obj: Any) -> int:
    """
    Compute a 'semantic map depth':
      - Count only map-like dicts as depth levels.
      - Do NOT count record-like dicts (mixed dict + non-dict values),
        but still traverse into their dict children.

    This avoids metadata wrappers inflating depth while still capturing
    real nested map structures.
    """
    if not isinstance(obj, dict) or not obj: #if not dict = 0 
        return 0

    # Recurse into dict-valued children
    child_depths = [
        _map_depth(v) for v in obj.values() if isinstance(v, dict) and v #go for child dict
    ]
    best_child = max(child_depths, default=0) #pick the highest of child_depth -> ex. 2, then dict of dict

    # Count this level only if it's map-like
    return (1 if _is_map_like_dict(obj) else 0) + best_child #1+2 = 3 if has 2 children

def _is_card_map(metric_block: Any) -> bool:
    """
    Example:
      {"(global)": {"status": "success", "mean": 1.2, ...}}
    """
    if not isinstance(metric_block, dict) or not metric_block: #non empty dict
        return False

    # must look like map -> dict
    vals = list(metric_block.values()) #{"(global)": {...}}
    if not vals or not all(isinstance(v, dict) for v in vals):
        return False

    # no other kind of structures
    if _contains_list_of_dicts(metric_block):
        return False

    # Each child must be a record (scalars/lists but NOT dicts)
    # (allow list values like ["a","b"] for future if needed)
    for rec in vals:
        if not isinstance(rec, dict) or not rec:
            return False
        for vv in rec.values():
            if isinstance(vv, dict):
                return False  # nested maps => not card_map
            if _is_list_of_dicts(vv):
                return False  # tables => not card_map

    return True

def detect_metric_schema(metric_block: Any) -> SchemaKind:
    if not isinstance(metric_block, dict) or not metric_block:
        return "unknown"
    
    if _contains_list_of_dicts(metric_block):
        return "record_with_table"
    
    if _is_card_map(metric_block):
        return "card_map"

    depth = _map_depth(metric_block)

    # schema based on semantic map-depth
    if depth == 1:
        return "scalar_map"
    elif depth == 2:
        return "group_metric_map"
    elif depth >= 3:
        return "conditional_nested"
    else:
        return "unknown"


def detect_all_result_schemas(all_results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    schemas: Dict[str, Dict[str, Any]] = {}

    for metric_name, metric_block in (all_results or {}).items():
        schema = detect_metric_schema(metric_block)

        if schema == "scalar_map":
            hint = {"ui": "simple_table_or_cards"}
        elif schema == "card_map":
            hint = {"ui": "summary_cards_only"}
        elif schema == "group_metric_map":
            hint = {"ui": "group_bar_chart_plus_summary"}
        elif schema == "conditional_nested":
            hint = {"ui": "condition_selector_then_group_chart"}
        elif schema == "record_with_table":
            hint = {"ui": "summary_plus_table"}
        else:
            hint = {"ui": "raw_json_fallback"}

        schemas[metric_name] = {"schema": schema, **hint}

    return schemas