def update_config(config, path):
    if not path:
        raise "Path not found"
    config.metadata["datasource"]["config"]["path"] = path
    return config


