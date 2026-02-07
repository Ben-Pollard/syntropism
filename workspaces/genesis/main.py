import json
import os

import requests


def main():
    if not os.path.exists("env.json"):
        print("Error: env.json not found")
        return

    with open("env.json") as f:
        env = json.load(f)

    print(f"Genesis Agent {env['agent_id']} active.")
    print(f"Balance: {env['credits']}")

    service_url = os.getenv("SYSTEM_SERVICE_URL")
    if service_url:
        try:
            res = requests.get(f"{service_url}/economic/balance/{env['agent_id']}")
            print(f"API Check: {res.json()}")
        except Exception as e:
            print(f"API Error: {e}")

if __name__ == "__main__":
    main()
