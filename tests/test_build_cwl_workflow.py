"""Tests for build_cwl_workflow.py"""
import importlib
import subprocess
import sys
import textwrap

import pytest

b = importlib.import_module("build_cwl_workflow")

TEMPLATE = "templates/process.v1_2.cwl"


def test_missing_config_flag_exits_nonzero():
    # argparse enforces required=True at the CLI even though the action YAML cannot.
    r = subprocess.run(
        [sys.executable, "build_cwl_workflow.py"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert "--config-file" in r.stderr


def test_duplicate_input_names_raise(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yml"
    cfg.write_text(textwrap.dedent(
        """
        algorithm_name: demo
        inputs:
          - {name: x, type: string}
          - {name: x, type: string}
        outputs:
          - {name: out, type: Directory}
        """
    ))
    monkeypatch.setenv("DOCKER_TAG", "ghcr.io/x/y:test")
    with pytest.raises(ValueError, match="Duplicate input"):
        b.yaml_to_cwl(str(cfg), str(tmp_path / "out"), TEMPLATE)


def test_valid_config_writes_cwl(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yml"
    cfg.write_text(textwrap.dedent(
        """
        algorithm_name: demo
        algorithm_description: a demo
        inputs:
          - {name: a, type: string}
        outputs:
          - {name: out, type: Directory}
        """
    ))
    out_dir = tmp_path / "out"
    monkeypatch.setenv("DOCKER_TAG", "ghcr.io/x/y:test")
    monkeypatch.setenv("CWL_WORKFLOW_FILE_NAME", "process_demo.cwl")
    b.yaml_to_cwl(str(cfg), str(out_dir), TEMPLATE)
    assert (out_dir / "process_demo.cwl").exists()
