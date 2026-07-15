"""Tests for validate_inputs.py, focused on missing/invalid inputs.
"""
import importlib

import pytest

vi = importlib.import_module("validate_inputs")


@pytest.fixture
def github_env(tmp_path, monkeypatch):
    """Provide a fake $GITHUB_ENV file and repo/ref env vars.

    validate_algorithm_config_file() appends DOCKER_TAG to $GITHUB_ENV on the
    success paths, so the file must exist. Returns the file for assertions.
    """
    env_file = tmp_path / "github_env"
    env_file.write_text("")
    monkeypatch.setenv("GITHUB_ENV", str(env_file))
    monkeypatch.setenv("GITHUB_REPOSITORY", "OWNER/Repo")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    return env_file


def _write_config(tmp_path, contents):
    cfg = tmp_path / "algorithm_config.yml"
    cfg.write_text(contents)
    return str(cfg)


def test_missing_config_path_fails(monkeypatch, github_env):
    monkeypatch.setenv("CONFIG_FILE_PATH", "")
    monkeypatch.setenv("DOCKERFILE_PATH", "Dockerfile")
    assert vi.validate_algorithm_config_file() is False


def test_nonexistent_config_file_fails(monkeypatch, github_env):
    monkeypatch.setenv("CONFIG_FILE_PATH", "/does/not/exist.yml")
    monkeypatch.setenv("DOCKERFILE_PATH", "Dockerfile")
    assert vi.validate_algorithm_config_file() is False


def test_invalid_yaml_fails(tmp_path, monkeypatch, github_env):
    cfg = _write_config(tmp_path, "key: [unterminated\n")
    monkeypatch.setenv("CONFIG_FILE_PATH", cfg)
    monkeypatch.setenv("DOCKERFILE_PATH", "Dockerfile")
    assert vi.validate_algorithm_config_file() is False


def test_dockerfile_and_container_url_are_mutually_exclusive(tmp_path, monkeypatch, github_env):
    cfg = _write_config(tmp_path, "algorithm_container_url: ghcr.io/x/y:1\n")
    monkeypatch.setenv("CONFIG_FILE_PATH", cfg)
    monkeypatch.setenv("DOCKERFILE_PATH", "Dockerfile")  # both provided -> invalid
    assert vi.validate_algorithm_config_file() is False


def test_neither_dockerfile_nor_container_url_fails(tmp_path, monkeypatch, github_env):
    cfg = _write_config(tmp_path, "algorithm_name: demo\n")
    monkeypatch.setenv("CONFIG_FILE_PATH", cfg)
    monkeypatch.setenv("DOCKERFILE_PATH", "")
    assert vi.validate_algorithm_config_file() is False


def test_empty_container_url_key_does_not_crash(tmp_path, monkeypatch, github_env):
    # `algorithm_container_url:` with no value parses to None; must not raise.
    cfg = _write_config(tmp_path, "algorithm_container_url:\n")
    monkeypatch.setenv("CONFIG_FILE_PATH", cfg)
    monkeypatch.setenv("DOCKERFILE_PATH", "")
    # No container and no dockerfile -> rejected, but cleanly (no AttributeError).
    assert vi.validate_algorithm_config_file() is False


def test_dockerfile_only_passes_and_sets_docker_tag(tmp_path, monkeypatch, github_env):
    cfg = _write_config(tmp_path, "algorithm_name: demo\n")
    monkeypatch.setenv("CONFIG_FILE_PATH", cfg)
    monkeypatch.setenv("DOCKERFILE_PATH", "Dockerfile")
    assert vi.validate_algorithm_config_file() is True
    env = github_env.read_text()
    # image name comes from the algorithm name (owner namespace), ref is the tag
    assert "DOCKER_TAG=ghcr.io/owner/demo:main" in env
    # CWL file name is derived from the algorithm name and branch
    assert "CWL_WORKFLOW_FILE_NAME=process_demo_main.cwl" in env


def test_container_url_only_passes_and_sets_docker_tag(tmp_path, monkeypatch, github_env):
    cfg = _write_config(
        tmp_path,
        "algorithm_name: demo\nalgorithm_container_url: ghcr.io/x/y:1.2.3\n",
    )
    monkeypatch.setenv("CONFIG_FILE_PATH", cfg)
    monkeypatch.setenv("DOCKERFILE_PATH", "")
    assert vi.validate_algorithm_config_file() is True
    env = github_env.read_text()
    assert "DOCKER_TAG=ghcr.io/x/y:1.2.3" in env
    assert "CWL_WORKFLOW_FILE_NAME=process_demo_main.cwl" in env


def test_missing_algorithm_name_fails(tmp_path, monkeypatch, github_env):
    cfg = _write_config(tmp_path, "algorithm_description: no name here\n")
    monkeypatch.setenv("CONFIG_FILE_PATH", cfg)
    monkeypatch.setenv("DOCKERFILE_PATH", "Dockerfile")
    assert vi.validate_algorithm_config_file() is False
