"""Tests for deploy_app_pack.py"""
import importlib
from unittest.mock import MagicMock, patch

import pytest
import requests

dep = importlib.import_module("deploy_app_pack")


@pytest.fixture
def template(tmp_path):
    tmpl = tmp_path / "ogcapppkg.yml"
    tmpl.write_text("executionUnit:\n  href: PLACEHOLDER\n")
    return str(tmpl)


def test_missing_maap_token_raises(monkeypatch, template):
    monkeypatch.delenv("MAAP_TOKEN", raising=False)
    with pytest.raises(ValueError, match="MAAP_TOKEN"):
        dep.deploy_app_pack("http://cwl", "http://registry", template)


def test_deploy_posts_with_token_header(monkeypatch, template):
    monkeypatch.setenv("MAAP_TOKEN", "PGT-abc")
    resp = MagicMock(text="ok")
    resp.raise_for_status.return_value = None
    with patch.object(dep.requests, "post", return_value=resp) as post:
        assert dep.deploy_app_pack("http://cwl", "http://registry", template) is True
    # Token is sent as the proxy-ticket header
    assert post.call_args.kwargs["headers"]["proxy-ticket"] == "PGT-abc"


def test_deploy_conflict_falls_back_to_put(monkeypatch, template):
    monkeypatch.setenv("MAAP_TOKEN", "PGT-abc")

    # POST raises a 409 HTTPError carrying the existing process id
    conflict = MagicMock(status_code=409)
    conflict.json.return_value = {
        "detail": "already exists",
        "additionalProperties": {"processID": "proc-1"},
    }
    post_resp = MagicMock(text="conflict")
    post_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=conflict)

    put_resp = MagicMock(text="updated")
    put_resp.raise_for_status.return_value = None

    with patch.object(dep.requests, "post", return_value=post_resp), \
         patch.object(dep.requests, "put", return_value=put_resp) as put:
        assert dep.deploy_app_pack("http://cwl", "http://registry", template) is True
    # PUT targets the existing process id
    assert put.call_args.args[0] == "http://registry/proc-1"


def test_deploy_non_409_error_returns_false(monkeypatch, template):
    monkeypatch.setenv("MAAP_TOKEN", "PGT-abc")
    server_error = MagicMock(status_code=500)
    post_resp = MagicMock(text="boom")
    post_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=server_error)
    with patch.object(dep.requests, "post", return_value=post_resp):
        assert dep.deploy_app_pack("http://cwl", "http://registry", template) is False
