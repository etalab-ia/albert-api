import logging

import pytest
import requests


def pytest_addoption(parser):
    parser.addoption("--base-url", action="store", default="http://localhost:8080/v1")
    parser.addoption("--api-key", action="store", default="EMPTY")


@pytest.fixture(autouse=True)
def setup_logging(caplog):
    caplog.set_level(logging.DEBUG)


@pytest.fixture
def args(request):
    return {
        "base_url": request.config.getoption("--base-url"),
        "api_key": request.config.getoption("--api-key"),
    }


@pytest.fixture
def session(args):
    s = requests.session()
    s.headers = {"Authorization": f"Bearer {args['api_key']}"}
    return s
