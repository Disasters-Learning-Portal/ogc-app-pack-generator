'''
Builds a CWL workflow from a yml input file.

Inputs:

--config-file-path (required)
yml file containing algorithm information that will be parsed to create the CWL workflow file.
See data/algorithm_config.yml for an example. This example contains the information
needed to create a CWL workflow that is compliant with OGC and CWL best practices.

--cwl-workflow-dir (optional)
The directory the CWL workflow files will be written to. If not provided, the default is `cwl_workflows`
and the directory will be created if it does not exist.

--cwl-template-file (optional)
Template file to use when creating the workflow file. Currently, only CWL v1.2 is supported and
will be used by default if not provided.

Outputs:

CWL v1.2 workflow file. Workflow file names will have the process name and version appended to
them. For example, if the process name is `myProcess` and its version is `main`, the resulting 
workflow file will be named `process_myProcess_main.cwl`.

Sample execution:
build_cwl_workflow.py --config-file-path data/algorithm_config.yml --cwl-workflow-dir cwl_workflows

'''

import yaml
import argparse
import os
from datetime import date
import logging


def process_value(target, value):
    """
    Processes algorithm config value to ensure expected format for targeted OGC CWL field.

    Args:
        target: Target OGC CWL field.
        value: Algorithm config value to be processed.

    Returns:
        str: Processed algorithm config value.
    """
    match target[-1]:
        case "s:version":
            if isinstance(value, str):
                return value.replace("/", "_")
            return value
        case _:
            return value


def set_path_value(workflow, path, value):
    """
    Assign value at given path within workflow template.

    Args:
        workflow (dict): The workflow template (nested dictionary) where the value will be set.
        path (list): A list of keys that specifies the location within the workflow template where the value should be assigned.
        value: Value to assign to the specified path in the workflow template.

    Returns:
        None
    """
    for key in path[:-1]:
        workflow = workflow[key]
    workflow[path[-1]] = value


def add_input_default(input_type, input_default):
    """
    Add default value for input.

    Args:
        input_type (str): The type of the input (e.g. "Directory", "string").
        input_default (str): The default value to assign to the input.

    Returns:
        dict or str: Returns a dict for special types and a string for primitive types.
    """
    match input_type:
        case "Directory" | "File":
            return {"class": input_type, "path": input_default}
        case _:
            return input_default
        
            

def yaml_to_cwl(config_file, cwl_workflow_dir, template_file):
    """
    Create a CWL file compliant with CWL and OGC best practices from a yml input file.

    Args:
        config_file (str): Path to input yml file.
        cwl_workflow_dir (str): Path to workflow output directory.
        template_file (str): Path to CWL template file to use when building CWL file.

    Return:
        None
    """
    # Load workflow configuration YML file
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    # Load CWL template file
    with open(template_file, 'r') as f:
        workflow = yaml.safe_load(f)

    # Create output directory if nonexistent
    if not os.path.exists(cwl_workflow_dir):
        os.makedirs(cwl_workflow_dir)


    # Attempt to retrieve information required to be compliant with OGC and CWL v1.2 best practices
    #
    # See CWL v1.2 docs here: https://www.commonwl.org/v1.2/Workflow.html#Workflow 
    # See OGC docs here: https://docs.ogc.org/bp/20-089r1.html#toc24
    
    # Define mapping of yml input file fields to OGC and CWL generic fields
    OGC_CWL_KEY_MAP = {
                "algorithm_description": [("$graph", 0, "doc")],
                "algorithm_name": [("$graph", 0, "label"), ("$graph", 0, "id")],
                "algorithm_version": [("s:version",)],
                "author": [("s:author", 0, "s:name")],
                "citation": [("s:citation",)],
                "code_repository": [("s:codeRepository",)],
                "contributor": [("s:contributor", 0, "s:name")],
                "cores_min": [("$graph", 1, "requirements", "ResourceRequirement", "coresMin")],
                "keywords": [("s:keywords",)],
                "license": [("s:license",)],
                "outdir_max": [("$graph", 1, "requirements", "ResourceRequirement", "outdirMax")],
                "ram_min": [("$graph", 1, "requirements", "ResourceRequirement", "ramMin")],
                "release_notes": [("s:releaseNotes",)],
                "run_command": [("$graph", 1, "baseCommand")]
              }
    
    for key in OGC_CWL_KEY_MAP:
        targets = OGC_CWL_KEY_MAP[key]
        if key in config:
            for target in targets:
                value = process_value(target, config[key])
                set_path_value(workflow, target, value)
        else:
            logging.warning(f'Expected key `{key}` not found in algorithm config.')


    # Handle inputs and outputs separately since the same information is used
    # differently across several fields.
    workflow_inputs = []
    step_inputs = []
    process_inputs = []
    
    workflow_outputs = []
    step_outputs = []
    process_outputs = []

    input_param_names = set()

    for input in config.get("inputs", []):
        input_name = input.get("name")

        # Check for input parameter name uniqueness
        if input_name not in input_param_names:
            input_param_names.add(input_name)
        else:
            raise ValueError(f"Duplicate input parameter name '{input_name}'. Input parameters must be unique.")

        input_type = input.get("type")
        input_doc = input.get("doc")
        input_label = input.get("label")
        input_default = input.get("default")

        if input_name is None or input_type is None:
            logging.warning("Expected both input type and input name to be provided for input.")
        
        # Workflow inputs
        workflow_tmp = {input_name: {
            "doc": input_doc,
            "label": input_label,
            "type": input_type
        }}
        workflow_inputs.append(workflow_tmp)

        # Process inputs
        process_tmp = {input_name: {
            "type": input_type,
            "inputBinding": {
                "position": len(process_inputs) + 1,
                "prefix": f"--{input_name}"
        }}}
        
        # If default value was provided, add that in
        if input_default is not None:
            workflow_tmp[input_name]["default"] = add_input_default(input_type, input_default)
            process_tmp[input_name]["default"] = add_input_default(input_type, input_default)

        process_inputs.append(process_tmp)

        # Step inputs
        step_tmp = {input_name: input_name}
        step_inputs.append(step_tmp)

    # Need to merge the lists of dicts to properly format output
    workflow_inputs = {k: v for d in workflow_inputs for k, v in d.items()}
    process_inputs = {k: v for d in process_inputs for k, v in d.items()}
    step_inputs = {k: v for d in step_inputs for k, v in d.items()}

    workflow["$graph"][0]["inputs"] = workflow_inputs
    workflow["$graph"][1]["inputs"] = process_inputs
    workflow["$graph"][0]["steps"]["process"]["in"] = step_inputs

    for output in config.get("outputs", []):
        output_name = output.get("name")
        output_type = output.get("type")
        #output_doc = output.get("doc")
        #output_label = output.get("label")

        if output_name is None or output_type is None:
            logging.warning("Expected output name and output type to be specified.")

        # Workflow outputs
        tmp = {output_name: {
            "type": output_type,
            "outputSource": f"process/outputs_result"
        }}
        workflow_outputs.append(tmp)

        # Process outputs
        tmp = {f"outputs_result" :{
            "outputBinding": {
                "glob": f"./output*"
            },
            "type": output_type
            }
        }
        process_outputs.append(tmp)

        # Step outputs
        step_outputs.append("outputs_result")


    workflow_outputs = {k: v for d in workflow_outputs for k, v in d.items()}
    process_outputs = {k: v for d in process_outputs for k, v in d.items()}
    
    workflow["$graph"][0]["outputs"] = workflow_outputs
    workflow["$graph"][1]["outputs"] = process_outputs
    workflow["$graph"][0]["steps"]["process"]["out"] = step_outputs

    # Add information that is required to be compliant with OGC and CWL best practices
    # that should not be in the yml input file
    workflow["s:dateCreated"] = date.today()
    workflow["s:softwareVersion"] = "1.0.0"
    workflow["$graph"][1]["requirements"]["DockerRequirement"]["dockerPull"] = os.getenv('DOCKER_TAG')

    # Add information that is not required to be compliant with OGC and CWL best practices and should not be in the yml input file,
    # yet is desired by MAAP.
    workflow["s:commitHash"] = os.getenv('GIT_COMMIT_HASH')

    # Dump data to workflow file
    workflow_file = os.path.join(cwl_workflow_dir, os.getenv('CWL_WORKFLOW_FILE_NAME', 'process.cwl'))
    with open(workflow_file, 'w') as f:
        yaml.dump(workflow, f, default_flow_style=False, sort_keys=False)

    print(f"CWL workflow saved to {workflow_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert yml configuration to CWL workflow.")
    parser.add_argument("--config-file-path", type=str, help="Path to the input workflow YML configuration file.", required=True)
    parser.add_argument("--cwl-workflow-dir", type=str, default="cwl_workflows", help="Directory workflow files will be written to. If not provided, `workflows` will be used as default. If the `workflows` directory does not exist, it will be created.")
    parser.add_argument("--cwl-template-file", type=str, default="templates/process.v1_2.cwl", help="Path to the CWL template file. Default template used is compliant with CWL v1.2.")

    args = parser.parse_args()
    print("Building CWL workflow file...\nInput file: {} \nWorkflow output directory: {} \nCWL template file: {}".format(args.config_file_path, args.cwl_workflow_dir, args.cwl_template_file))
    yaml_to_cwl(args.config_file_path, args.cwl_workflow_dir, args.cwl_template_file)
