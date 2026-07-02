# OGC Application Package Generator
GitHub action to build & deploy Open Geospatial Consortium (OGC) application packages to the MAAP. 

This action builds a CWL workflow file from an input YAML file. The CWL workflow file is validated using `cwltool` and `ogc_ap_validator` to ensure it is compliant with CWL and OGC best practices. It is then committed to the client repository's working branch under `cwl_workflows/`. A docker image will be built from the user-specified Dockerfile and pushed to the client repository's GitHub Container Registry.

See `data/algorithm_config.yml` for a sample YAML input file.

The CWL workflow file generated is validated using [cwltool](https://pypi.org/project/cwltool/) and [ogc_ap_validator](https://pypi.org/project/ogc-ap-validator/) to ensure it is compliant with CWL and OGC best practices.

> [!IMPORTANT]
> This action **writes to your repository**. On each run it commits the generated CWL workflow file to `cwl_workflows/` on the triggering branch. It also builds and pushes a Docker image to your repository's GitHub Container Registry (when `dockerfile-path` is set). Because of this, the calling workflow must grant `contents: write` and `packages: write` permissions (see the sample below), and the action must run on a branch it is allowed to push to. Do not use this action on untrusted pull requests.

## Set your action up

1. To use this action, create a GitHub workflow file in your repository:

`touch .github/workflows/my_workflow.yml`

2. Copy the sample workflow below into `my_workflow.yml` and be sure to change the action inputs if needed.

```
on:
  push:
    branches:
      - '**'
jobs:
  build_app_pack:
    runs-on: ubuntu-latest

    permissions:
      contents: write
      packages: write

    steps:
      - name: Checkout repo content
        uses: actions/checkout@v6

      - name: Use OGC App Pack Generator Action
        uses: MAAP-Project/ogc-app-pack-generator@1.0.0
        with:
          # Specify action inputs
          algorithm-configuration-path: my_algo_repo/algorithm_config.yml
          dockerfile-path: my_algo_repo/Dockerfile
          deploy-app-pack: true
          app-pack-register-endpoint: https://api.uat.maap-project.org/api/ogc/processes
        env:
          # MAAP token is required to deploy the process
          MAAP_TOKEN: ${{ secrets.MAAP_TOKEN }}
```

3. Update the following action inputs:

- `algorithm-configuration-path`: Update this to the path to your config YAML file. See `data/algorithm_config.yml` for an example.
- `dockerfile-path`: Update this to the path to your Dockerfile.
- `app-pack-register-endpoint`: Update this to the URL the registration request will be sent to.

4. Create a GitHub repository secret named `MAAP_TOKEN` and set its value to the value of your MAAP token. See GitHub instructions [here](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets#creating-secrets-for-a-repository).

## Action inputs

| Parameter        | Description           | Required | Default | Type  | Example |
|:-------------|:---------------------|:-----:|:-----:|:-----:|:-------|
| algorithm-configuration-path | Path to the algorithm config file | Yes | - | string | `my_algo_repo/algorithm_config.yml` |
| cwl-workflow-dir | Directory to which generated CWL workflow files will be written | No | `cwl_workflows` | string | `cwl_workflows` |
| dockerfile-path | Path to Dockerfile that will be used to build the docker image | Yes | - | string | `my_algo_repo/Dockerfile` |
| deploy-app-pack | Flag indicating whether or not to deploy the application package to a registry | No | false | Boolean | `true` |
| app-pack-register-endpoint | URL to send registration request to | No | - | string | `https://api.uat.maap-project.org/api/ogc/processes` |
| MAAP token | The MAAP token used in the application package deployment request. The sample workflow shows this parameter being accessed from the client repository's secrets store. | No | - | string | `PGT-XXXX` or `JWT-XXXX` |

The algorithm config file is a YAML file that contains fields required to generate the CWL workflow that is compliant with CWL and OGC best practices. See `data/algorithm_config.yml` as an example.

See `data/process_sardem-sarsen_mlucas_nasa-ogc.cwl` for a sample CWL workflow file that was generated using this action.

> [!NOTE]
> The workflow is currently set to trigger on a push to any branch. To limit workflow triggering to a specific branch, replace `'**'` with your branch name.

## Working locally
If you want to build a CWL workflow file outside the GitHub action, you may do so by cloning this repository and running the following command:

`python build_cwl_workflow.py --config-file data/algorithm_config.yml`

This will create `cwl_workflows/process.cwl`.

To run CWL validation, install `cwltool` and run with the validation flag:
```
pip install cwltool &&
cwltool --validate cwl_workflows/process.cwl
```

To run OGC validation, install `ogc_ap_validator` and run the validation:
```
pip install ogc_ap_validator &&
ap-validator cwl_workflows/process.cwl
```

The OGC validator has an option to return the validation results in json format by adding the `--format` flag. For example:
```
ap-validator --format json cwl_workflows/process.cwl
```

Here is a sample response indicating the CWL is OGC-compliant:
```
{
  "valid": true,
  "issues": [],
  "requirements": {}
}
```

Here is a sample response indicating the CWL is NOT OGC-compliant:
```
{
  "valid": false,
  "issues": [
    {
      "type": "error",
      "message": "Missing element for Workflow 'sardem-sarsen': doc",
      "req": "req-9"
    }
  ],
  "requirements": {
    "req-9": "The Application Package CWL Workflow class SHALL contain the following elements: Identifier ('id'); Title ('label'); Abstract ('doc')."
  }
}
```

> [!NOTE]
> If running this script outside of the GitHub action, it will only generate the CWL and not the Docker image. Users will have to update the Docker requirements in the generated CWL to point to an existing image if they wish to execute the workflow.

### Run CWL workflow
Sample command to execute a CWL workflow (be sure to provide any required inputs):

`cwltool cwl_workflows/process.cwl --input_1 "input1" --input_2 "input2"`

Inputs may also be provided as a YAML file, for example:

`cwltool cwl_workflows/process.cwl data/input.yml`

See `data/input.yml` for a sample YAML input file.

## Running the tests

From the repository root, install the test dependencies and run the suite with
[pytest](https://pypi.org/project/pytest/):

```
pip install -r tests/requirements-dev.txt
pytest
```

