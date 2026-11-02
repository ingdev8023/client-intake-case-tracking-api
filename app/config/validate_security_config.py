def validate_security_config(key):
               
    if not key:
        raise ValueError("Config Error missing key")

    if len(key.encode("utf-8")) < 32:
        raise ValueError("Config Error short key")