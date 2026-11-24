"""Test another version of dedupe_latest without touching the real one: pytest --candidate FILE"""

import importlib.util

import pytest

from pipeline import transform


def pytest_addoption(parser):
    parser.addoption("--candidate", help="a Python file whose dedupe_latest replaces the real one for this run")


@pytest.fixture(autouse=True)
def use_candidate(request, monkeypatch):
    """With --candidate FILE, every test that calls transform.dedupe_latest runs FILE's version."""
    path = request.config.getoption("--candidate")
    if path:
        spec = importlib.util.spec_from_file_location("candidate", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        monkeypatch.setattr(transform, "dedupe_latest", module.dedupe_latest)
