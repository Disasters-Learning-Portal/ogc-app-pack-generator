#!/usr/bin/env python3
"""
This script validates the inputs for the OGC Application Package Builder action.
It checks for required inputs, validates file paths, and ensures proper input combinations.
"""

import os
import sys
import re
from urllib.parse import urlparse
from pathlib import Path

def validate_algorithm_config_file():
    """Validate algorithm config YAML file."""
    config_path = os.environ.get('CONFIG_FILE_PATH', '')
    if not config_path:
        print("ERROR: algorithm-configuration-path is required.")
        return False
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: Algorithm configuration file provided is not valid YAML: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Cannot read algorithm configuration file: {e}")
        return False

    # If algorithm_container_url is provided in yaml file, there won't be a need to build a container.
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        algorithm_container_url = (config.get('algorithm_container_url') or '').strip()
        dockerfile_path = os.environ.get('DOCKERFILE_PATH', '')
        has_container = bool(algorithm_container_url)
        has_dockerfile_path = bool(dockerfile_path)

        if has_container and has_dockerfile_path:
            print("ERROR: algorithm_container_url is specified in the algorithm configuration file, but dockerfile-path is also provided. Only one may be provided.")
            print(f"  algorithm-container-url: {algorithm_container_url}")
            print(f"  dockerfile-path: {dockerfile_path}")
            return False
        
        if not has_container and not has_dockerfile_path:
            print("ERROR: algorithm_container_url or dockerfile-path must be provided.")
            return False

        if has_container:
            print(f"Setting DOCKER_TAG environment variable to {algorithm_container_url}")
            with open(os.environ['GITHUB_ENV'], 'a') as env_file:
                env_file.write(f"DOCKER_TAG={algorithm_container_url}\n")

        else:
            github_repo = os.environ.get('GITHUB_REPOSITORY', '').lower()
            github_ref_name = os.environ.get('GITHUB_REF_NAME', '')
            github_ref_name_clean = github_ref_name.replace('/', '_')
            docker_tag = f"ghcr.io/{github_repo}:{github_ref_name_clean}"
            print(f"Setting DOCKER_TAG environment variable to {docker_tag}")
            with open(os.environ['GITHUB_ENV'], 'a') as env_file:
                env_file.write(f"DOCKER_TAG={docker_tag}\n")
    
    return True


def main():    
    validations = [
        ("Algorithm configuration file", validate_algorithm_config_file)
    ]
    
    for validation_name, validation_func in validations:
        print(f"Running {validation_name} validation...")
        if not validation_func():
            print(f"{validation_name} validation failed")
            sys.exit(1)
        print(f"{validation_name} validation passed")
    
    print("🎉 All validations passed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main() 