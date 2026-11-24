"""Shared fixtures: a mock API on a free port, started for the whole test session."""

import threading

import pytest
import requests

import mock_api


@pytest.fixture(scope="session")
def api_url():
    """Start the mock API with `Retry-After: 0` so a test never waits, and stop it afterwards."""
    server = mock_api.make_server(port=0, retry_after=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture
def get_page(api_url):
    """Ask for one page, trying again after a 429 or a 500 (at most 5 tries), and return the answer."""

    def get(**params):
        for _ in range(5):
            response = requests.get(f"{api_url}/order-lines", params=params, timeout=10)
            if response.status_code not in (429, 500):
                return response
        return response

    return get
