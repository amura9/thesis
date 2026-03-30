def get_config_value(config, section, key, default=None, required=False):
    """
    Retrieve a key's value from a specific section of the configuration.

    :param config: The configuration dictionary.
    :param section: The section name (e.g., "k_anonymity").
    :param key: The key to look up (e.g., "sensitive_features").
    :param default: The default value to return if the key is not found.
    :param required: If True, raise an exception when the key is missing.
    :return: The value found in the config, or `default` if not found (and not required).
    """
    try:
        value = config.get(section, {}).get(key, default)
        if required and value is None:
            raise ValueError(
                f"The key '{key}' in section '{section}' is required but missing from the configuration."
            )
        return value
    except KeyError:
        if required:
            raise ValueError(f"The section '{section}' is missing from the configuration.")
        return default
