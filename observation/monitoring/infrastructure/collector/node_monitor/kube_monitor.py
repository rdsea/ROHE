import kubernetes.client
from kubernetes.client.rest import ApiException
configuration = kubernetes.client.Configuration()
configuration.api_key['authorization'] = 'ZXlKaGJHY2lPaUpTVXpJMU5pSXNJbXRwWkNJNklqQnNkMFJuU0VSUFdERm1TREU0WDBoeFZEUkZiRVV6V0hBM2JqTTJUMHhtYUdVemNXWk5NVkZzWnpBaWZRLmV5SnBjM01pT2lKcmRXSmxjbTVsZEdWekwzTmxjblpwWTJWaFkyTnZkVzUwSWl3aWEzVmlaWEp1WlhSbGN5NXBieTl6WlhKMmFXTmxZV05qYjNWdWRDOXVZVzFsYzNCaFkyVWlPaUprWldaaGRXeDBJaXdpYTNWaVpYSnVaWFJsY3k1cGJ5OXpaWEoyYVdObFlXTmpiM1Z1ZEM5elpXTnlaWFF1Ym1GdFpTSTZJblJ5YVc1bmRYbGxiaTEwYjJ0bGJpMTJORFZ6WnlJc0ltdDFZbVZ5Ym1WMFpYTXVhVzh2YzJWeWRtbGpaV0ZqWTI5MWJuUXZjMlZ5ZG1salpTMWhZMk52ZFc1MExtNWhiV1VpT2lKMGNtbHVaM1Y1Wlc0aUxDSnJkV0psY201bGRHVnpMbWx2TDNObGNuWnBZMlZoWTJOdmRXNTBMM05sY25acFkyVXRZV05qYjNWdWRDNTFhV1FpT2lKa1pUSTVPR001WVMwMk5qSTFMVFJoTmpndE9UbGxNUzFsTlRJNVlXRmpPR00wWm1NaUxDSnpkV0lpT2lKemVYTjBaVzA2YzJWeWRtbGpaV0ZqWTI5MWJuUTZaR1ZtWVhWc2REcDBjbWx1WjNWNVpXNGlmUS5UN0pVZkpXRDlIMTA3SDRGM3pJS3BNRFIwX3J0eUpzS056V2VpTU9NMzFES1FaSkVyNURGdmk2ZnBHSWFUNHJYTHpfdG1LVTg4YTVSclpPeU1FdlZMdnBQdlNKTWlISW5YMm1KNC1NbnE2Ui04SDMyNXdCV1pNTVQ2dmpoUDk5cWdRbkc1U1NaSVQwTDA2UTlDT0VOWlpHa0x3VHBYbFBVTXVRMGJLRnhaaHFQYTBKZzBXZHBzcmppelQzcUxOMVFKdDUzUkRjVWtqc2NiOGVqMW13OUR1REFPT3ptSGkzUExyaGdzOEZLU2JhQ3ZtRnhkQ05oTEczamVPYzFrVmhBVkpiVUQ0YUQ2YnkyaDZPclgwTkhZMENVSE82ZEs2WWpsUDZoZzFUbWZsOXNPR2xYcmNVOFRGSUJLUUcxbDd3bmFfT2M0ak1wVkxLNWdncVZSUFdUY2c='
configuration.host = "http://edge-k3s-r1.cs.aalto.fi:6443"
with kubernetes.client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = kubernetes.client.WellKnownApi(api_client)
    
    try:
        api_response = api_instance.get_service_account_issuer_open_id_configuration()
        print(api_response)
    except ApiException as e:
        print("Exception when calling WellKnownApi->get_service_account_issuer_open_id_configuration: %s\n" % e)