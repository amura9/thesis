from core.plugin_loader import discover_all_plugins

plugins = discover_all_plugins(base_package="plugins")

print(f"Discovered {len(plugins)} plugins:")
for p in plugins:
    print("-", p.__class__.__module__ + "." + p.__class__.__name__)
