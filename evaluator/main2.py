import os
import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from core.config_loader import load_config
from core.data_loader import load_dataset
from core.model_loader import load_model
from core.plugin_loader import load_plugins
from utilities.postprocessing import apply_binning
from utilities.ohe_utils import combine_ohe_columns_by_prefix
from core.load_config_value import get_config_value
from utilities.utils import to_series_1d, sanitize_sensitive_col
from utilities.detect_metric_schema import detect_all_result_schemas #detect the schema for UI displaying
# Helper: configuration resolver

def resolve_config_path(default_dir: str = "config") -> Path:
    """
    Precedence order for selecting the configuration file:
      1) --config PATH (CLI argument)
      2) Environment variable EVALUATOR_CONFIG
      3) Auto-discovery in `default_dir`:
         - `FileConfigurazione.json` if it exists
         - the only *.json file found in the folder
      4) Take it if available from frontend
    Raises an explicit error if no valid file is found or if multiple candidates create ambiguity.
    """
    
    parser = argparse.ArgumentParser(add_help=False) 
    parser.add_argument("--config", type=str, help="Path to the JSON configuration file")
    known, _ = parser.parse_known_args()
    print(known)
    # 1) CLI  -> pass config
    if known.config:
        p = Path(known.config).expanduser().resolve()
        print(p)
        if not p.exists():
            raise FileNotFoundError(f"--config points to a non-existent file: {p}")
        return p

    # 2) ENV -> from env
    env_path = os.getenv("EVALUATOR_CONFIG")
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"EVALUATOR_CONFIG points to a non-existent file: {p}")
        return p
    
    '''
    # 3) Auto-discovery 
    cfg_dir = Path(default_dir)
    if not cfg_dir.exists():
        raise FileNotFoundError(
            f"Default configuration directory not found: {cfg_dir.resolve()}\n"
            "Provide --config or set EVALUATOR_CONFIG."
        )

    preferred = cfg_dir / "FileConfigurazione.json" #preferred config file to provide
    if preferred.exists():
        return preferred.resolve()

    candidates = sorted(cfg_dir.glob("*.json"))
    if len(candidates) == 1:
        return candidates[0].resolve()
    elif len(candidates) == 0:
        raise FileNotFoundError(
            f"No .json file found in {cfg_dir.resolve()}. "
            "Provide --config or set EVALUATOR_CONFIG."
        )
    else:
        names = "\n  - " + "\n  - ".join(str(c) for c in candidates)
        raise RuntimeError(
            "Multiple configuration files found in the directory; cannot choose automatically."
            f"{names}\nSpecify which one to use with --config or EVALUATOR_CONFIG."
        )
    '''
    # 4) Frontend JSON
    config_json = known.config_json
    if config_json:
        try:
            cfg_obj = json.loads(config_json)  # validate JSON
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON provided via --config-json / EVALUATOR_CONFIG_JSON: {e}")

        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(parents=True, exist_ok=True)
        out_path = (runtime_dir / "frontend_config.json").resolve()
        out_path.write_text(json.dumps(cfg_obj, indent=2), encoding="utf-8")
        return out_path


# Helper: safe feature flags access with default fall-backs

#indicate IF a plugin is required, else is a sensible default feature
def requires(plugin, attr, default):
    """Return plugin.{attr} if present, otherwise a sensible default."""
    return getattr(plugin, attr, default)



# Pretty printer for heterogeneous metric IO. Print: K-anonimity, MI, precision by group, L-diversity, Closeness  
# to have csv printed
def export_all_results_to_csv(all_results: dict, out_csv: str = "run_results/all_results.csv") -> str:
    rows = []

    def as_json(x):
        try:
            return json.dumps(x, ensure_ascii=False)
        except Exception:
            return str(x)

    for metric_name, results in all_results.items():
        if not isinstance(results, dict):
            rows.append({
                "metric_name": metric_name,
                "feature": "(global)",
                "value_type": type(results).__name__,
                "value_json": as_json(results),
            })
            continue

        for feature, data in results.items():
            row = {
                "metric_name": metric_name,
                "feature": feature,
                "value_type": "none" if data is None else type(data).__name__,
                "value_json": as_json(data),
            }

            # OPTIONAL: pull out common fields (if present) into dedicated columns
            if isinstance(data, dict):
                for k in [
                    "k_value",
                    "min_group_size",
                    "max_group_size",
                    "avg_group_size",
                    "compliance",
                    "compliance_percentage",
                    "l_min",
                    "l_avg",
                    "t_optimal",
                    "total_groups",
                    "precision_ratio",
                    "difference",
                ]:
                    if k in data:
                        row[k] = data.get(k)

                # Special: Mutual Information structure (if present)
                if "total_mi" in data:
                    row["total_mi"] = data.get("total_mi")

            rows.append(row)

    df = pd.DataFrame(rows)

    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8")

    return str(out_path)

#Pretty printer final results ...
def print_all_results(all_results):
    """Pretty-print the final results of all metrics in a uniform way."""
    print("\n=== FINAL RESULTS ===")

    for metric_name, results in all_results.items(): #all results dictionary {MetricName: {featureA: 1, featureB: 2}}
        print(f"\n--- Metrics: {metric_name} ---")
        #indicates what is combined
        for feature, data in results.items():
            if data is None:
                print(f"  No data for feature: {feature}")
                continue

            if feature == "__combined__":
                print(f"\n  Combined result:")
            else:
                print(f"\n  Feature: {feature}")

            # --- Global: print metric name if provided by plugin
            if isinstance(data, dict) and "metric" in data:
                print(f"    Metric: {data.get('metric')}")

            # ---- K-ANONYMITY
            if isinstance(data, dict) and "k_value" in data:
                k = data.get("k_value")
                min_g = data.get("min_group_size")
                max_g = data.get("max_group_size")
                avg_g = data.get("avg_group_size")

                print(f"    k: {k}")
                if min_g is not None:
                    derived_compliance = (min_g >= k) if (k is not None) else None
                else:
                    derived_compliance = None

                compliance = data.get("compliance", derived_compliance)
                comp_pct = data.get("compliance_percentage")

                # If percentage is missing, derive it from the size distribution (if available)
                if comp_pct is None:
                    dist = data.get("distribution")  #distribution from where actually?
                    if isinstance(dist, dict) and k is not None:
                        compliant_groups = 0
                        total_groups = 0
                        for key, cnt in dist.items():
                            try:
                                size = int(str(key).replace("+", ""))
                            except Exception:
                                continue
                            total_groups += cnt
                            if size >= k:
                                compliant_groups += cnt
                        if total_groups > 0:
                            comp_pct = round(100.0 * compliant_groups / total_groups, 2)

                print(
                    f"    Compliance: {compliance if compliance is not None else 'N/A'}"
                    f"{f' ({comp_pct}%)' if comp_pct is not None else ''}"
                )
                if min_g is not None:
                    print(f"    Min group size: {min_g}")
                if max_g is not None:
                    print(f"    Max group size: {max_g}")
                if avg_g is not None:
                    print(
                        f"    Avg group size: {avg_g:.2f}"
                        if isinstance(avg_g, (int, float))
                        else f"    Avg group size: {avg_g}"
                    )

                nc = data.get("example_groups") or data.get("non_compliant_groups") #these are the non compliant groups
                if isinstance(nc, dict) and nc:
                    print("    Non-compliant groups:")
                    for group, count in nc.items():
                        print(f"      {group}: {count}")

                formatted_groups = data.get("full_results", [])
                if formatted_groups:
                    max_examples = 5 #maximum displayable examples
                    print("\n[COMPACT] Example groups (max 5):")
                    for gi in formatted_groups[:max_examples]:
                        print(f"      Group:\n{gi.get('group')}")
                        print(f"      Count: {gi.get('count')}")
                        print(f"      Compliant: {gi.get('compliant')}\n")
                    if len(formatted_groups) > max_examples:
                        print(f"    ... ({len(formatted_groups) - max_examples} groups omitted)")

            # ---- MUTUAL INFORMATION (example: your plugin name must match)
            elif metric_name == "Mutual Information":
                if isinstance(data, dict) and data.get('status') == 'success':
                    print(f"\n  Sensitive attribute: {data['sensitive_attribute']}") #defines which are the sensitive attributes to MI
                    print("\n  Mutual Information by feature:")
                    df = pd.DataFrame(data['mi_df'])
                    print(df.to_string(
                        index=False,
                        float_format="%.6f",
                        header=['Feature', 'Mutual Information'],
                        justify='left'
                    ))
                    print(f"\n  Total Mutual Information: {data['total_mi']:.6f}")
                else:
                    print(f"  Error: {isinstance(data, dict) and data.get('message')}")

            # ---- EXAMPLE FAIRNESS OUTPUTS (precision-by-group style)
            elif isinstance(data, dict) and "precision_by_group" in data:
                print(f"    Precision by group:\n{data['precision_by_group']}")
                print(f"    Precision ratio: {data['precision_ratio']}")
                print(f"    Difference: {data['difference']}")

            # ---- L-DIVERSITY (compact formatting)
            elif isinstance(data, dict) and "l_by_group" in data:
                status = data.get("status", "success")
                if status != "success":
                    print(f"  Error: {data.get('message')}")
                else:
                    l_min = data.get("l_min")
                    l_avg = data.get("l_avg")
                    total_groups = data.get("total_groups")
                    qi = data.get("quasi_identifiers")
                    sa = data.get("sensitive_attribute")

                    print(f"    Quasi-identifiers: {qi}")
                    print(f"    Sensitive attribute: {sa}")
                    if l_min is not None:
                        print(f"    l_min: {l_min}")
                    if l_avg is not None:
                        print(f"    l_avg: {l_avg:.3f}" if isinstance(l_avg, (int, float)) else f"    l_avg: {l_avg}")
                    if total_groups is not None:
                        print(f"    Total groups: {total_groups}")

                    l_by_group = data.get("l_by_group", {})
                    if isinstance(l_by_group, dict) and l_by_group:
                        items = sorted(l_by_group.items(), key=lambda x: x[1])  # ascending: worst first
                        max_show = 5
                        print("\n    [COMPACT] Groups with lowest L (max 5):")
                        for k, v in items[:max_show]:
                            print(f"      {k}: L = {v}")

            # ---- T-CLOSENESS (compact formatting)
            elif isinstance(data, dict) and "t_by_group" in data:
                status = data.get("status", "success")
                if status != "success":
                    print(f"  Error: {data.get('message')}")
                else:
                    t_opt = data.get("t_optimal")
                    qi = data.get("quasi_identifiers")
                    sa = data.get("sensitive_attribute")

                    print(f"    Quasi-identifiers: {qi}")
                    print(f"    Sensitive attribute: {sa}")
                    if t_opt is not None:
                        try:
                            print(f"    t_optimal (max distance): {float(t_opt):.6f}")
                        except Exception:
                            print(f"    t_optimal: {t_opt}")

                    t_by_group = data.get("t_by_group", {})
                    if isinstance(t_by_group, dict) and t_by_group:
                        items = sorted(t_by_group.items(), key=lambda x: x[1], reverse=True)  # worst first
                        max_show = 5
                        print("\n    [COMPACT] Groups with highest t (max 5):")
                        for k, v in items[:max_show]:
                            try:
                                vv = float(v)
                                print(f"      {k}: t = {vv:.6f}")
                            except Exception:
                                print(f"      {k}: t = {v}")

            # ---- Generic fallback (unknown structure)
            else:
                print(f"    Value: {data}")

            #get printed result in csv path
        #csv_path = export_all_results_to_csv(all_results, out_csv="run_results/all_results.csv")

#save printed results to .csv file
def save_pretty_print(all_results, out_txt):
    from pathlib import Path
    Path(out_txt).parent.mkdir(parents=True, exist_ok=True)

    import io, sys
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        print_all_results(all_results)
    finally:
        sys.stdout = old

    Path(out_txt).write_text(buf.getvalue(), encoding="utf-8")
    return out_txt

#ADDED -> excluding the __combined__ for all_results.json. __combined__ will then be used only for pretty_print
def flatten_combined_results(all_results: dict) -> dict:
    """
    If a metric contains only '__combined__',
    flatten it so the JSON does not include that wrapper.
    Example:
      { "k_anonymity": { "__combined__": {...} } }
    becomes:
      { "k_anonymity": {...} }
    """
    flattened = {}

    for metric_name, metric_data in all_results.items():
        if (
            isinstance(metric_data, dict)
            and "__combined__" in metric_data
            and len(metric_data) == 1
        ):
            flattened[metric_name] = metric_data["__combined__"]
        else:
            flattened[metric_name] = metric_data

    return flattened





###########################
# Main evaluation pipeline#
###########################

def main():
    """Pipeline entrypoint: load config/data, post-process, run plugins, print results."""
    # 1) choose configuration (CLI/ENV/autodiscovery) 
    # 

    # -> on CLI: python main.py --config config/FileConfigurazione-test_DiCristo.json
    config_path = resolve_config_path(default_dir="config") #choose configuration
    print(f"[INFO] Using config: {config_path}")

    # 2) load configuration #gliela passi con la CLI
    config = load_config(str(config_path)) #config path: config/FileConfigurazione-test_DiCristo.json
    post_cfg = config.get('postprocessing', {})

    # 3) load datasets (all optional) #from the configuration
    ds = config.get('datasets', {}) #so we need to provide 4 type of DS. 
    train = load_dataset(ds.get('train')) if ds.get('train') else None
    X_test = load_dataset(ds.get('X_test')) if ds.get('X_test') else None #il DS necessario
    y_true = load_dataset(ds.get('y_true')) if ds.get('y_true') else None #compare y_true e y_test solo per vedere accuracy (credo)
    y_pred = load_dataset(ds.get('y_pred')) if ds.get('y_pred') else None


    # 4) original copy for plugins that require raw columns
    X_original = X_test.copy() if X_test is not None else None

    # 5) optional model -> provide only optionally
    model_path = config.get('model', {}).get('path') #from the config file still
    model = load_model(model_path) if model_path else None 

    # 6) post-processing (only if X_test available)
    binning_mapping = {}
    if X_test is not None:
        if post_cfg.get("use_inverse_encoding", False):
            prefixes = post_cfg.get("inverse_encoding_prefixes", [])
            X_test = combine_ohe_columns_by_prefix(X_test, prefixes) #all in one column with same prefix

            #the ones done are these: 'gender_cv_': ['gender_cv_Female', 'gender_cv_Male', 'gender_cv_Not binary', 'gender_cv_Not declared']      "gender_cv_",      "nationality_cv_",     "disability_cv_"

           

        binning_cfg = post_cfg.get("binning", {}) 
        #use binning: True -> works
        if binning_cfg.get("use_binning", False):
            X_test, binning_mapping = apply_binning(X_test, binning_cfg)
            
            #bin age ->
            #{'age_cv': 'age_cv_binned'} only binned performed

    # 7) detect sensitive features (only if X_test available)

    #SENSITIVE features in the X_text 

    '''
    in Marcos File:
    features": {
    "gender_cv": { "sensitive": true },
    "age_cv": { "sensitive": true },
    "disability_cv": { "sensitive": true },
    "nationality_cv": { "sensitive": true },
    "education_cv_encoded": { "sensitive": true }
    '''
    sensitive_features = {}
    if X_test is not None: #sensitive features from X_test
        for feat, props in config.get('features', {}).items():
            if props.get("sensitive", False):
                corrected_feat = binning_mapping.get(feat, feat) if binning_mapping else feat #correct name if changed with binning col name
                if corrected_feat in X_test.columns:
                    sensitive_features[feat] = corrected_feat

    if X_test is None:
        print("\n[INFO] X_test not provided: skipping metrics which require feature columns.")
    else:
        print(f"\nSelected sensitive features: {list(sensitive_features.keys())}") #['gender_cv', 'age_cv', 'disability_cv', 'nationality_cv', 'education_cv_encoded']
        print(f"\nColumns available after preprocessing: {X_test.columns.tolist()}")
        

    # 8) normalize targets/predictions (if provided) -> 1D array
    y_true = to_series_1d(y_true) if y_true is not None else None 
    y_pred = to_series_1d(y_pred) if y_pred is not None else None


##############
    # 9) sanitize sensitive columns for stable grouping
    if X_test is not None:
        for _, col in sensitive_features.items():
            if col in X_test.columns:
                X_test[col] = sanitize_sensitive_col(X_test[col]) #clean sensitive features
        if X_original is not None:
            X_original = X_original.reset_index(drop=True)

    # 10) load plugin metrics from .json file            ex. "plugins.fairness.demographic_parity"
    plugins = load_plugins(config.get('plugins', []), config=config) 

    #ADDED
    raw_plugin_outputs = {} 

    # 11) run all metrics with capability checks 
    all_results = {}
    skipped = {}  # metric_name -> reason

    for plugin in plugins:
        print(f"\nRunning {plugin.name}")

        # Declare/assume dependencies (plugin can override these flags)
        needs_X = requires(plugin, 'needs_X', True)
        needs_y_true = requires(plugin, 'needs_y_true', False)
        needs_y_pred = requires(plugin, 'needs_y_pred', False)

        # Global pre-checks
        if needs_X and X_test is None:
            skipped[plugin.name] = "requires X_test"
            print(f"  [SKIP] {plugin.name}: requires X_test.")
            continue
        if needs_y_true and y_true is None:
            skipped[plugin.name] = "requires y_true"
            print(f"  [SKIP] {plugin.name}: requires y_true.")
            continue
        if needs_y_pred and y_pred is None:
            skipped[plugin.name] = "requires y_pred"
            print(f"  [SKIP] {plugin.name}: requires y_pred.")
            continue

        plugin_results = {}

        # Choose dataset passed to plugin
        # (Mutual Information needs original one-hot columns; others use post-processed)
        current_X = X_original if (X_original is not None and plugin.name == "Mutual Information") else X_test #X_test is the DS always passed

        # Case: metrics that require all sensitive features together
        if requires(plugin, 'requires_all_sensitive_features', False):
            if not sensitive_features:
                skipped[plugin.name] = "requires sensitive features on X_test"
                print(f"  [SKIP] {plugin.name}: no sensitive features available.")
                continue  ###sensitive_attributes required.... [gender_cv', 'age_cv_binned', 'disability_cv', 'nationality_cv', 'education_cv_encoded']
                #among others

            sensitive_cols = list(sensitive_features.values())
            score = plugin.evaluate(
                y_true=y_true,
                y_pred=y_pred,
                X_test=current_X,
                sensitive_features=sensitive_cols
            )

            '''if isinstance(metric_result, dict):
                metric_result["metric_description"] = getattr(plugin, "description", "")'''

            #ADDED - save in all results without being combined
            metric_key = plugin.__class__.__module__.split(".")[-1]

            #SAVE RAW OUTPUT (before wrapping)
            raw_plugin_outputs[metric_key] = score


            plugin_results["__combined__"] = score
            
            metric_key = plugin.__class__.__module__.split(".")[-1] #of this: plugin.right.metric, add only the module
            all_results[metric_key] = plugin_results
            continue

        # Case: per-feature metrics (and maybe conditional variable)
        if requires(plugin, 'needs_sensitive_feature', False):
            if not sensitive_features:
                skipped[plugin.name] = "requires sensitive features on X_test"
                print(f"  [SKIP] {plugin.name}: no sensitive features available.")
                continue

            for _, feat_column in sensitive_features.items():
                print(f"  Computing for feature: {feat_column}")

                if requires(plugin, 'needs_conditional_variable', False):
                    try:
                        cond_var = get_config_value(
                            config, "conditional_statistical_parity", "conditional_variable", required=True
                        )
                        metric_result = plugin.evaluate(y_true, y_pred, current_X, feat_column, cond_var)
                    except ValueError as e:
                        print(f"  [SKIP feature] {e}")
                        continue
                else:
                    # Some fairness plugins expect a list; others a single name.
                    # If your plugin expects a single column, adapt here accordingly.
                    metric_result = plugin.evaluate(y_true, y_pred, current_X, [feat_column]) #got to check which

                '''# avoid double dictionary if the plugin already delivers a dict
                if isinstance(metric_result, dict) and len(metric_result) == 1 and feat_column in metric_result:
                    inner_result = metric_result[feat_column]
                    if isinstance(inner_result, dict):
                        inner_result["metric_description"] = getattr(plugin, "description", "")
                    plugin_results[feat_column] = inner_result
                else:
                    if isinstance(metric_result, dict):
                        metric_result["metric_description"] = getattr(plugin, "description", "")
                    plugin_results[feat_column] = metric_result'''

                #ADDED
                #avoids double dictionary if the plugin already delivers a dict. 
                if isinstance(metric_result, dict) and len(metric_result) == 1 and feat_column in metric_result:
                    plugin_results[feat_column] = metric_result[feat_column]
                else:
                    plugin_results[feat_column] = metric_result

        #Case: global metrics (no sensitive features loop - (global) - for new metrics)
        else:
            score = plugin.evaluate(y_true, y_pred, current_X)
            plugin_results["(global)"] = score

            metric_key = plugin.__class__.__module__.split(".")[-1] #of this: plugin.right.metric, add only the module
            all_results[metric_key] = plugin_results
            continue

        metric_key = plugin.__class__.__module__.split(".")[-1] #of this: plugin.right.metric, add only the module
        all_results[metric_key] = plugin_results

    # 12) Capability report (skipped metrics) 
    if skipped:
        print("\n=== SKIPPED METRICS (capability report) ===")
        for m, why in skipped.items():
            print(f"  - {m}: {why}")

    # 13) Print results
    print_all_results(all_results)

    # 14) Save results to CSV 
    save_pretty_print(all_results, out_txt="run_results/all_results.csv")

    # 15) Save results to JSON 
    json_out = Path("run_results/all_results.json")
    json_out.parent.mkdir(parents=True, exist_ok=True)

    #ADDED - save in all_results.json only results without __combined__
    flattened_results = flatten_combined_results(all_results)

    json_out.write_text(
    json.dumps(flattened_results, indent=2, default=str, ensure_ascii=False),
    encoding="utf-8"
    )

    #ADDED - detect plugin schemas and save it in results/result_schemas.json
    schemas = detect_all_result_schemas(all_results)
    schema_out = Path("run_results/result_schemas.json") 
    schema_out.parent.mkdir(parents=True, exist_ok=True)
    schema_out.write_text(
        json.dumps(schemas, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"[INFO] Saved UI schemas to: {schema_out.resolve()}")

if __name__ == "__main__":
    main()
