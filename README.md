# OGC Application Package Generator
GitHub action to build & deploy OGC application packages to the MAAP.

This action builds a CWL workflow file and commits it to the client repository's working branch under `cwl_workflows/` by default. A docker image will be built from the user-provided Dockerfile then pushed to the client repository's GitHub Container Registry.

The CWL workflow file generated is validated using [cwltool](https://pypi.org/project/cwltool/) and [ogc_ap_validator](https://pypi.org/project/ogc-ap-validator/) to ensure it is compliant with CWL and OGC best practices.

### Inputs:

| Parameter        | Description           | Required | Default | Type  | Example |
|:-------------|:---------------------|:-----:|:-----:|:-----:|:-------|
| config-file-path | Path to the algorithm config file | Yes | - | string | `my_algo_repo/algorithm_config.yml` |
| cwl-workflow-dir | Directory to which generated CWL workflow files will be written | No | `cwl_workflows/` | string | `cwl_workflows/` |
| dockerfile-path | Path to Dockerfile that will be used to build the docker image | Yes | - | string | `my_algo_repo/Dockerfile` |
| deploy-app-pack | Flag indicating whether or not to deploy the application package to a registry | No | false | Boolean | `true` |
| app-pack-register-endpoint | URL to send registration request to | No | - | string | `https://api.uat.maap-project.org/api/ogc/processes` |
| MAAP token | The MAAP token used in the application package deployment request. The sample workflow shows this parameter being accessed from the client repository's secrets store. | No | - | string | `PGT-XXXX` or `JWT-XXXX` |

The algorithm config file is a yml file that contains fields required to generate the CWL workflow that is compliant with CWL and OGC best practices. See `data/algorithm_config.yml` as an example.

See `data/process_sardem-sarsen_mlucas_nasa-ogc.cwl` for a sample CWL workflow file that was generated using this action.

## Set your action up

To use this action, create a GitHub workflow file in your repository:

`touch .github/workflows/my_workflow.yml`

Copy the sample workflow below into `my_workflow.yml`:

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
        uses: actions/checkout@v4

      - name: Use OGC App Pack Generator Action
        uses: MAAP-Project/ogc-app-pack-generator@main
        with:
          # Specify action inputs
          config-file-path: my_algo_repo/algorithm_config.yml
          dockerfile-path: my_algo_repo/Dockerfile
          deploy-app-pack: true
          app-pack-register-endpoint: https://api.uat.maap-project.org/api/ogc/processes
        env:
          # MAAP token is required to deploy the algorithm to the MAAP
          MAAP_TOKEN: ${{ secrets.MAAP_TOKEN_MLUCAS }}
```

Update the following action inputs:

- `config-file-path`: Update this to the path to your config yml file. See `data/algorithm_config.yml` for an example.
- `dockerfile-path`: Update this to the path to your Dockerfile.
- `app-pack-register-endpoint`: Update this to the URL the registration request will be sent to.

If deploying the application package to the MAAP, you will need to provide your MAAP token. Retrieve the token from your MAAP profile and add it as a secret to your GitHub repository. Be sure to name this token `MAAP_TOKEN`.

> [!NOTE]
> The workflow is currently set to trigger on a push to any branch. To limit workflow triggering to a specific branch, replace `'**'` with your branch name.

## Working locally
If you want to build a CWL workflow file outside the GitHub action, you may do so by cloning this repository and running the following command:

`python build_cwl_workflow.py --config-file-path data/algorithm_config.yml`

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

Inputs may also be provided as a yml file, for example:

`cwltool cwl_workflows/process.cwl data/input.yml`

See `data/input.yml` for a sample yml input file.

