from kubernetes import client, config


def get_kube_client(host="localhost", port=6443, key=None):
    if host == "localhost":
        configuration = config.load_kube_config()
        return client.AppsV1Api(), client.CoreV1Api()

    configuration = client.Configuration()
    configuration.api_key["authorization"] = key
    configuration.host = str(host) + ":" + str(port)
    k3s_client = client.ApiClient(configuration)
    return client.AppsV1Api(k3s_client), client.CoreV1Api(k3s_client)


def convert_boolean(dict_obj):
    # Convert string boolean to True/False value
    _BOOL_MAP = {"true": True, "false": False}
    for key in dict_obj:
        if isinstance(dict_obj[key], str) and dict_obj[key].lower() in _BOOL_MAP:
            dict_obj[key] = _BOOL_MAP[dict_obj[key].lower()]
    return dict_obj
