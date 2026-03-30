#core/load_config.py
import json

def load_config(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

#passata con CLI