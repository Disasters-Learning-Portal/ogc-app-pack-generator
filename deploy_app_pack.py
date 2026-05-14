'''
Deploy application package
'''
import yaml
import requests
import argparse
import os
import json
import sys


def submit_request(url, data, headers):
    """
    Submit a request to the application package registry. A POST request is attempted first. If the response to the POST
    is an HTTP status code of 409, this indicates the process already exists then a PUT request will be submitted,
    overwriting the existing process.
    
    Args:
        url (str): The registry URL.
        data (dict): The request body, containing the process CWL URL or path.
        headers (dict): The request headers.

    Returns:
        bool: True if the request (POST or fallback PUT) completes successfully, False otherwise.
    """
    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        print(response.text)
        response.raise_for_status()
        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            try:
                r = e.response.json()
                print(r.get("detail", None))

                process_id = r["additionalProperties"]["processID"]
                url = f"{url}/{process_id}"

                print("Submitting PUT request to modify existing process...")
                response = requests.put(url, data=json.dumps(data), headers=headers)
                response.raise_for_status()
                print(f'Response: {response.text}')
                return True

            except (KeyError, requests.exceptions.RequestException, ValueError) as e:
                print(f"Failed to submit request: {e}")
                return False
        else:
            print(f"HTTP error: {e}")
            return False

    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def deploy_app_pack(process_cwl_url, app_pack_registry, template_file):
    """
    Builds a request to deploy an application package process CWL to a specified registry.

    Args:
        process_cwl_url (str): The URL or path to the process CWL.
        app_pack_register_endpoint (str): The URL of the application package registry to which the process will be deployed.
        template_file (str): The path to the YAML template file containing the deployment request.

    Returns:
        None
        
    Raises:
        ValueError: Raises a ValueError if the MAAP token is not set. This token is required to deploy processes.
    """
    with open(template_file, 'r') as f:
        data = yaml.safe_load(f)

    if data.get("executionUnit", {}).get("href"):
        data["executionUnit"]["href"] = process_cwl_url

    maap_token = os.getenv('MAAP_TOKEN')
    if not maap_token:
        raise ValueError("Environment variable `MAAP_TOKEN` is not set.")

    headers = {
        'proxy-ticket': maap_token,
        'Content-Type': 'application/json'
    }

    return submit_request(app_pack_registry, data, headers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy application package.")
    parser.add_argument("--process-cwl-url", type=str, help="URL or path to process CWL describing application package to deploy", required=True)
    parser.add_argument("--app-pack-register-endpoint", type=str, help="Application package registry to deploy application package to.")
    parser.add_argument("--app-pack-template-file", type=str, default="templates/ogcapppkg.yml", help="Path to the OGC API processes compliant OGC application package schema template.")

    args = parser.parse_args()
    print(f"Parameters: \n \
    Process CWL: {args.process_cwl_url} \n \
    Application package register endpoint: {args.app_pack_register_endpoint} \n \
    Template file: {args.app_pack_template_file}")

    with open(args.app_pack_template_file, 'r') as f:
        data = yaml.safe_load(f)
        
    if not deploy_app_pack(process_cwl_url=args.process_cwl_url, app_pack_registry=args.app_pack_register_endpoint, template_file=args.app_pack_template_file):
        sys.exit(1)
