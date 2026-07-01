# Contributing

Thank you for your interest in improving the OGC Application Package Generator!

## Reporting Issues

- Search [existing issues](https://github.com/MAAP-Project/ogc-app-pack-generator/issues)
  before opening a new one.
- For bugs, include the failing workflow configuration, the generated CWL (if
  any), and the relevant action logs.

## Development Setup

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Generate a CWL workflow from the sample config and validate it, mirroring what
the action and CI do:

```bash
DOCKER_TAG=ghcr.io/example/repo:test \
GIT_COMMIT_HASH=local \
WORKFLOW_FILE_NAME=process_test.cwl \
python3 build_cwl_workflow.py \
  --config-file data/algorithm_config.yml \
  --cwl-template-file templates/process.v1_2.cwl

cwltool --validate --strict cwl_workflows/process_test.cwl
ap-validator --detail all cwl_workflows/process_test.cwl
```
