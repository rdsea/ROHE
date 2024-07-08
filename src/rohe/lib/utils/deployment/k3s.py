from kubernetes import client, config


def get_kube_client(host="localhost", port=6443, key=None):
    if host == "localhost":
        configuration = config.load_kube_config()
        return client.AppsV1Api(), client.CoreV1Api()

    configuration = client.Configuration()
    # example_key = 'ZXlKaGJHY2lPaUpTVXpJMU5pSXNJbXRwWkNJNklqQnNkMFJuU0VSUFdERm1TREU0WDBoeFZEUkZiRVV6V0hBM2JqTTJUMHhtYUdVemNXWk5NVkZzWnpBaWZRLmV5SnBjM01pT2lKcmRXSmxjbTVsZEdWekwzTmxjblpwWTJWaFkyTnZkVzUwSWl3aWEzVmlaWEp1WlhSbGN5NXBieTl6WlhKMmFXTmxZV05qYjNWdWRDOXVZVzFsYzNCaFkyVWlPaUprWldaaGRXeDBJaXdpYTNWaVpYSnVaWFJsY3k1cGJ5OXpaWEoyYVdObFlXTmpiM1Z1ZEM5elpXTnlaWFF1Ym1GdFpTSTZJblJ5YVc1bmRYbGxiaTEwYjJ0bGJpMTJORFZ6WnlJc0ltdDFZbVZ5Ym1WMFpYTXVhVzh2YzJWeWRtbGpaV0ZqWTI5MWJuUXZjMlZ5ZG1salpTMWhZMk52ZFc1MExtNWhiV1VpT2lKMGNtbHVaM1Y1Wlc0aUxDSnJkV0psY201bGRHVnpMbWx2TDNObGNuWnBZMlZoWTJOdmRXNTBMM05sY25acFkyVXRZV05qYjNWdWRDNTFhV1FpT2lKa1pUSTVPR001WVMwMk5qSTFMVFJoTmpndE9UbGxNUzFsTlRJNVlXRmpPR00wWm1NaUxDSnpkV0lpT2lKemVYTjBaVzA2YzJWeWRtbGpaV0ZqWTI5MWJuUTZaR1ZtWVhWc2REcDBjbWx1WjNWNVpXNGlmUS5UN0pVZkpXRDlIMTA3SDRGM3pJS3BNRFIwX3J0eUpzS056V2VpTU9NMzFES1FaSkVyNURGdmk2ZnBHSWFUNHJYTHpfdG1LVTg4YTVSclpPeU1FdlZMdnBQdlNKTWlISW5YMm1KNC1NbnE2Ui04SDMyNXdCV1pNTVQ2dmpoUDk5cWdRbkc1U1NaSVQwTDA2UTlDT0VOWlpHa0x3VHBYbFBVTXVRMGJLRnhaaHFQYTBKZzBXZHBzcmppelQzcUxOMVFKdDUzUkRjVWtqc2NiOGVqMW13OUR1REFPT3ptSGkzUExyaGdzOEZLU2JhQ3ZtRnhkQ05oTEczamVPYzFrVmhBVkpiVUQ0YUQ2YnkyaDZPclgwTkhZMENVSE82ZEs2WWpsUDZoZzFUbWZsOXNPR2xYcmNVOFRGSUJLUUcxbDd3bmFfT2M0ak1wVkxLNWdncVZSUFdUY2c='
    configuration.api_key["authorization"] = key
    # example_host_port = 'http://standalone-master-k3s.cs.aalto.fi:6443'
    configuration.host = str(host) + ":" + str(port)
    k3s_client = client.ApiClient(configuration)
    return client.AppsV1Api(k3s_client), client.CoreV1Api(k3s_client)


def convert_boolean(dict_obj):
    # Convert string boolean to True/False value
    for key in dict_obj:
        try:
            if isinstance(dict_obj[key], str):
                if isinstance(eval(dict_obj[key]), bool):
                    dict_obj[key] = eval(dict_obj[key])
        except Exception as e:
            print("Unable to convert some attribute:", e)
        return dict_obj
    return None
