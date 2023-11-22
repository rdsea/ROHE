import argparse, requests, json, logging

headers = {
    'Content-Type': 'application/json'
}

# Specify parameter:
# --app: Application Name
# --run: Run/experiment name, id
# --user: User ID, who registrate the application
# --url: Link to the registration service
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Node Monitoring")
    parser.add_argument('--app', help='application name', default="test")
    parser.add_argument('--run', help='application name', default="experiment1")
    parser.add_argument('--user', help='application name', default="aaltosea1")
    parser.add_argument('--url', help='registration url', default="http://localhost:5010/agent")

    args = parser.parse_args()
    url = args.url

    res_data = {"appName": args.app}
    res_data["runID"] = args.run
    res_data["userID"] = args.user
    res_data["command"] = "delete"

    logging.debug(res_data)
    # Send delete application command to registration service
    response = requests.request("POST", url, headers=headers, data=json.dumps(res_data))
    logging.debug(response.json())

    

        